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
REPOSITORIOS_ANDALUCIA = {
    "Helvia (Córdoba)": {"url_base": "https://helvia.uco.es", "patron_handle": r'handle/(\d+/\d+)'},
    "idUS (Sevilla)": {"url_base": "https://idus.us.es", "patron_handle": r'handle/(\d+/\d+)'},
    "Digibug (Granada)": {"url_base": "https://digibug.ugr.es", "patron_handle": r'handle/(\d+/\d+)'},
    "RODIN (Cádiz)": {"url_base": "https://rodin.uca.es", "patron_handle": r'handle/(\d+/\d+)'},
    "riUAL (Almería)": {"url_base": "https://repositorio.ual.es", "patron_handle": r'handle/(\d+/\d+)'},
    "Arias Montano (Huelva)": {"url_base": "https://ariasmontano.uhu.es", "patron_handle": r'handle/(\d+/\d+)'},
    "Ruja (Jaén)": {"url_base": "https://ruja.ujaen.es", "patron_handle": r'handle/(\d+/\d+)'},
    "Riuma (Málaga)": {"url_base": "https://riuma.uma.es", "patron_handle": r'handle/(\d+/\d+)'},
    "RIO (Olavide)": {"url_base": "https://rio.upo.es", "patron_handle": r'handle/(\d+/\d+)'},
    "UNIA (Andalucía)": {"url_base": "https://dspace.unia.es", "patron_handle": r'handle/(\d+/\d+)'}
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
    estado_final = "❌ No encontrado"
    datos_utiles = None

    # QUITAMOS LAS COMILLAS %22 PARA QUE LA UPO FUNCIONE
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
                # Extraemos Handles únicos para no procesar duplicados de la misma página
                handles_unicos = []
                for enlace in enlaces:
                    match = re.search(patron_regex, enlace['href'])
                    if match and match.group(1) not in handles_unicos:
                        handles_unicos.append(match.group(1))
                
                # --- FILTRO DE VERACIDAD ---
                # Visitamos solo los 3 primeros resultados para confirmar si el DOI está dentro
                for posible_handle in handles_unicos[:3]:
                    url_item = f"{url_base}/handle/{posible_handle}"
                    try:
                        res_item = requests.get(url_item, headers=CABECERAS_CLASICAS, timeout=10, verify=False)
                        # Si el texto del DOI aparece literalmente en la página del artículo:
                        if doi.lower() in res_item.text.lower():
                            datos_utiles = {"url_base": url_base, "handle": posible_handle}
                            estado_final = "✅ Encontrado"
                            handle_verificado = True
                            break # Encontramos el real, salimos del bucle de verificación
                    except:
                        continue # Si falla la conexión de este artículo, probamos el siguiente
            
            if handle_verificado:
                break # Salimos del bucle de rutas, éxito total
                
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
    url_estadisticas = f"{url_base}/handle/{handle}/statistics"
    try:
        res = requests.get(url_estadisticas, headers=CABECERAS_CLASICAS, timeout=15, verify=False)
        res.raise_for_status()
        sopa = BeautifulSoup(res.text, 'html.parser')
        
        celda_numero = sopa.find('td', class_='datacell')
        if celda_numero:
            return celda_numero.get_text(strip=True), url_estadisticas
            
        return "Dato no encontrado", url_estadisticas
    except Exception:
        return f"Error de lectura", url_estadisticas

# ==========================================
# 3. INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================

st.set_page_config(page_title="Impacto Andalucía", page_icon="🌍", layout="centered")
st.title("🌍 Buscador de Impacto: Red de Repositorios")
st.write("Introduce un DOI para buscarlo simultáneamente y ver el estado de cada repositorio en tiempo real.")

doi_input = st.text_input("Introduce el DOI:", placeholder="Ejemplo: 10.3390/cells9061353")

if st.button("Rastrear en Andalucía"):
    if doi_input:
        with st.spinner("🚀 Lanzando búsqueda inteligente y verificando resultados..."):
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
