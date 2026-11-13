from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from src.calculos import cargar_datos, resumen
from src.filtros import filtrar_ventas, productos_disponibles

BASE = Path(__file__).resolve().parents[1]


def test_filtro_segmento_y_periodo():
    v, f = cargar_datos(BASE / 'data')
    for mes in sorted(v.mes.unique()):
        partes = [filtrar_ventas(v, [mes], c) for c in v.categoria.unique()]
        assert sum(p.ingresos.sum() for p in partes) == resumen(v, f, [mes])['ingresos']
        for c in v.categoria.unique():
            assert productos_disponibles(v, c) == sorted(v.loc[v.categoria.eq(c), 'producto'].unique())
    assert filtrar_ventas(v, ['2026-01'], producto='inexistente').empty


def test_fijos_independientes_del_segmento():
    v, f = cargar_datos(BASE / 'data')
    seleccion = filtrar_ventas(v, ['2026-02'], categoria=v.categoria.iloc[0])
    assert seleccion.costos_variables.sum() == (seleccion.cantidad * seleccion.costo_variable_unitario_cop).sum()
    assert resumen(v, f, ['2026-02'])['costos_fijos'] == f.loc[f.mes.eq('2026-02'), 'valor_cop'].sum()


def test_interaccion_filtros_navegacion_y_reset():
    app = AppTest.from_file(str(BASE / 'app.py')).run(timeout=30)
    assert not app.exception
    app.selectbox(key='periodo').select('Febrero').run()
    app.selectbox(key='categoria').select('Audio').run()
    opciones = app.selectbox(key='producto').options
    assert 'Teclado mecánico' not in opciones
    app.selectbox(key='producto').select(opciones[1]).run()
    app.selectbox(key='categoria').select('Periféricos').run()
    assert app.selectbox(key='producto').value == 'Todos los productos'
    for vista in ['Ventas', 'Costos', 'Rentabilidad', 'Resumen general']:
        app.radio(key='vista').set_value(vista).run()
        assert not app.exception
        assert app.selectbox(key='periodo').value == 'Febrero'
    app.button[0].click().run()
    assert app.selectbox(key='periodo').value == 'Todos los meses'
    assert app.selectbox(key='categoria').value == 'Todas las categorías'
    assert app.selectbox(key='producto').value == 'Todos los productos'
    assert not app.exception
