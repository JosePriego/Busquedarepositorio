import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import urllib3
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. DIRECTORIO DE REPOSITORIOS
# ==========================================
REPOSITORIOS_ANDALUCIA = {
    "Helvia (Córdoba)": {"url_base": "https://helvia.uco.es", "es_dspace7": False},
    "idUS (Sevilla)": {"url_base": "https://idus.us.es", "es_dspace7": False},
    "Digibug (Granada)": {"url_base": "https://digibug.ugr.es", "es_dspace7": False},
    "RODIN (Cádiz)": {"url_base": "https://rodin.uca.es", "es_dspace7": False},
    "riUAL (Almería)": {"url_base": "https://repositorio.ual.es", "es_dspace7": False},
    "Arias Montano (Huelva)": {"url_base": "https://ariasmontano.uhu.es", "es_dspace7": False},
    "Ruja (Jaén)": {"url_base": "https://ruja.ujaen.es", "es_dspace7": False},
    "Riuma (Málaga)": {"url_base": "https://riuma.uma.es", "es_dspace7": False},
    "RIO (Olavide)": {"url_base": "https://rio.upo.es", "es_dspace7": True}, 
    "UNIA (Andalucía)": {"url_base": "https://dspace.unia.es", "es_dspace7": False}
}

CABECERAS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

def crear_sesion():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    return s

# ==========================================
# 2. LÓGICA DE EXTRACCIÓN
# ==========================================

def procesar_repositorio(nombre, config, doi):
    url_base = config["url_base"]
    sesion = crear_sesion()
    
    # 1. BUSQUEDA EN DSPACE 7 (API JSON)
    if config["es_dspace7"]:
        # DSpace 7 prefiere el DOI sin comillas en la API
        url_api = f"{url_base}/server/api/discover/search/objects?query={doi}&scope="
        try:
            res = sesion.get(url_api, headers=CABECERAS, timeout=25, verify=False)
            data = res.json()
            # Navegamos por el JSON para encontrar el UUID
            if "_embedded" in data and "searchObjects" in data["_embedded"]:
                obj = data["_embedded"]["searchObjects"][0]["_embedded"]["indexableObject"]
                uuid = obj["uuid"]
                return {"nombre": nombre, "estado": "✅ Encontrado", "id": uuid, "tipo": "dspace7", "url_base": url_base}
        except: pass
        return {"nombre": nombre, "estado": "❌ No encontrado", "id": None}

    # 2. BUSQUEDA EN DSPACE CLÁSICO (HTML)
    rutas = ["/discover?query={doi}", "/search?query={doi}", "/xmlui/discover?query={doi}"]
    for r in rutas:
        url = f"{url_base}{r.format(doi=doi)}"
        try:
            res = sesion.get(url, headers=CABECERAS, timeout=20, verify=False)
            if res.status_code == 200:
                sopa = BeautifulSoup(res.text, 'html.parser')
                # Buscamos cualquier enlace que parezca un Handle
                enlaces = sopa.find_all('a', href=re.compile(r'handle/\d+/\d+'))
                if enlaces:
                    handle = re.search(r'handle/(\d+/\d+)', enlaces[0]['href']).group(1)
                    return {"nombre": nombre, "estado": "✅ Encontrado", "id": handle, "tipo": "clasico", "url_base": url_base}
        except: continue
    
    return {"nombre": nombre, "estado": "❌ No encontrado", "id": None}

def obtener_stats(info):
    url_base = info["url_base"]
    id_obj = info["id"]
    sesion = crear_sesion()

    if info["tipo"] == "dspace7":
        # ¡MAGIA! Llamamos a la API de estadísticas de DSpace 7 directamente
        url_stats_api = f"{url_base}/server/api/statistics/viewevents/search/total?scope={id_obj}&type=item"
        url_publica = f"{url_base}/statistics/items/{id_obj}"
        try:
            res = sesion.get(url_stats_api, headers=CABECERAS, timeout=15, verify=False)
            total = res.json().get("total", "No disponible")
            return f"{total} (Dato de API)", url_publica
        except:
            return "Ver en web (API protegida)", url_publica

    # DSpace Clásico
    url_stats = f"{url_base}/handle/{id_obj}/statistics"
    try:
        res = sesion.get(url_stats, headers=CABECERAS, timeout=15, verify=False)
        sopa = BeautifulSoup(res.text, 'html.parser')
        # Buscamos en la tabla de datos
        celda = sopa.find('td', class_='datacell') or sopa.find('td', string=re.compile(r'^\d+$'))
        if celda:
            return celda.get_text(strip=True), url_stats
        return "Dato no visible", url_stats
    except:
        return "Error de lectura", url_stats

# ==========================================
# 3. INTERFAZ
# ==========================================

st.set_page_config(page_title="Impacto Andalucía", layout="wide")
st.title("🌍 Monitor de Impacto Andalucía")

doi_input = st.text_input("Introduce el DOI del artículo:", placeholder="10.3390/healthcare9091216").strip()

if st.button("🚀 Iniciar Rastreo"):
    if doi_input:
        with st.spinner("Buscando en toda la red andaluza..."):
            # Paralelismo para ir rápido
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futuros = [executor.submit(procesar_repositorio, n, c, doi_input) for n, c in REPOSITORIOS_ANDALUCIA.items()]
                resultados = [f.result() for f in concurrent.futures.as_completed(futuros)]
            
            # Informe de búsqueda
            st.subheader("📡 Informe de Búsqueda")
            resultados = sorted(resultados, key=lambda x: x['nombre'])
            cols = st.columns(2)
            for i, r in enumerate(resultados):
                cols[i%2].write(f"**{r['nombre']}**: {r['estado']}")
            
            # Resultados detallados
            hallazgos = [r for r in resultados if r["id"]]
            if hallazgos:
                st.divider()
                st.success(f"Se han encontrado {len(hallazgos)} fuentes.")
                for h in hallazgos:
                    with st.expander(f"📊 Estadísticas en {h['nombre']}", expanded=True):
                        valor, link = obtener_stats(h)
                        st.metric("Visualizaciones Totales", valor)
                        st.write(f"🔗 [Enlace oficial a la fuente]({link})")
            else:
                st.error("No se ha encontrado el DOI en ningún repositorio. Verifica que el DOI sea correcto.")
