import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import urllib3
import time

# Silenciamos las advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# CONSTANTES Y DISFRAZ AVANZADO
# ==========================================
# Hemos añadido más datos para parecer un humano navegando desde España
CABECERAS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def crear_sesion_robusta():
    sesion = requests.Session()
    reintentos = Retry(total=3, backoff_factor=2, status_forcelist=[403, 500, 502, 503, 504])
    adaptador = HTTPAdapter(max_retries=reintentos)
    sesion.mount('http://', adaptador)
    sesion.mount('https://', adaptador)
    return sesion

# ==========================================
# 1. MÓDULOS DE EXTRACCIÓN
# ==========================================

def extraer_uco(doi):
    """Módulo especialista para Helvia (Universidad de Córdoba)"""
    url_base = "https://helvia.uco.es"
    # Quitamos las comillas %22 para evitar bloqueos
    url_busqueda = f"{url_base}/discover?query={doi}"
    sesion = crear_sesion_robusta()
    
    try:
        time.sleep(1) # Pequeña pausa humana antes de entrar
        res_busqueda = sesion.get(url_busqueda, headers=CABECERAS, timeout=30, verify=False)
        res_busqueda.raise_for_status()
        sopa_busqueda = BeautifulSoup(res_busqueda.text, 'html.parser')
        
        enlaces = sopa_busqueda.find_all('a', href=re.compile(r'handle/\d+/\d+'))
        if not enlaces:
            return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
            
        match = re.search(r'(handle/\d+/\d+)', enlaces[0]['href'])
        if not match:
            return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
            
        handle_encontrado = match.group(1)
        url_stats = f"{url_base}/{handle_encontrado}/statistics"
        
        time.sleep(1) # Otra pequeña pausa humana
        res_stats = sesion.get(url_stats, headers=CABECERAS, timeout=30, verify=False)
        res_stats.raise_for_status()
        sopa_stats = BeautifulSoup(res_stats.text, 'html.parser')
        
        celda_numero = sopa_stats.find('td', class_='datacell')
        if celda_numero:
            visitas = celda_numero.get_text(strip=True)
            return {"estado": "✅ Encontrado", "visitas": visitas, "enlace": url_stats}
        else:
            return {"estado": "⚠️ Dato no visible", "visitas": None, "enlace": url_stats}
            
    except requests.exceptions.ConnectionError:
         return {"estado": "⚠️ Error: Conexión rechazada (Posible bloqueo por IP)", "visitas": None, "enlace": None}
    except requests.exceptions.Timeout:
        return {"estado": "⚠️ Tiempo agotado", "visitas": None, "enlace": None}
    except Exception as e:
        return {"estado": f"⚠️ Error: {type(e).__name__}", "visitas": None, "enlace": None}


def extraer_uca(doi):
    """Módulo especialista para RODIN (Universidad de Cádiz)"""
    url_base = "https://rodin.uca.es"
    # Quitamos las comillas %22 para que la BD de Cádiz no colapse
    url_busqueda = f"{url_base}/discover?query={doi}"
    sesion = crear_sesion_robusta()
    
    try:
        res_busqueda = sesion.get(url_busqueda, headers=CABECERAS, timeout=30, verify=False)
        res_busqueda.raise_for_status()
        sopa_busqueda = BeautifulSoup(res_busqueda.text, 'html.parser')
        
        enlaces = sopa_busqueda.find_all('a', href=re.compile(r'handle/\d+/\d+'))
        if not enlaces:
            return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
            
        match = re.search(r'(handle/\d+/\d+)', enlaces[0]['href'])
        if not match:
            return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
            
        handle_encontrado = match.group(1)
        url_stats = f"{url_base}/{handle_encontrado}/statistics"
        
        res_stats = sesion.get(url_stats, headers=CABECERAS, timeout=30, verify=False)
        res_stats.raise_for_status()
        sopa_stats = BeautifulSoup(res_stats.text, 'html.parser')
        
        celda_numero = sopa_stats.find('td', class_='datacell')
        if celda_numero:
            visitas = celda_numero.get_text(strip=True)
            return {"estado": "✅ Encontrado", "visitas": visitas, "enlace": url_stats}
        else:
            return {"estado": "⚠️ Dato no visible", "visitas": None, "enlace": url_stats}
            
    except requests.exceptions.Timeout:
        return {"estado": "⚠️ Tiempo agotado", "visitas": None, "enlace": None}
    except Exception as e:
        return {"estado": f"⚠️ Error: {type(e).__name__}", "visitas": None, "enlace": None}


def extraer_upo(doi):
    """Módulo especialista para RIO (Universidad Pablo de Olavide)"""
    return {"estado": "⏳ Pendiente de programar", "visitas": None, "enlace": None}

# ==========================================
# 2. DIRECTORIO GENERAL
# ==========================================
REPOSITORIOS = {
    "Helvia (Córdoba)": extraer_uco,
    "RODIN (Cádiz)": extraer_uca,
    "RIO (Olavide)": extraer_upo
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
        
        for nombre_repo, funcion_especialista in REPOSITORIOS.items():
            with st.spinner(f"Consultando a {nombre_repo}..."):
                resultado = funcion_especialista(doi_input)
                
                with st.expander(f"📌 {nombre_repo} - {resultado['estado']}", expanded=True):
                    if resultado['visitas']:
                        st.info(f"📊 **Visualizaciones totales:** {resultado['visitas']}")
                    if resultado['enlace']:
                        st.write(f"🔗 [Ver estadísticas oficiales]({resultado['enlace']})")
                    if not resultado['visitas'] and not resultado['enlace']:
                         st.write("Módulo en construcción o dato no encontrado.")
    else:
        st.error("Por favor, introduce un DOI para comenzar.")
