// Real browser interpolation on a persistent Plotly graph, never Python frames.
const instances = new WeakMap();
const clone = value => JSON.parse(JSON.stringify(value));
const numeric = values => Array.isArray(values) && values.every(Number.isFinite);
const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

function resample(values, length) {
  if (!values?.length) return Array(length).fill(0);
  if (length === 1) return [values[0]];
  return Array.from({length}, (_, i) => {
    const at = i * (values.length - 1) / (length - 1);
    const lo = Math.floor(at), hi = Math.ceil(at);
    return values[lo] + (values[hi] - values[lo]) * (at - lo);
  });
}

function interpolate(previous, target, progress) {
  const next = clone(target);
  next.forEach((trace, i) => {
    const old = previous[i];
    for (const field of ['x', 'y', 'values']) {
      const values = trace[field];
      if (!numeric(values)) continue;
      const oldValues = old?.[field];
      let start;
      const labels = field === 'values' ? trace.labels : field === 'y' ? trace.x : trace.y;
      const oldLabels = field === 'values' ? old?.labels : field === 'y' ? old?.x : old?.y;
      // Match categorical bars and slices by label, regardless of sort/filter.
      if (Array.isArray(labels) && labels.some(v => typeof v === 'string') && Array.isArray(oldLabels)) {
        const lookup = new Map(oldLabels.map((label, j) => [label, oldValues?.[j] ?? 0]));
        start = labels.map(label => lookup.get(label) ?? (labels.length === 1 && oldLabels.length === 1 ? oldValues?.[0] ?? 0 : 0));
      } else {
        start = resample(numeric(oldValues) ? oldValues : [], values.length);
      }
      trace[field] = values.map((v, j) => start[j] + (v - start[j]) * progress);
    }
  });
  return next;
}

function compatible(a, b) {
  return a?.length === b.length && a.every((t, i) => t.type === b[i].type);
}

function numericRanges(figure) {
  const ranges = {};
  for (const field of ['x', 'y']) {
    const arrays = figure.data.map(trace => trace[field]);
    if (!arrays.length || !arrays.every(numeric)) continue;
    const values = arrays.flat();
    if (!values.length) continue;
    const lo = Math.min(0, ...values), hi = Math.max(0, ...values);
    const pad = (hi - lo || 1) * 0.07;
    ranges[`${field}axis`] = [lo < 0 ? lo - pad : 0, hi + pad];
  }
  return ranges;
}

export default function(component) {
  const {parentElement, data} = component;
  const gd = parentElement.querySelector('.finantrack-plot');
  if (!gd) return;
  let state = instances.get(gd);
  if (!state) {
    state = {revision: 0, signature: null, queue: Promise.resolve(), disposed: false, current: null};
    instances.set(gd, state);
    state.motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    state.observer = new ResizeObserver(() => {
      if (gd._fullLayout && !state.disposed) window.Plotly.Plots.resize(gd);
    });
    state.observer.observe(gd);
    state.onMotion = () => {
      if (state.motion.matches) state.skipMotion = true;
    };
    state.motion.addEventListener('change', state.onMotion);
  }
  gd.style.width = '100%';
  gd.style.height = `${data.figure.layout.height}px`;
  gd.setAttribute('aria-label', data.title);
  const signature = JSON.stringify(data.figure);
  if (signature !== state.signature) {
    state.signature = signature;
    gd.dataset.pending = 'true';
    const revision = ++state.revision;
    const target = clone(data.figure);
    const finalRanges = numericRanges(target);
    const chartId = data.chartId;
    state.queue = state.queue.catch(() => {}).then(async () => {
      if (revision !== state.revision || state.disposed) return;
      const Plotly = window.Plotly;
      const config = {displayModeBar: false, responsive: true, displaylogo: false};
      // Plotly.react cannot reliably migrate a pie-only layout to Cartesian
      // axes in every version. Different charts start clean in the same card;
      // numerical updates of the same chart always keep the existing plot.
      if (state.current && (state.chartId !== chartId || !compatible(state.current, target.data))) {
        Plotly.purge(gd);
        state.current = null;
      }
      const previous = state.current;
      const animate = previous && compatible(previous, target.data) && state.chartId === chartId && !state.motion.matches;
      for (const [axis, range] of Object.entries(finalRanges)) {
        // Keep a stable scale when filtering down; expand only if necessary.
        // This also avoids a costly axes/layout redraw on every animation tick.
        const old = state.chartId === chartId ? gd._fullLayout?.[axis]?.range : null;
        const stable = old ? [Math.min(old[0], range[0]), Math.max(old[1], range[1])] : range;
        target.layout[axis] = {...target.layout[axis], range: stable, autorange: false};
      }
      state.chartId = chartId;
      state.skipMotion = false;
      gd.dataset.animating = 'false';
      if (animate) {
        // React reconciles labels/styles once. A RAF clock then interpolates
        // numeric trace arrays via restyle on the SAME graph (including pies,
        // for which Plotly.animate does not offer a smooth interpolation).
        const start = interpolate(previous, target.data, 0);
        const layout = clone(target.layout);
        await Plotly.react(gd, start, layout, config);
        gd.dataset.animating = 'true';
        const began = performance.now();
        while (revision === state.revision && !state.disposed) {
          const now = await new Promise(resolve => requestAnimationFrame(resolve));
          if (revision !== state.revision || state.disposed) return;
          const t = state.motion.matches || state.skipMotion ? 1 : Math.min(1, (now - began) / data.duration);
          const current = interpolate(previous, target.data, ease(t));
          const update = {};
          for (const field of ['x', 'y', 'values']) {
            if (current.some(trace => numeric(trace[field]))) {
              update[field] = current.map(trace => trace[field] ?? null);
            }
          }
          await Plotly.restyle(gd, update);
          state.current = current;
          if (t === 1) break;
        }
      }
      if (revision !== state.revision || state.disposed) return;
      await Plotly.react(gd, clone(target.data), clone(target.layout), config);
      state.current = clone(target.data);
      delete gd.dataset.error;
      gd.dataset.animating = 'false';
      gd.dataset.revision = String(revision);
      gd.dataset.pending = 'false';
    }).catch(error => {
      gd.dataset.animating = 'false';
      gd.dataset.pending = 'false';
      gd.dataset.error = String(error);
      console.error('FinanTrack Plotly update failed', error);
      // Retain the existing graph and show a readable error, never a blank card.
      gd.setAttribute('aria-label', `${data.title}: no se pudo actualizar el gráfico`);
    });
  }
  return () => {
    state.disposed = true;
    state.revision++;
    state.observer.disconnect();
    state.motion.removeEventListener('change', state.onMotion);
    window.Plotly.purge(gd);
    instances.delete(gd);
  };
}
