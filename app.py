import streamlit as st
import requests
from bs4 import BeautifulSoup

# --- FUNCIONES DE LÓGICA ---

def obtener_url_desde_doi(doi):
    """Resuelve el DOI usando la API de Crossref."""
    url_api = f"https://api.crossref.org/works/{doi}"
    try:
        respuesta = requests.get(url_api)
        respuesta.raise_for_status()
        datos = respuesta.json()
        return datos['message'].get('URL')
    except:
        return None

def extraer_visualizaciones_dspace(url_repo):
    """Extrae las visualizaciones de una página de DSpace."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} # Simulamos un navegador
        respuesta = requests.get(url_repo, headers=headers)
        respuesta.raise_for_status()
        
        sopa = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Estrategia de búsqueda: buscamos etiquetas que suelan contener estadísticas
        # DSpace suele usar clases como 'ds-table' o texto como 'Statistics' / 'Visualizaciones'
        elemento = sopa.find(string=lambda t: t and ('Visualizaciones' in t or 'Views' in t or 'Visitas' in t))
        
        if elemento:
            # Intentamos obtener el número que acompaña al texto
            return elemento.parent.get_text(strip=True)
        return "No disponible"
    except:
        return "Error al acceder al repositorio"

# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.title("📊 Extractor de Métricas DSpace")
st.write("Introduce un DOI para conocer el impacto del artículo en su repositorio institucional.")

# Caja de búsqueda
doi_usuario = st.text_input("Introduce el DOI (ejemplo: 10.1371/journal.pone.0115069)", "")

if st.button("Buscar estadísticas"):
    if doi_usuario:
        with st.spinner("Buscando información..."):
            # 1. Obtener URL
            url_articulo = obtener_url_desde_doi(doi_usuario)
            
            if url_articulo:
                # 2. Obtener Visualizaciones
                conteo = extraer_visualizaciones_dspace(url_articulo)
                
                # 3. Mostrar Resultado
                st.success(f"¡Articulo encontrado!")
                st.info(f"En el repositorio ha tenido **{conteo}** visualizaciones.")
                st.write(f"🔗 [Enlace al artículo]({url_articulo})")
            else:
                st.error("No se pudo encontrar una URL válida para ese DOI.")
    else:
        st.warning("Por favor, introduce un DOI.")
