import streamlit as st
import time

# ==========================================
# 1. MÓDULOS DE EXTRACCIÓN (Los iremos creando uno a uno)
# ==========================================

def extraer_upo(doi):
    """Módulo especialista para RIO (Universidad Pablo de Olavide)"""
    # Aquí pondremos el código exacto cuando me pases la captura
    return {"estado": "⏳ Pendiente de programar", "visitas": None, "enlace": None}

def extraer_uco(doi):
    """Módulo especialista para Helvia (Universidad de Córdoba)"""
    # Aquí pondremos el código exacto cuando me pases la captura
    return {"estado": "⏳ Pendiente de programar", "visitas": None, "enlace": None}

# (Iremos añadiendo el resto de universidades aquí...)

# ==========================================
# 2. DIRECTORIO GENERAL
# ==========================================
# Vinculamos el nombre del repositorio con su función especialista
REPOSITORIOS = {
    "RIO (Olavide)": extraer_upo,
    "Helvia (Córdoba)": extraer_uco,
    # Añadiremos las demás poco a poco...
}

# ==========================================
# 3. INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================

st.set_page_config(page_title="Impacto Andalucía", page_icon="🌍", layout="centered")
st.title("🌍 Buscador de Impacto: Red de Repositorios")
st.write("Arquitectura Modular Activa.")

doi_input = st.text_input("Introduce el DOI del artículo:", placeholder="Ej: 10.3390/healthcare9091216").strip()

if st.button("🚀 Iniciar Rastreo"):
    if doi_input:
        st.subheader("📡 Informe de Búsqueda")
        
        # Vamos universidad por universidad llamando a su especialista
        for nombre_repo, funcion_especialista in REPOSITORIOS.items():
            with st.spinner(f"Consultando a {nombre_repo}..."):
                
                # Ejecutamos el módulo
                resultado = funcion_especialista(doi_input)
                
                # Mostramos el resultado en una caja
                with st.expander(f"📌 {nombre_repo} - {resultado['estado']}", expanded=True):
                    if resultado['visitas']:
                        st.info(f"📊 **Visualizaciones totales:** {resultado['visitas']}")
                    if resultado['enlace']:
                        st.write(f"🔗 [Ver estadísticas oficiales]({resultado['enlace']})")
                    if not resultado['visitas'] and not resultado['enlace']:
                         st.write("Módulo en construcción o dato no encontrado.")
    else:
        st.error("Por favor, introduce un DOI para comenzar.")
