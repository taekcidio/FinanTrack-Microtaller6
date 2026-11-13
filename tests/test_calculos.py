from pathlib import Path
import pandas as pd
from src.calculos import cargar_datos, resumen, mensual, conclusiones
BASE = Path(__file__).resolve().parents[1] / 'data'

def test_cifras_control():
    v,f=cargar_datos(BASE); r=resumen(v,f)
    assert len(v)==60 and len(f)==24
    assert r['ingresos']==37977000
    assert r['costos_variables']==22064000
    assert r['costos_fijos']==5383500
    assert r['costos_totales']==27447500
    assert r['utilidad_operativa']==10529500
    assert r['unidades']==344
    assert round(r['margen_operativo'],2)==27.73
    assert r['equilibrio_mensual']==20

def test_costos_no_repetidos():
    v,f=cargar_datos(BASE)
    assert resumen(v,f,['2026-01'])['costos_fijos']==f.loc[f.mes=='2026-01','valor_cop'].sum()
    assert mensual(v,f,sorted(v.mes.unique())).costos_fijos.sum()==f.valor_cop.sum()

def test_sin_ingresos_ni_unidades():
    v,f=cargar_datos(BASE)
    r=resumen(v.iloc[0:0],f,['2026-01'])
    assert r['margen_operativo'] is None and r['equilibrio_mensual'] is None

def test_margen_no_positivo():
    v,f=cargar_datos(BASE)
    v=v.copy();v['costos_variables']=v['ingresos']+100
    assert resumen(v,f)['equilibrio_mensual'] is None

def test_conclusiones_consistentes():
    v,f=cargar_datos(BASE); meses=sorted(v.mes.unique()); r=resumen(v,f,meses)
    textos=conclusiones(r,mensual(v,f,meses))
    assert len(textos)==3 and '20 unidades' in textos[2]
