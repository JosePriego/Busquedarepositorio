def extraer_estadisticas_helvia(handle):
    """
    Visita la página de estadísticas directas de un Handle en Helvia 
    y extrae el número de la tabla principal utilizando la estructura HTML.
    """
    url_estadisticas = f"https://helvia.uco.es/handle/{handle}/statistics"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        res = requests.get(url_estadisticas, headers=headers, timeout=15)
        res.raise_for_status()
        sopa = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Buscamos la tabla que contiene el resumen total. 
        # Basado en tu imagen, Helvia usa la clase 'detailtable' para estas tablas de datos.
        tabla_total = sopa.find('table', class_='detailtable')
        
        if tabla_total:
            # 2. Entramos al cuerpo de la tabla (donde están los datos reales, ignorando las cabeceras)
            cuerpo_tabla = tabla_total.find('tbody')
            if cuerpo_tabla:
                # 3. Tomamos la primera fila de resultados
                primera_fila = cuerpo_tabla.find('tr')
                if primera_fila:
                    # 4. Obtenemos todas las celdas de esa fila
                    celdas = primera_fila.find_all('td')
                    
                    # Verificamos que haya al menos dos columnas (Título y Número)
                    if len(celdas) >= 2:
                        # La última celda (índice -1) es la que contiene el número, según tu imagen
                        numero_visualizaciones = celdas[-1].get_text(strip=True)
                        return numero_visualizaciones, url_estadisticas
                        
        return "No se pudo encontrar el dato en la tabla", url_estadisticas
        
    except requests.exceptions.RequestException as e:
        return f"Error de conexión: {e}", url_estadisticas
    except Exception as e:
        return f"Error inesperado al procesar el HTML: {e}", url_estadisticas
