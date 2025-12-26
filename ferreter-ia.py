# ==========================================================
# FERRETERÍA IA PRO+++ – UI PROFESIONAL (SIN JSON)
# ==========================================================

import streamlit as st
import json
import math
from typing import Optional, Dict
from dataclasses import dataclass
from groq import Groq
import pandas as pd
from io import BytesIO

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
    "cliente": {"password": "cliente123", "rol": "cliente"},
}

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    st.subheader("Ingreso al sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if u in USUARIOS and USUARIOS[u]["password"] == p:
            st.session_state.usuario = {
                "nombre": u,
                "rol": USUARIOS[u]["rol"]
            }
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
    "México": {"acero_kg_m3": 125, "desperdicio": 1.08},
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
    tipo_obra: Optional[str] = None  # piso / losa / muro

# ==========================================================
# IA – EXTRACCIÓN CONTROLADA
# ==========================================================
def extraer_datos_ia(texto: str) -> Dict:
    prompt = f"""
    Eres un ingeniero civil.
    Extrae SOLO datos explícitos.
    NO infieras valores.

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
    "acero_kg": 1.2,
}

if st.session_state.usuario["rol"] == "admin":
    st.subheader("⚙️ Gestión de precios")
    for k in PRECIOS:
        PRECIOS[k] = st.number_input(k, value=PRECIOS[k])

# ==========================================================
# CÁLCULO DE CONCRETO
# ==========================================================
def calcular_concreto(p: Proyecto) -> Dict:
    norm = NORMATIVAS[pais]

    volumen = p.largo * p.ancho * (p.espesor_cm / 100)

    sacos_m3 = {
        "ligero": 6.5,
        "estructural": 8,
        "industrial": 9.5
    }.get(p.uso, 6.5)

    sacos = math.ceil(volumen * sacos_m3 * norm["desperdicio"])
    arena = volumen * 0.55 * norm["desperdicio"]
    grava = volumen * 0.75 * norm["desperdicio"]
    acero = volumen * norm["acero_kg_m3"]

    total = (
        sacos * PRECIOS["cemento_saco"] +
        arena * PRECIOS["arena_m3"] +
        grava * PRECIOS["grava_m3"] +
        acero * PRECIOS["acero_kg"]
    )

    return {
        "Volumen (m³)": round(volumen, 2),
        "Cemento (sacos)": sacos,
        "Arena (m³)": round(arena, 2),
        "Grava (m³)": round(grava, 2),
        "Acero (kg)": round(acero, 1),
        "Total estimado ($)": round(total, 2),
    }

# ==========================================================
# INTERFAZ PRINCIPAL
# ==========================================================
st.title("🏗️ Ferretería IA Pro+++")

entrada = st.text_input("Describe la obra")

if "memoria" not in st.session_state:
    st.session_state.memoria = {}

if entrada:
    nuevos = extraer_datos_ia(entrada)
    st.session_state.memoria.update(
        {k: v for k, v in nuevos.items() if v is not None}
    )

    proyecto = Proyecto(**st.session_state.memoria)

    # VALIDACIÓN SEGÚN TIPO DE OBRA
    if proyecto.tipo_obra in ["piso", "losa"]:
        requeridos = ["largo", "ancho", "espesor_cm"]
    elif proyecto.tipo_obra == "muro":
        requeridos = ["largo", "alto", "espesor_cm"]
    else:
        requeridos = []

    faltantes = [k for k in requeridos if getattr(proyecto, k) is None]

    if faltantes:
        st.warning(f"Faltan datos para continuar: {', '.join(faltantes)}")
    else:
        resultado = calcular_concreto(proyecto)

        st.success("✅ Presupuesto generado")

        # ==================================================
        # MÉTRICAS PRINCIPALES (TARJETAS)
        # ==================================================
        c1, c2, c3 = st.columns(3)
        c1.metric("Volumen", f"{resultado['Volumen (m³)']} m³")
        c2.metric("Cemento", f"{resultado['Cemento (sacos)']} sacos")
        c3.metric("Total", f"${resultado['Total estimado ($)']}")

        # ==================================================
        # TABLA DETALLADA
        # ==================================================
        st.subheader("📋 Detalle del presupuesto")

        df = pd.DataFrame(
            resultado.items(),
            columns=["Concepto", "Cantidad"]
        )

        st.table(df)

        # ==================================================
        # WHATSAPP
        # ==================================================
        mensaje_wp = (
            "🏗️ Presupuesto de obra\n\n" +
            "\n".join([f"- {k}: {v}" for k, v in resultado.items()])
        )

        url_wp = (
            "https://wa.me/?text=" +
            mensaje_wp.replace(" ", "%20").replace("\n", "%0A")
        )

        st.markdown(f"📲 [Enviar presupuesto por WhatsApp]({url_wp})")

        # ==================================================
        # EXCEL DESCARGABLE
        # ==================================================
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Presupuesto")

        st.download_button(
            label="⬇️ Descargar presupuesto en Excel",
            data=buffer.getvalue(),
            file_name="presupuesto_obra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
