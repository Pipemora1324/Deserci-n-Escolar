import json
import math
import sys
import unicodedata
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd
from django.shortcuts import render


base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

try:
    from src.model_ia import entrenar_predictor_desercion
except Exception as exc:
    print(f"Error cargando src.model_ia: {exc}")
    entrenar_predictor_desercion = None


def _normalizar_texto(valor):
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return "".join(caracter if caracter.isalnum() else "_" for caracter in texto).strip("_")


def _normalizar_columnas(df):
    columnas_normalizadas = {}
    columnas_finales = []

    for columna in df.columns:
        nombre = _normalizar_texto(columna)
        if not nombre:
            nombre = "columna"

        nombre_unico = nombre
        contador = 2
        while nombre_unico in columnas_normalizadas:
            nombre_unico = f"{nombre}_{contador}"
            contador += 1

        columnas_normalizadas[nombre_unico] = columna
        columnas_finales.append(nombre_unico)

    df = df.copy()
    df.columns = columnas_finales
    return df


def _buscar_columna(df, prioridades, excluir=()):
    columnas = list(df.columns)
    exclusiones = tuple(_normalizar_texto(item) for item in excluir)

    for prioridad in prioridades:
        prioridad_norm = _normalizar_texto(prioridad)
        for columna in columnas:
            if columna in exclusiones or any(exclusion in columna for exclusion in exclusiones):
                continue
            if columna == prioridad_norm:
                return columna

    for prioridad in prioridades:
        prioridad_norm = _normalizar_texto(prioridad)
        for columna in columnas:
            if columna in exclusiones or any(exclusion in columna for exclusion in exclusiones):
                continue
            if prioridad_norm in columna:
                return columna

    return None


def _a_numerico(serie):
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce")

    return pd.to_numeric(
        serie.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip(),
        errors="coerce",
    )


def _formato_numero(valor, decimales=2):
    if valor is None or pd.isna(valor):
        return "N/D"
    return f"{float(valor):.{decimales}f}"


def _formato_entero_colombia(valor):
    if valor is None or pd.isna(valor):
        return "N/D"
    return f"{int(round(float(valor))):,}".replace(",", ".")


def _json_para_template(datos):
    payload = json.dumps(datos, ensure_ascii=True, separators=(",", ":"))
    return (
        payload.replace("\\", "\\\\")
        .replace("'", "\\u0027")
        .replace("<", "\\u003C")
        .replace(">", "\\u003E")
        .replace("&", "\\u0026")
    )


def _modo_seguro(motivo, departamentos=None):
    departamentos = sorted(set(departamentos or []))
    insights = {
        "General": (
            "MODO SEGURO: no fue posible completar la inferencia automatica. "
            f"Motivo tecnico: {motivo}. La interfaz permanece activa sin datos inventados."
        )
    }

    for departamento in departamentos:
        insights[departamento] = (
            "MODO SEGURO: el departamento existe en la base limpia, pero el diagnostico IA "
            "no se pudo recalcular en esta ejecucion."
        )

    return {
        "promedio": "N/D",
        "total_estudiantes": "N/D",
        "periodo_analizado": "N/D",
        "ultimo_ano": "N/D",
        "total_departamentos": len(departamentos),
        "total_registros": "N/D",
        "promedio_matricula": "N/D",
        "prediccion_ia": "N/D",
        "ano_prediccion": "N/D",
        "margen_modelo": "N/D",
        "depto_critico": "N/D",
        "valor_depto_critico": "N/D",
        "depto_destacado": "N/D",
        "valor_depto_destacado": "N/D",
        "top_riesgo": [],
        "ia_insights_json": _json_para_template(insights),
        "departamentos": departamentos,
        "powerbi_filter_table": "master_data_final",
        "powerbi_filter_field": "Ubicacion Completa",
        "powerbi_embed_url": "https://app.powerbi.com/view?r=eyJrIjoiNWU2NzJmZGUtNTIwNi00MmY2LWE0NzUtYzVkMzgwNTk5YmY4IiwidCI6IjhkMzY4MzZlLTZiNzUtNGRlNi1iYWI5LTVmNGIxNzc1NDI3ZiIsImMiOjR9",
    }


def _diagnostico_desercion(desviacion, margen):
    if desviacion > margen:
        return "Riesgo"
    if desviacion < -margen:
        return "Exito"
    return "Estabilidad"


def home(request):
    csv_path = base_dir / "data" / "processed" / "master_data_final.csv"

    if not csv_path.exists():
        return render(request, "index.html", _modo_seguro("CSV no encontrado"))

    try:
        df = _normalizar_columnas(pd.read_csv(csv_path))

        col_departamento = _buscar_columna(
            df,
            prioridades=("departamento", "depto", "region", "territorio"),
            excluir=("codigo", "cod", "id"),
        )
        col_codigo_departamento = _buscar_columna(
            df,
            prioridades=(
                "codigo_departamento",
                "cod_departamento",
                "c_digo_departamento",
                "digo_departamento",
            ),
        )
        col_ano = _buscar_columna(df, prioridades=("ano", "anio", "year", "vigencia"))
        col_desercion = _buscar_columna(
            df,
            prioridades=("desercion", "tasa_desercion", "abandono"),
            excluir=("predicha", "prediccion", "forecast"),
        )
        col_matricula = _buscar_columna(
            df,
            prioridades=("tasa_matriculacion_5_16", "tasa_matriculacion", "matriculacion"),
        )
        col_poblacion = _buscar_columna(
            df,
            prioridades=("poblacion_5_16", "poblacion", "estudiantes", "matricula"),
            excluir=("tasa",),
        )

        columnas_requeridas = {
            "departamento": col_departamento,
            "ano": col_ano,
            "desercion": col_desercion,
        }
        faltantes = [nombre for nombre, columna in columnas_requeridas.items() if not columna]
        if faltantes:
            return render(
                request,
                "index.html",
                _modo_seguro(f"columnas requeridas no detectadas: {', '.join(faltantes)}"),
            )

        df[col_departamento] = df[col_departamento].astype(str).str.strip()
        df[col_departamento] = df[col_departamento].where(
            df[col_departamento].str.lower().ne("nan")
        )
        df[col_ano] = _a_numerico(df[col_ano])
        df[col_desercion] = _a_numerico(df[col_desercion])

        if col_codigo_departamento:
            df[col_codigo_departamento] = _a_numerico(df[col_codigo_departamento])
        if col_matricula:
            df[col_matricula] = _a_numerico(df[col_matricula])
        if col_poblacion:
            df[col_poblacion] = _a_numerico(df[col_poblacion])

        historico = df.dropna(subset=[col_departamento, col_ano, col_desercion]).copy()
        historico = historico[historico[col_departamento].astype(str).str.len() > 0]
        historico[col_departamento] = historico[col_departamento].astype(str).str.strip().str.upper()

        if col_codigo_departamento and col_codigo_departamento in historico.columns:
            nombres_canonicos = (
                historico.dropna(subset=[col_codigo_departamento])
                .sort_values([col_codigo_departamento, col_ano])
                .groupby(col_codigo_departamento)[col_departamento]
                .last()
                .to_dict()
            )
            historico[col_departamento] = historico.apply(
                lambda fila: nombres_canonicos.get(
                    fila[col_codigo_departamento], fila[col_departamento]
                ),
                axis=1,
            )

        if historico.empty:
            return render(request, "index.html", _modo_seguro("CSV sin filas historicas validas"))

        departamentos = sorted(historico[col_departamento].dropna().unique().tolist())
        ultimo_ano = int(historico[col_ano].max())
        datos_ultimo_ano = historico[historico[col_ano] == ultimo_ano].copy()

        promedio_nacional_actual = float(datos_ultimo_ano[col_desercion].mean())
        promedio_matricula = (
            float(datos_ultimo_ano[col_matricula].mean())
            if col_matricula
            else None
        )
        total_estudiantes = "10 millones"

        prediccion_ia = None
        ano_prediccion = None
        error_modelo = None

        if entrenar_predictor_desercion is None:
            error_modelo = "modelo no importado"
        else:
            try:
                datos_modelo = historico[[col_ano, col_desercion]].rename(
                    columns={col_ano: "ano", col_desercion: "desercion"}
                )
                datos_modelo = datos_modelo.dropna()
                with redirect_stdout(StringIO()):
                    predicciones = entrenar_predictor_desercion(datos_modelo)
                if predicciones is not None and not predicciones.empty:
                    predicciones = predicciones.copy()
                    predicciones["ano"] = _a_numerico(predicciones["ano"])
                    predicciones["desercion_predicha"] = _a_numerico(
                        predicciones["desercion_predicha"]
                    )
                    predicciones = predicciones.dropna(subset=["ano", "desercion_predicha"])
                    predicciones_futuras = predicciones[predicciones["ano"] > ultimo_ano]
                    fila_prediccion = (
                        predicciones_futuras.sort_values("ano").iloc[0]
                        if not predicciones_futuras.empty
                        else predicciones.sort_values("ano").iloc[-1]
                    )
                    prediccion_ia = float(fila_prediccion["desercion_predicha"])
                    ano_prediccion = int(fila_prediccion["ano"])
            except Exception as exc:
                error_modelo = str(exc)

        if prediccion_ia is None or not math.isfinite(prediccion_ia):
            prediccion_ia = promedio_nacional_actual
            ano_prediccion = ultimo_ano

        desviacion_estandar = float(datos_ultimo_ano[col_desercion].std(ddof=0) or 0)
        margen = max(desviacion_estandar * 0.50, 0.50)
        datos_ranking = datos_ultimo_ano.sort_values(col_desercion, ascending=False)
        fila_critica = datos_ranking.iloc[0]
        fila_destacada = datos_ranking.iloc[-1]

        top_riesgo = []
        for _, fila in datos_ranking.head(5).iterrows():
            top_riesgo.append(
                {
                    "departamento": fila[col_departamento],
                    "desercion": _formato_numero(fila[col_desercion]),
                    "matricula": (
                        _formato_numero(fila[col_matricula])
                        if col_matricula and not pd.isna(fila[col_matricula])
                        else "N/D"
                    ),
                }
            )

        ia_insights = {
            "General": (
                f"ANALISIS IA NACIONAL: con datos limpios hasta {ultimo_ano}, "
                f"la desercion promedio observada es {_formato_numero(promedio_nacional_actual)}%. "
                f"El modelo de regresion lineal proyecta {_formato_numero(prediccion_ia)}% "
                f"para {ano_prediccion}. Margen tecnico usado: +/-{_formato_numero(margen)} puntos."
            )
        }

        if error_modelo:
            ia_insights["General"] += (
                f" Nota: se activo respaldo estadistico porque el modelo reporto: {error_modelo}."
            )

        for departamento in departamentos:
            serie_depto = historico[historico[col_departamento] == departamento].sort_values(col_ano)
            fila_actual = serie_depto.iloc[-1]
            desercion_actual = float(fila_actual[col_desercion])
            ano_actual = int(fila_actual[col_ano])
            diferencia = desercion_actual - prediccion_ia
            diagnostico = _diagnostico_desercion(diferencia, margen)

            matricula_texto = ""
            if col_matricula and not pd.isna(fila_actual[col_matricula]):
                matricula_texto = (
                    f" Tasa de matriculacion 5-16 observada: "
                    f"{_formato_numero(fila_actual[col_matricula])}%."
                )

            if diagnostico == "Riesgo":
                lectura = (
                    "supera la prediccion nacional y requiere priorizacion en permanencia escolar"
                )
            elif diagnostico == "Exito":
                lectura = (
                    "esta por debajo de la prediccion nacional y muestra un resultado favorable"
                )
            else:
                lectura = (
                    "se mantiene dentro del rango esperado por el modelo"
                )

            ia_insights[departamento] = (
                f"{diagnostico.upper()} IA: {departamento} registro "
                f"{_formato_numero(desercion_actual)}% de desercion en {ano_actual}; "
                f"la IA proyecta {_formato_numero(prediccion_ia)}% para {ano_prediccion}. "
                f"Desviacion: {_formato_numero(diferencia)} puntos, umbral: "
                f"+/-{_formato_numero(margen)}. El departamento {lectura}."
                f"{matricula_texto}"
            )

        context = {
            "promedio": _formato_numero(promedio_nacional_actual),
            "total_estudiantes": total_estudiantes,
            "periodo_analizado": f"{int(historico[col_ano].min())} - {ultimo_ano}",
            "ultimo_ano": ultimo_ano,
            "total_departamentos": len(departamentos),
            "total_registros": _formato_entero_colombia(len(historico)),
            "promedio_matricula": _formato_numero(promedio_matricula),
            "prediccion_ia": _formato_numero(prediccion_ia),
            "ano_prediccion": ano_prediccion,
            "margen_modelo": _formato_numero(margen),
            "depto_critico": fila_critica[col_departamento],
            "valor_depto_critico": _formato_numero(fila_critica[col_desercion]),
            "depto_destacado": fila_destacada[col_departamento],
            "valor_depto_destacado": _formato_numero(fila_destacada[col_desercion]),
            "top_riesgo": top_riesgo,
            "ia_insights_json": _json_para_template(ia_insights),
            "departamentos": departamentos,
            "powerbi_filter_table": "master_data_final",
            "powerbi_filter_field": "Ubicacion Completa",
            "powerbi_embed_url": "https://app.powerbi.com/view?r=eyJrIjoiNWU2NzJmZGUtNTIwNi00MmY2LWE0NzUtYzVkMzgwNTk5YmY4IiwidCI6IjhkMzY4MzZlLTZiNzUtNGRlNi1iYWI5LTVmNGIxNzc1NDI3ZiIsImMiOjR9",
        }
        return render(request, "index.html", context)

    except Exception as exc:
        print(f"Error fatal en analytics.views.home: {exc}")
        return render(request, "index.html", _modo_seguro(str(exc)))
