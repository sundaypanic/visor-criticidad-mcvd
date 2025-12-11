import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile
import streamlit.components.v1 as components
from fpdf import FPDF
from datetime import datetime

# --- 1. LÓGICA DE NEGOCIO (Motor MCVD) ---
class CriticalityEngine:
    def __init__(self, w_safety, w_operational, w_env):
        self.weights = {'S': w_safety, 'O': w_operational, 'E': w_env}

    def _calculate_aging_factor(self, install_year, useful_life_years):
        current_year = 2025
        age = current_year - install_year
        life_consumed = age / useful_life_years
        if life_consumed <= 0.5: return 0.0
        elif life_consumed <= 1.0: return life_consumed * 0.2
        else: return 0.2 + ((life_consumed - 1.0) * 0.5)

    def compute_matrix(self, df):
        df['F_obs'] = df.apply(lambda row: self._calculate_aging_factor(row['install_year'], row['useful_life']), axis=1)
        df['Impact_Score'] = (self.weights['S'] * df['S_score']) + (self.weights['O'] * df['O_score']) + (self.weights['E'] * df['E_score'])
        df['MCVD_Index'] = (df['Impact_Score'] * (1 + df['F_obs'])) / df['R_red']
        return df

# --- 2. GENERADOR DE REPORTES PDF ---
class ReportGenerator(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Informe Técnico de Criticidad Eléctrica (MCVD)', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Fecha de Emisión: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, label, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 5, body)
        self.ln()

def create_pdf_report(df_sorted):
    pdf = ReportGenerator()
    pdf.add_page()
    
    # Resumen Ejecutivo
    top_asset = df_sorted.iloc[0]
    pdf.chapter_title('1. DIAGNÓSTICO DE ALTO NIVEL')
    pdf.chapter_body(
        f"El sistema ha analizado {len(df_sorted)} activos eléctricos bajo el estándar MCVD.\n"
        f"Se ha detectado una situación de ALTA PRIORIDAD en el activo: {top_asset['label']}.\n"
        f"Este equipo presenta un Índice de Criticidad de {top_asset['MCVD_Index']:.2f}, lo cual supera el umbral de seguridad recomendado."
    )
    
    # Detalle del Top 1
    pdf.chapter_title(f'2. FICHA TÉCNICA: {top_asset["label"]}')
    
    # Lógica de recomendación automática
    motivo = ""
    if top_asset['F_obs'] > 0.5: motivo += "- El equipo ha superado ampliamente su vida útil (Obsolescencia Crítica).\n"
    if top_asset['R_red'] == 1.0: motivo += "- Es un punto único de fallo (Sin Redundancia).\n"
    if top_asset['S_score'] >= 8: motivo += "- Representa un riesgo severo para la seguridad humana.\n"
    
    pdf.set_font('Arial', '', 10)
    text_detail = (
        f"ID Activo: {top_asset['id']}\n"
        f"Año Instalación: {top_asset['install_year']} (Vida Útil: {top_asset['useful_life']} años)\n"
        f"Factor de Obsolescencia Calculado: +{top_asset['F_obs']*100:.1f}%\n"
        f"Redundancia: {'NO (Sistema N)' if top_asset['R_red']==1 else 'SÍ (Sistema N+1/2N)'}\n\n"
        f"FACTORES DE RIESGO DETECTADOS:\n{motivo}"
    )
    pdf.multi_cell(0, 6, text_detail)
    
    # Tabla Resumen
    pdf.ln(5)
    pdf.chapter_title('3. LISTADO DE PRIORIDADES (TOP 5)')
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(80, 7, 'Activo', 1)
    pdf.cell(30, 7, 'Criticidad', 1)
    pdf.cell(40, 7, 'Estado', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 10)
    for index, row in df_sorted.head(5).iterrows():
        estado = "CRÍTICO" if row['MCVD_Index'] > 10 else "ALERTA" if row['MCVD_Index'] > 5 else "NORMAL"
        pdf.cell(80, 7, row['label'], 1)
        pdf.cell(30, 7, f"{row['MCVD_Index']:.2f}", 1)
        pdf.cell(40, 7, estado, 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# --- 3. CONFIGURACIÓN DE LA APP STREAMLIT ---
st.set_page_config(page_title="MCVD: Mapa de Criticidad", layout="wide")

st.title("⚡ Sistema de Criticidad Vectorial Dinámica (MCVD)")
st.markdown("**Visualización Topológica de Riesgo Eléctrico**")

# --- 4. SIDEBAR ---
st.sidebar.header("⚙️ Configuración Estratégica")
w_s = st.sidebar.slider("Peso Seguridad (S)", 0.0, 1.0, 0.5, 0.05)
w_o = st.sidebar.slider("Peso Operacional (O)", 0.0, 1.0, 0.4, 0.05)
w_e = st.sidebar.slider("Peso Ambiental (E)", 0.0, 1.0, 0.1, 0.05)

total = w_s + w_o + w_e
st.sidebar.metric("Suma de Pesos", f"{total:.2f}")
if total == 0: total = 1 
engine = CriticalityEngine(w_s/total, w_o/total, w_e/total)

# --- 5. DATOS DEMO ---
data = [
    {'id': 'ACOMETIDA', 'label': 'Acometida MT', 'group': 'FUENTE', 'S_score': 10, 'O_score': 10, 'E_score': 5, 'install_year': 2010, 'useful_life': 40, 'R_red': 1.0},
    {'id': 'TR-01', 'label': 'Trafo General', 'group': 'DIST', 'S_score': 9, 'O_score': 10, 'E_score': 5, 'install_year': 1995, 'useful_life': 30, 'R_red': 1.0},
    {'id': 'CGBT', 'label': 'Cuadro General', 'group': 'DIST', 'S_score': 8, 'O_score': 10, 'E_score': 2, 'install_year': 2000, 'useful_life': 30, 'R_red': 1.0},
    {'id': 'SAI-01', 'label': 'UPS IT', 'group': 'BACKUP', 'S_score': 2, 'O_score': 9, 'E_score': 1, 'install_year': 2023, 'useful_life': 10, 'R_red': 2.0},
    {'id': 'SRV-RACK', 'label': 'Rack Servidores', 'group': 'LOAD', 'S_score': 1, 'O_score': 9, 'E_score': 0, 'install_year': 2020, 'useful_life': 10, 'R_red': 1.0},
    {'id': 'MOTOR-01', 'label': 'Compresor Aire', 'group': 'LOAD', 'S_score': 4, 'O_score': 7, 'E_score': 3, 'install_year': 2005, 'useful_life': 15, 'R_red': 1.0},
    {'id': 'ILUM-NAVE', 'label': 'Ilum. Nave', 'group': 'LOAD', 'S_score': 1, 'O_score': 3, 'E_score': 0, 'install_year': 2010, 'useful_life': 20, 'R_red': 1.0},
]
connections = [('ACOMETIDA', 'TR-01'), ('TR-01', 'CGBT'), ('CGBT', 'SAI-01'), ('CGBT', 'MOTOR-01'), ('CGBT', 'ILUM-NAVE'), ('SAI-01', 'SRV-RACK')]

df = pd.DataFrame(data)
df_result = engine.compute_matrix(df)
df_sorted = df_result.sort_values('MCVD_Index', ascending=False)

# --- 6. VISUALIZACIÓN ---
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Mapa Topológico de Calor")
    net = Network(height='500px', width='100%', bgcolor='#222222', font_color='white')
    
    def get_color(value):
        if value > 10: return '#ff0000' 
        elif value > 5: return '#ff9900' 
        else: return '#00cc66' 

    for index, row in df_result.iterrows():
        size_val = 20 + (row['MCVD_Index'] * 3)
        title_html = f"<b>{row['label']}</b><br>MCVD: {row['MCVD_Index']:.2f}"
        net.add_node(row['id'], label=row['label'], title=title_html, color=get_color(row['MCVD_Index']), size=size_val)

    for source, target in connections:
        net.add_edge(source, target, color='gray')
    
    net.repulsion(node_distance=150, spring_length=150)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        with open(tmp.name, 'r', encoding='utf-8') as f:
            html_string = f.read()
    components.html(html_string, height=520)

with col2:
    st.subheader("🚨 Top Críticos")
    st.dataframe(df_sorted[['label', 'MCVD_Index']].head(5), hide_index=True)
    
    st.markdown("---")
    st.subheader("Exportar")
    
    # GENERAR PDF AL VUELO
    if st.button("Generar Informe Oficial"):
        pdf_bytes = create_pdf_report(df_sorted)
        st.download_button(
            label="💾 Descargar PDF",
            data=pdf_bytes,
            file_name="Reporte_Criticidad_MCVD.pdf",
            mime="application/pdf"
        )
        st.success("Informe generado. Pulsa Descargar.")

# --- 7. TABLA DETALLADA INFERIOR ---
st.markdown("### Matriz de Datos en Tiempo Real")
st.dataframe(df_sorted.style.background_gradient(subset=['MCVD_Index'], cmap='RdYlGn_r'))
