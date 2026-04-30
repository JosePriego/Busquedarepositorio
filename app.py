import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# ==========================================
# 1. DIRECTORIO DE REPOSITORIOS (ANDALUCÍA)
# ==========================================
REPOSITORIOS_ANDALUCIA = {
    "Helvia (Córdoba)": {
        "url_base": "https://helvia.uco.es", 
        "ruta_busqueda": "/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "idUS (Sevilla)": {
        "url_base": "https://idus.us.es", 
        "ruta_busqueda": "/xmlui/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "Digibug (Granada)": {
        "url_base": "https://digibug.ugr.es", 
        "ruta_busqueda": "/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "RODIN (Cádiz)": {
        "url_base": "https://rodin.uca.es", 
        "ruta_busqueda": "/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "riUAL (Almería)": {
        "url_base": "https://repositorio.ual.es", 
        "ruta_busqueda": "/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "Arias Montano (Huelva)": {
        "url_base": "https://ariasmontano.uhu.es", 
        "ruta_busqueda": "/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "Ruja (Jaén)": {
        "url_base": "https://ruja.ujaen.es", 
        "ruta_busqueda": "/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "Riuma (Málaga)": {
        "url_base": "https://riuma.uma.es", 
        "ruta_busqueda": "/xmlui/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "RIO (Olavide)": {
        "url_base": "https://rio.upo.es", 
        "ruta_busqueda": "/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    },
    "UNIA (Andalucía)": {
        "url_base": "https://dspace.unia.es", 
        "ruta_busqueda": "/discover?query=%22{doi}%22", 
        "patron_handle": r'handle/(\d+/\d+)'
    }
} # <--- ¡Esta es la llave que faltaba en tu código!

# ==========================================
# 2. LÓGICA DE PROGRAMACIÓN (BACKEND)
# ==========================================

def buscar_doi_en_andalucia(doi):
    """
    Recorre el diccionario buscando el DOI de forma estricta en todos los repositorios.
    """
    resultados_encontrados = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for nombre_repo, config in REPOSITORIOS_ANDALUCIA.items():
        url_base = config["url_base"]
        # Inyectamos el DOI en la ruta de búsqueda configurada
        ruta_especifica = config["ruta_busqueda"].format(doi=doi)
        url_busqueda = f"{url_base}{ruta_especifica}"
        
        try:
            res = requests.get(url_busqueda, headers=headers, timeout=10)
            res.raise_for_status()
            sopa = BeautifulSoup(res.text, 'html.parser')
            
            patron_regex = config["patron_handle"]
            enlaces = sopa.find_all('a', href=re.compile(patron_regex))
            
            if enlaces:
                for enlace in enlaces:
                    match = re.search(patron_regex, enlace['href'])
                    if match:
                        handle = match.group(1)
                        resultados_encontrados.append({
                            "nombre_repo": nombre_repo,
                            "url_base": url_base,
                            "handle": handle
                        })
                        break 
                        
        except Exception:
            continue 

    return resultados_encontrados

def extraer_estadisticas_universales(url_base, handle):
    """
    Visita la página de estadísticas de un repositorio y extrae el número.
    """
    url_estadisticas = f"{url_base}/handle/{handle}/statistics"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        res = requests.get(url_estadisticas, headers=headers, timeout=10)
        res.raise_for_status()
        sopa = BeautifulSoup(res.text, 'html.parser')
        
        celda_numero = sopa.find('td', class_='datacell')
        
        if celda_numero:
            numero_visualizaciones = celda_numero.get_text(strip=True)
            return numero_visualizaciones, url_estadisticas
            
        return "Dato no encontrado", url_estadisticas
        
    except Exception:
        return "Error al leer estadísticas", url_estadisticas

# ==========================================
# 3. INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================

st.set_page_config(page_title="Impacto Andalucía", page_icon="🌍", layout="centered")
st.title("🌍 Buscador de Impacto: Red de Repositorios de Andalucía")
st.write("Introduce un DOI para buscarlo simultáneamente en todas las universidades andaluzas y extraer sus estadísticas de visualización.")

doi_input = st.text_input("Introduce el DOI:", placeholder="Ejemplo: 10.3390/cells9061353")

if st.button("Rastrear en Andalucía"):
    if doi_input:
        with st.spinner("Buscando de forma estricta en 10 repositorios... Esto puede tardar unos segundos."):
            hallazgos = buscar_doi_en_andalucia(doi_input)
            
            if not hallazgos:
                st.warning("No se ha encontrado este artículo exacto en ninguno de los repositorios indexados.")
            else:
                st.success(f"¡Búsqueda finalizada! Artículo encontrado en {len(hallazgos)} repositorio(s).")
                
                for item in hallazgos:
                    nombre = item["nombre_repo"]
                    url_base = item["url_base"]
                    handle = item["handle"]
                    
                    with st.expander(f"📌 Resultados en: {nombre}", expanded=True):
                        st.write(f"**Handle:** `{handle}`")
                        
                        datos_visitas, url_stats = extraer_estadisticas_universales(url_base, handle)
                        
                        if "Error" in datos_visitas or "no encontrado" in datos_visitas:
                            st.warning(f"Estadísticas: {datos_visitas}")
                        else:
                            st.info(f"📊 **Visualizaciones totales:** {datos_visitas}")
                            
                        st.write(f"🔗 [Ver estadísticas oficiales]({url_stats})")
    else:
        st.error("Por favor, introduce un DOI para comenzar.")
