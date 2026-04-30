import re
import unicodedata

import pandas as pd


DEPARTAMENTOS_DANE = {
    5: "ANTIOQUIA",
    8: "ATLÁNTICO",
    11: "BOGOTÁ, D.C.",
    13: "BOLÍVAR",
    15: "BOYACÁ",
    17: "CALDAS",
    18: "CAQUETÁ",
    19: "CAUCA",
    20: "CESAR",
    23: "CÓRDOBA",
    25: "CUNDINAMARCA",
    27: "CHOCÓ",
    41: "HUILA",
    44: "LA GUAJIRA",
    47: "MAGDALENA",
    50: "META",
    52: "NARIÑO",
    54: "NORTE DE SANTANDER",
    63: "QUINDÍO",
    66: "RISARALDA",
    68: "SANTANDER",
    70: "SUCRE",
    73: "TOLIMA",
    76: "VALLE DEL CAUCA",
    81: "ARAUCA",
    85: "CASANARE",
    86: "PUTUMAYO",
    88: "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA",
    91: "AMAZONAS",
    94: "GUAINÍA",
    95: "GUAVIARE",
    97: "VAUPÉS",
    99: "VICHADA",
}

DEPARTAMENTOS_POR_NOMBRE = {
    "ANTIOQUIA": "ANTIOQUIA",
    "ATLANTICO": "ATLÁNTICO",
    "ATLÁNTICO": "ATLÁNTICO",
    "BOGOTA": "BOGOTÁ, D.C.",
    "BOGOTA DC": "BOGOTÁ, D.C.",
    "BOGOTA D C": "BOGOTÁ, D.C.",
    "BOGOTA D,C": "BOGOTÁ, D.C.",
    "BOGOTA D,C,": "BOGOTÁ, D.C.",
    "BOGOTÁ, D.C.": "BOGOTÁ, D.C.",
    "BOGOTÁ, D,C,": "BOGOTÁ, D.C.",
    "BOLIVAR": "BOLÍVAR",
    "BOLÍVAR": "BOLÍVAR",
    "BOYACA": "BOYACÁ",
    "BOYACÁ": "BOYACÁ",
    "CALDAS": "CALDAS",
    "CAQUETA": "CAQUETÁ",
    "CAQUETÁ": "CAQUETÁ",
    "CAUCA": "CAUCA",
    "CESAR": "CESAR",
    "CORDOBA": "CÓRDOBA",
    "CÓRDOBA": "CÓRDOBA",
    "CUNDINAMARCA": "CUNDINAMARCA",
    "CHOCO": "CHOCÓ",
    "CHOCÓ": "CHOCÓ",
    "HUILA": "HUILA",
    "LA GUAJIRA": "LA GUAJIRA",
    "MAGDALENA": "MAGDALENA",
    "META": "META",
    "NARINO": "NARIÑO",
    "NARIÑO": "NARIÑO",
    "NORTE DE SANTANDER": "NORTE DE SANTANDER",
    "QUINDIO": "QUINDÍO",
    "QUINDÍO": "QUINDÍO",
    "RISARALDA": "RISARALDA",
    "SANTANDER": "SANTANDER",
    "SUCRE": "SUCRE",
    "TOLIMA": "TOLIMA",
    "VALLE": "VALLE DEL CAUCA",
    "VALLE DEL CAUCA": "VALLE DEL CAUCA",
    "ARAUCA": "ARAUCA",
    "CASANARE": "CASANARE",
    "PUTUMAYO": "PUTUMAYO",
    "SAN ANDRES": "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA",
    "SAN ANDRÉS": "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA",
    "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA": (
        "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA"
    ),
    "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA": (
        "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA"
    ),
    "AMAZONAS": "AMAZONAS",
    "GUAINIA": "GUAINÍA",
    "GUAINÍA": "GUAINÍA",
    "GUAVIARE": "GUAVIARE",
    "VAUPES": "VAUPÉS",
    "VAUPÉS": "VAUPÉS",
    "VICHADA": "VICHADA",
}


def _reparar_mojibake(valor):
    if pd.isna(valor):
        return valor

    texto = str(valor).strip()
    if not texto:
        return pd.NA

    if any(marca in texto for marca in ("Ã", "Â", "â")):
        for origen in ("latin1", "cp1252"):
            try:
                texto = texto.encode(origen).decode("utf-8")
                break
            except UnicodeError:
                pass

    return texto


def _sin_tildes(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(caracter for caracter in texto if not unicodedata.combining(caracter))


def _clave_nombre_departamento(valor):
    texto = _reparar_mojibake(valor)
    if pd.isna(texto):
        return None

    texto = str(texto).upper().strip()
    texto = _sin_tildes(texto)
    texto = re.sub(r"[^A-Z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def estandarizar_departamento(nombre, codigo=None):
    codigo_num = pd.to_numeric(pd.Series([codigo]), errors="coerce").iloc[0]
    if pd.notna(codigo_num):
        codigo_int = int(codigo_num)
        if codigo_int in DEPARTAMENTOS_DANE:
            return DEPARTAMENTOS_DANE[codigo_int]

    if pd.isna(nombre):
        return pd.NA

    nombre_reparado = str(_reparar_mojibake(nombre)).upper().strip()
    if nombre_reparado in DEPARTAMENTOS_POR_NOMBRE:
        return DEPARTAMENTOS_POR_NOMBRE[nombre_reparado]

    clave = _clave_nombre_departamento(nombre_reparado)
    return DEPARTAMENTOS_POR_NOMBRE.get(clave, nombre_reparado)


def _normalizar_nombre_columna(columna):
    texto = _reparar_mojibake(columna)
    texto = _sin_tildes(texto).lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")

    equivalencias = {
        "anio": "ano",
        "ano": "ano",
        "a_o": "ano",
        "codigo_departamento": "codigo_departamento",
        "cod_departamento": "codigo_departamento",
        "c_digo_departamento": "codigo_departamento",
        "digo_departamento": "codigo_departamento",
    }
    return equivalencias.get(texto, texto)


def normalizar_columnas(df):
    df = df.copy()
    columnas = []
    usadas = set()

    for columna in df.columns:
        nombre = _normalizar_nombre_columna(columna)
        nombre_unico = nombre
        contador = 2
        while nombre_unico in usadas:
            nombre_unico = f"{nombre}_{contador}"
            contador += 1
        columnas.append(nombre_unico)
        usadas.add(nombre_unico)

    df.columns = columnas
    return df


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


def limpiar_master_data(df):
    df = normalizar_columnas(df)

    if "ubicacion_completa" in df.columns:
        df = df.drop(columns=["ubicacion_completa"])

    if "departamento" not in df.columns:
        raise ValueError("No se encontro la columna departamento.")

    if "ano" in df.columns:
        df["ano"] = _a_numerico(df["ano"]).astype("Int64")

    if "codigo_departamento" in df.columns:
        df["codigo_departamento"] = _a_numerico(df["codigo_departamento"]).astype("Int64")
        df["departamento"] = [
            estandarizar_departamento(nombre, codigo)
            for nombre, codigo in zip(df["departamento"], df["codigo_departamento"])
        ]
    else:
        df["departamento"] = df["departamento"].apply(estandarizar_departamento)

    df["departamento"] = df["departamento"].astype("string").str.strip().str.upper()
    df["Ubicacion Completa"] = df["departamento"]

    columnas_texto = ["tipo"]
    for columna in columnas_texto:
        if columna in df.columns:
            df[columna] = df[columna].apply(_reparar_mojibake)

    excluir_numericas = {"departamento", "Ubicacion Completa", "tipo"}
    for columna in df.columns:
        if columna not in excluir_numericas:
            df[columna] = _a_numerico(df[columna])

    historicas = df[df["departamento"].notna()].copy()
    predicciones = df[df["departamento"].isna()].copy()

    claves = [col for col in ("ano", "codigo_departamento", "departamento") if col in historicas.columns]
    if claves:
        historicas = historicas.sort_values(claves).drop_duplicates(subset=claves, keep="last")

    if "desercion" in historicas.columns:
        historicas = historicas.dropna(subset=["desercion"])

    df_limpio = pd.concat([historicas, predicciones], ignore_index=True)

    columnas_principales = [
        "ano",
        "codigo_departamento",
        "departamento",
        "Ubicacion Completa",
        "poblacion_5_16",
        "tasa_matriculacion_5_16",
        "desercion",
        "desercion_predicha",
        "tipo",
    ]
    columnas_ordenadas = [col for col in columnas_principales if col in df_limpio.columns]
    columnas_ordenadas += [col for col in df_limpio.columns if col not in columnas_ordenadas]

    return df_limpio[columnas_ordenadas]


def limpiar_datos(df_des, df_icf):
    print("Limpieza: iniciando cruce de desercion vs resultados Saber 11...")

    df_des = limpiar_master_data(df_des)

    if not df_icf.empty:
        print("Procesando microdatos de Saber 11...")
        df_icf = normalizar_columnas(df_icf)

        if "periodo" in df_icf.columns:
            df_icf["ano"] = pd.to_numeric(df_icf["periodo"].astype(str).str[:4], errors="coerce")

        col_depto = next(
            (col for col in ("cole_mcpio_depar", "estu_depto_reside", "departamento") if col in df_icf.columns),
            None,
        )
        col_puntaje = next(
            (col for col in ("punt_global", "puntaje_global", "punt_total") if col in df_icf.columns),
            None,
        )

        if col_depto and col_puntaje and "ano" in df_icf.columns:
            df_icf["departamento"] = df_icf[col_depto].apply(estandarizar_departamento)
            df_icf["puntaje_estudiante"] = _a_numerico(df_icf[col_puntaje])

            df_icf_agrupado = (
                df_icf.dropna(subset=["departamento", "ano"])
                .groupby(["departamento", "ano"], as_index=False)["puntaje_estudiante"]
                .mean()
            )
            df_final = pd.merge(df_des, df_icf_agrupado, on=["departamento", "ano"], how="left")
            print(f"Cruce exitoso. Puntaje agregado usando {col_depto}.")
        else:
            print("No se hallaron columnas suficientes para cruzar Saber 11.")
            df_final = df_des
            if "puntaje_estudiante" not in df_final.columns:
                df_final["puntaje_estudiante"] = pd.NA
    else:
        df_final = df_des
        if "puntaje_estudiante" not in df_final.columns:
            df_final["puntaje_estudiante"] = pd.NA

    return limpiar_master_data(df_final)
