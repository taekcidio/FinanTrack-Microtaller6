"""Cálculos financieros de FinanTrack; los costos fijos se contabilizan una vez por mes/concepto."""
from __future__ import annotations
import math
from pathlib import Path
import pandas as pd

VENTAS_COL = ['id_venta','fecha','producto','categoria','cantidad','precio_unitario_cop','costo_variable_unitario_cop']
FIJOS_COL = ['mes','concepto','valor_cop']


def cargar_datos(base: str | Path = 'data') -> tuple[pd.DataFrame, pd.DataFrame]:
    base = Path(base)
    ventas = pd.read_csv(base / 'ventas.csv', encoding='utf-8-sig')
    fijos = pd.read_csv(base / 'costos_fijos.csv', encoding='utf-8-sig')
    for df, cols, name in [(ventas, VENTAS_COL, 'ventas.csv'), (fijos, FIJOS_COL, 'costos_fijos.csv')]:
        faltan = set(cols) - set(df.columns)
        if faltan:
            raise ValueError(f'{name}: faltan columnas: {", ".join(sorted(faltan))}')
        if df.empty:
            raise ValueError(f'{name} no tiene registros')
    ventas['fecha'] = pd.to_datetime(ventas['fecha'], errors='raise')
    ventas['mes'] = ventas['fecha'].dt.strftime('%Y-%m')
    for col in ['cantidad','precio_unitario_cop','costo_variable_unitario_cop']:
        ventas[col] = pd.to_numeric(ventas[col], errors='raise')
    fijos['valor_cop'] = pd.to_numeric(fijos['valor_cop'], errors='raise')
    if ventas[['cantidad','precio_unitario_cop','costo_variable_unitario_cop']].isna().any().any() or fijos['valor_cop'].isna().any():
        raise ValueError('Hay importes o cantidades vacíos')
    if (ventas[['cantidad','precio_unitario_cop','costo_variable_unitario_cop']] < 0).any().any() or (fijos['valor_cop'] < 0).any():
        raise ValueError('Los valores de cantidades, precios y costos no pueden ser negativos')
    if ventas['id_venta'].duplicated().any() or fijos.duplicated(['mes','concepto']).any():
        raise ValueError('Se encontraron identificadores de venta o conceptos mensuales duplicados')
    ventas['ingresos'] = ventas['cantidad'] * ventas['precio_unitario_cop']
    ventas['costos_variables'] = ventas['cantidad'] * ventas['costo_variable_unitario_cop']
    ventas['contribucion'] = ventas['ingresos'] - ventas['costos_variables']
    return ventas, fijos


def resumen(ventas: pd.DataFrame, fijos: pd.DataFrame, meses: list[str] | None = None) -> dict:
    if meses is None:
        meses = sorted(set(ventas['mes'].tolist()) | set(fijos['mes'].tolist()))
    vv = ventas[ventas['mes'].isin(meses)]
    ff = fijos[fijos['mes'].isin(meses)]
    ingresos = float(vv['ingresos'].sum())
    variables = float(vv['costos_variables'].sum())
    costo_fijo = float(ff['valor_cop'].sum())
    unidades = float(vv['cantidad'].sum())
    contribucion = ingresos - variables
    utilidad = contribucion - costo_fijo
    meses_cantidad = len(meses)
    margen_unitario = contribucion / unidades if unidades > 0 else 0
    equilibrio = math.ceil((costo_fijo / meses_cantidad) / margen_unitario) if margen_unitario > 0 and meses_cantidad > 0 else None
    return dict(ingresos=ingresos, costos_variables=variables, costos_fijos=costo_fijo,
                costos_totales=variables + costo_fijo, contribucion=contribucion,
                utilidad_operativa=utilidad, margen_operativo=100*utilidad/ingresos if ingresos else None,
                unidades=unidades, equilibrio_mensual=equilibrio, margen_unitario=margen_unitario,
                precio_unitario=ingresos/unidades if unidades else 0, variable_unitario=variables/unidades if unidades else 0,
                costo_fijo_promedio=costo_fijo/meses_cantidad if meses_cantidad else 0,
                meses=meses_cantidad)


def mensual(ventas: pd.DataFrame, fijos: pd.DataFrame, meses: list[str]) -> pd.DataFrame:
    filas = []
    for m in meses:
        r = resumen(ventas, fijos, [m])
        filas.append(dict(mes=m, ingresos=r['ingresos'], costos_variables=r['costos_variables'],
                         costos_fijos=r['costos_fijos'], costos_totales=r['costos_totales'],
                         utilidad_operativa=r['utilidad_operativa'], unidades=r['unidades']))
    return pd.DataFrame(filas)


def conclusiones(globales: dict, tabla_mensual: pd.DataFrame) -> list[str]:
    resultado = 'positiva' if globales['utilidad_operativa'] >= 0 else 'negativa'
    c1 = f"La empresa registra una utilidad operativa {resultado} de {cop(globales['utilidad_operativa'])}, frente a ingresos de {cop(globales['ingresos'])} y costos totales de {cop(globales['costos_totales'])}."
    if not tabla_mensual.empty:
        mejor = tabla_mensual.loc[tabla_mensual['utilidad_operativa'].idxmax()]
        peor = tabla_mensual.loc[tabla_mensual['utilidad_operativa'].idxmin()]
        c2 = f"El mayor resultado operativo corresponde a {mejor['mes']} ({cop(mejor['utilidad_operativa'])}); el menor, a {peor['mes']} ({cop(peor['utilidad_operativa'])})."
    else:
        c2 = 'No hay meses disponibles para comparación.'
    eq = globales['equilibrio_mensual']
    c3 = (f"Con la mezcla de productos observada, el punto de equilibrio aproximado es de {eq} unidades en un mes promedio; cambia si varían precios, costos o composición de ventas." if eq is not None else 'No existe un punto de equilibrio calculable con un margen de contribución unitario no positivo.')
    return [c1, c2, c3]


def cop(valor: float) -> str:
    return '$' + f'{valor:,.0f}'.replace(',', '.') + ' COP'
