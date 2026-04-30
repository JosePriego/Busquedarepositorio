import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# ==========================================
# LÓGICA DE PROGRAMACIÓN (BACKEND)
# ==========================================

def buscar_doi_en_helvia(doi):
    """
    Fase 1: Busca un DOI en Helvia (UCO) y extrae su Handle.
    """
    url_base = "https://helvia.uco.es"
    url_busqueda = f"{url_base}/discover?query={doi}"
    
    # Simulamos ser un navegador para evitar bloqueos
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        respuesta = requests.get(url_busqueda, headers=headers, timeout=15)
        respuesta.raise_for_status()
        sopa = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Buscamos el patrón del handle en los enlaces
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
    Fase 2 y 3: Visita la página de estadísticas del Handle 
    y extrae el número de la tabla principal.
    """
    url_estadisticas = f"https://helvia.uco.es/handle/{handle}/statistics"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        res = requests.get(url_estadisticas, headers=headers, timeout=15)
        res.raise_for_status()
        sopa = BeautifulSoup(res.text, 'html.parser')
        
        # Localizamos la tabla exacta por su clase HTML
        tabla_total = sopa.find('table', class_='detailtable')
        
        if tabla_total:
            cuerpo_tabla = tabla_total.find('tbody')
            if cuerpo_tabla:
                primera_fila = cuerpo_tabla.find('tr')
                if primera_fila:
                    celdas = primera_fila.find_all('td')
                    
                    if len(celdas) >= 2:
                        # Extraemos el texto de la última celda limpia de espacios
                        numero_visualizaciones = celdas[-1].get_text(strip=True)
                        return numero_visualizaciones, url_estadisticas
                        
        return "Dato no encontrado en la tabla", url_estadisticas
        
    except requests.exceptions.RequestException as e:
        return f"Error de conexión", url_estadisticas
    except Exception as e:
        return f"Error de lectura", url_estadisticas

# ==========================================
# INTERFAZ DE USUARIO (FRONTEND EN STREAMLIT)
# ==========================================

# Configuración básica de la página
st.set_page_config(page_title="Helvia Tracker", page_icon="🎓")
st.title("🎓 Estadísticas en Helvia (UCO)")
st.write("Introduce el DOI para localizar el artículo y extraer sus visualizaciones.")

# Caja de texto para el usuario
doi_input = st.text_input("Introduce el DOI:", placeholder="Ejemplo: 10.3390/cells9061353")

# Botón de acción
if st.button("Obtener Estadísticas"):
    if doi_input:
        # Iniciamos la Fase 1
        with st.spinner("Paso 1: Localizando el artículo en Helvia..."):
            handle, url_resultados = buscar_doi_en_helvia(doi_input)
            
            if handle == "Error":
                st.error("Hubo un problema de conexión con los servidores de Helvia.")
            elif handle:
                st.success(f"¡Artículo localizado! Handle: `{handle}`")
                
                # Iniciamos la Fase 2 y 3
                with st.spinner("Paso 2: Leyendo página de estadísticas..."):
                    datos_visitas, url_stats = extraer_estadisticas_helvia(handle)
                    
                    if "Error" in datos_visitas or "no encontrado" in datos_visitas:
                        st.warning(datos_visitas)
                    else:
                        # Mostramos el resultado final triunfalmente
                        st.info(f"📊 **Visualizaciones totales:** {datos_visitas}")
                        
                    st.write(f"🔗 [Enlace directo a las estadísticas oficiales]({url_stats})")
            else:
                st.warning("No se encontró este DOI en la base de datos de Helvia.")
    else:
        st.error("Por favor, introduce un DOI válido.")
