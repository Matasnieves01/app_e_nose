"""Compensacion por humedad y temperatura (usa el DHT22 para ayudar al modelo).

Los sensores MQ bajan su Rs/Ro cuando sube la humedad (y la temperatura), AUNQUE
el gas no cambie. Como el modelo no puede recibir la humedad como entrada, la
usamos para CORREGIR las lecturas de gas antes de pasarlas al modelo:

    corregido = medido + k_hum*(hum - HUM_REF) + k_temp*(temp - TEMP_REF)

Asi "deshacemos" el efecto de la humedad/temperatura y dejamos solo la senal del
gas, llevandola a una condicion de referencia (la de tu base estable).

LIMITE HONESTO: esto sirve en humedad MODERADA. Cuando exhalas y la humedad
llega a ~90-100%, los sensores estan SATURADOS (condensacion) y ninguna formula
los recupera — ahi hace falta SECAR la muestra (desecante). La compensacion
estabiliza tu base y el rango moderado, no rescata el aliento saturado.
"""

# Condicion de referencia = tu base estable (ajusta a la tuya real).
HUM_REF = 50.0   # %
TEMP_REF = 25.0  # °C

# Cuanto BAJA cada Rs/Ro por cada +1% de humedad y por cada +1 °C, a gas
# constante. SON VALORES INICIALES APROXIMADOS: medelos con tus sensores
# (ver "Como medir los coeficientes" abajo) y ajusta aqui.
COEF = {
    "CO":      {"k_hum": 0.12, "k_temp": 0.15},
    "Alcohol": {"k_hum": 0.70, "k_temp": 0.40},
    "Acetone": {"k_hum": 0.02, "k_temp": 0.03},
}


def compensar(co: float, alcohol: float, acetone: float,
              temp: float, hum: float) -> tuple:
    """Devuelve (co, alcohol, acetone) corregidos a la condicion de referencia."""
    dh = hum - HUM_REF
    dt = temp - TEMP_REF

    def corr(valor: float, feature: str) -> float:
        c = COEF[feature]
        return valor + c["k_hum"] * dh + c["k_temp"] * dt

    return corr(co, "CO"), corr(alcohol, "Alcohol"), corr(acetone, "Acetone")


# ---------------------------------------------------------------------------
# COMO MEDIR LOS COEFICIENTES (una vez, para que sea correcto):
#
#   1. Sin exhalar (gas ~constante = aire de la sala), deja que la humedad de la
#      camara varie (p. ej. acercando una fuente de humedad lentamente) y anota
#      pares (humedad, Rs/Ro) de cada sensor.
#   2. La pendiente Rs/Ro vs humedad (con signo invertido) es k_hum:
#         k_hum = -(RsRo_alto - RsRo_bajo) / (hum_alto - hum_bajo)
#   3. Repite variando temperatura (a humedad estable) para k_temp.
#   4. Pega los valores arriba.
#
# Si no los mides, los valores por defecto solo aproximan; el modelo seguira
# sensible a la humedad.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Lectura tuya a 62% / 28°C corregida a la referencia 50% / 25°C:
    print(compensar(28.33, 61.27, 3.17, temp=28.3, hum=61.9))
