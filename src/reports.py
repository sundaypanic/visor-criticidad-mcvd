from fpdf import FPDF
from datetime import datetime

class ReportGenerator(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(30, 30, 30)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, ' MCVD SYSTEM REPORT - DIGITAL TWIN SNAPSHOT', 0, 1, 'C', 1)
        self.ln(5)

def create_pdf_report(df_sorted):
    pdf = ReportGenerator()
    pdf.add_page()
    pdf.set_text_color(0,0,0)
    pdf.set_font('Arial', '', 10)
    
    pdf.cell(0, 10, f"Timestamp: {datetime.now()}", 0, 1)
    
    # Tabla resumen de incidentes
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "1. Incidentes Activos", 0, 1)
    pdf.set_font('Arial', '', 10)
    
    alerts = df_sorted[df_sorted['RealTime_Status'] != "NORMAL"]
    if not alerts.empty:
        for _, row in alerts.iterrows():
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 8, f"[{row['RealTime_Status']}] Activo: {row['label']} | {row['RealTime_Msg']}", 0, 1)
    else:
        pdf.set_text_color(0, 100, 0)
        pdf.cell(0, 8, "Sistema Nominal. Sin incidencias reportadas.", 0, 1)

    pdf.ln(5)
    pdf.set_text_color(0,0,0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "2. Detalle de Criticidad (Ranking MCVD)", 0, 1)
    
    # Cabecera tabla
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(40, 8, "Activo", 1)
    pdf.cell(30, 8, "MCVD Index", 1)
    pdf.cell(30, 8, "Temp Actual", 1)
    pdf.cell(30, 8, "Limite Trip", 1)
    pdf.cell(0, 8, "Estado", 1, 1)
    
    pdf.set_font('Arial', '', 9)
    for _, row in df_sorted.iterrows():
        pdf.cell(40, 8, str(row['label']), 1)
        pdf.cell(30, 8, f"{row['MCVD_Index']:.2f}", 1)
        pdf.cell(30, 8, f"{row['Temp_Actual']:.1f} C", 1)
        pdf.cell(30, 8, f"{row['Limit_Trip']:.1f} C", 1)
        pdf.cell(0, 8, str(row['RealTime_Status']), 1, 1)
        
    return pdf.output(dest='S').encode('latin-1')