import os
import sys
import pandas as pd

# Configuración de rutas
directorio_actual = os.path.dirname(os.path.abspath(__file__))
sys.path.append(directorio_actual)

from ingestion import extraer_datos_api
from cleaning import limpiar_datos
from model_ia import entrenar_predictor_desercion

def correr_pipeline():
    print("\n" + "="*60)
    print("👑 PIPELINE MULTI-DATASET (IA + INVERSIÓN) - UCC 2026")
    print("="*60)
    
    try:
        # 1. Traer ambos datasets
        df_des_raw, df_inv_raw = extraer_datos_api()
        
        # 2. Unir y Limpiar
        df_clean = limpiar_datos(df_des_raw, df_inv_raw)
        
        # 3. Entrenar IA con la data cruzada
        df_futuro = entrenar_predictor_desercion(df_clean)
        
        # 4. Consolidar Real + Predicción
        df_final = pd.concat([df_clean, df_futuro], ignore_index=True)
        
        # 5. Guardar en data/processed
        ruta_salida = os.path.join(directorio_actual, '..', 'data', 'processed', 'master_data_final.csv')
        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        df_final.to_csv(ruta_salida, index=False, encoding='utf-8-sig')
        
        print("\n" + "-"*60)
        print(f"🌟 ¡PROCESO EXITOSO! Data cruzada con inversión lista.")
        print(f"📂 Ubicación: {os.path.abspath(ruta_salida)}")
        print("-" * 60)

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")

if __name__ == "__main__":
    correr_pipeline()