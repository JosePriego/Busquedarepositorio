import streamlit as st
import requests
import re
from bs4 import BeautifulSoup

# --- FUNCIONES DE LÓGICA DE PROGRAMACIÓN ---

def buscar_url_repositorio(doi):
    """
    Usa la API de Unpaywall para saltar de la editorial al repositorio institucional.
    """
    # Unpaywall requiere un email para su base de datos gratuita
    email = "jpriego@uco.es"
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    
    try:
        respuesta = requests.get(api_url, timeout=10)
        if respuesta.status_status == 200:
            datos = respuesta.json()
            # Filtramos las ubicaciones para encontrar solo las de tipo 'repository'
            for loc in datos.get('oa_locations', []):
                if loc.get('host_type') == 'repository':
                    return loc.get('url_for_landing_page')
        return None
    except Exception as e:
        st.error(f"Error de conexión con la API: {e}")
        return None

def extraer_handle(url_repo):
    """
    Analiza la página del repositorio para localizar el identificador Handle.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url_repo, headers=headers, timeout=10)
        # 1. Intentar encontrar el Handle en la URL final (redireccionada)
        match = re.search(r'handle/(\d+/\d+)', res.url)
        if match:
            return match.group(1)
        
        # 2. Intentar buscar en los metadatos HTML (Dublin Core)
        sopa = BeautifulSoup(res.text, 'html.parser')
        meta_tag = sopa.find('meta', attrs={'name': 'DC.identifier'})
        if meta_tag and 'handle.net/' in meta_tag['content']:
            return meta_tag['content'].split('handle.net/')[-1]
            
        return "Handle no detectado visualmente."
    except Exception as e:
        return f"Error al analizar el repositorio: {e}"

# --- INTERFAZ DE USUARIO CON STREAMLIT ---

st.set_page_config(page_title="DOI to DSpace Handle", page_icon="🔗")

st.title("🔍 Localizador de Handle desde DOI")
st.markdown("""
Esta app resuelve el problema de los DOI que apuntan a revistas comerciales, 
buscando la versión depositada en el **repositorio DSpace** de la institución.
""")

doi_input = st.text_input("Introduce el DOI del artículo:", placeholder="Ej: 10.1016/j.jbiotec.2020.10.001")

if st.button("Encontrar en Repositorio"):
    if doi_input:
        with st.spinner("Consultando bases de datos de acceso abierto..."):
            url_inst = buscar_url_repositorio(doi_input.strip())
            
            if url_inst:
                handle_detectado = extraer_handle(url_inst)
                
                st.success("¡Versión en repositorio encontrada!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Handle Identificado", handle_detectado)
                with col2:
                    st.write(f"**Repositorio:** [Ir al sitio]({url_inst})")
                
                st.info(f"Ahora puedes usar el Handle **{handle_detectado}** para consultar las estadísticas en DSpace.")
            else:
                st.warning("No se encontró una versión de este artículo en repositorios institucionales públicos.")
    else:
        st.error("Por favor, introduce un DOI válido.")
