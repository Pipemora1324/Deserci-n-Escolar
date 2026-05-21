# 🇨🇴 Sistema de Analítica para la Deserción Escolar en Colombia

<div align="center">

**Concurso Datos al Ecosistema 2026 · Ministerio de TIC · República de Colombia**

[![Live Demo](https://img.shields.io/badge/🌐_Demo_en_Vivo-desercion--escolar--ucc.vercel.app-003580?style=for-the-badge)](https://desercion-escolar-ucc.vercel.app/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Vercel](https://img.shields.io/badge/Vercel-Deploy-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)
[![Power BI](https://img.shields.io/badge/Power_BI-Dashboard-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com/)

*Universidad Cooperativa de Colombia · Sede Pasto · Nariño*

</div>

---

## 📋 Tabla de contenidos

1. [Descripción del proyecto](#descripción-del-proyecto)
2. [Hallazgos principales](#hallazgos-principales)
3. [Demo en vivo](#demo-en-vivo)
4. [Stack tecnológico](#stack-tecnológico)
5. [Estructura del proyecto](#estructura-del-proyecto)
6. [Fuente de datos](#fuente-de-datos)
7. [Pipeline de datos](#pipeline-de-datos)
8. [Análisis estadístico ANOVA](#análisis-estadístico-anova)
9. [Instalación y uso local](#instalación-y-uso-local)
10. [Despliegue en Vercel](#despliegue-en-vercel)
11. [Equipo](#equipo)

---

## Descripción del proyecto

Este proyecto analiza la **deserción escolar en Colombia** usando datos abiertos del Ministerio de Educación Nacional, publicados en [datos.gov.co](https://www.datos.gov.co/Educaci-n/Tasa-de-Deserci-n-Escolar/ji8i-4anb) (dataset `ji8i-4anb`).

El sistema transforma **462 registros históricos** de 33 departamentos (2011–2024) en inteligencia accionable mediante estadística inferencial, visualización interactiva y un portal web institucional desplegado en Vercel.

### Objetivos

- Identificar patrones territoriales de deserción escolar mediante análisis ANOVA
- Cuantificar diferencias por región geográfica, nivel educativo y período histórico
- Proporcionar evidencia estadística para orientar políticas de permanencia escolar
- Presentar los resultados en un portal web de calidad institucional

---

## Hallazgos principales

| Análisis | F-estadístico | p-valor | Conclusión |
|---|---|---|---|
| Por región geográfica | **49.08** | < 0.001 | La Amazonia (5.91%) supera significativamente al resto de regiones |
| Por nivel educativo | **58.24** | < 0.001 | Secundaria (5.10%) vs. Primaria (3.42%) — diferencia crítica |
| Por período histórico | **3.82** | 0.022 | Pandemia (3.59%) → Post-pandemia (4.34%) — rebote significativo |

### Top 5 departamentos con mayor deserción histórica

| # | Departamento | Deserción promedio | Región |
|---|---|---|---|
| 1 | **Guainía** | 6.86% | Amazonia |
| 2 | **Vichada** | 6.80% | Orinoquia |
| 3 | **Putumayo** | 6.14% | Amazonia |
| 4 | **Caquetá** | 6.12% | Amazonia |
| 5 | **Vaupés** | 6.05% | Amazonia |

> **Promedio nacional histórico:** 4.07% · **Aprobación:** 90.05% · **Reprobación:** 5.89%
>
> **Nariño** (sede UCC Pasto): 2.59% — por debajo del promedio nacional, en el tercio inferior del ranking (mejor rendimiento).

---

## Demo en vivo

🌐 **[https://desercion-escolar-ucc.vercel.app/](https://desercion-escolar-ucc.vercel.app/)**

| Página | URL | Descripción |
|---|---|---|
| Inicio | `/` | Hero, KPIs, hallazgos, Top 5, consultor departamental |
| Dashboard | `/#dashboard` | Power BI embebido con filtros interactivos |
| Análisis Estadístico | `/anova/` | 3 ANOVAs + Tukey HSD + gráficos matplotlib |
| Metodología | `/metodologia/` | Fuentes, pipeline, hipótesis formales, referencias |

---

## Stack tecnológico

### Backend
| Tecnología | Uso |
|---|---|
| **Python 3.13** | Lenguaje principal |
| **Django 5.x** | Framework web |
| **pandas** | Manipulación del dataset |
| **scipy.stats** | Pruebas ANOVA (`f_oneway`) |
| **statsmodels** | Post-hoc Tukey HSD (`pairwise_tukeyhsd`) |
| **matplotlib** | Generación de gráficos estadísticos (base64) |
| **scikit-learn** | Modelo de regresión lineal para proyecciones |
| **whitenoise** | Servicio de archivos estáticos en producción |

### Frontend
| Tecnología | Uso |
|---|---|
| **Bootstrap 5.3** | Layout responsivo |
| **Merriweather / Source Sans 3** | Tipografía institucional (Google Fonts) |
| **Font Awesome 6** | Iconografía |
| **Power BI Embedded** | Dashboard interactivo |

### Data & Infraestructura
| Tecnología | Uso |
|---|---|
| **PySpark** | ETL y procesamiento de Big Data |
| **Power BI** | Visualización interactiva del dashboard |
| **Vercel** | Despliegue serverless (Python runtime) |
| **GitHub** | Control de versiones |
| **datos.gov.co** | Fuente primaria de datos abiertos |

---

## Estructura del proyecto

```
colombia-edu-analytics-pipeline/
│
├── 📁 web/                          # Aplicación Django
│   ├── 📁 analytics/                # App principal
│   │   └── views.py                 # Vistas: home, anova_view, metodologia
│   ├── 📁 core/                     # Configuración Django
│   │   ├── settings.py
│   │   └── urls.py                  # Rutas: /, /anova/, /metodologia/
│   └── 📁 templates/                # Templates HTML
│       ├── base.html                # Navbar + Footer institucional
│       ├── index.html               # Página de inicio
│       ├── anova.html               # Análisis estadístico
│       └── metodologia.html         # Documento metodológico
│
├── 📁 src/                          # Pipeline de datos
│   ├── ingestion.py                 # Extracción desde API datos.gov.co
│   ├── cleaning.py                  # Limpieza y normalización DANE
│   ├── model_ia.py                  # Modelo regresión lineal
│   └── main.py                      # Orquestador del pipeline
│
├── 📁 data/
│   └── 📁 processed/
│       ├── master_data_final.csv    # Dataset consolidado (462 registros, 41 cols)
│       └── Dashboard_Desercion_UCC_Pasto.pbix
│
├── wsgi.py                          # Entry point para Vercel
├── vercel.json                      # Configuración de despliegue
└── requirements.txt                 # Dependencias Python
```

---

## Fuente de datos

| Campo | Detalle |
|---|---|
| **Fuente** | Ministerio de Educación Nacional de Colombia |
| **Portal** | [datos.gov.co](https://www.datos.gov.co) |
| **Dataset ID** | `ji8i-4anb` |
| **Período** | 2011 – 2024 |
| **Registros** | 462 históricos (33 departamentos) |
| **Variables** | 41 columnas (deserción, cobertura, aprobación, reprobación, etc.) |
| **Licencia** | Datos abiertos — Gobierno de Colombia |

### Variables clave

```
desercion              → Tasa de deserción total (%)
desercion_transicion   → Deserción en nivel Transición (%)
desercion_primaria     → Deserción en Primaria (%)
desercion_secundaria   → Deserción en Secundaria (%)
desercion_media        → Deserción en Media (%)
departamento           → Nombre del departamento (normalizado DANE)
ano                    → Año del registro
tasa_matriculacion_5_16→ Cobertura población en edad escolar
```

---

## Pipeline de datos

```
datos.gov.co (API REST)
        │
        ▼
  [ingestion.py]
  Extracción ~50.000 registros/llamada
        │
        ▼
  [cleaning.py]
  - Normalización nombres DANE (tildes, variantes)
  - Conversión porcentajes → float
  - Eliminación de duplicados
  - Estandarización tipos numéricos
        │
        ▼
  [main.py → model_ia.py]
  - Regresión lineal (scikit-learn)
  - Proyecciones 2025-2027
  - Concatenación datos reales + predicciones
        │
        ▼
  master_data_final.csv (462 registros × 41 columnas)
        │
        ├──▶ Power BI → Dashboard interactivo
        │
        └──▶ Django views.py
              ├── ANOVA (scipy.stats.f_oneway)
              ├── Tukey HSD (statsmodels)
              └── Gráficos matplotlib → base64 → HTML
```

---

## Análisis estadístico ANOVA

Se aplican **tres pruebas ANOVA de un factor** (α = 0.05) sobre los 462 registros reales:

### ANOVA 1 — Por Región Geográfica

```
H₀: μ_Caribe = μ_Andina = μ_Pacífica = μ_Orinoquia = μ_Amazonia
H₁: ∃ i,j : μᵢ ≠ μⱼ

Resultado: F = 49.08, p < 0.001 → Se rechaza H₀
```

La región Amazónica (5.91%) presenta deserción significativamente mayor que todas las demás regiones. El post-hoc Tukey HSD confirma diferencias en todos los pares que involucran la Amazonia.

### ANOVA 2 — Por Nivel Educativo

```
H₀: μ_Transición = μ_Primaria = μ_Secundaria = μ_Media
H₁: ∃ i,j : μᵢ ≠ μⱼ

Resultado: F = 58.24, p < 0.001 → Se rechaza H₀
```

| Nivel | Media | Posición |
|---|---|---|
| Secundaria | 5.10% | Mayor riesgo |
| Transición | 4.12% | — |
| Media | 3.74% | — |
| Primaria | 3.42% | Menor riesgo |

### ANOVA 3 — Por Período Histórico

```
H₀: μ_pre-pandemia = μ_pandemia = μ_post-pandemia
H₁: ∃ i,j : μᵢ ≠ μⱼ

Resultado: F = 3.82, p = 0.022 → Se rechaza H₀
```

| Período | Años | Deserción promedio |
|---|---|---|
| Pre-pandemia | 2011–2019 | 4.08% |
| **Pandemia** | 2020–2021 | **3.59%** ↓ |
| Post-pandemia | 2022–2024 | **4.34%** ↑ |

La pandemia redujo temporalmente la deserción (subsidios de permanencia). El rebote post-pandemia (4.34%) requiere atención urgente de política pública.

---

## Instalación y uso local

### Requisitos previos

- Python 3.10+
- Git

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Pipemora1324/Deserci-n-Escolar.git
cd Deserci-n-Escolar

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar el pipeline de datos (opcional — el CSV ya está incluido)
python src/main.py

# 5. Correr el servidor Django
cd web
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000/`

### Variables de entorno

Actualmente no se requieren variables de entorno para la funcionalidad básica.
El archivo `requirements.txt` incluye todas las dependencias necesarias.

---

## Despliegue en Vercel

El proyecto está configurado para despliegue automático en Vercel mediante `vercel.json`:

```json
{
  "builds": [{ "src": "wsgi.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "wsgi.py" }]
}
```

### Pasos para desplegar

```bash
# 1. Asegurarse de estar en la rama correcta
git checkout vercel-fix

# 2. Hacer cambios y commit
git add .
git commit -m "descripción de los cambios"

# 3. Push — Vercel detecta automáticamente y despliega
git push origin vercel-fix

# 4. Merge a main para actualizar la URL de producción
git checkout main
git merge vercel-fix
git push origin main
```

> Vercel despliega automáticamente en ~2 minutos tras el push a `main`.

---

## Equipo

**Universidad Cooperativa de Colombia — Sede Pasto**

Proyecto desarrollado en el marco del concurso **Datos al Ecosistema 2026** del Ministerio de Tecnologías de la Información y las Comunicaciones (MinTIC) de Colombia.

---

## Referencias

1. Ministerio de Educación Nacional. *Tasa de Deserción Escolar por Departamento (2011-2024)*. [datos.gov.co/ji8i-4anb](https://www.datos.gov.co/Educaci-n/Tasa-de-Deserci-n-Escolar/ji8i-4anb)
2. MinTIC Colombia. *Concurso Datos al Ecosistema 2026*. [mintic.gov.co](https://www.mintic.gov.co)
3. Virtanen, P. et al. (2020). *SciPy 1.0*. Nature Methods, 17(3), 261–272.
4. Seabold, S. & Perktold, J. (2010). *Statsmodels*. Proc. 9th Python in Science Conf.
5. Apache Software Foundation. *PySpark — Apache Spark Python API*. [spark.apache.org](https://spark.apache.org)

---

<div align="center">

**🇨🇴 Sistema Nacional de Analítica Educativa · Colombia 2026**

*Datos abiertos del Ministerio de Educación Nacional*

[![Ver demo](https://img.shields.io/badge/Ver_Demo-003580?style=for-the-badge&logo=vercel&logoColor=white)](https://desercion-escolar-ucc.vercel.app/)

</div>
