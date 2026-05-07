import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import urllib3
import concurrent.futures
# NUESTRA NUEVA ARMA: El suplantador de huella digital de Chrome
from curl_cffi import requests as c_requests

# Silenciamos las advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CABECERAS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

def crear_sesion_robusta():
    sesion = requests.Session()
    reintentos = Retry(total=3, backoff_factor=1, status_forcelist=[403, 500, 502, 503, 504])
    adaptador = HTTPAdapter(max_retries=reintentos)
    sesion.mount('http://', adaptador)
    sesion.mount('https://', adaptador)
    return sesion

# ==========================================
# 1. MÓDULOS DE EXTRACCIÓN (ESPECIALISTAS)
# ==========================================

def extraer_uco(doi):
    """Módulo para Helvia (Córdoba)"""
    url_base = "https://helvia.uco.es"
    sesion = crear_sesion_robusta()
    try:
        res_busqueda = sesion.get(f"{url_base}/discover?query={doi}", headers=CABECERAS, timeout=20, verify=False)
        sopa_busqueda = BeautifulSoup(res_busqueda.text, 'html.parser')
        enlaces = sopa_busqueda.find_all('a', href=re.compile(r'handle/\d+/\d+'))
        
        if not enlaces: return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}

        for link in enlaces[:3]:
            handle_path = re.search(r'(handle/\d+/\d+)', link['href']).group(1)
            url_articulo = f"{url_base}/{handle_path}"
            res_art = sesion.get(url_articulo, headers=CABECERAS, timeout=15, verify=False)
            if doi.lower() in res_art.text.lower():
                url_stats = f"{url_articulo}/statistics"
                res_stats = sesion.get(url_stats, headers=CABECERAS, timeout=15, verify=False)
                celda = BeautifulSoup(res_stats.text, 'html.parser').find('td', class_='datacell')
                return {"estado": "✅ Verificado", "visitas": celda.get_text(strip=True) if celda else "0", "enlace": url_stats}
        return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
    except: return {"estado": "⚠️ Error de conexión", "visitas": None, "enlace": None}

def extraer_uca(doi):
    """Módulo para RODIN (Cádiz)"""
    url_base = "https://rodin.uca.es"
    sesion = crear_sesion_robusta()
    try:
        res_busqueda = sesion.get(f"{url_base}/discover?query={doi}", headers=CABECERAS, timeout=20, verify=False)
        sopa_busqueda = BeautifulSoup(res_busqueda.text, 'html.parser')
        enlaces = sopa_busqueda.find_all('a', href=re.compile(r'handle/\d+/\d+'))
        
        if not enlaces: return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}

        for link in enlaces[:3]:
            handle_path = re.search(r'(handle/\d+/\d+)', link['href']).group(1)
            url_articulo = f"{url_base}/{handle_path}"
            res_art = sesion.get(url_articulo, headers=CABECERAS, timeout=15, verify=False)
            if doi.lower() in res_art.text.lower():
                url_stats = f"{url_articulo}/statistics"
                res_stats = sesion.get(url_stats, headers=CABECERAS, timeout=15, verify=False)
                celda = BeautifulSoup(res_stats.text, 'html.parser').find('td', class_='datacell')
                return {"estado": "✅ Verificado", "visitas": celda.get_text(strip=True) if celda else "0", "enlace": url_stats}
        return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
    except: return {"estado": "⚠️ Error de conexión", "visitas": None, "enlace": None}


def extraer_upo(doi):
    """Módulo para RIO (Olavide) - ESTRATEGIA GOOGLEBOT"""
    url_base = "https://rio.upo.es"
    
    # Volvemos a la sesión normal, pero con el "Carnet de Identidad" de Google
    sesion = crear_sesion_robusta()
    
    headers_googlebot = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept': 'application/json, application/hal+json'
    }
    
    doi_busqueda = doi.split('/')[-1] if '/' in doi else doi
        
    try:
        url_api_busqueda = f"{url_base}/server/api/discover/search/objects?query={doi_busqueda}"
        res_busqueda = sesion.get(url_api_busqueda, headers=headers_googlebot, timeout=25, verify=False)
        
        if "json" not in res_busqueda.headers.get("Content-Type", "").lower():
            return {"estado": "⚠️ Bloqueo de IP estricto (Requiere ejecución local)", "visitas": None, "enlace": None}
             
        datos = res_busqueda.json()
        
        if "_embedded" in datos and "searchObjects" in datos["_embedded"] and len(datos["_embedded"]["searchObjects"]) > 0:
            uuid_correcto = None
            for objeto in datos["_embedded"]["searchObjects"]:
                item = objeto["_embedded"]["indexableObject"]
                if doi.lower() in str(item).lower():
                    uuid_correcto = item["uuid"]
                    break
            
            if uuid_correcto:
                url_api_stats = f"{url_base}/server/api/statistics/viewevents/search/total?scope={uuid_correcto}&type=item"
                res_stats = sesion.get(url_api_stats, headers=headers_googlebot, timeout=20, verify=False)
                
                if "json" in res_stats.headers.get("Content-Type", "").lower():
                    total = res_stats.json().get("total", 0)
                    return {"estado": "✅ Encontrado (Vía Googlebot)", "visitas": str(total), "enlace": f"{url_base}/statistics/items/{uuid_correcto}"}
                else:
                    return {"estado": "✅ Encontrado", "visitas": None, "enlace": f"{url_base}/statistics/items/{uuid_correcto}"}
            
        return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
    except Exception as e:
        return {"estado": f"⚠️ Error: {type(e).__name__}", "visitas": None, "enlace": None}

# ==========================================
# 2. MOTOR DE BÚSQUEDA SIMULTÁNEA
# ==========================================
REPOSITORIOS = {
    "Helvia (Córdoba)": extraer_uco,
    "RODIN (Cádiz)": extraer_uca,
    "RIO (Olavide)": extraer_upo
}

# ==========================================
# 3. INTERFAZ STREAMLIT
# ==========================================
st.set_page_config(page_title="Impacto Andalucía", layout="centered")
st.title("🌍 Monitor de Impacto Andalucía")

doi_input = st.text_input("Introduce el DOI del artículo:", placeholder="10.3390/healthcare9091216").strip()

if st.button("🚀 Iniciar Rastreo"):
    if doi_input:
        st.subheader("📡 Informe de Búsqueda")
        resultados_finales = {}
        
        with st.spinner("Lanzando drones de búsqueda a las bases de datos..."):
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ejecutor:
                futuros = {ejecutor.submit(func, doi_input): nombre for nombre, func in REPOSITORIOS.items()}
                for futuro in concurrent.futures.as_completed(futuros):
                    resultados_finales[futuros[futuro]] = futuro.result()
        
        for nombre in REPOSITORIOS.keys():
            res = resultados_finales.get(nombre)
            with st.expander(f"📌 {nombre} - {res['estado']}", expanded=True):
                if res['visitas']:
                    st.metric("Visualizaciones Totales", res['visitas'])
                if res['enlace']:
                    st.write(f"🔗 [Enlace oficial a la fuente]({res['enlace']})")
    else:
        st.error("Por favor, introduce un DOI.")
