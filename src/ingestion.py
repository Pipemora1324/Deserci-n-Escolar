import pandas as pd
import requests

def extraer_datos_api():
    # IDs VERIFICADOS PARA EL CRUCE FINAL
    datasets = {
        "desercion": "ji8i-4anb",
        "icfes": "kgxf-xxbe" 
    }
    
    resultados = {}
    
    for nombre, ds_id in datasets.items():
        url = f"https://www.datos.gov.co/resource/{ds_id}.json?$limit=50000"
        print(f"📡 Ingestión: Conectando con {nombre} (ID: {ds_id})...")
        
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                resultados[nombre] = pd.DataFrame(response.json())
                print(f"✅ {nombre.capitalize()} descargado con éxito.")
            else:
                print(f"❌ Error {response.status_code} en {nombre}.")
                resultados[nombre] = pd.DataFrame()
        except Exception as e:
            print(f"🔥 Error de conexión en {nombre}: {e}")
            resultados[nombre] = pd.DataFrame()
            
    return resultados.get("desercion", pd.DataFrame()), resultados.get("icfes", pd.DataFrame())