"""Compensacion por temperatura y humedad usando la curva del datasheet MQ.

Los sensores MQ (oxido metalico) cambian su Rs/Ro con la temperatura y la
humedad AUNQUE el gas no cambie. La hoja de datos da un FACTOR DE CORRECCION
CF(temp, hum) relativo a la condicion de referencia (20 C / 33 %RH):

    Rs/Ro corregido = Rs/Ro medido / CF(temp, hum)

CF = 1 en la referencia; <1 cuando hace mas calor/humedad (la lectura baja),
asi que al dividir se "devuelve" la lectura a la referencia. Esto es mas
correcto que una correccion lineal a ojo, y aprovecha mejor el DHT22.

NOTA: el polinomio es el del MQ-135. Se aplica a los 3 sensores como
aproximacion (MQ-7 y MQ-3 tienen curvas parecidas). Si quieres exactitud por
sensor, mide la curva de cada uno y ajusta.

LIMITE HONESTO: a ~90-100 %RH los sensores estan saturados (condensacion) y
ninguna formula los recupera -> hace falta SECAR la muestra (desecante).
"""

# Constantes del factor de correccion (MQ-135, hoja de datos / libreria MQ135).
CORA = 0.00035
CORB = 0.02718
CORC = 1.39538
CORD = 0.0018
CORE = -0.003333333
CORF = -0.001923077
CORG = 1.130128205


def factor_correccion(temp: float, hum: float) -> float:
    """CF(temp, hum) segun la curva del datasheet. CF = 1 en 20 C / 33 %RH."""
    if temp < 20:
        return CORA * temp * temp - CORB * temp + CORC - (hum - 33.0) * CORD
    return CORE * temp + CORF * hum + CORG


def compensar(co: float, alcohol: float, acetone: float,
              temp: float, hum: float) -> tuple:
    """Corrige (co, alcohol, acetone) a la condicion de referencia."""
    cf = factor_correccion(temp, hum)
    if cf <= 0.1:          # proteccion ante valores raros
        cf = 1.0
    return co / cf, alcohol / cf, acetone / cf


if __name__ == "__main__":
    # CF deberia ser ~1.0 en la referencia y bajar (corregir mas) con calor/humedad.
    for t, h in [(20, 33), (25, 50), (28, 62), (34, 86)]:
        cf = factor_correccion(t, h)
        print(f"temp={t} hum={h}% -> CF={cf:.3f}  (x{1/cf:.3f} a la lectura)")
