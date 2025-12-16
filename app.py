import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import streamlit.components.v1 as components
import plotly.graph_objects as go
from datetime import datetime

# --- IMPORTACIONES PROFESIONALES ---
# Asegúrate de tener la carpeta 'src' creada con engine.py y reports.py
from src.engine import CriticalityEngine 
from src.reports import create_pdf_report 

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="MCVD: Digital Twin & Protección",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="⚡"
)

# --- ESTÉTICA CYBERPUNK / SCADA (NIVEL 1) ---
st.markdown("""
<style>
    /* 1. Fondo Principal: Negro Profundo con Grid Digital */
    .stApp {
        background-color: #050505;
        background-image: linear-gradient(0deg, transparent 24%, rgba(0, 255, 0, .05) 25%, rgba(0, 255, 0, .05) 26%, transparent 27%, transparent 74%, rgba(0, 255, 0, .05) 75%, rgba(0, 255, 0, .05) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(0, 255, 0, .05) 25%, rgba(0, 255, 0, .05) 26%, transparent 27%, transparent 74%, rgba(0, 255, 0, .05) 75%, rgba(0, 255, 0, .05) 76%, transparent 77%, transparent);
        background-size: 50px 50px;
    }
    
    /* 2. Tarjetas y Métricas: Efecto Cristal + Borde Neón */
    div[data-testid="stMetric"], div[data-testid="stExpander"] {
        background-color: rgba(10, 10, 10, 0.8) !important;
        border: 1px solid #00FF41 !important; /* Verde Matrix */
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.1);
        border-radius: 5px;
        color: #fff;
    }
    
    /* 3. Textos y Títulos: Brillantes */
    h1, h2, h3 {
        color: #00FFFF !important; /* Cyan Futurista */
        font-family: 'Courier New', monospace;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
        letter-spacing: 2px;
    }
    
    /* 4. Etiquetas de métricas y valores */
    div[data-testid="stMetricLabel"] p {
        color: #00FFFF !important;
        font-weight: bold;
    }
    div[data-testid="stMetricValue"] div {
        color: #00FF41 !important;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.8);
    }

    /* 5. Botones: Estilo Reactor */
    .stButton>button {
        background: linear-gradient(90deg, #000000, #004400);
        color: #00FF41;
        border: 1px solid #00FF41;
        font-family: 'Courier New', monospace;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: #00FF41;
        color: black;
        box-shadow: 0 0 20px #00FF41;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar Estado
if 'history' not in st.session_state:
    st.session_state.history = {}
    st.session_state.cycle_count = 0

# --- SIDEBAR DE CONTROL ---
with st.sidebar:
    st.header("🎛️ Panel de Ingeniería")
    with st.expander("⚖️ Ponderación de Riesgos", expanded=True):
        w_s = st.slider("Seguridad (Personas)", 0.0, 1.0, 0.6)
        w_o = st.slider("Operacional ($$)", 0.0, 1.0, 0.3)
        w_e = st.slider("Ambiental (ISO 14001)", 0.0, 1.0, 0.1)
        
    st.divider()
    if st.button("🔄 CICLO DE ESCANEO (SIMULAR)", type="primary", use_container_width=True):
        st.session_state.cycle_count += 1
    
    st.caption(f"Ciclos ejecutados: {st.session_state.cycle_count}")
    
    if st.button("🗑️ Resetear Historial"):
        st.session_state.history = {}
        st.success("Buffer de memoria borrado.")

# --- INICIALIZAR MOTOR ---
total = w_s + w_o + w_e
if total == 0: total = 1 
engine = CriticalityEngine(w_s/total, w_o/total, w_e/total)

# DATOS BASE
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame([
        {'id': 'ACOMETIDA', 'label': 'Acometida 20kV', 'group': 'GRID', 'S_score': 10, 'O_score': 10, 'E_score': 5, 'install_year': 2010, 'useful_life': 40, 'R_red': 1.0},
        {'id': 'TR-01', 'label': 'Trafo Principal', 'group': 'TRANSF', 'S_score': 9, 'O_score': 10, 'E_score': 8, 'install_year': 1990, 'useful_life': 35, 'R_red': 1.0},
        {'id': 'CGBT', 'label': 'Cuadro General BT', 'group': 'PANEL', 'S_score': 8, 'O_score': 9, 'E_score': 2, 'install_year': 2005, 'useful_life': 25, 'R_red': 1.0},
        {'id': 'GEN-01', 'label': 'Grupo Electrógeno', 'group': 'BACKUP', 'S_score': 3, 'O_score': 8, 'E_score': 6, 'install_year': 2015, 'useful_life': 20, 'R_red': 2.0},
        {'id': 'MOTOR-A', 'label': 'Bomba Hidráulica', 'group': 'MOTOR', 'S_score': 5, 'O_score': 7, 'E_score': 4, 'install_year': 2018, 'useful_life': 12, 'R_red': 1.0},
        {'id': 'SRV-ROOM', 'label': 'Clima DataCenter', 'group': 'HVAC', 'S_score': 1, 'O_score': 9, 'E_score': 1, 'install_year': 2021, 'useful_life': 10, 'R_red': 1.5},
    ])

# CÁLCULOS
df_processed = engine.compute_matrix(st.session_state.data)

if st.session_state.cycle_count > 0:
    realtime_data = df_processed.apply(engine.evaluate_protection_logic, axis=1)
    realtime_data.columns = ['Temp_Actual', 'Vib_Actual', 'RealTime_Status', 'RealTime_Msg', 'Limit_Trip', 'Limit_Alarm', 'Status_Color']
    df_final = pd.concat([df_processed, realtime_data], axis=1)
else:
    df_final = df_processed.copy()
    for col in ['Temp_Actual', 'Vib_Actual', 'Limit_Trip', 'Limit_Alarm']: df_final[col] = 0.0
    df_final['RealTime_Status'] = "OFFLINE"
    df_final['RealTime_Msg'] = "Sistema detenido"
    df_final['Status_Color'] = "grey"

df_sorted = df_final.sort_values('MCVD_Index', ascending=False)

# --- DASHBOARD VISUAL ---
st.title("⚡ MCVD: Sistema de Protección Adaptativa")
st.markdown("### Centro de Control de Activos Críticos")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
n_alarms = len(df_sorted[df_sorted['RealTime_Status'].str.contains("ALARM")])
n_trips = len(df_sorted[df_sorted['RealTime_Status'].str.contains("TRIP")])
max_risk = df_sorted['MCVD_Index'].max()

kpi1.metric("Activos Monitoreados", len(df_sorted), delta="Online")
kpi2.metric("Riesgo Máximo (MCVD)", f"{max_risk:.2f}", delta="-Critico" if max_risk > 8 else "Normal", delta_color="inverse")
kpi3.metric("Alarmas Activas", n_alarms, delta="Requiere Atención" if n_alarms > 0 else "OK", delta_color="inverse")
kpi4.metric("Disparos (TRIP)", n_trips, delta="STOP" if n_trips > 0 else "Normal", delta_color="inverse")

st.divider()

col_topology, col_detail = st.columns([2, 1])

with col_topology:
    st.subheader("🌐 Topología de Red")
    # Ajustamos el fondo del grafo para que coincida con el tema oscuro (#050505)
    net = Network(height='450px', width='100%', bgcolor='#050505', font_color='white')
    shape_map = {'GRID': 'triangle', 'TRANSF': 'square', 'MOTOR': 'star', 'BACKUP': 'diamond', 'PANEL': 'box'}
    
    for index, row in df_sorted.iterrows():
        color = "#00ff00" # Verde neón por defecto
        if "ALARM" in row['RealTime_Status']: color = "#ffff00"
        if "TRIP" in row['RealTime_Status']: color = "#ff0000"
        size_val = 20 + (row['MCVD_Index'] * 3)
        title_html = f"<b>{row['label']}</b><br>MCVD: {row['MCVD_Index']:.2f}<br>Temp: {row['Temp_Actual']:.1f}ºC"
        net.add_node(row['id'], label=row['label'], title=title_html, color=color, shape=shape_map.get(row['group'], 'dot'), size=size_val)

    edges = [('ACOMETIDA', 'TR-01'), ('TR-01', 'CGBT'), ('CGBT', 'MOTOR-A'), ('CGBT', 'SRV-ROOM'), ('GEN-01', 'CGBT')]
    for u, v in edges:
        if u in df_sorted['id'].values and v in df_sorted['id'].values:
            net.add_edge(u, v, color='#555555', width=2)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        with open(tmp.name, 'r', encoding='utf-8') as f:
            html_string = f.read()
    components.html(html_string, height=470)

    st.subheader("📋 Matriz de Activos")
    # Estilizamos un poco el dataframe (aunque es nativo de streamlit, heredará algunos colores)
    edited_df = st.data_editor(st.session_state.data, use_container_width=True, hide_index=True)
    if not edited_df.equals(st.session_state.data):
        st.session_state.data = edited_df
        st.rerun()

with col_detail:
    st.subheader("📈 Análisis de Tendencias 3D")
    selected_asset = st.selectbox("Seleccionar Activo:", df_sorted['label'].values)
    selected_id = df_sorted[df_sorted['label'] == selected_asset]['id'].values[0]
    
    if selected_id in st.session_state.history:
        hist = st.session_state.history[selected_id]
        
        # 1. Recuperamos las variables, incluyendo Vibración para el eje Z
        df_hist = pd.DataFrame({
            'Tiempo': list(hist['time']),
            'Temp': list(hist['temp']),
            'Vib': list(hist['vib']),    # Nueva Dimensión Z
            'Limit': list(hist['limit']) 
        })
        
        # 2. Creamos el Gráfico 3D Futurista
        fig = go.Figure()
        
        # Trazo Principal: La línea de comportamiento del activo
        fig.add_trace(go.Scatter3d(
            x=df_hist['Tiempo'], 
            y=df_hist['Temp'], 
            z=df_hist['Vib'],
            mode='lines+markers',
            marker=dict(
                size=5,
                color=df_hist['Temp'],                # El color cambia con la temperatura
                colorscale='Electric',                # Paleta de colores "Electric"
                opacity=0.9
            ),
            line=dict(color='#00FFFF', width=5),      # Línea cian neón
            name='Estado Activo'
        ))

        # Plano de Límite (Techo rojo semitransparente)
        fig.add_trace(go.Surface(
            z=[[0,0],[10,10]], # Un plano vertical referencial o suelo, aquí simplificado
            x=[[df_hist['Tiempo'].iloc[0], df_hist['Tiempo'].iloc[-1]]]*2,
            y=[[df_hist['Limit'].iloc[0], df_hist['Limit'].iloc[0]]]*2,
            colorscale=[[0, 'red'], [1, 'red']],
            opacity=0.1,
            showscale=False,
            name="Límite Trip"
        ))

        # Configuración de la Escena 3D (Grid minimalista)
        fig.update_layout(
            scene = dict(
                xaxis = dict(title='TIEMPO', backgroundcolor="rgba(0,0,0,0)", gridcolor="#444", showbackground=True, tickfont=dict(color="#00FF41")),
                yaxis = dict(title='TEMP (ºC)', backgroundcolor="rgba(0,0,0,0)", gridcolor="#444", showbackground=True, tickfont=dict(color="#00FF41")),
                zaxis = dict(title='VIB (mm/s)', backgroundcolor="rgba(0,0,0,0)", gridcolor="#444", showbackground=True, tickfont=dict(color="#00FF41")),
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0),
            height=450,
            font=dict(family="Courier New", color="#00FFFF"),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Mensaje de estado estilizado
        row_detail = df_sorted[df_sorted['id'] == selected_id].iloc[0]
        status_color = "red" if "TRIP" in row_detail['RealTime_Status'] else "#00FF41"
        
        st.markdown(f"""
        <div style="border: 1px solid {status_color}; padding: 10px; border-radius: 5px; background: rgba(0,0,0,0.5); text-align: center;">
            <h3 style="margin:0; color: {status_color} !important;">ESTADO: {row_detail['RealTime_Msg']}</h3>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.warning("⚠️ SISTEMA EN ESPERA... INICIE SIMULACIÓN")

    st.markdown("---")
    if st.button("Descargar Informe PDF"):
        pdf_bytes = create_pdf_report(df_sorted)
        st.download_button("💾 Guardar PDF", data=pdf_bytes, file_name=f"MCVD_Report_{datetime.now().strftime('%H%M')}.pdf", mime="application/pdf")