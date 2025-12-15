import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import streamlit.components.v1 as components
from fpdf import FPDF
from datetime import datetime
import random
import time

# --- 1. CLASE DE INTERFAZ DE HARDWARE (Simulación de Capa OT) ---
class HardwareController:
    """
    Esta clase gestiona la comunicación con la capa física (PLCs, Relés, Sensores).
    Para efectos de la patente, esta es la interfaz que ejecuta la acción física.
    """
    def __init__(self):
        # En producción, aquí se inicializaría la conexión Modbus/TCP o IEC 61850
        pass

    def read_sensors(self, asset_id):
        """
        Simula la lectura de sensores en tiempo real.
        En entorno real: return client.read_holding_registers(address, count)
        """
        # Simulación de variables físicas con ruido aleatorio
        return {
            'temp_aceite': random.uniform(45.0, 105.0), # Temperatura ºC
            'vibracion': random.uniform(0.1, 15.0),     # mm/s
            'carga': random.uniform(20.0, 110.0)        # % de carga
        }

    def send_trip_signal(self, asset_id, reason):
        """
        ENVÍA LA ORDEN DE CORTE AL INTERRUPTOR AUTOMÁTICO.
        Esta función contiene la 'Actividad Inventiva' de actuación física.
        """
        # --- ZONA DE CONEXIÓN FÍSICA (PATENTE) ---
        # Ejemplo: client.write_coil(address_trip_coil, True)
        # -----------------------------------------
        
        # Log para la interfaz HMI
        return True

# --- 2. LÓGICA DE NEGOCIO Y PROTECCIÓN (Motor MCVD) ---
class CriticalityEngine:
    def __init__(self, w_safety, w_operational, w_env):
        self.weights = {'S': w_safety, 'O': w_operational, 'E': w_env}
        self.hardware = HardwareController()

    def _calculate_aging_factor(self, install_year, useful_life_years):
        current_year = datetime.now().year
        age = current_year - install_year
        life_consumed = age / useful_life_years
        if life_consumed <= 0.5: return 0.0
        elif life_consumed <= 1.0: return life_consumed * 0.2
        else: return 0.2 + ((life_consumed - 1.0) * 0.5)

    def evaluate_protection_logic(self, row):
        """
        ALGORITMO ADAPTATIVO (PATENTE):
        Reduce los umbrales de disparo (Trip) basándose en la salud calculada (MCVD).
        """
        # 1. Leer estado físico actual
        sensors = self.hardware.read_sensors(row['id'])
        mcvd_index = row['MCVD_Index']

        # 2. Calcular Umbrales Dinámicos
        # Un equipo crítico (MCVD alto) tiene menos tolerancia térmica y mecánica.
        
        # Base: 100ºC. Por cada punto de MCVD, restamos tolerancia.
        # Si MCVD es 10 (muy crítico), el límite baja drásticamente.
        limit_temp = 100.0 - (mcvd_index * 2.5) 
        limit_vib = 12.0 - (mcvd_index * 0.8)

        status = "NORMAL"
        trip_action = False
        msg = "Estable"

        # 3. Comparador Lógico
        if sensors['temp_aceite'] > limit_temp:
            status = "TRIP (TEMP)"
            trip_action = True
            msg = f"T.Aceite {sensors['temp_aceite']:.1f}ºC > Límite Dinámico {limit_temp:.1f}ºC"
        
        elif sensors['vibracion'] > limit_vib:
            status = "TRIP (VIB)"
            trip_action = True
            msg = f"Vibración {sensors['vibracion']:.1f}mm/s > Límite Dinámico {limit_vib:.1f}mm/s"

        # 4. Ejecución de Protección
        if trip_action:
            self.hardware.send_trip_signal(row['id'], msg)
        
        return pd.Series([sensors['temp_aceite'], sensors['vibracion'], status, msg])

    def compute_matrix(self, df):
        # 1. Cálculo Estático
        df['F_obs'] = df.apply(lambda row: self._calculate_aging_factor(row['install_year'], row['useful_life']), axis=1)
        df['Impact_Score'] = (self.weights['S'] * df['S_score']) + (self.weights['O'] * df['O_score']) + (self.weights['E'] * df['E_score'])
        df['MCVD_Index'] = (df['Impact_Score'] * (1 + df['F_obs'])) / df['R_red']
        
        return df

# --- 3. GENERADOR DE REPORTES PDF ---
class ReportGenerator(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Informe Técnico de Criticidad & Disparos (MCVD)', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Fecha de Emisión: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)

def create_pdf_report(df_sorted):
    pdf = ReportGenerator()
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    
    # Resumen de Disparos
    tripped = df_sorted[df_sorted['RealTime_Status'].str.contains("TRIP")]
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '1. LOG DE ACTUACIONES DEL SISTEMA DE PROTECCIÓN', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    if not tripped.empty:
        pdf.set_text_color(255, 0, 0)
        pdf.multi_cell(0, 7, f"¡ATENCIÓN! El sistema ha enviado señales de disparo a {len(tripped)} activos para prevenir fallos catastróficos.")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        for _, row in tripped.iterrows():
            pdf.cell(0, 7, f"-> ACTIVO: {row['label']} | CAUSA: {row['RealTime_Msg']}", 0, 1)
    else:
        pdf.cell(0, 7, "El sistema opera dentro de los parámetros normales. Sin disparos registrados.", 0, 1)

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '2. MATRIZ DE RIESGO ESTÁTICO', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    for index, row in df_sorted.head(5).iterrows():
        pdf.cell(0, 7, f"{row['label']} - Index: {row['MCVD_Index']:.2f}", 0, 1)
        
    return pdf.output(dest='S').encode('latin-1')

# --- 4. CONFIGURACIÓN DE LA APP STREAMLIT ---
st.set_page_config(page_title="MCVD: Sistema de Protección Activa", layout="wide")

st.title("⚡ Sistema MCVD: Protección Eléctrica Adaptativa")
st.markdown("""
**Modo:** Supervisión y Control en Tiempo Real.  
*Este sistema ajusta los relés de protección basándose en el índice de obsolescencia y criticidad.*
""")

# --- 5. SIDEBAR ---
st.sidebar.header("⚙️ Parametrización")
w_s = st.sidebar.slider("Peso Seguridad (S)", 0.0, 1.0, 0.5, 0.05)
w_o = st.sidebar.slider("Peso Operacional (O)", 0.0, 1.0, 0.4, 0.05)
w_e = st.sidebar.slider("Peso Ambiental (E)", 0.0, 1.0, 0.1, 0.05)

total = w_s + w_o + w_e
if total == 0: total = 1 
engine = CriticalityEngine(w_s/total, w_o/total, w_e/total)

# --- 6. GESTIÓN DE DATOS (EDITABLES) ---
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame([
        {'id': 'ACOMETIDA', 'label': 'Acometida MT', 'group': 'FUENTE', 'S_score': 10, 'O_score': 10, 'E_score': 5, 'install_year': 2010, 'useful_life': 40, 'R_red': 1.0},
        {'id': 'TR-01', 'label': 'Trafo General', 'group': 'DIST', 'S_score': 9, 'O_score': 10, 'E_score': 5, 'install_year': 1995, 'useful_life': 30, 'R_red': 1.0},
        {'id': 'CGBT', 'label': 'Cuadro General', 'group': 'DIST', 'S_score': 8, 'O_score': 10, 'E_score': 2, 'install_year': 2000, 'useful_life': 30, 'R_red': 1.0},
        {'id': 'SAI-01', 'label': 'UPS IT', 'group': 'BACKUP', 'S_score': 2, 'O_score': 9, 'E_score': 1, 'install_year': 2023, 'useful_life': 10, 'R_red': 2.0},
        {'id': 'SRV-RACK', 'label': 'Rack Servidores', 'group': 'LOAD', 'S_score': 1, 'O_score': 9, 'E_score': 0, 'install_year': 2020, 'useful_life': 10, 'R_red': 1.0},
        {'id': 'MOTOR-01', 'label': 'Compresor Aire', 'group': 'LOAD', 'S_score': 4, 'O_score': 7, 'E_score': 3, 'install_year': 2005, 'useful_life': 15, 'R_red': 1.0},
    ])

st.subheader("📝 Inventario de Activos (Editable)")
st.info("Edita los valores en la tabla para recalcular la matriz. El sistema simulará sensores basándose en estos datos.")

# Widget editable que actualiza el session_state
edited_df = st.data_editor(st.session_state.data, num_rows="dynamic")

# --- 7. PROCESAMIENTO ---
# 1. Calcular estática
df_processed = engine.compute_matrix(edited_df)

# 2. Simulación de Tiempo Real (Botón de Pánico / Refresco)
if st.button("🔄 Ejecutar Ciclo de Escaneo de Sensores (Simulación)"):
    # Aplicar lógica de protección
    realtime_data = df_processed.apply(engine.evaluate_protection_logic, axis=1)
    realtime_data.columns = ['Temp_Actual', 'Vib_Actual', 'RealTime_Status', 'RealTime_Msg']
    df_final = pd.concat([df_processed, realtime_data], axis=1)
else:
    # Estado inicial sin datos de sensores
    df_final = df_processed.copy()
    df_final['Temp_Actual'] = 0.0
    df_final['Vib_Actual'] = 0.0
    df_final['RealTime_Status'] = "ESPERA"
    df_final['RealTime_Msg'] = "Esperando ciclo..."

# Ordenar por riesgo
df_sorted = df_final.sort_values('MCVD_Index', ascending=False)

# --- 8. VISUALIZACIÓN ---
col1, col2 = st.columns([3, 1])

connections = [('ACOMETIDA', 'TR-01'), ('TR-01', 'CGBT'), ('CGBT', 'SAI-01'), ('CGBT', 'MOTOR-01'), ('SAI-01', 'SRV-RACK')]

with col1:
    st.subheader("Topología de Estado en Tiempo Real")
    net = Network(height='500px', width='100%', bgcolor='#1E1E1E', font_color='white')
    
    for index, row in df_sorted.iterrows():
        # Lógica de colores del Nodo
        color = '#00cc66' # Verde (OK)
        if 'TRIP' in row['RealTime_Status']:
            color = '#FF0000' # ROJO (DISPARADO)
            label_node = f"❌ {row['label']} (OFF)"
        elif row['MCVD_Index'] > 8:
            color = '#ff9900' # Naranja (Riesgo Latente)
            label_node = row['label']
        else:
            label_node = row['label']

        size_val = 25 + (row['MCVD_Index'] * 2)
        
        # Tooltip técnico
        title_html = (
            f"<b>{row['label']}</b><br>"
            f"MCVD Index: {row['MCVD_Index']:.2f}<br>"
            f"Temp: {row['Temp_Actual']:.1f}ºC<br>"
            f"Vib: {row['Vib_Actual']:.1f}mm/s<br>"
            f"Status: {row['RealTime_Status']}"
        )
        
        net.add_node(row['id'], label=label_node, title=title_html, color=color, size=size_val)

    for source, target in connections:
        # Verificar si nodos existen antes de crear aristas (por si el usuario borra filas)
        ids = df_sorted['id'].values
        if source in ids and target in ids:
            net.add_edge(source, target, color='gray')
    
    net.repulsion(node_distance=150, spring_length=150)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        with open(tmp.name, 'r', encoding='utf-8') as f:
            html_string = f.read()
    components.html(html_string, height=520)

with col2:
    st.subheader("🚨 Panel de Eventos")
    
    # Filtrar solo los disparados
    trips = df_sorted[df_sorted['RealTime_Status'].str.contains("TRIP")]
    
    if not trips.empty:
        st.error(f"¡ALERTA! {len(trips)} DISPAROS ACTIVOS")
        for _, trip in trips.iterrows():
            with st.expander(f"❌ {trip['label']}", expanded=True):
                st.write(f"**Causa:** {trip['RealTime_Msg']}")
                st.caption(f"Index MCVD: {trip['MCVD_Index']:.2f}")
    else:
        st.success("SISTEMA ESTABLE. Ningún parámetro excede el umbral dinámico.")

    st.markdown("---")
    
    # GENERAR PDF
    if st.button("📄 Descargar Informe Oficial"):
        pdf_bytes = create_pdf_report(df_sorted)
        st.download_button(
            label="Guardar PDF",
            data=pdf_bytes,
            file_name="Reporte_Proteccion_MCVD.pdf",
            mime="application/pdf"
        )

# --- 9. DATOS TÉCNICOS ---
st.markdown("### Telemetría Detallada")
# Estilizar la tabla para resaltar los disparos
def highlight_trip(row):
    if 'TRIP' in row['RealTime_Status']:
        return ['background-color: #ffcccc; color: black'] * len(row)
    else:
        return [''] * len(row)

st.dataframe(
    df_sorted[['label', 'MCVD_Index', 'Temp_Actual', 'Vib_Actual', 'RealTime_Status', 'RealTime_Msg']]
    .style.apply(highlight_trip, axis=1)
    .format({'MCVD_Index': "{:.2f}", 'Temp_Actual': "{:.1f}ºC", 'Vib_Actual': "{:.1f}"})
)