# ==========================================================
# FERRETERÍA IA PRO+++ – CÓDIGO ESTABLE PARA STREAMLIT CLOUD
# - SIN reportlab (no rompe el deploy)
# - Usuarios y roles
# - Normativas por país
# - IA controlada (no inventa datos)
# - Precios dinámicos
# - Presupuestos exportables a Excel
# ==========================================================

import streamlit as st
import json
import math
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from groq import Groq
import pandas as pd

# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================
st.set_page_config(
    page_title="Ferretería IA Pro+++",
    page_icon="🏗️",
    layout="centered"
)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ==========================================================
# AUTENTICACIÓN SIMPLE (MVP)
# ==========================================================
USUARIOS = {
    "admin": {"password": "admin123", "rol": "admin"},
    "ventas": {"password": "ventas123", "rol": "ventas"},
    "cliente": {"password": "cliente123", "rol": "cliente"}
}

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    st.subheader("Ingreso al sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u in USUARIOS and USUARIOS[u]["password"] == p:
            st.session_state.usuario = {"nombre": u, "rol": USUARIOS[u]["rol"]}
            st.experimental_rerun()
        else:
            st.error("Credenciales inválidas")
    st.stop()

# ==========================================================
# NORMATIVAS POR PAÍS
# ==========================================================
NORMATIVAS = {
    "Argentina": {"acero_kg_m3": 120, "desperdicio": 1.07},
    "Brasil": {"acero_kg_m3": 110, "desperdicio": 1.05},
    "México": {"acero_kg_m3": 125, "desperdicio": 1.08}
}

pais = st.selectbox("País de la obra", list(NORMATIVAS.keys()))

# ==========================================================
# MODELO DE OBRA
# ==========================================================
@dataclass
class Proyecto:
    largo: Optional[float] = None
    ancho: Optional[float] = None
    alto: Optional[float] = None
    espesor_cm: Optional[float] = None
    uso: Optional[str] = None
    tipo_obra: Optional[str] = None

# ==========================================================
# IA – EXTRACCIÓN SEGURA
# ==========================================================
def extraer_datos_ia(texto: str) -> Dict:
    prompt = f"""
    Eres un ingeniero civil.
    Extrae SOLO datos explícitos del texto.
    NO infieras.

    Devuelve JSON con:
    largo, ancho, alto, espesor_cm, uso, tipo_obra.
    Usa null si un dato no aparece.

    Texto: {texto}
    """

    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": prompt}],
        response_format={"type": "json_object"}
    )

    return json.loads(r.choices[0].message.content)

# ==========================================================
# PRECIOS DINÁMICOS
# ==========================================================
PRECIOS = {
    "cemento_saco": 15.0,
    "arena_m3": 18.0,
    "grava_m3": 22.0,
    "acero_kg": 1.2
}

if st.session_state.usuario["rol"] == "admin":
    st.subheader("Gestión de precios")
    for k in PRECIOS:
        PRECIOS[k] = st.number_input(k, value=PRECIOS[k])

# ==========================================================
# CÁLCULO DE CONCRETO
# ==========================================================
def calcular_concreto(p: Proyecto) -> Dict:
    norm = NORMATIVAS[pais]

    volumen = p.largo * p.ancho * (p.espesor_cm / 100)
    sacos_m3 = {"ligero": 6.5, "estructural": 8, "industrial": 9.5}.get(p.uso, 6.5)

    sacos = math.ceil(volumen * sacos_m3 * norm["desperdicio"])
    arena = volumen * 0.55 * norm["desperdicio"]
    grava = volumen * 0.75 * norm["desperdicio"]
    acero = volumen * norm["acero_kg_m3"]

    costo = (
        sacos * PRECIOS["cemento_saco"] +
        arena * PRECIOS["arena_m3"] +
        grava * PRECIOS["grava_m3"] +
        acero * PRECIOS["acero_kg"]
    )

    return {
        "volumen_m3": round(volumen, 2),
        "cemento_sacos": sacos,
        "arena_m3": round(arena, 2),
        "grava_m3": round(grava, 2),
        "acero_kg": round(acero, 1),
        "total_estimado": round(costo, 2)
    }

# ==========================================================
# INTERFAZ PRINCIPAL
# ==========================================================
st.title("🏗️ Ferretería IA Pro+++ – Plataforma Comercial")

entrada = st.text_input("Describe la obra")

if "memoria" not in st.session_state:
    st.session_state.memoria = {}

if entrada:
    nuevos = extraer_datos_ia(entrada)
    st.session_state.memoria.update({k: v for k, v in nuevos.items() if v is not None})

    proyecto = Proyecto(**st.session_state.memoria)
    faltantes = [k for k, v in asdict(proyecto).items() if v is None]

    if faltantes:
        st.warning(f"Faltan datos: {', '.join(faltantes)}")
    else:
        resultado = calcular_concreto(proyecto)
        st.success("Presupuesto generado")
        st.json(resultado)

        if st.button("Exportar a Excel"):
            df = pd.DataFrame(resultado.items(), columns=["Concepto", "Valor"])
            df.to_excel("presupuesto.xlsx", index=False)
            st.success("Archivo Excel generado correctamente")
