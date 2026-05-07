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
    """Módulo para RIO (Olavide) - Estrategia de Enlace de Rescate"""
    url_base = "https://rio.upo.es"
    sesion = crear_sesion_robusta()
    
    # Usamos cabeceras estándar de navegador, sin disfraces de Google que puedan fallar
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, application/hal+json'
    }
    
    # Buscamos solo la parte final del DOI para no activar el firewall
    doi_busqueda = doi.split('/')[-1] if '/' in doi else doi
        
    try:
        url_api_busqueda = f"{url_base}/server/api/discover/search/objects?query={doi_busqueda}"
        res_busqueda = sesion.get(url_api_busqueda, headers=headers, timeout=20, verify=False)
        
        # Si hay respuesta exitosa (JSON)
        if res_busqueda.status_code == 200 and "json" in res_busqueda.headers.get("Content-Type", "").lower():
            datos = res_busqueda.json()
            if "_embedded" in datos and "searchObjects" in datos["_embedded"] and len(datos["_embedded"]["searchObjects"]) > 0:
                # Localizamos el UUID
                objeto = datos["_embedded"]["searchObjects"][0]
                uuid = objeto["_embedded"]["indexableObject"]["uuid"]
                
                # Intentamos la última llamada para el número
                url_api_stats = f"{url_base}/server/api/statistics/viewevents/search/total?scope={uuid}&type=item"
                res_stats = sesion.get(url_api_stats, headers=headers, timeout=15, verify=False)
                
                if res_stats.status_code == 200:
                    total = res_stats.json().get("total", 0)
                    return {"estado": "✅ Encontrado", "visitas": str(total), "enlace": f"{url_base}/statistics/items/{uuid}"}
                else:
                    # SI EL FIREWALL BLOQUEA EL NÚMERO, DAMOS EL ENLACE
                    return {"estado": "✅ Localizado (Carga manual)", "visitas": "Hacer clic abajo", "enlace": f"{url_base}/statistics/items/{uuid}"}
        
        # Si hay bloqueo total, generamos una URL de búsqueda manual para el usuario
        url_manual = f"{url_base}/search?query={doi}"
        return {"estado": "⚠️ Protegido por Firewall", "visitas": None, "enlace": url_manual}
        
    except Exception:
        return {"estado": "❌ No se pudo conectar", "visitas": None, "enlace": f"{url_base}/search?query={doi}"}

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
