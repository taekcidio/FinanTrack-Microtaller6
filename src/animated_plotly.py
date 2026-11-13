"""Persistent CCv2 Plotly renderer; all financial calculations remain in Python."""
import json
import base64
import hashlib
from pathlib import Path

import numpy as np
import plotly.io as pio
from plotly.offline import get_plotlyjs
import streamlit as st


# Inline CCv2 module: the library comes from the installed Plotly package,
# not a CDN. Streamlit serves/caches this JS module once for all chart instances.
_RENDERER = st.components.v2.component(
    'finantrack_animated_plotly',
    html='<div class="finantrack-plot" role="group"></div>',
    js=get_plotlyjs() + '\n' + Path(__file__).with_name('animated_plotly.js').read_text(encoding='utf-8'),
    isolate_styles=False,
)


def figure_payload(fig, title, chart_id):
    # Plotly 6 encodes numpy arrays as typed binary buffers. Browser-side
    # interpolation needs ordinary numeric arrays, so normalize before JSON.
    def normalize(value):
        if isinstance(value, dict):
            if 'bdata' in value and 'dtype' in value:
                array = np.frombuffer(base64.b64decode(value['bdata']), dtype=value['dtype'])
                if value.get('shape'):
                    array = array.reshape(tuple(int(n) for n in value['shape'].split(',')))
                return array.tolist()
            return {k: normalize(v) for k, v in value.items()}
        if hasattr(value, 'tolist'):
            return normalize(value.tolist())
        if isinstance(value, (list, tuple)):
            return [normalize(v) for v in value]
        return value

    figure = json.loads(pio.to_json(normalize(fig.to_dict()), validate=False))
    figure['layout'].pop('template', None)
    figure['layout']['uirevision'] = chart_id
    figure['layout']['transition'] = {'duration': 0}
    # Plotly uses trace UIDs inside CSS selectors during react/purge.
    # Titles contain spaces, punctuation and accents, so never use them as UIDs.
    safe_id = hashlib.sha256(chart_id.encode('utf-8')).hexdigest()[:16]
    for index, trace in enumerate(figure['data']):
        trace['uid'] = f'trace-{safe_id}-{index}'
        if trace.get('type') == 'scatter':
            trace.setdefault('line', {})['simplify'] = False
    return {'figure': figure, 'title': title, 'chartId': chart_id, 'duration': 550}


def animated_plotly(fig, *, title, chart_id, key, height):
    return _RENDERER(
        data=figure_payload(fig, title, chart_id),
        key=key, height=height, width='stretch',
    )
