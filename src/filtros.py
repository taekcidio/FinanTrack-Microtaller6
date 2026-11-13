"""Filtros comerciales: nunca asignan costos fijos a un segmento."""
import pandas as pd

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


def nombre_mes(mes: str) -> str:
    return MESES[int(mes[5:7]) - 1]


def filtrar_ventas(ventas: pd.DataFrame, meses: list[str], categoria=None, producto=None):
    mascara = ventas.mes.isin(meses)
    if categoria is not None:
        mascara &= ventas.categoria.eq(categoria)
    if producto is not None:
        mascara &= ventas.producto.eq(producto)
    return ventas.loc[mascara].copy()


def productos_disponibles(ventas: pd.DataFrame, categoria=None):
    base = ventas if categoria is None else ventas[ventas.categoria.eq(categoria)]
    return sorted(base.producto.unique().tolist())
