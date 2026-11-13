"""FinanTrack: análisis empresarial de NovaTech Store con datos ficticios."""
from pathlib import Path
from html import escape
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.calculos import cargar_datos, resumen, mensual, conclusiones, cop
from src.filtros import filtrar_ventas, productos_disponibles, nombre_mes
from src.animated_plotly import animated_plotly

BASE = Path(__file__).parent
GREEN, ORANGE, PURPLE, RED = '#28786B', '#AEB6CE', '#655FC2', '#B7465C'
PALETTE = [PURPLE, '#283958', '#A7A2D8', '#7485A6', '#CFCCE9']
st.set_page_config(page_title='FinanTrack | NovaTech Store', page_icon=':material/monitoring:', layout='wide')
st.html(f'<style>{(BASE / "src/dashboard.css").read_text(encoding="utf-8-sig")}</style>')

@st.cache_data
def obtener():
    return cargar_datos(BASE / 'data')


def restablecer():
    st.session_state.update(periodo='Todos los meses', categoria='Todas las categorías', producto='Todos los productos')


def tarjeta(label, value, color='#253451'):
    st.html(f'<div class="kpi"><div class="label">{escape(label)}</div><div class="value" style="color:{color}">{escape(str(value))}</div></div>')


def franja(datos, clase='secondary-strip'):
    items = ''.join(f'<div class="strip-item"><span>{escape(label)}</span><strong>{escape(str(value))}</strong></div>' for label, value in datos)
    st.html(f'<div class="{clase}">{items}</div>')


def dibujar_grafico(fig, titulo, indice, height=350):
    with st.container(border=True, key=f'chart_{indice}'):
        st.markdown(f'#### {titulo}')
        fig.update_layout(height=height, margin=dict(l=12,r=12,t=20,b=30),
                          paper_bgcolor='white', plot_bgcolor='white',
                          font=dict(family='Arial, sans-serif',color='#384663'),
                          separators=',.', legend=dict(orientation='h',y=-.22,x=0),
                          hoverlabel=dict(bgcolor='white'), hovermode='closest')
        if not any(trace.type == 'pie' for trace in fig.data):
            fig.update_yaxes(gridcolor='#EDF0F6', zerolinecolor='#CCD4E3', automargin=True)
            fig.update_xaxes(automargin=True)
        animated_plotly(fig, title=titulo, chart_id=titulo.split(' · ')[0],
                        key=f'animated_chart_{indice}', height=height)


def barras(tabla, campos, nombres, colores, apiladas=False):
    fig = go.Figure()
    for campo, nombre, color in zip(campos, nombres, colores):
        fig.add_bar(x=tabla.mes.map(nombre_mes), y=tabla[campo], name=nombre, marker_color=color,
                    hovertemplate='%{x}<br>'+nombre+': %{y:,.0f} COP<extra></extra>')
    fig.update_layout(barmode='stack' if apiladas else 'group', yaxis_title='COP', bargap=.32)
    return fig

try:
    ventas, fijos = obtener()
except (OSError, ValueError, pd.errors.ParserError) as exc:
    st.error(f'No se pudo abrir la base financiera: {exc}')
    st.stop()

meses_todos = sorted(set(ventas.mes) | set(fijos.mes))
periodos = {'Todos los meses': meses_todos, **{nombre_mes(m): [m] for m in meses_todos}}
for clave, valor in [('periodo','Todos los meses'),('categoria','Todas las categorías'),('producto','Todos los productos'),('vista','Resumen general')]:
    if clave not in st.session_state:
        st.session_state[clave] = valor

st.html('<h1 class="dashboard-title">Dashboard de análisis financiero</h1>')
@st.fragment
def dashboard():
    graficos = []

    def grafico(fig, titulo, nota=''):
        graficos.append((fig, titulo))

    with st.container(border=True, key='filters'):
        cols = st.columns([1,1,1.3,1], vertical_alignment='bottom')
        cols[0].selectbox('Periodo · 2026', list(periodos), key='periodo')
        cols[1].selectbox('Categoría', ['Todas las categorías']+sorted(ventas.categoria.unique()), key='categoria')
        categoria = None if st.session_state.categoria == 'Todas las categorías' else st.session_state.categoria
        opciones = ['Todos los productos'] + productos_disponibles(ventas, categoria)
        if st.session_state.producto not in opciones:
            st.session_state.producto = 'Todos los productos'
        cols[2].selectbox('Producto', opciones, key='producto')
        cols[3].button('Restablecer', on_click=restablecer, icon=':material/restart_alt:', width='stretch')

    st.radio('Navegación', ['Resumen general','Ventas','Costos','Rentabilidad'], key='vista', horizontal=True,
             format_func=lambda v: 'Resumen' if v == 'Resumen general' else v, label_visibility='collapsed')

    meses = periodos[st.session_state.periodo]
    producto = None if st.session_state.producto == 'Todos los productos' else st.session_state.producto
    segmento = categoria is not None or producto is not None
    vf = filtrar_ventas(ventas, meses, categoria, producto)
    r = resumen(ventas, fijos, meses)
    mg = mensual(ventas, fijos, meses)
    ms = mensual(vf, fijos.iloc[:0], meses)
    periodo_texto = 'Enero–junio de 2026' if len(meses)==6 else f'{st.session_state.periodo} de 2026'
    st.caption(f'{periodo_texto} · Indicadores de NovaTech Store · COP')

    with st.grid(4, min_column_width=230):
        tarjeta('Ingresos totales', cop(r['ingresos']))
        tarjeta('Costos totales', cop(r['costos_totales']))
        tarjeta('Utilidad operativa', cop(r['utilidad_operativa']), GREEN if r['utilidad_operativa']>=0 else RED)
        tarjeta('Rentabilidad operativa', f"{r['margen_operativo']:.2f} %" if r['margen_operativo'] is not None else 'No disponible', PURPLE if r['utilidad_operativa']>=0 else RED)

    franja([
        ('Costos variables', cop(r['costos_variables'])),
        ('Costos fijos', cop(r['costos_fijos'])),
        ('Unidades vendidas', f"{r['unidades']:,.0f}".replace(',','.')),
        ('Punto de equilibrio · mes promedio', f"≈ {r['equilibrio_mensual']} u./mes" if r['equilibrio_mensual'] is not None else 'No calculable'),
    ])
    if vf.empty:
        st.warning('No existen ventas para esta selección. Los indicadores de empresa conservan el resultado real del periodo; ajusta los filtros para consultar un segmento con ventas.')

    vista = st.session_state.vista
    if vista == 'Ventas':
        st.markdown('#### Detalle de la selección')
        st.caption(f'{st.session_state.categoria} · {st.session_state.producto}')
        franja([('Ingresos', cop(vf.ingresos.sum())), ('Costos variables', cop(vf.costos_variables.sum())),
                ('Contribución', cop(vf.contribucion.sum())), ('Unidades', str(int(vf.cantidad.sum())))])
    with st.container(key='chart_preparation'):
        if vista in ['Resumen general','Rentabilidad']:
            grafico(barras(mg,['ingresos','costos_totales'],['Ingresos','Costos totales'],[GREEN,ORANGE]), 'Ingresos vs. costos', 'Empresa completa · costos fijos incluidos una vez por mes.')
            fig = go.Figure(go.Scatter(x=mg.mes.map(nombre_mes),y=mg.utilidad_operativa,mode='lines+markers',name='Utilidad operativa',line=dict(color=PURPLE,width=3),marker=dict(size=10,color=[GREEN if u>=0 else RED for u in mg.utilidad_operativa]),fill='tozeroy',fillcolor='rgba(89,86,202,.09)',hovertemplate='%{x}<br>Utilidad: %{y:,.0f} COP<extra></extra>'))
            fig.add_hline(y=0,line_dash='dot',line_color=RED)
            fig.update_layout(yaxis_title='COP')
            grafico(fig,'Evolución de utilidad','Empresa completa · verde: resultado positivo; rojo: negativo.')
        if vista in ['Resumen general','Ventas']:
            categorias = sorted(ventas.categoria.unique())
            cat = vf.groupby('categoria').ingresos.sum().reindex(categorias, fill_value=0).rename_axis('categoria').reset_index()
            colores = {categoria: PALETTE[i % len(PALETTE)] for i, categoria in enumerate(categorias)}
            fig=px.pie(cat,names='categoria',values='ingresos',hole=.7,color='categoria',color_discrete_map=colores)
            fig.update_traces(sort=False, ids=categorias)
            fig.update_traces(textinfo='percent',textposition='inside',hovertemplate='%{label}<br>%{value:,.0f} COP · %{percent}<extra></extra>')
            if vf.empty or vf.ingresos.sum() <= 0:
                fig.add_annotation(text='Sin ingresos para esta selección', showarrow=False, x=.5, y=.5, xref='paper', yref='paper')
            grafico(fig,'Distribución por categoría · selección' if segmento else 'Distribución por categoría')
        if vista in ['Resumen general','Rentabilidad']:
            eq=r['equilibrio_mensual']
            maximo=max((eq or 20)*2,math.ceil(r['unidades']/len(meses)*1.3),20)
            qs=sorted(set([0,maximo]+list(range(0,maximo+1,max(1,maximo//70)))+([eq] if eq is not None else [])))
            fig=go.Figure()
            for nombre, ys, color in [('Ingresos estimados',[q*r['precio_unitario'] for q in qs],GREEN),('Costos totales estimados',[r['costo_fijo_promedio']+q*r['variable_unitario'] for q in qs],ORANGE)]:
                fig.add_scatter(x=qs,y=ys,name=nombre,mode='lines',line=dict(color=color,width=3),hovertemplate='%{x} unidades<br>%{y:,.0f} COP<extra>'+nombre+'</extra>')
            if eq is not None:
                exacto=r['costo_fijo_promedio']/r['margen_unitario']
                fig.add_scatter(x=[exacto],y=[exacto*r['precio_unitario']],mode='markers',marker=dict(color=PURPLE,size=11),name=f'Equilibrio ≈ {eq} u.',hovertemplate='Intersección: %{x:.2f} u.<br>%{y:,.0f} COP<extra></extra>')
            fig.update_layout(xaxis_title='Unidades por mes',yaxis_title='COP')
            grafico(fig,'Punto de equilibrio estimado','Empresa · mes promedio. Precio y costo unitarios ponderados; mezcla constante. Cantidad redondeada hacia arriba.')
        if vista == 'Ventas':
            grafico(barras(ms,['ingresos'],['Ingresos'],[GREEN]),'Ventas por mes','Selección comercial · periodo seleccionado.')
            for campo,titulo,color in [('ingresos','Ingresos por producto',GREEN),('contribucion','Contribución por producto',PURPLE)]:
                agrupado=vf.groupby('producto',as_index=False)[campo].sum().sort_values(campo)
                fig=px.bar(agrupado,x=campo,y='producto',orientation='h',color_discrete_sequence=[color],labels={campo:'COP','producto':''})
                fig.update_traces(hovertemplate='%{y}<br>%{x:,.0f} COP<extra></extra>')
                grafico(fig,titulo,'Selección comercial · sin asignación de costos fijos.')
        if vista == 'Costos':
            grafico(barras(mg,['costos_variables','costos_fijos'],['Variables','Fijos'],[ORANGE,PURPLE],True),'Evolución de costos','Empresa completa · periodo seleccionado.')
            fig=go.Figure(go.Pie(labels=['Variables','Fijos'],values=[r['costos_variables'],r['costos_fijos']],hole=.7,marker_colors=[ORANGE,PURPLE],textinfo='percent',hovertemplate='%{label}<br>%{value:,.0f} COP · %{percent}<extra></extra>'))
            grafico(fig,'Composición de costos','Empresa completa · costos totales del periodo.')
            ff=fijos[fijos.mes.isin(meses)].groupby('concepto',as_index=False).valor_cop.sum()
            fig=px.bar(ff,x='valor_cop',y='concepto',orientation='h',color_discrete_sequence=[PURPLE],labels={'valor_cop':'COP','concepto':''})
            fig.update_traces(hovertemplate='%{y}<br>%{x:,.0f} COP<extra></extra>')
            grafico(fig,'Costos fijos por concepto','Empresa completa · acumulado del periodo.')
            grafico(barras(ms,['costos_variables'],['Costos variables'],[ORANGE]),'Costos variables de ventas','Selección comercial · sin gastos fijos asignados.')

    for inicio in range(0, len(graficos), 2):
        proporciones = [1.6, 1] if inicio == 0 else [1, 1.6]
        columnas = st.columns(proporciones, gap='medium')
        for indice, (fig, titulo) in enumerate(graficos[inicio:inicio+2], inicio):
            with columnas[indice-inicio]:
                dibujar_grafico(fig, titulo, indice, height=370 if inicio == 0 else 340)

    textos=conclusiones(r,mg)
    if segmento:
        ingresos=float(vf.ingresos.sum()); contrib=float(vf.contribucion.sum())
        textos[1]=f"El segmento seleccionado aporta ingresos de {cop(ingresos)}, costos variables de {cop(vf.costos_variables.sum())} y contribución de {cop(contrib)}. " + (f"Su tasa de contribución es {100*contrib/ingresos:.2f} %." if ingresos>0 else 'Sin ingresos, su tasa de contribución no está disponible.')
    with st.expander('Lectura financiera del periodo'):
        for i,texto in enumerate(textos,1):
            st.markdown(f'**{i:02d}.** {texto}')

    with st.expander('Consultar registros y descargar CSV',icon=':material/table_view:'):
        st.caption(f'Filtros aplicados: {periodo_texto} / {st.session_state.categoria} / {st.session_state.producto}. Importes monetarios en COP.')
        nombres={'id_venta':'Venta','fecha':'Fecha','producto':'Producto','categoria':'Categoría','cantidad':'Unidades','precio_unitario_cop':'Precio unitario (COP)','costo_variable_unitario_cop':'Costo variable unitario (COP)','ingresos':'Ingresos (COP)','costos_variables':'Costos variables (COP)','contribucion':'Contribución (COP)'}
        tabla=vf[list(nombres)].copy()
        tabla['fecha']=tabla.fecha.dt.strftime('%Y-%m-%d')
        tabla=tabla.rename(columns=nombres)
        config={nombre:st.column_config.NumberColumn(format='localized',help='Pesos colombianos (COP)') for nombre in nombres.values() if '(COP)' in nombre}
        st.dataframe(tabla,hide_index=True,width='stretch',column_config=config,alt='Transacciones de ventas filtradas')
        st.download_button('Descargar ventas filtradas',tabla.to_csv(index=False).encode('utf-8-sig'),'ventas_filtradas.csv','text/csv',icon=':material/download:')
        if vista=='Costos':
            tabla_fijos=fijos[fijos.mes.isin(meses)].rename(columns={'mes':'Mes','concepto':'Concepto','valor_cop':'Valor (COP)'})
            st.dataframe(tabla_fijos,hide_index=True,width='stretch',alt='Costos fijos del periodo')
            st.download_button('Descargar costos fijos',tabla_fijos.to_csv(index=False).encode('utf-8-sig'),'costos_fijos_periodo.csv','text/csv')
    with st.expander('Metodología'):
        st.caption('Datos ficticios – Uso académico')
        st.markdown('''**Ingresos:** cantidad × precio unitario. **Costos variables:** cantidad × costo variable unitario. **Contribución:** ingresos − costos variables. **Costos totales:** variables + fijos aplicables al periodo. **Utilidad operativa:** ingresos − costos totales. **Margen operativo:** utilidad / ingresos × 100; sin ingresos, no disponible.

    **Equilibrio de un mes promedio:** costo fijo mensual promedio / contribución unitaria ponderada por las unidades reales. Se redondea hacia arriba; el punto marcado representa la intersección matemática. Solo es calculable con contribución unitaria positiva. Supone precios, costos y mezcla global constantes. No representa el equilibrio propio de un segmento ni la cantidad acumulada de los seis meses.

    Los indicadores empresariales y sus gráficos conservan el alcance global al filtrar categorías o productos. Las ventas, la distribución, los costos variables comerciales y la contribución sí reflejan el segmento. No se reparten gastos fijos sin una base de asignación. Datos ficticios; no incluye impuestos, intereses, depreciación ni movimientos de caja.''')
    st.caption('FinanTrack · NovaTech Store · Microtaller 6 · Datos ficticios – Uso académico')


dashboard()
