import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import urllib3
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. DIRECTORIO DE REPOSITORIOS (ANDALUCÍA)
# ==========================================
# Añadimos un "interruptor" (es_dspace7) a nuestro diccionario.
REPOSITORIOS_ANDALUCIA = {
    "Helvia (Córdoba)": {"url_base": "https://helvia.uco.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False},
    "idUS (Sevilla)": {"url_base": "https://idus.us.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False},
    "Digibug (Granada)": {"url_base": "https://digibug.ugr.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False},
    "RODIN (Cádiz)": {"url_base": "https://rodin.uca.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False},
    "riUAL (Almería)": {"url_base": "https://repositorio.ual.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False},
    "Arias Montano (Huelva)": {"url_base": "https://ariasmontano.uhu.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False},
    "Ruja (Jaén)": {"url_base": "https://ruja.ujaen.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False},
    "Riuma (Málaga)": {"url_base": "https://riuma.uma.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False},
    "RIO (Olavide)": {"url_base": "https://rio.upo.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": True}, # ¡Activamos el modo DSpace 7!
    "UNIA (Andalucía)": {"url_base": "https://dspace.unia.es", "patron_handle": r'handle/(\d+/\d+)', "es_dspace7": False}
}

CABECERAS_CLASICAS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# ==========================================
# 2. LÓGICA DE PROGRAMACIÓN (BACKEND MULTIHILO)
# ==========================================

def procesar_un_repositorio(nombre_repo, config, doi):
    url_base = config["url_base"]
    patron_regex = config["patron_handle"]
    es_dspace7 = config.get("es_dspace7", False)
    
    estado_final = "❌ No encontrado"
    datos_utiles = None

    # ESTRATEGIA A: Para repositorios modernos (UPO)
    if es_dspace7:
        # Usamos la puerta trasera (API) y forzamos las comillas para precisión
        url_api = f"{url_base}/server/api/discover/search/objects?query=%22{doi}%22"
        try:
            res = requests.get(url_api, headers=CABECERAS_CLASICAS, timeout=15, verify=False)
            res.raise_for_status()
            
            # La API devuelve un texto puro. Buscamos cualquier Handle que aparezca dentro.
            match = re.search(r'(\d{4,5}/\d+)', res.text)
            
            if match:
                posible_handle = match.group(1)
                # Verificamos si realmente el DOI está asociado a este artículo
                url_item_api = f"{url_base}/server/api/core/items/{posible_handle}" # Endpoint genérico
                # Para simplificar y asegurar, verificamos el DOI en el texto crudo de la respuesta inicial
                if doi.lower() in res.text.lower():
                    datos_utiles = {"url_base": url_base, "handle": posible_handle}
                    estado_final = "✅ Encontrado"

        except Exception as e:
            estado_final = f"⚠️ Error API: {type(e).__name__}"

        return {"nombre_repo": nombre_repo, "estado": estado_final, "datos_utiles": datos_utiles}


    # ESTRATEGIA B: Para repositorios clásicos (HTML) (UCO, US, UGR...)
    RUTAS_COMUNES = [
        "/discover?query={doi}",        
        "/search?query={doi}",          
        "/simple-search?query={doi}",   
        "/xmlui/discover?query={doi}"   
    ]

    for ruta in RUTAS_COMUNES:
        url_busqueda = f"{url_base}{ruta.format(doi=doi)}"
        try:
            res = requests.get(url_busqueda, headers=CABECERAS_CLASICAS, timeout=15, verify=False)
            
            if res.status_code == 404:
                continue 
                
            res.raise_for_status()
            sopa = BeautifulSoup(res.text, 'html.parser')
            enlaces = sopa.find_all('a', href=re.compile(patron_regex))
            
            handle_verificado = False
            if enlaces:
                handles_unicos = []
                for enlace in enlaces:
                    match = re.search(patron_regex, enlace['href'])
                    if match and match.group(1) not in handles_unicos:
                        handles_unicos.append(match.group(1))
                
                for posible_handle in handles_unicos[:3]:
                    url_item = f"{url_base}/handle/{posible_handle}"
                    try:
                        res_item = requests.get(url_item, headers=CABECERAS_CLASICAS, timeout=10, verify=False)
                        if doi.lower() in res_item.text.lower():
                            datos_utiles = {"url_base": url_base, "handle": posible_handle}
                            estado_final = "✅ Encontrado"
                            handle_verificado = True
                            break 
                    except:
                        continue 
            
            if handle_verificado:
                break 
                
        except requests.exceptions.HTTPError as e:
            estado_final = f"⚠️ Error {e.response.status_code}"
            break
        except requests.exceptions.Timeout:
            estado_final = "⚠️ Tiempo agotado"
            break
        except Exception as e:
            estado_final = f"⚠️ Error: {type(e).__name__}"
            break

    return {"nombre_repo": nombre_repo, "estado": estado_final, "datos_utiles": datos_utiles}


def buscar_doi_en_andalucia_paralelo(doi):
    registro_completo = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ejecutor:
        futuros = []
        for nombre_repo, config in REPOSITORIOS_ANDALUCIA.items():
            tarea = ejecutor.submit(procesar_un_repositorio, nombre_repo, config, doi)
            futuros.append(tarea)
            
        for tarea_completada in concurrent.futures.as_completed(futuros):
            resultado = tarea_completada.result()
            registro_completo.append(resultado)

    registro_completo = sorted(registro_completo, key=lambda x: x['nombre_repo'])
    return registro_completo

def extraer_estadisticas_universales(url_base, handle):
    # En DSpace 7, las estadísticas a veces se muestran igual en /statistics, 
    # pero vamos a intentar la ruta estándar por si mantienen compatibilidad.
    url_estadisticas = f"{url_base}/handle/{handle}/statistics"
    try:
        res = requests.get(url_estadisticas, headers=CABECERAS_CLASICAS, timeout=15, verify=False)
        res.raise_for_status()
        sopa = BeautifulSoup(res.text, 'html.parser')
        
        celda_numero = sopa.find('td', class_='datacell')
        if celda_numero:
            return celda_numero.get_text(strip=True), url_estadisticas
            
        return "Dato no visible públicamente en HTML", url_estadisticas
    except Exception:
        return f"Error de lectura (posible API requerida)", url_estadisticas

# ==========================================
# 3. INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================

st.set_page_config(page_title="Impacto Andalucía", page_icon="🌍", layout="centered")
st.title("🌍 Buscador de Impacto: Red de Repositorios")
st.write("Introduce un DOI para buscarlo simultáneamente y ver el estado de cada repositorio en tiempo real.")

doi_input = st.text_input("Introduce el DOI:", placeholder="Ejemplo: 10.3390/cells9061353")

if st.button("Rastrear en Andalucía"):
    if doi_input:
        with st.spinner("🚀 Explorando bases de datos (HTML y API) en paralelo..."):
            registro_busqueda = buscar_doi_en_andalucia_paralelo(doi_input)
            
            st.subheader("📡 Informe de Búsqueda")
            
            col1, col2 = st.columns(2)
            for i, item in enumerate(registro_busqueda):
                if i < 5:
                    col1.write(f"**{item['nombre_repo']}**: {item['estado']}")
                else:
                    col2.write(f"**{item['nombre_repo']}**: {item['estado']}")
            
            st.divider()

            hallazgos = [item for item in registro_busqueda if item["datos_utiles"] is not None]
            
            if not hallazgos:
                st.warning("No se ha encontrado este artículo exacto en ninguno de los repositorios.")
            else:
                st.success(f"¡Extracción lista! Artículo encontrado y verificado en {len(hallazgos)} repositorio(s).")
                
                for item in hallazgos:
                    nombre = item["nombre_repo"]
                    url_base = item["datos_utiles"]["url_base"]
                    handle = item["datos_utiles"]["handle"]
                    
                    with st.expander(f"📌 Estadísticas en: {nombre}", expanded=True):
                        st.write(f"**Handle Verificado:** `{handle}`")
                        
                        datos_visitas, url_stats = extraer_estadisticas_universales(url_base, handle)
                        
                        if "Error" in datos_visitas or "no encontrado" in datos_visitas:
                            st.warning(f"Estadísticas: {datos_visitas}")
                        else:
                            st.info(f"📊 **Visualizaciones totales:** {datos_visitas}")
                            
                        st.write(f"🔗 [Ver estadísticas oficiales]({url_stats})")
    else:
        st.error("Por favor, introduce un DOI para comenzar.")
