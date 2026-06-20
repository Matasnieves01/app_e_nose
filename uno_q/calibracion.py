"""Calibracion: mapea las lecturas de TUS sensores al espacio del dataset.

Problema: tus Rs/Ro estan en una escala distinta a la del dataset (otros
sensores / otro Ro), asi que caen fuera del rango que el modelo conoce y este
satura (siempre "diabetico"). Solucion sin tocar dataset ni modelos: alinear la
DISTRIBUCION de tus lecturas a la del dataset (z-score matching):

    mapeado = mean_dataset + (crudo - mean_tuyo) / std_tuyo * std_dataset

Asi tu lectura promedio cae en el promedio del dataset y tus variaciones se
expresan en la misma escala que el modelo aprendio. Al final se recorta al
rango del dataset para no extrapolar.

IMPORTANTE (honestidad cientifica):
  Esto NO calibra fisicamente los sensores; ASUME que la distribucion de tus
  mediciones se parece a la del dataset. Hace que el sistema responda de forma
  coherente (deja de saturar), pero la validez clinica depende de que esa
  suposicion se cumpla. Documenta esta calibracion en tu trabajo.
"""

# ---- Estadisticos del DATASET. Calculados de diabetessynthetic.csv ----
# 'std'/'min'/'max' = de todo el dataset (escala y recorte).
# 'sano' = media de la clase SANA (target=0): es el ANCLA de tu linea base.
# Anclamos tu lectura promedio a la zona SANA (no al centro, que es la frontera),
# para que en reposo des "Sano" y solo un cambio real de gas cruce a diabetico.
DATASET = {
    "CO":      {"sano": 44.721, "std": 5.815, "min": 32.412, "max": 50.282},
    "Alcohol": {"sano": 273.780, "std": 72.718, "min": 92.960, "max": 342.644},
    "Acetone": {"sano": 31.233, "std": 3.927, "min": 21.988, "max": 33.801},
    # CO_7 NO es igual a CO: vive en otra escala (~4.16x). Como solo tienes un
    # MQ-7, mapeamos la MISMA lectura cruda del MQ-7 a la distribucion de CO_7.
    "CO_7":    {"sano": 189.105, "std": 32.577, "min": 124.124, "max": 216.948},
}

# ---- Estadisticos de TUS sensores (medir con estimar_calibracion.py) ----
# Valores iniciales APROXIMADOS sacados de tu salida serial. RECALIBRA con tus
# propias mediciones (ver estimar_calibracion.py) para que sea correcto.
USUARIO = {
    "CO":      {"mean": 27.5, "std": 1.6},
    "Alcohol": {"mean": 54.0, "std": 5.5},
    "Acetone": {"mean": 3.6,  "std": 0.35},
    # CO_7 = misma lectura cruda del MQ-7, asi que usa los mismos stats que CO.
    "CO_7":    {"mean": 27.5, "std": 1.6},
}


def _mapear(valor: float, feature: str, mean: float) -> float:
    u = USUARIO[feature]
    d = DATASET[feature]
    std = u["std"] if u["std"] else 1.0
    z = (valor - mean) / std
    # Ancla tu media en la zona SANA; las desviaciones usan la escala del dataset.
    mapeado = d["sano"] + z * d["std"]
    # Recorta al rango del dataset (evita extrapolar fuera de lo entrenado).
    return max(d["min"], min(d["max"], mapeado))


def calibrar(co: float, alcohol: float, acetone: float, medias=None) -> dict:
    """Mapea tus 3 lecturas crudas al espacio del dataset.

    `medias` permite usar una base POR SESION (capturada al iniciar la medicion)
    en vez de la fija de USUARIO. Asi se auto-ajusta a la deriva del Ro entre
    arranques. Si es None, usa las medias de USUARIO.
    """
    m_co = medias["CO"] if medias else USUARIO["CO"]["mean"]
    m_alc = medias["Alcohol"] if medias else USUARIO["Alcohol"]["mean"]
    m_ace = medias["Acetone"] if medias else USUARIO["Acetone"]["mean"]
    return {
        "CO": _mapear(co, "CO", m_co),
        "Alcohol": _mapear(alcohol, "Alcohol", m_alc),
        "Acetone": _mapear(acetone, "Acetone", m_ace),
        "CO_7": _mapear(co, "CO_7", m_co),  # mismo MQ-7, otra escala
    }


if __name__ == "__main__":
    # Base por sesion = {CO:27.5, Alcohol:54, Acetone:3.6}
    base = {"CO": 27.5, "Alcohol": 54.0, "Acetone": 3.6}
    print(calibrar(27.5, 54.0, 3.6, base))   # en la base -> zona sana
    print(calibrar(25.0, 50.0, 3.0, base))   # mas gas -> baja hacia diabetico
