import streamlit as st
import requests
import re
from bs4 import BeautifulSoup

# --- FUNCIONES DE LÓGICA (BACKEND) ---

def obtener_url_repositorio(doi):
    """
    Consulta la API gratuita de Unpaywall para encontrar la versión del artículo 
    alojada en un repositorio institucional (Open Access).
    """
    # IMPORTANTE: Cambia este correo por el tuyo para cumplir con las normas de Unpaywall
    email = "jpriego@uco.es" 
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    
    try:
        respuesta = requests.get(api_url, timeout=10)
        
        # Esta es la forma correcta de comprobar si la conexión fue exitosa
        respuesta.raise_for_status() 
        
        datos = respuesta.json()
        
        # Buscamos entre las localizaciones para encontrar un repositorio
        for loc in datos.get('oa_locations', []):
            if loc.get('host_type') == 'repository':
                return loc.get('url_for_landing_page')
        
        return None
        
    except requests.exceptions.RequestException as e:
        # Capturamos errores de red y los devolvemos como texto
        return f"Error de conexión con la API: {e}"
    except Exception as e:
        return f"Error inesperado: {e}"

def extraer_handle_final(url_repo):
    """
    Analiza la URL del repositorio o su código HTML para extraer el Handle de DSpace.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # Visitamos la URL del repositorio
        res = requests.get(url_repo, headers=headers, timeout=15)
        
        # Estrategia 1: Buscar el Handle directamente en la URL final
        match = re.search(r'handle/(\d+/\d+)', res.url)
        if match:
            return match.group(1)
            
        # Estrategia 2: Buscar en las etiquetas meta del HTML (Dublin Core)
        sopa = BeautifulSoup(res.text, 'html.parser')
        meta = sopa.find('meta', attrs={'name': 'DC.identifier'})
        if meta and 'handle.net/' in meta['content']:
            return meta['content'].split('handle.net/')[-1]
            
        return "Handle no detectado en el HTML del repositorio."
        
    except Exception as e:
        return f"Error al acceder al repositorio: {e}"

# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.set_page_config(page_title="Localizador de Handle", page_icon="🔍")

st.title("🔍 Localizador de Handle desde DOI")
st.write("Esta app resuelve el problema de los DOI que apuntan a revistas comerciales, buscando la versión depositada en el **repositorio DSpace** de la institución.")

# Caja de entrada de texto
doi_usuario = st.text_input("Introduce el DOI del artículo:", placeholder="10.3390/cells9061353")

# Botón de acción
if st.button("Encontrar en Repositorio"):
    if doi_usuario:
        with st.spinner("Consultando bases de datos de acceso abierto..."):
            
            # Paso 1: Obtener la URL del repositorio
            resultado_unpaywall = obtener_url_repositorio(doi_usuario)
            
            # Verificamos si Unpaywall devolvió un error de texto
            if isinstance(resultado_unpaywall, str) and "Error" in resultado_unpaywall:
                st.error(resultado_unpaywall)
            
            # Verificamos si Unpaywall encontró una URL válida
            elif resultado_unpaywall:
                st.info(f"✅ ¡Versión en repositorio encontrada!\nURL: {resultado_unpaywall}")
                
                # Paso 2: Extraer el Handle de esa URL
                with st.spinner("Extrayendo identificador Handle..."):
                    handle = extraer_handle_final(resultado_unpaywall)
                    
                    if "Error" in handle or "no detectado" in handle:
                        st.warning(handle)
                    else:
                        st.success("¡Handle extraído con éxito!")
                        st.metric(label="Handle de DSpace", value=handle)
                        
            # Si no hubo error, pero tampoco encontró nada
            else:
                st.warning("No se encontró una versión de este artículo en repositorios institucionales públicos.")
    else:
        st.warning("Por favor, introduce un DOI antes de buscar.")
