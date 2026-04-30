import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import urllib3

# Desactivamos las advertencias de seguridad SSL en la consola 
# ya que estamos permitiendo conexiones a universidades con certificados peculiares
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. DIRECTORIO DE REPOSITORIOS (ANDALUCÍA)
# ==========================================
REPOSITORIOS_ANDALUCIA = {
    "Helvia (Córdoba)": {"url_base": "https://helvia.uco.es", "ruta_busqueda": "/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "idUS (Sevilla)": {"url_base": "https://idus.us.es", "ruta_busqueda": "/xmlui/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "Digibug (Granada)": {"url_base": "https://digibug.ugr.es", "ruta_busqueda": "/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "RODIN (Cádiz)": {"url_base": "https://rodin.uca.es", "ruta_busqueda": "/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "riUAL (Almería)": {"url_base": "https://repositorio.ual.es", "ruta_busqueda": "/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "Arias Montano (Huelva)": {"url_base": "https://ariasmontano.uhu.es", "ruta_busqueda": "/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "Ruja (Jaén)": {"url_base": "https://ruja.ujaen.es", "ruta_busqueda": "/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "Riuma (Málaga)": {"url_base": "https://riuma.uma.es", "ruta_busqueda": "/xmlui/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "RIO (Olavide)": {"url_base": "https://rio.upo.es", "ruta_busqueda": "/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'},
    "UNIA (Andalucía)": {"url_base": "https://dspace.unia.es", "ruta_busqueda": "/discover?query=%22{doi}%22", "patron_handle": r'handle/(\d+/\d+)'}
}

# ==========================================
# 2. LÓGICA DE PROGRAMACIÓN (BACKEND)
# ==========================================

# Cabeceras mejoradas para parecer un humano navegando
CABECERAS_NAVEGADOR = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

def buscar_doi_en_andalucia(doi):
    registro_completo = []

    for nombre_repo, config in REPOSITORIOS_ANDALUCIA.items():
        url_base = config["url_base"]
        ruta_especifica = config["ruta_busqueda"].format(doi=doi)
        url_busqueda = f"{url_base}{ruta_especifica}"
        
        try:
            # MEJORA: Aumentamos el timeout a 20s y añadimos verify=False para ignorar errores SSL
            res = requests.get(url_busqueda, headers=CABECERAS_NAVEGADOR, timeout=20, verify=False)
            res.raise_for_status()
            sopa = BeautifulSoup(res.text, 'html.parser')
            
            patron_regex = config["patron_handle"]
            enlaces = sopa.find_all('a', href=re.compile(patron_regex))
            
            if enlaces:
                handle_encontrado = None
                for enlace in enlaces:
                    match = re.search(patron_regex, enlace['href'])
                    if match:
                        handle_encontrado = match.group(1)
                        break
                
                if handle_encontrado:
                    registro_completo.append({
                        "nombre_repo": nombre_repo,
                        "estado": "✅ Encontrado",
                        "datos_utiles": {"url_base": url_base, "handle": handle_encontrado}
                    })
                else:
                    registro_completo.append({
                        "nombre_repo": nombre_repo,
                        "estado": "❌ No encontrado",
                        "datos_utiles": None
                    })
            else:
                registro_completo.append({
                    "nombre_repo": nombre_repo,
                    "estado": "❌ No encontrado",
                    "datos_utiles": None
                })
                        
        except Exception as e:
            # Si quieres ver el error real en tu consola de Streamlit para depurar, puedes imprimir 'e'
            # print(f"Error en {nombre_repo}: {e}")
            registro_completo.append({
                "nombre_repo": nombre_repo,
                "estado": "⚠️ Error de conexión",
                "datos_utiles": None
            })

    return registro_completo

def extraer_estadisticas_universales(url_base, handle):
    url_estadisticas = f"{url_base}/handle/{handle}/statistics"
    
    try:
        # MEJORA: Aplicamos el timeout y el verify=False también aquí
        res = requests.get(url_estadisticas, headers=CABECERAS_NAVEGADOR, timeout=20, verify=False)
        res.raise_for_status()
        sopa = BeautifulSoup(res.text, 'html.parser')
        
        celda_numero = sopa.find('td', class_='datacell')
        
        if celda_numero:
            return celda_numero.get_text(strip=True), url_estadisticas
            
        return "Dato no encontrado", url_estadisticas
    except Exception:
        return "Error al leer estadísticas", url_estadisticas

# ==========================================
# 3. INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================

st.set_page_config(page_title="Impacto Andalucía", page_icon="🌍", layout="centered")
st.title("🌍 Buscador de Impacto: Red de Repositorios")
st.write("Introduce un DOI para buscarlo simultáneamente y ver el estado de cada repositorio en tiempo real.")

doi_input = st.text_input("Introduce el DOI:", placeholder="Ejemplo: 10.3390/cells9061353")

if st.button("Rastrear en Andalucía"):
    if doi_input:
        # Al aumentar el timeout, avisamos al usuario de que puede tardar más
        with st.spinner("Conectando con 10 servidores universitarios... Esto puede tomar hasta 20-30 segundos."):
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
