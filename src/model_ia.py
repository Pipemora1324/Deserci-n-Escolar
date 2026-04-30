import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def entrenar_predictor_desercion(df):
    print("\n🤖 Fase de IA: Entrenando modelo predictivo...")

    # 1. Preparar datos para tendencia nacional
    # Agrupamos por año y sacamos el promedio de deserción
    datos_modelo = df.groupby('ano')['desercion'].mean().reset_index()
    
    # X = Años (Variable independiente), y = Deserción (Variable a predecir)
    X = datos_modelo['ano'].values.reshape(-1, 1)
    y = datos_modelo['desercion'].values

    # 2. Crear y entrenar la IA
    modelo = LinearRegression()
    modelo.fit(X, y)

    # 3. Generar predicción para el futuro (2025, 2026, 2027)
    anos_futuros = np.array([[2025], [2026], [2027]])
    predicciones = modelo.predict(anos_futuros)
    
    # Creamos un pequeño DataFrame con los resultados de la IA
    df_predicciones = pd.DataFrame({
        'ano': [2025, 2026, 2027],
        'desercion_predicha': predicciones,
        'tipo': 'PREDICCIÓN IA'
    })

    print("✅ IA entrenada con éxito.")
    print(f"📈 Pronóstico para 2027: {predicciones[2]:.2f}% de deserción nacional.")
    
    return df_predicciones