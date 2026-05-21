import io
import json
import math
import os
import sys
import unicodedata
import base64
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
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

try:
    from scipy import stats
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import anthropic as anthropic_sdk
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


CHATBOT_SYSTEM_PROMPT = """Eres un asistente experto en análisis de deserción escolar en Colombia,
especializado en el proyecto "Datos al Ecosistema 2026" de la Universidad
Cooperativa de Colombia sede Pasto.

Tienes acceso al análisis completo del proyecto:

DATOS DEL PROYECTO:
- Dataset: 465 registros, 33 departamentos, años 2011-2024
- Deserción promedio nacional: 4.07%
- Total estudiantes analizados en el período
- Los 5 departamentos con mayor deserción: Guainía (6.86%), Vichada (6.80%),
  Putumayo (6.14%), Caquetá (6.12%), Vaupés (6.05%)
- Nariño (donde está la UCC Pasto): deserción en rango medio nacional

RESULTADOS ANOVA:
- ANOVA por Región: F=49.08, p<0.001 → La Amazonia tiene deserción
  significativamente mayor (5.91%) que todas las demás regiones
- ANOVA por Nivel Educativo: F=58.24, p<0.001 → La Secundaria tiene
  la mayor deserción (5.10%), la Primaria la menor (3.42%)
- ANOVA por Período: F=3.82, p=0.022 → Durante pandemia bajó a 3.59%
  (subsidios y retención), en post-pandemia rebotó a 4.34%

TECNOLOGÍA:
- Procesamiento con PySpark, visualización en Power BI
- Análisis estadístico con scipy.stats (ANOVA + Tukey HSD)
- Web en Django desplegada en Vercel

Responde siempre en español, de forma clara y accesible.
Cuando sea relevante, conecta los datos con políticas educativas reales de Colombia.
Puedes hacer cálculos simples si te los piden.
Si no sabes algo específico del proyecto, dilo honestamente."""


# ── helpers ──────────────────────────────────────────────────────────────────

def _normalizar_texto(valor):
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return "".join(c if c.isalnum() else "_" for c in texto).strip("_")


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
            if columna in exclusiones or any(e in columna for e in exclusiones):
                continue
            if columna == prioridad_norm:
                return columna
    for prioridad in prioridades:
        prioridad_norm = _normalizar_texto(prioridad)
        for columna in columnas:
            if columna in exclusiones or any(e in columna for e in exclusiones):
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
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "N/D"
    return f"{float(valor):.{decimales}f}"


def _formato_entero_colombia(valor):
    if valor is None:
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


# ── ANOVA helpers ─────────────────────────────────────────────────────────────

DARK_BG = '#0d1117'
DARK_SURFACE = '#161b22'
DARK_BORDER = '#30363d'
DARK_TEXT = '#e6edf3'
DARK_TEXT_SEC = '#8b949e'
PALETTE = ['#1a6eb5', '#f5a623', '#3fb950', '#d0021b', '#a371f7', '#58a6ff', '#f78166']


def _setup_dark_fig(figsize=(11, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_SURFACE)
    ax.tick_params(colors=DARK_TEXT, labelsize=9)
    ax.xaxis.label.set_color(DARK_TEXT)
    ax.yaxis.label.set_color(DARK_TEXT)
    ax.title.set_color(DARK_TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(DARK_BORDER)
    ax.grid(axis='y', color=DARK_BORDER, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    return fig, ax


def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=110, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{img_b64}"


def _boxplot_b64(groups_data, group_names, title, ylabel):
    fig, ax = _setup_dark_fig()
    colors = PALETTE[:len(group_names)]
    bp = ax.boxplot(
        groups_data, patch_artist=True,
        labels=group_names, widths=0.55,
        medianprops=dict(color='white', linewidth=2),
        whiskerprops=dict(color=DARK_TEXT_SEC),
        capprops=dict(color=DARK_TEXT_SEC),
        flierprops=dict(marker='o', markerfacecolor=DARK_TEXT_SEC,
                        markeredgecolor=DARK_TEXT_SEC, markersize=4),
    )
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
        patch.set_edgecolor(color)

    # Overlay mean dots
    for i, (data, color) in enumerate(zip(groups_data, colors), start=1):
        mn = np.nanmean(data)
        ax.plot(i, mn, 'D', color='white', markersize=6, zorder=5,
                markeredgecolor=color, markeredgewidth=1.5)

    ax.set_title(title, fontsize=13, pad=14, color=DARK_TEXT, fontweight='bold')
    ax.set_ylabel(ylabel, color=DARK_TEXT, fontsize=10)
    plt.xticks(rotation=15, ha='right', color=DARK_TEXT, fontsize=9)
    plt.tight_layout()
    return _fig_to_b64(fig)


def _barplot_b64(group_names, means, stds, title, ylabel):
    fig, ax = _setup_dark_fig()
    x = range(len(group_names))
    colors = PALETTE[:len(group_names)]
    bars = ax.bar(x, means, color=colors, alpha=0.82, edgecolor=DARK_BORDER,
                  width=0.55, zorder=3)
    ax.errorbar(x, means, yerr=stds, fmt='none', color='white',
                capsize=5, capthick=1.5, elinewidth=1.5, zorder=4)
    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f'{mean:.2f}%', ha='center', va='bottom',
                color=DARK_TEXT, fontfamily='monospace', fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(group_names, rotation=10, ha='right', color=DARK_TEXT, fontsize=9)
    ax.set_title(title, fontsize=13, pad=14, color=DARK_TEXT, fontweight='bold')
    ax.set_ylabel(ylabel, color=DARK_TEXT, fontsize=10)
    plt.tight_layout()
    return _fig_to_b64(fig)


def _format_pval(p):
    if p < 0.001:
        return "< 0.001"
    return f"{p:.4f}"


def _norm_dept_str(s):
    s = unicodedata.normalize('NFD', str(s).strip().upper())
    return ''.join(c for c in s if not unicodedata.combining(c))


def _run_tukey(values, groups):
    try:
        tukey = pairwise_tukeyhsd(values, groups)
        tbl = tukey._results_table
        rows = []
        for r in tbl.data[1:]:
            rows.append({
                'g1': str(r[0]), 'g2': str(r[1]),
                'diff': round(float(r[2]), 4),
                'p_adj': _format_pval(float(r[3])),
                'lower': round(float(r[4]), 4),
                'upper': round(float(r[5]), 4),
                'reject': bool(r[6]),
            })
        return rows
    except Exception:
        return []


# ── views ─────────────────────────────────────────────────────────────────────

def home(request):
    csv_path = base_dir / "data" / "processed" / "master_data_final.csv"

    if not csv_path.exists():
        return render(request, "index.html", _modo_seguro("CSV no encontrado"))

    try:
        df = _normalizar_columnas(pd.read_csv(csv_path))

        col_departamento = _buscar_columna(
            df, prioridades=("departamento", "depto", "region", "territorio"),
            excluir=("codigo", "cod", "id"),
        )
        col_codigo_departamento = _buscar_columna(
            df, prioridades=("codigo_departamento", "cod_departamento",
                             "c_digo_departamento", "digo_departamento"),
        )
        col_ano = _buscar_columna(df, prioridades=("ano", "anio", "year", "vigencia"))
        col_desercion = _buscar_columna(
            df, prioridades=("desercion", "tasa_desercion", "abandono"),
            excluir=("predicha", "prediccion", "forecast"),
        )
        col_matricula = _buscar_columna(
            df, prioridades=("tasa_matriculacion_5_16", "tasa_matriculacion", "matriculacion"),
        )
        col_poblacion = _buscar_columna(
            df, prioridades=("poblacion_5_16", "poblacion", "estudiantes", "matricula"),
            excluir=("tasa",),
        )

        faltantes = [n for n, c in {"departamento": col_departamento,
                                     "ano": col_ano,
                                     "desercion": col_desercion}.items() if not c]
        if faltantes:
            return render(request, "index.html",
                          _modo_seguro(f"columnas requeridas no detectadas: {', '.join(faltantes)}"))

        df[col_departamento] = df[col_departamento].astype(str).str.strip()
        df[col_departamento] = df[col_departamento].where(
            df[col_departamento].str.lower().ne("nan"))
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
        historico[col_departamento] = (
            historico[col_departamento].astype(str).str.strip().str.upper()
        )

        if col_codigo_departamento and col_codigo_departamento in historico.columns:
            nombres_canonicos = (
                historico.dropna(subset=[col_codigo_departamento])
                .sort_values([col_codigo_departamento, col_ano])
                .groupby(col_codigo_departamento)[col_departamento]
                .last()
                .to_dict()
            )
            historico[col_departamento] = historico.apply(
                lambda f: nombres_canonicos.get(f[col_codigo_departamento], f[col_departamento]),
                axis=1,
            )

        if historico.empty:
            return render(request, "index.html", _modo_seguro("CSV sin filas históricas válidas"))

        departamentos = sorted(historico[col_departamento].dropna().unique().tolist())
        ultimo_ano = int(historico[col_ano].max())
        datos_ultimo_ano = historico[historico[col_ano] == ultimo_ano].copy()

        promedio_nacional_actual = float(datos_ultimo_ano[col_desercion].mean())
        promedio_matricula = (
            float(datos_ultimo_ano[col_matricula].mean()) if col_matricula else None
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
                        predicciones["desercion_predicha"])
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

        top5_rows = datos_ranking.head(5)
        max_d = float(top5_rows[col_desercion].max()) if not top5_rows.empty else 1.0
        top_riesgo = []
        for _, fila in top5_rows.iterrows():
            val = float(fila[col_desercion])
            top_riesgo.append({
                "departamento": fila[col_departamento],
                "desercion": _formato_numero(val),
                "bar_pct": round(val / max(max_d, 0.01) * 90, 1),
                "matricula": (
                    _formato_numero(fila[col_matricula])
                    if col_matricula and not pd.isna(fila[col_matricula])
                    else "N/D"
                ),
            })

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
            serie_depto = (
                historico[historico[col_departamento] == departamento]
                .sort_values(col_ano)
            )
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

            lectura = {
                "Riesgo": "supera la prediccion nacional y requiere priorizacion en permanencia escolar",
                "Exito": "esta por debajo de la prediccion nacional y muestra un resultado favorable",
                "Estabilidad": "se mantiene dentro del rango esperado por el modelo",
            }[diagnostico]

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


# ── ANOVA view ────────────────────────────────────────────────────────────────

REGIONES = {
    'Caribe':    ['ATLÁNTICO', 'BOLÍVAR', 'CESAR', 'CÓRDOBA', 'LA GUAJIRA',
                  'MAGDALENA', 'SUCRE', 'SAN ANDRÉS'],
    'Andina':    ['ANTIOQUIA', 'BOYACÁ', 'CALDAS', 'CUNDINAMARCA', 'HUILA',
                  'NARIÑO', 'NORTE DE SANTANDER', 'QUINDÍO', 'RISARALDA',
                  'SANTANDER', 'TOLIMA', 'BOGOTÁ D.C.'],
    'Pacífica':  ['CAUCA', 'CHOCÓ', 'VALLE DEL CAUCA'],
    'Amazonia':  ['AMAZONAS', 'CAQUETÁ', 'GUAINÍA', 'GUAVIARE',
                  'PUTUMAYO', 'VAUPÉS', 'VICHADA'],
    'Orinoquia': ['ARAUCA', 'CASANARE', 'META'],
}


def anova_view(request):
    if not SCIPY_AVAILABLE:
        return render(request, 'anova.html', {
            'error': 'scipy y statsmodels no están instalados. '
                     'Ejecuta: pip install scipy statsmodels'
        })

    csv_path = base_dir / "data" / "processed" / "master_data_final.csv"
    if not csv_path.exists():
        return render(request, 'anova.html', {'error': 'No se encontró master_data_final.csv'})

    try:
        df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')

        # Keep only real (non-predicted) rows
        if 'tipo' in df.columns:
            df = df[df['tipo'].isna() | ~df['tipo'].astype(str).str.lower().str.contains('pred')]
        if 'ano' in df.columns:
            df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
            df = df[df['ano'] <= 2024]

        if 'departamento' in df.columns:
            df['departamento'] = df['departamento'].astype(str).str.strip().str.upper()
        if 'desercion' in df.columns:
            df['desercion'] = pd.to_numeric(df['desercion'], errors='coerce')

        df = df.dropna(subset=['departamento', 'desercion', 'ano'])

        # ── ANOVA 1: Por Región ─────────────────────────────────────
        dept_to_region = {}
        for region, depts in REGIONES.items():
            for dept in depts:
                dept_to_region[_norm_dept_str(dept)] = region

        df['region'] = df['departamento'].apply(
            lambda d: dept_to_region.get(_norm_dept_str(d), None)
        )

        df_a1 = df[['region', 'desercion']].dropna()
        region_order = ['Andina', 'Caribe', 'Pacífica', 'Orinoquia', 'Amazonia']
        present_regions = [r for r in region_order if r in df_a1['region'].unique()]

        groups_a1 = [df_a1[df_a1['region'] == r]['desercion'].values for r in present_regions]
        f1, p1 = stats.f_oneway(*groups_a1)

        anova1_groups = []
        for r in present_regions:
            vals = df_a1[df_a1['region'] == r]['desercion']
            anova1_groups.append({
                'name': r,
                'mean': round(float(vals.mean()), 3),
                'std': round(float(vals.std()), 3),
                'min': round(float(vals.min()), 3),
                'max': round(float(vals.max()), 3),
                'n': int(len(vals)),
            })

        tukey1 = _run_tukey(df_a1['desercion'].values, df_a1['region'].values)
        plot1 = _boxplot_b64(
            groups_a1, present_regions,
            'Deserción Escolar por Región Geográfica',
            'Tasa de Deserción (%)',
        )

        # ── ANOVA 2: Por Nivel Educativo ────────────────────────────
        nivel_map = {
            'desercion_transicion': 'Transición',
            'desercion_primaria': 'Primaria',
            'desercion_secundaria': 'Secundaria',
            'desercion_media': 'Media',
        }
        existing_nivel = {k: v for k, v in nivel_map.items() if k in df.columns}

        if len(existing_nivel) < 2:
            plot2 = None
            anova2_groups = []
            f2, p2 = float('nan'), float('nan')
            tukey2 = []
            anova2_error = 'No se encontraron columnas de deserción por nivel educativo.'
        else:
            df_melt = df.melt(
                id_vars=['departamento', 'ano'],
                value_vars=list(existing_nivel.keys()),
                var_name='nivel_raw', value_name='desercion_nivel',
            )
            df_melt['nivel'] = df_melt['nivel_raw'].map(existing_nivel)
            df_a2 = df_melt[['nivel', 'desercion_nivel']].dropna()
            df_a2.columns = ['nivel', 'desercion']

            nivel_order = ['Transición', 'Primaria', 'Secundaria', 'Media']
            present_niveles = [n for n in nivel_order if n in df_a2['nivel'].unique()]
            groups_a2 = [df_a2[df_a2['nivel'] == n]['desercion'].values for n in present_niveles]

            f2, p2 = stats.f_oneway(*groups_a2)

            anova2_groups = []
            for n in present_niveles:
                vals = df_a2[df_a2['nivel'] == n]['desercion']
                anova2_groups.append({
                    'name': n,
                    'mean': round(float(vals.mean()), 3),
                    'std': round(float(vals.std()), 3),
                    'min': round(float(vals.min()), 3),
                    'max': round(float(vals.max()), 3),
                    'n': int(len(vals)),
                })

            tukey2 = _run_tukey(df_a2['desercion'].values, df_a2['nivel'].values)
            plot2 = _boxplot_b64(
                groups_a2, present_niveles,
                'Deserción Escolar por Nivel Educativo',
                'Tasa de Deserción (%)',
            )
            anova2_error = None

        # ── ANOVA 3: Por Período Histórico ──────────────────────────
        def _assign_period(year):
            if year <= 2019:
                return 'Pre-pandemia'
            elif year <= 2021:
                return 'Pandemia'
            else:
                return 'Post-pandemia'

        df['periodo'] = df['ano'].apply(_assign_period)
        df_a3 = df[['periodo', 'desercion']].dropna()

        period_order = ['Pre-pandemia', 'Pandemia', 'Post-pandemia']
        present_periods = [p for p in period_order if p in df_a3['periodo'].unique()]
        groups_a3 = [df_a3[df_a3['periodo'] == p]['desercion'].values for p in present_periods]

        f3, p3 = stats.f_oneway(*groups_a3)

        anova3_groups = []
        for p in present_periods:
            vals = df_a3[df_a3['periodo'] == p]['desercion']
            anova3_groups.append({
                'name': p,
                'mean': round(float(vals.mean()), 3),
                'std': round(float(vals.std()), 3),
                'min': round(float(vals.min()), 3),
                'max': round(float(vals.max()), 3),
                'n': int(len(vals)),
            })

        tukey3 = _run_tukey(df_a3['desercion'].values, df_a3['periodo'].values)

        period_labels_full = {
            'Pre-pandemia': 'Pre-pandemia\n2011–2019',
            'Pandemia': 'Pandemia\n2020–2021',
            'Post-pandemia': 'Post-pandemia\n2022–2024',
        }
        means3 = [g['mean'] for g in anova3_groups]
        stds3 = [g['std'] for g in anova3_groups]
        labels3 = [period_labels_full.get(p, p) for p in present_periods]
        plot3 = _barplot_b64(labels3, means3, stds3,
                             'Deserción Escolar por Período Histórico',
                             'Tasa de Deserción Promedio (%)')

        context = {
            # ANOVA 1
            'a1_f': round(float(f1), 3),
            'a1_p': _format_pval(float(p1)),
            'a1_sig': float(p1) < 0.05,
            'a1_groups': anova1_groups,
            'a1_tukey': tukey1,
            'a1_plot': plot1,
            # ANOVA 2
            'a2_f': round(float(f2), 3) if not math.isnan(f2) else 'N/D',
            'a2_p': _format_pval(float(p2)) if not math.isnan(p2) else 'N/D',
            'a2_sig': (not math.isnan(p2)) and float(p2) < 0.05,
            'a2_groups': anova2_groups,
            'a2_tukey': tukey2,
            'a2_plot': plot2,
            'a2_error': anova2_error if 'anova2_error' in dir() else None,
            # ANOVA 3
            'a3_f': round(float(f3), 3),
            'a3_p': _format_pval(float(p3)),
            'a3_sig': float(p3) < 0.05,
            'a3_groups': anova3_groups,
            'a3_tukey': tukey3,
            'a3_plot': plot3,
            'error': None,
        }
        return render(request, 'anova.html', context)

    except Exception as exc:
        import traceback
        print(traceback.format_exc())
        return render(request, 'anova.html', {'error': f'Error al ejecutar el análisis: {exc}'})


# ── chatbot views ─────────────────────────────────────────────────────────────

def chatbot_page(request):
    return render(request, 'chatbot.html')


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    if not ANTHROPIC_AVAILABLE:
        return JsonResponse(
            {'error': 'SDK de Anthropic no disponible en el servidor.'}, status=503
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    user_message = data.get('message', '').strip()
    history = data.get('history', [])

    if not user_message:
        return JsonResponse({'error': 'Mensaje vacío.'}, status=400)

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return JsonResponse({
            'response': (
                'La API key de Anthropic no está configurada en el servidor. '
                'Contacta al administrador para agregar la variable ANTHROPIC_API_KEY.'
            )
        })

    try:
        client = anthropic_sdk.Anthropic(api_key=api_key)

        messages = []
        for msg in history[-10:]:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role in ('user', 'assistant') and content:
                messages.append({'role': role, 'content': content})
        messages.append({'role': 'user', 'content': user_message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            system=CHATBOT_SYSTEM_PROMPT,
            messages=messages,
        )
        return JsonResponse({'response': response.content[0].text})

    except anthropic_sdk.AuthenticationError:
        return JsonResponse({'response': 'API key inválida. Verifica la configuración.'})
    except anthropic_sdk.RateLimitError:
        return JsonResponse({
            'response': 'Límite de uso de la API alcanzado. Intenta en unos minutos.'
        })
    except Exception as exc:
        print(f"Error en chat_api: {exc}")
        return JsonResponse({'response': f'Error del servidor: {exc}'}, status=500)
