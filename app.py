import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# --- FUNCIONES DE LÓGICA ---

def buscar_doi_en_helvia(doi):
    """Busca un DOI en Helvia (UCO) y extrae el Handle."""
    url_base = "https://helvia.uco.es"
    url_busqueda = f"{url_base}/discover?query={doi}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        respuesta = requests.get(url_busqueda, headers=headers, timeout=15)
        respuesta.raise_for_status()
        sopa = BeautifulSoup(respuesta.text, 'html.parser')
        enlaces = sopa.find_all('a', href=re.compile(r'handle/\d+/\d+'))
        
        if enlaces:
            for enlace in enlaces:
                match = re.search(r'handle/(\d+/\d+)', enlace['href'])
                if match:
                    return match.group(1), url_busqueda
        return None, url_busqueda
    except requests.exceptions.RequestException as e:
        return f"Error", str(e)

def extraer_estadisticas_helvia(handle):
    """
    Visita la página de estadísticas directas de un Handle en Helvia 
    y busca el número total de visitas.
    """
    # ¡Aquí aplicamos lo que descubriste en la imagen!
    url_estadisticas = f"https://helvia.uco.es/handle/{handle}/statistics"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url_estadisticas, headers=headers, timeout=15)
        res.raise_for_status()
        sopa = BeautifulSoup(res.text, 'html.parser')
        
        # En DSpace, las estadísticas suelen estar en tablas. 
        # Buscamos celdas que contengan la palabra "Visitas" o "Total"
        celda_visitas = sopa.find(string=lambda text: text and ('Total visitas' in text or 'Visitas' in text))
        
        if celda_visitas:
            # Si encontramos el texto, intentamos extraer el número de la celda de al lado o de su contenedor
            fila = celda_visitas.find_parent('tr')
            if fila:
                # Obtenemos todo el texto de la fila, limpiando espacios en blanco
                datos_fila = fila.get_text(separator=" | ", strip=True)
                return datos_fila, url_estadisticas
                
        return "Tabla de estadísticas no reconocida automáticamente.", url_estadisticas
        
    except Exception as e:
        return f"Error al acceder a las estadísticas: {e}", url_estadisticas


# --- INTERFAZ DE STREAMLIT ---

st.set_page_config(page_title="Helvia Tracker", page_icon="🎓")
st.title("🎓 Estadísticas en Helvia (UCO)")
st.write("Introduce el DOI para localizar el artículo y extraer sus visitas.")

doi_input = st.text_input("Introduce el DOI:", placeholder="Ejemplo: 10.3390/cells9061353")

if st.button("Obtener Estadísticas"):
    if doi_input:
        with st.spinner("Paso 1: Localizando el artículo en Helvia..."):
            handle, url_resultados = buscar_doi_en_helvia(doi_input)
            
            if handle == "Error":
                st.error("Hubo un problema de conexión con Helvia.")
            elif handle:
                st.success(f"¡Artículo localizado! Handle: `{handle}`")
                
                with st.spinner("Paso 2: Leyendo página de estadísticas..."):
                    # Llamamos a nuestra nueva función usando el Handle recién descubierto
                    datos_visitas, url_stats = extraer_estadisticas_helvia(handle)
                    
                    st.info(f"📊 **Datos extraídos:** {datos_visitas}")
                    st.write(f"🔗 [Enlace directo a las estadísticas oficiales]({url_stats})")
            else:
                st.warning("No se encontró este DOI en la base de datos de Helvia.")
    else:
        st.error("Por favor, introduce un DOI válido.")
