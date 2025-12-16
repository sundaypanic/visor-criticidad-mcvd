import streamlit as st
import pandas as pd
import random
from datetime import datetime
from collections import deque

# --- GESTIÓN DE ESTADO (MEMORY BUFFER) ---
def update_history(asset_id, temp, vib, limit_temp):
    if asset_id not in st.session_state.history:
        st.session_state.history[asset_id] = {
            'temp': deque(maxlen=20),
            'vib': deque(maxlen=20),
            'limit': deque(maxlen=20),
            'time': deque(maxlen=20)
        }
    
    now_str = datetime.now().strftime("%H:%M:%S")
    st.session_state.history[asset_id]['temp'].append(temp)
    st.session_state.history[asset_id]['vib'].append(vib)
    st.session_state.history[asset_id]['limit'].append(limit_temp)
    st.session_state.history[asset_id]['time'].append(now_str)

# --- INTERFAZ DE HARDWARE ---
class HardwareController:
    """Simula la capa física con ruido browniano"""
    def read_sensors(self, asset_id, previous_temp=None):
        if previous_temp is None:
            base_temp = random.uniform(50.0, 90.0)
        else:
            change = random.uniform(-2.0, 3.0) 
            base_temp = previous_temp + change
            base_temp = max(20, min(150, base_temp))

        return {
            'temp_aceite': base_temp,
            'vibracion': random.uniform(0.5, 8.0) + (base_temp/20.0),
            'carga': random.uniform(40.0, 95.0)
        }

# --- MOTOR DE CRITICIDAD ---
class CriticalityEngine:
    def __init__(self, w_safety, w_operational, w_env):
        self.weights = {'S': w_safety, 'O': w_operational, 'E': w_env}
        self.hardware = HardwareController()

    def _calculate_aging_factor(self, install_year, useful_life_years):
        current_year = datetime.now().year
        age = current_year - install_year
        life_consumed = age / useful_life_years
        if life_consumed > 1.0: return 0.5 + ((life_consumed - 1.0))
        return life_consumed * 0.3

    def evaluate_protection_logic(self, row):
        prev_temp = None
        # Accedemos al historial de sesión de forma segura
        if 'history' in st.session_state and row['id'] in st.session_state.history:
            if st.session_state.history[row['id']]['temp']:
                prev_temp = st.session_state.history[row['id']]['temp'][-1]

        sensors = self.hardware.read_sensors(row['id'], prev_temp)
        mcvd_index = row['MCVD_Index']

        limit_trip = 110.0 - (mcvd_index * 3.0) 
        limit_alarm = limit_trip * 0.85 

        update_history(row['id'], sensors['temp_aceite'], sensors['vibracion'], limit_trip)

        status = "NORMAL"
        status_color = "green"
        msg = "Parámetros Nominales"

        if sensors['temp_aceite'] > limit_trip:
            status = "TRIP (STOP)"
            status_color = "red"
            msg = f"CRÍTICO: Temp {sensors['temp_aceite']:.1f}ºC > Trip {limit_trip:.1f}ºC"
        elif sensors['temp_aceite'] > limit_alarm:
            status = "ALARM (WARN)"
            status_color = "orange"
            msg = f"ADVERTENCIA: Temp {sensors['temp_aceite']:.1f}ºC en zona de riesgo."
        
        return pd.Series([sensors['temp_aceite'], sensors['vibracion'], status, msg, limit_trip, limit_alarm, status_color])

    def compute_matrix(self, df):
        df['F_obs'] = df.apply(lambda row: self._calculate_aging_factor(row['install_year'], row['useful_life']), axis=1)
        df['Impact_Score'] = (self.weights['S'] * df['S_score']) + \
                             (self.weights['O'] * df['O_score']) + \
                             (self.weights['E'] * df['E_score'])
        df['MCVD_Index'] = (df['Impact_Score'] * (1 + df['F_obs'])) / df['R_red']
        return df