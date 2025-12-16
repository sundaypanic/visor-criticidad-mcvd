from fastapi import FastAPI
from pydantic import BaseModel
from src.engine import CriticalityEngine # ¡Reusamos tu motor!

# 1. Definimos la estructura de los datos que esperamos recibir (El "Ticket del pedido")
class AssetData(BaseModel):
    id: str
    install_year: int
    useful_life: int
    S_score: float
    O_score: float
    E_score: float
    R_red: float
    MCVD_Index: float = 0.0 # Opcional al inicio

# 2. Inicializamos la App (La "Cocina")
app = FastAPI(title="MCVD API Engine", version="1.0")

# Inicializamos tu motor de lógica
# (Asumimos pesos por defecto o los recibimos también)
engine = CriticalityEngine(0.6, 0.3, 0.1)

# 3. Creamos el Endpoint (La "Ventanilla")
@app.get("/")
def home():
    return {"mensaje": "La API MCVD está operativa 🚀"}

@app.post("/diagnosticar")
def diagnosticar_activo(data: AssetData):
    """
    Recibe los datos de un activo y devuelve su estado de salud.
    """
    # Convertimos el formato JSON a un diccionario para tu motor
    row = {
        'id': data.id,
        'install_year': data.install_year,
        'useful_life': data.useful_life,
        'S_score': data.S_score,
        'O_score': data.O_score,
        'E_score': data.E_score,
        'R_red': data.R_red,
        'MCVD_Index': data.MCVD_Index
    }
    
    # 1. Calculamos envejecimiento y MCVD si no viene dado
    # (Aquí podríamos adaptar tu función compute_matrix para una sola fila)
    # Por simplicidad, usamos la lógica de protección directa:
    
    # Simulamos que usamos tu motor para evaluar la lógica
    # Nota: Tu motor actual espera un DataFrame completo, 
    # en una API real adaptaríamos engine.py para aceptar datos sueltos.
    # Aquí hacemos una simulación rápida usando la lógica interna:
    
    resultado = engine.evaluate_protection_logic(row)
    
    # Devolvemos un JSON (Texto estructurado)
    return {
        "activo_id": data.id,
        "temperatura_actual": resultado['Temp_Actual'], # Asumiendo que adaptamos el retorno
        "estado": resultado[2], # STATUS
        "mensaje": resultado[3], # MSG
        "recomendacion": "Revisión inmediata" if "TRIP" in resultado[2] else "Monitorizar"
    }