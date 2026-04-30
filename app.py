import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# --- FUNCIONES DE LÓGICA ---

def buscar_doi_en_helvia(doi):
    """
    Busca un DOI en el repositorio Helvia (UCO) y extrae el Handle.
    """
    url_base = "https://helvia.uco.es"
    # DSpace usa /discover para su búsqueda avanzada
    url_busqueda = f"{url_base}/discover?query={doi}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        respuesta = requests.get(url_busqueda, headers=headers, timeout=15)
        respuesta.raise_for_status() # Verifica que la conexión a Helvia fue exitosa
        
        sopa_html = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Buscamos en el HTML cualquier enlace que contenga la estructura de un Handle
        enlaces = sopa_html.find_all('a', href=re.compile(r'handle/\d+/\d+'))
        
        if enlaces:
            # Iteramos sobre los enlaces encontrados para extraer solo la parte numérica
            for enlace in enlaces:
                match = re.search(r'handle/(\d+/\d+)', enlace['href'])
                if match:
                    handle_encontrado = match.group(1)
                    # Devolvemos el handle y la URL de búsqueda para que el usuario pueda verificar
                    return handle_encontrado, url_busqueda
                    
        # Si llegamos aquí, Helvia cargó bien pero no encontró el DOI
        return None, url_busqueda
        
    except requests.exceptions.RequestException as e:
        return f"Error de conexión", str(e)

# --- INTERFAZ DE STREAMLIT ---

st.set_page_config(page_title="Helvia Tracker", page_icon="🎓")
st.title("🎓 Localizador en Helvia (UCO)")
st.write("Introduce el DOI de un artículo para comprobar si está depositado en el repositorio Helvia y obtener su identificador (Handle).")

# Caja de texto para el DOI
doi_input = st.text_input("Introduce el DOI:", placeholder="Ejemplo: 10.3390/cells9061353")

if st.button("Buscar en Helvia"):
    if doi_input:
        with st.spinner("Consultando la base de datos de Helvia..."):
            handle, url_resultados = buscar_doi_en_helvia(doi_input)
            
            if handle == "Error de conexión":
                st.error("Hubo un problema al intentar conectarse con los servidores de Helvia.")
                st.code(url_resultados) # Muestra el error técnico para depurar
            elif handle:
                st.success("¡Artículo localizado en Helvia!")
                st.write(f"**Handle detectado:** `{handle}`")
                
                # Construimos el enlace directo al artículo dentro de Helvia
                url_articulo_helvia = f"https://helvia.uco.es/handle/{handle}"
                st.write(f"🔗 [Ir a la página del artículo en Helvia]({url_articulo_helvia})")
            else:
                st.warning("La conexión fue exitosa, pero Helvia no devolvió resultados para este DOI.")
                st.write(f"Es posible que el artículo no esté depositado o que el DOI no esté en los metadatos. [Comprobar búsqueda manualmente]({url_resultados})")
    else:
        st.error("Por favor, introduce un DOI válido antes de buscar.")
