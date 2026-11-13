"""Serialization regression tests; no changes to financial formulas."""
import pandas as pd
import re
import plotly.graph_objects as go

from src.animated_plotly import figure_payload


def test_numeric_arrays_remain_exact_and_can_be_interpolated():
    fig = go.Figure(go.Bar(x=['Enero', 'Febrero'], y=pd.Series([7725000., 5498000.])))
    payload = figure_payload(fig, 'Ingresos', 'ingresos')
    trace = payload['figure']['data'][0]
    assert trace['y'] == [7725000., 5498000.]
    assert payload['duration'] == 550
    assert payload['figure']['layout']['uirevision'] == 'ingresos'
    assert 'uid' not in fig.data[0].to_plotly_json()
    assert re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*', trace['uid'])


def test_equilibrium_marker_and_negative_values_are_not_modified():
    fig = go.Figure(go.Scatter(x=[19.39634261295796], y=[-2141322.3936404195]))
    trace = figure_payload(fig, 'Equilibrio', 'equilibrio')['figure']['data'][0]
    assert trace['x'] == [19.39634261295796]
    assert trace['y'] == [-2141322.3936404195]
    assert trace['line']['simplify'] is False


def test_donut_values_and_colors_are_preserved():
    fig = go.Figure(go.Pie(labels=['Audio', 'Periféricos'], values=pd.Series([2312000, 0]),
                           marker_colors=['#655FC2', '#283958'], sort=False))
    trace = figure_payload(fig, 'Categorías', 'categorias')['figure']['data'][0]
    assert trace['values'] == [2312000, 0]
    assert trace['marker']['colors'] == ['#655FC2', '#283958']
    assert trace['sort'] is False
