import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import urllib3
import time
import concurrent.futures

# Silenciamos las advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# CONSTANTES Y CONFIGURACIÓN DE RED
# ==========================================
CABECERAS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
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
    url_busqueda = f"{url_base}/discover?query={doi}"
    sesion = crear_sesion_robusta()
    try:
        res_busqueda = sesion.get(url_busqueda, headers=CABECERAS, timeout=20, verify=False)
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
    url_busqueda = f"{url_base}/discover?query={doi}"
    sesion = crear_sesion_robusta()
    try:
        res_busqueda = sesion.get(url_busqueda, headers=CABECERAS, timeout=20, verify=False)
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
    """Módulo para RIO (Olavide) - DSpace 7 API (Evasión por Sufijo)"""
    url_base = "https://rio.upo.es"
    sesion = crear_sesion_robusta()
    
    headers_api = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, application/hal+json'
    }
    
    # EL TRUCO: Cortamos el DOI por la barra '/' y nos quedamos solo con la parte final
    # Así el cortafuegos de la universidad no pensará que somos un ataque informático.
    if '/' in doi:
        doi_busqueda = doi.split('/')[-1]
    else:
        doi_busqueda = doi
        
    try:
        url_api_busqueda = f"{url_base}/server/api/discover/search/objects?query={doi_busqueda}"
        res_busqueda = sesion.get(url_api_busqueda, headers=headers_api, timeout=25, verify=False)
        
        if res_busqueda.status_code != 200:
             return {"estado": f"⚠️ Cortafuegos (Código {res_busqueda.status_code})", "visitas": None, "enlace": None}
             
        try:
            datos = res_busqueda.json()
        except:
            return {"estado": "⚠️ Bloqueo de datos", "visitas": None, "enlace": None}
        
        if "_embedded" in datos and "searchObjects" in datos["_embedded"] and len(datos["_embedded"]["searchObjects"]) > 0:
            
            # Filtramos los resultados para asegurarnos de que es nuestro artículo exacto
            uuid_correcto = None
            for objeto in datos["_embedded"]["searchObjects"]:
                item = objeto["_embedded"]["indexableObject"]
                # Comprobamos que el DOI completo está escondido en los metadatos del artículo
                if doi.lower() in str(item).lower():
                    uuid_correcto = item["uuid"]
                    break
            
            if uuid_correcto:
                # Pedimos las estadísticas del UUID correcto
                url_api_stats = f"{url_base}/server/api/statistics/viewevents/search/total?scope={uuid_correcto}&type=item"
                res_stats = sesion.get(url_api_stats, headers=headers_api, timeout=20, verify=False)
                
                if res_stats.status_code == 200:
                    total = res_stats.json().get("total", 0)
                    return {"estado": "✅ Encontrado", "visitas": str(total), "enlace": f"{url_base}/statistics/items/{uuid_correcto}"}
                else:
                    return {"estado": "✅ Encontrado (Stats ocultas)", "visitas": None, "enlace": f"{url_base}/statistics/items/{uuid_correcto}"}
            
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
        
        with st.spinner("Lanzando búsqueda fantasma a las bases de datos..."):
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
