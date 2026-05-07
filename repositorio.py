def extraer_upo(doi):
    """Módulo para RIO (Olavide) - ESTRATEGIA GOOGLEBOT"""
    url_base = "https://rio.upo.es"
    
    # Volvemos a la sesión normal, pero con el "Carnet de Identidad" de Google
    sesion = crear_sesion_robusta()
    
    headers_googlebot = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept': 'application/json, application/hal+json'
    }
    
    doi_busqueda = doi.split('/')[-1] if '/' in doi else doi
        
    try:
        url_api_busqueda = f"{url_base}/server/api/discover/search/objects?query={doi_busqueda}"
        res_busqueda = sesion.get(url_api_busqueda, headers=headers_googlebot, timeout=25, verify=False)
        
        if "json" not in res_busqueda.headers.get("Content-Type", "").lower():
            return {"estado": "⚠️ Bloqueo de IP estricto (Requiere ejecución local)", "visitas": None, "enlace": None}
             
        datos = res_busqueda.json()
        
        if "_embedded" in datos and "searchObjects" in datos["_embedded"] and len(datos["_embedded"]["searchObjects"]) > 0:
            uuid_correcto = None
            for objeto in datos["_embedded"]["searchObjects"]:
                item = objeto["_embedded"]["indexableObject"]
                if doi.lower() in str(item).lower():
                    uuid_correcto = item["uuid"]
                    break
            
            if uuid_correcto:
                url_api_stats = f"{url_base}/server/api/statistics/viewevents/search/total?scope={uuid_correcto}&type=item"
                res_stats = sesion.get(url_api_stats, headers=headers_googlebot, timeout=20, verify=False)
                
                if "json" in res_stats.headers.get("Content-Type", "").lower():
                    total = res_stats.json().get("total", 0)
                    return {"estado": "✅ Encontrado (Vía Googlebot)", "visitas": str(total), "enlace": f"{url_base}/statistics/items/{uuid_correcto}"}
                else:
                    return {"estado": "✅ Encontrado", "visitas": None, "enlace": f"{url_base}/statistics/items/{uuid_correcto}"}
            
        return {"estado": "❌ No encontrado", "visitas": None, "enlace": None}
    except Exception as e:
        return {"estado": f"⚠️ Error: {type(e).__name__}", "visitas": None, "enlace": None}
