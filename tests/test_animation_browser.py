"""Opt-in real-browser checks: set FINANTRACK_BROWSER_URL for a running app.

Requires Playwright as a development tool, not an application dependency.
"""
import os
from pathlib import Path

import pytest

URL = os.environ.get('FINANTRACK_BROWSER_URL')
pytestmark = pytest.mark.skipif(not URL, reason='Set FINANTRACK_BROWSER_URL for browser validation')


def test_real_transitions_and_reduced_motion():
    sync_api = pytest.importorskip('playwright.sync_api')
    from src.calculos import cargar_datos, resumen

    root = Path(__file__).resolve().parents[1]
    executable = next((root / '.venv/playwright-browsers').glob('chromium-*/chrome-win64/chrome.exe'), None)
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_function("document.querySelectorAll('.finantrack-plot[data-revision]').length===4", timeout=60000)

        def settle():
            page.wait_for_function("Array.from(document.querySelectorAll('.finantrack-plot')).every(g=>g.dataset.pending==='false' && !g.dataset.error)")

        def select(index, value):
            page.get_by_role('combobox').nth(index).click()
            page.get_by_role('option', name=value, exact=True).click()

        select(0, 'Enero')
        page.wait_for_function("Array.from(document.querySelectorAll('.finantrack-plot')).every(g=>g.dataset.revision==='2')")
        settle()
        # Capture actual intermediate numbers and DOM identities at each RAF.
        page.evaluate("""() => {
          window.savedGraphs = Array.from(document.querySelectorAll('.finantrack-plot'));
          window.samples = []; window.sampling = true;
          const sample = time => {
            window.samples.push({time, charts: window.savedGraphs.map(g => ({
              active: g.dataset.animating, y: Array.from(g.data?.[0]?.y || []),
              values: Array.from(g.data?.[0]?.values || []),
              marker: g.data?.[2]?.x?.[0], height: g.getBoundingClientRect().height
            }))});
            if (window.sampling) requestAnimationFrame(sample);
          }; requestAnimationFrame(sample);
        }""")
        select(0, 'Febrero')
        page.wait_for_function("Array.from(document.querySelectorAll('.finantrack-plot')).every(g=>g.dataset.revision==='3')")
        settle()
        page.evaluate('window.sampling=false')
        assert page.evaluate("window.savedGraphs.every((g,i)=>g===document.querySelectorAll('.finantrack-plot')[i])")
        samples = page.evaluate('window.samples')
        for index in range(4):
            active = [s['charts'][index] for s in samples if s['charts'][index]['active'] == 'true']
            assert len(active) >= 2, (index, len(active))
            field = 'values' if index == 2 else 'y'
            assert len({str(s[field]) for s in active}) > 2, (index, active)
            assert len({s['height'] for s in active}) == 1
        markers = [s['charts'][3]['marker'] for s in samples if s['charts'][3]['active'] == 'true']
        assert len(set(markers)) > 2
        values = page.locator('.finantrack-plot').evaluate_all('(els)=>els.map(g=>g.data)')
        v, f = cargar_datos(root / 'data')
        r = resumen(v, f, ['2026-02'])
        assert values[0][0]['y'] == [r['ingresos']]
        assert values[0][1]['y'] == [r['costos_totales']]
        assert values[1][0]['y'] == [r['utilidad_operativa']]
        assert sum(values[2][0]['values']) == r['ingresos']
        assert values[3][2]['x'][0] == pytest.approx(r['costo_fijo_promedio'] / r['margen_unitario'])

        before = page.locator('.finantrack-plot').nth(2).evaluate('(g)=>({labels:g.data[0].labels,colors:g.data[0].marker.colors})')
        select(1, 'Audio')
        page.wait_for_function("document.querySelectorAll('.finantrack-plot')[2].dataset.revision==='4'")
        settle()
        after = page.locator('.finantrack-plot').nth(2).evaluate('(g)=>({labels:g.data[0].labels,colors:g.data[0].marker.colors})')
        assert before == after
        assert page.locator('.finantrack-plot').nth(0).get_attribute('data-revision') == '3'
        select(2, 'Audífonos con cable')
        page.wait_for_function("document.querySelectorAll('.finantrack-plot')[2].dataset.revision==='5'")
        settle()
        selected = v[(v.mes == '2026-02') & (v.producto == 'Audífonos con cable')]
        assert page.locator('.finantrack-plot').nth(2).evaluate('(g)=>g.data[0].values.reduce((a,b)=>a+b,0)') == selected.ingresos.sum()
        # Hover and legend remain genuine Plotly interactions after animation.
        # Plotly's transparent drag rectangle intentionally overlays SVG bars.
        page.locator('.finantrack-plot').nth(0).locator('.bars .point path').first.hover(force=True)
        page.wait_for_selector('.hoverlayer .hovertext')
        first = page.locator('.finantrack-plot').nth(0)
        first.locator('.legendtoggle').first.click()
        page.wait_for_function("document.querySelector('.finantrack-plot').data[0].visible==='legendonly'")
        first.locator('.legendtoggle').first.click()
        # Reduced motion: no transient active animation state on any frame.
        page.emulate_media(reduced_motion='reduce')
        page.evaluate("window.motionStates=[]; window.mo=new MutationObserver(ms=>{for(const m of ms)if(m.attributeName==='data-animating')window.motionStates.push(m.target.dataset.animating)}); window.savedGraphs.forEach(g=>window.mo.observe(g,{attributes:true}))")
        select(0, 'Marzo')
        page.wait_for_function("document.querySelector('.finantrack-plot').dataset.revision==='4'")
        settle()
        assert 'true' not in page.evaluate('window.motionStates')
        # All existing views still render and retain filter state.
        for label, title in [('Ventas', 'Distribución por categoría · selección'), ('Costos', 'Evolución de costos'), ('Rentabilidad', 'Ingresos vs. costos'), ('Resumen', 'Ingresos vs. costos')]:
            page.get_by_text(label, exact=True).last.click()
            page.wait_for_function('(title)=>document.querySelector(".finantrack-plot")?.getAttribute("aria-label")===title', arg=title)
            page.wait_for_function('(count)=>document.querySelectorAll(".finantrack-plot[data-revision]").length===count', arg=3 if label == 'Rentabilidad' else 4)
            settle()
        # Rapid input changes must settle on the latest values, not stale frames.
        page.emulate_media(reduced_motion='no-preference')
        select(0, 'Abril')
        select(0, 'Mayo')
        page.wait_for_function("document.querySelector('.finantrack-plot').data[0].y?.[0]===7670000")
        settle()
        assert not page.locator('.finantrack-plot[data-error]').count()
        assert not errors
        browser.close()
