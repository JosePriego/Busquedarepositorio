def extraer_upo(doi):
    """Módulo para RIO (Olavide) - DSpace 7 API (Evasión de Bloqueos)"""
    url_base = "https://rio.upo.es"
    sesion = crear_sesion_robusta()
    
    # Hacemos el disfraz de la API más natural
    headers_api = CABECERAS.copy()
    headers_api['Accept'] = 'application/json, application/hal+json, text/plain, */*'
    
    # TRUCO: Cambiamos la barra del DOI para que no rompa la URL de la API
    doi_seguro = doi.replace('/', '%2F')
    
    try:
        url_api_busqueda = f"{url_base}/server/api/discover/search/objects?query={doi_seguro}"
        res_busqueda = sesion.get(url_api_busqueda, headers=headers_api, timeout=25, verify=False)
        
        # CHIVATO: Si el servidor nos corta el paso, nos chivará el número de error
        if res_busqueda.status_code != 200:
             return {"estado": f"⚠️ Bloqueo de seguridad en UPO (Código {res_busqueda.status_code})", "visitas": None, "enlace": None}
             
        try:
            datos = res_busqueda.json()
        except:
            return {"estado": "⚠️ UPO devolvió una página de bloqueo (Cortafuegos)", "visitas": None, "enlace": None}
        
        if "_embedded" in datos and "searchObjects" in datos["_embedded"] and len(datos["_embedded"]["searchObjects"]) > 0:
            objeto = datos["_embedded"]["searchObjects"][0]
            uuid = objeto["_embedded"]["indexableObject"]["uuid"]
            
            # Consulta de estadísticas
            url_api_stats = f"{url_base}/server/api/statistics/viewevents/search/total?scope={uuid}&type=item"
            res_stats = sesion.get(url_api_stats, headers=headers_api, timeout=20, verify=False)
            
            if res_stats.status_code == 200:
                total = res_stats.json().get("total", 0)
                return {"estado": "✅ Encontrado (API)", "visitas": str(total), "enlace": f"{url_base}/statistics/items/{uuid}"}
            else:
                return {"estado": "✅ Encontrado (Pero estadísticas bloqueadas)", "visitas": None, "enlace": f"{url_base}/statistics/items/{uuid}"}
        
        return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
    except Exception as e:
        return {"estado": f"⚠️ Error en comunicación: {type(e).__name__}", "visitas": None, "enlace": None}
