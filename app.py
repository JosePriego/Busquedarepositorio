import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. DIRECTORIO DE REPOSITORIOS (ANDALUCÍA)
# ==========================================
# Ya no necesitamos especificar la 'ruta_busqueda' aquí, 
# el bot lo descubrirá automáticamente.
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

# ==========================================
# 2. LÓGICA DE PROGRAMACIÓN (BACKEND)
# ==========================================

CABECERAS_CLASICAS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def buscar_doi_en_andalucia(doi):
    registro_completo = []
    
    # El "juego de llaves": Las 4 rutas más comunes en la historia de DSpace
    RUTAS_COMUNES = [
        "/discover?query=%22{doi}%22",        # DSpace 5 y 6 (Estándar)
        "/search?query=%22{doi}%22",          # DSpace 7 (Nuevo)
        "/simple-search?query=%22{doi}%22",   # DSpace antiguo (JSPUI)
        "/xmlui/discover?query=%22{doi}%22"   # DSpace antiguo (XMLUI)
    ]

    for nombre_repo, config in REPOSITORIOS_ANDALUCIA.items():
        url_base = config["url_base"]
        patron_regex = config["patron_handle"]
        
        estado_final = "❌ No encontrado" # Por defecto
        datos_utiles = None

        # Bucle de ensayo y error para las rutas
        for ruta in RUTAS_COMUNES:
            url_busqueda = f"{url_base}{ruta.format(doi=doi)}"
            
            try:
                res = requests.get(url_busqueda, headers=CABECERAS_CLASICAS, timeout=15, verify=False)
                
                # Si la página no existe, pasamos a la siguiente ruta de la lista
                if res.status_code == 404:
                    continue 
                    
                # Si hay otro tipo de error HTTP (como 403 o 500), lanzará una excepción
                res.raise_for_status()
                
                # Si llegamos aquí, la página cargó bien (Código 200). Buscamos el Handle.
                sopa = BeautifulSoup(res.text, 'html.parser')
                enlaces = sopa.find_all('a', href=re.compile(patron_regex))
                
                if enlaces:
                    for enlace in enlaces:
                        match = re.search(patron_regex, enlace['href'])
                        if match:
                            datos_utiles = {"url_base": url_base, "handle": match.group(1)}
                            estado_final = "✅ Encontrado"
                            break
                            
                # Rompemos el bucle de rutas porque ya encontramos una página de búsqueda válida
                break 

            except requests.exceptions.HTTPError as e:
                # Captura errores del servidor y rompe el bucle (no intentamos más rutas)
                estado_final = f"⚠️ Error {e.response.status_code}"
                break
            except requests.exceptions.Timeout:
                estado_final = "⚠️ Tiempo agotado"
                break
            except Exception as e:
                # Ahora imprimimos el nombre técnico del error para saber qué pasa exactamente
                nombre_error = type(e).__name__
                estado_final = f"⚠️ Error: {nombre_error}"
                break

        # Guardamos el resultado final del repositorio
        registro_completo.append({
            "nombre_repo": nombre_repo,
            "estado": estado_final,
            "datos_utiles": datos_utiles
        })

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
        with st.spinner("Rastreo avanzado en proceso... Probando múltiples rutas por servidor."):
            registro_busqueda = buscar_doi_en_andalucia(doi_input)
            
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
                st.success(f"¡Extracción lista! Artículo encontrado en {len(hallazgos)} repositorio(s).")
                
                for item in hallazgos:
                    nombre = item["nombre_repo"]
                    url_base = item["datos_utiles"]["url_base"]
                    handle = item["datos_utiles"]["handle"]
                    
                    with st.expander(f"📌 Estadísticas en: {nombre}", expanded=True):
                        st.write(f"**Handle:** `{handle}`")
                        
                        datos_visitas, url_stats = extraer_estadisticas_universales(url_base, handle)
                        
                        if "Error" in datos_visitas or "no encontrado" in datos_visitas:
                            st.warning(f"Estadísticas: {datos_visitas}")
                        else:
                            st.info(f"📊 **Visualizaciones totales:** {datos_visitas}")
                            
                        st.write(f"🔗 [Ver estadísticas oficiales]({url_stats})")
    else:
        st.error("Por favor, introduce un DOI para comenzar.")
