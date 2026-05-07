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
    import requests
from bs4 import BeautifulSoup
import re
import urllib3

# Silenciamos las advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cabecera estándar para simular ser un navegador humano
CABECERAS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

def extraer_uco(doi):
    """
    Módulo especialista para Helvia (Universidad de Córdoba)
    Flujo: Búsqueda exacta -> Extracción de Handle -> Lectura de celda 'datacell'
    """
    url_base = "https://helvia.uco.es"
    # 1. Búsqueda exacta usando las comillas que vimos en tu captura (%22)
    url_busqueda = f"{url_base}/discover?query=%22{doi}%22"
    
    try:
        # Fase 1: Buscar el artículo
        res_busqueda = requests.get(url_busqueda, headers=CABECERAS, timeout=15, verify=False)
        res_busqueda.raise_for_status()
        sopa_busqueda = BeautifulSoup(res_busqueda.text, 'html.parser')
        
        # Buscamos el Handle en los enlaces de la página de resultados
        enlaces = sopa_busqueda.find_all('a', href=re.compile(r'handle/\d+/\d+'))
        
        if not enlaces:
            return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
            
        # Extraemos el código exacto (ej: 10396/22616)
        match = re.search(r'(handle/\d+/\d+)', enlaces[0]['href'])
        if not match:
            return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
            
        handle_encontrado = match.group(1)
        
        # Fase 2: Extraer estadísticas directas
        url_stats = f"{url_base}/{handle_encontrado}/statistics"
        res_stats = requests.get(url_stats, headers=CABECERAS, timeout=15, verify=False)
        res_stats.raise_for_status()
        sopa_stats = BeautifulSoup(res_stats.text, 'html.parser')
        
        # Buscamos directamente la celda con la clase de DSpace
        celda_numero = sopa_stats.find('td', class_='datacell')
        
        if celda_numero:
            visitas = celda_numero.get_text(strip=True)
            return {"estado": "✅ Encontrado", "visitas": visitas, "enlace": url_stats}
        else:
            return {"estado": "⚠️ Dato no visible en tabla", "visitas": None, "enlace": url_stats}
            
    except requests.exceptions.Timeout:
        return {"estado": "⚠️ Tiempo agotado", "visitas": None, "enlace": None}
    except Exception as e:
        return {"estado": f"⚠️ Error: {type(e).__name__}", "visitas": None, "enlace": None}

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
