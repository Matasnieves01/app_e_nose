"""inferir() con CALIBRACION aplicada.

Igual que tu version, pero antes de pasar las lecturas al modelo las mapea al
espacio del dataset con calibracion.calibrar(). Asi dejan de caer fuera de
rango y el modelo deja de saturar en "diabetico".

Pasos para que funcione bien:
  1. Junta una tanda de lecturas crudas de tus sensores (aire limpio + varias
     exhalaciones) y estima tus stats:  python3 estimar_calibracion.py --csv ...
  2. Pega el bloque USUARIO que te imprime en calibracion.py.
  3. Corre este inferir().
"""
import json
import os
from collections import deque

import joblib
import pandas as pd
from arduino.app_utils import App, Bridge

from calibracion import calibrar
from compensacion import compensar

# --- Puente con el host por archivos compartidos ---
# El contenedor de App Lab esta aislado de la red local (NAT), asi que el
# servidor WiFi corre en el HOST (wifi_host.py). Este proceso (contenedor)
# escribe el resultado en result.json y lee los comandos START/STOP de
# command.txt. La carpeta es compartida (bind mount), por eso funciona.
_HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = os.path.join(_HERE, "result.json")
CMD_FILE = os.path.join(_HERE, "command.txt")

_midiendo = False

# --- Calibracion por sesion (auto-base) ---
# El Ro de los MQ cambia entre arranques, asi que la base se mueve. Solucion:
# al iniciar cada medicion (START), las primeras N lecturas (aire limpio, antes
# de exhalar) definen la base de ESA sesion. Todo se mide relativo a esa base.
N_BASE = 5
_base_buf: list = []          # lecturas crudas para armar la base
_medias_sesion = None         # {"CO":.., "Alcohol":.., "Acetone":..} o None


def _check_command() -> None:
    """Lee command.txt (lo escribe wifi_host cuando la app manda START/STOP)."""
    global _midiendo, _base_buf, _medias_sesion
    try:
        with open(CMD_FILE) as f:
            nuevo = f.read().strip().upper() == "START"
    except FileNotFoundError:
        return
    # Flanco de subida (arranca una medicion nueva): reinicia la base de sesion.
    if nuevo and not _midiendo:
        _base_buf = []
        _medias_sesion = None
        print("[sesion] START - capturando base...")
    _midiendo = nuevo


def _publicar(obj: dict) -> None:
    """Escribe el resultado en result.json (lo sirve wifi_host por WiFi)."""
    try:
        tmp = RESULT_FILE + ".tmp"
        with open(tmp, "w") as f:
            f.write(json.dumps(obj))
        os.replace(tmp, RESULT_FILE)
    except Exception as e:
        print(f"[publicar] error: {e}")


MODELS_DIR = "python/models"
FEATURES = ["CO", "Alcohol", "Acetone", "CO_7"]

# Guard: la HUMEDAD es el confounder real. A ~85% los MQ aun NO condensan, asi
# que con la compensacion bien medida ese rango es utilizable. Por encima de 88%
# ya hay riesgo de condensacion -> se rechaza.
# IMPORTANTE: este umbral alto SOLO es seguro si mediste los coeficientes de
# compensacion (estimar_compensacion.py). Sin medirlos, la humedad arrastra la
# clasificacion a falso diabetico -> en ese caso baja HUM_MAX a 70.
HUM_MAX = 85.0   # % humedad relativa
TEMP_MAX = 40.0  # °C (solo tope de seguridad; ambiente normal pasa)

# Suavizado: promedia las ultimas N lecturas crudas para que el jitter/deriva
# del sensor no haga saltar la clasificacion lectura a lectura.
VENTANA = 5
_buffer = deque(maxlen=VENTANA)

# Ultimo resultado VALIDO (antes de saturar). Al exhalar, la humedad sube y el
# pico satura; guardamos el resultado de la ventana valida del aliento para
# mostrarlo en vez de solo "no valida".
_ultimo_valido = None


def _suavizar(co: float, alcohol: float, acetone: float) -> tuple:
    _buffer.append((co, alcohol, acetone))
    n = len(_buffer)
    return (
        sum(v[0] for v in _buffer) / n,
        sum(v[1] for v in _buffer) / n,
        sum(v[2] for v in _buffer) / n,
    )

print("Cargando modelos...")
scaler = joblib.load(f"{MODELS_DIR}/nb1_scaler_clasificacion.pkl")
clf = joblib.load(f"{MODELS_DIR}/nb1_modelo_clasificacion.pkl")
reg = joblib.load(f"{MODELS_DIR}/nb2_modelo_regresion.pkl")
print(f"✓ {type(scaler).__name__} | {type(clf).__name__} | {type(reg).__name__}")


def inferir(payload: str) -> str:
    global _ultimo_valido, _medias_sesion
    try:
        # Revisa si la app pidio START/STOP (via wifi_host -> command.txt).
        _check_command()

        # Solo detecta cuando la app inicio la medicion (START). En espera, no
        # procesa ni publica (evita lecturas fuera de sesion).
        if not _midiendo:
            return json.dumps({"midiendo": False})

        d = json.loads(payload)

        # Lecturas crudas de tus sensores (Rs/Ro).
        co_raw = float(d["rs_ro_7"])
        alcohol_raw = float(d["rs_ro_3"])
        acetone_raw = float(d["rs_ro_135"])
        hum = float(d.get("hum", 0))
        temp = float(d.get("temp", 0))

        # GUARD: si hay exceso de humedad (o temp fuera del tope), la lectura no
        # sirve. Mejor avisar que reportar un falso positivo.
        if hum > HUM_MAX or temp > TEMP_MAX:
            motivo = "humedad_alta" if hum > HUM_MAX else "temperatura_alta"
            print("─" * 50)
            print(f"  ⚠ SATURADO ({motivo}) — humedad {hum}% / temp {temp}°C")
            if _ultimo_valido:
                print(f"  Mostrando ultimo resultado valido del aliento:")
                print(f"  → {_ultimo_valido['clase']} | BGL {_ultimo_valido['bgl']} mg/dL")
            else:
                print("  Aun sin resultado valido. Exhala mas suave o seca la muestra.")
            print("─" * 50)
            # Notifica a la app: lectura no valida + el ultimo resultado valido.
            app_msg = {"valida": False, "motivo": motivo, "hum": hum, "temp": temp}
            if _ultimo_valido:
                app_msg.update({
                    "glucose": _ultimo_valido["bgl"],
                    "diabetes": 1 if _ultimo_valido["clase"] == "DM" else 0,
                    "prob": _ultimo_valido["p_dm"],
                })
            _publicar(app_msg)
            return json.dumps({
                "valida": False,
                "motivo": motivo,
                "hum": hum,
                "temp": temp,
                "ultimo": _ultimo_valido,  # resultado de la ventana valida
            })

        # 1) COMPENSACION: quita el efecto de humedad/temperatura usando el DHT22.
        co_c, alcohol_c, acetone_c = compensar(
            co_raw, alcohol_raw, acetone_raw, temp=temp, hum=hum)

        # 2) SUAVIZADO: promedio movil para que el jitter no salte.
        co_s, alcohol_s, acetone_s = _suavizar(co_c, alcohol_c, acetone_c)

        # AUTO-BASE: las primeras N lecturas de la sesion (aire limpio, antes de
        # exhalar) definen la base, ya compensada y suavizada. Todo se calibra
        # relativo a ella -> robusto a la deriva del Ro entre arranques.
        if _medias_sesion is None:
            _base_buf.append((co_s, alcohol_s, acetone_s))
            faltan = N_BASE - len(_base_buf)
            if faltan > 0:
                print(f"[base] capturando... faltan {faltan}")
                _publicar({"valida": False, "motivo": "preparando", "faltan": faltan})
                return json.dumps({"preparando": True, "faltan": faltan})
            k = len(_base_buf)
            _medias_sesion = {
                "CO": sum(b[0] for b in _base_buf) / k,
                "Alcohol": sum(b[1] for b in _base_buf) / k,
                "Acetone": sum(b[2] for b in _base_buf) / k,
            }
            print(f"[base] lista: {_medias_sesion}")

        # 3) CALIBRACION relativa a la base de la sesion (auto-ajustada).
        cal = calibrar(co_s, alcohol_s, acetone_s, medias=_medias_sesion)

        muestra = pd.DataFrame([cal])[FEATURES]
        muestra_scaled = pd.DataFrame(scaler.transform(muestra), columns=FEATURES)

        clase = clf.predict(muestra_scaled)[0]
        proba = clf.predict_proba(muestra_scaled)[0]
        bgl = reg.predict(muestra_scaled)[0]

        resultado = {
            "valida": True,
            "clase": "DM" if clase == 1 else "HI",
            "p_hi": round(float(proba[0]), 3),
            "p_dm": round(float(proba[1]), 3),
            "bgl": round(float(bgl), 1),
        }
        _ultimo_valido = resultado  # se retiene si luego satura el aliento

        print("─" * 50)
        print(f"  CRUDO   CO={co_raw:.2f}  Alc={alcohol_raw:.2f}  Ace={acetone_raw:.2f}")
        print(f"  CALIBR  CO={cal['CO']:.2f}  Alc={cal['Alcohol']:.2f}  "
              f"Ace={cal['Acetone']:.2f}  CO_7={cal['CO_7']:.2f}")
        print(f"  Temp {d.get('temp','?')} °C | Humedad {d.get('hum','?')} %")
        print(f"  Clasificación : {'DM — Diabético' if clase == 1 else 'HI — Sano'}")
        print(f"  P(HI — Sano)  : {resultado['p_hi']}")
        print(f"  P(DM — Diab.) : {resultado['p_dm']}")
        print(f"  BGL estimado  : {resultado['bgl']} mg/dL")
        print("─" * 50)

        # Publica el resultado para el host BLE (contrato de la app).
        _publicar({
            "valida": True,
            "co": round(co_raw, 2),
            "alcohol": round(alcohol_raw, 2),
            "acetone": round(acetone_raw, 2),
            "glucose": resultado["bgl"],
            "diabetes": 1 if clase == 1 else 0,
            "prob": resultado["p_dm"],
            "hum": hum,
            "temp": temp,
        })

        return json.dumps(resultado)

    except Exception as e:
        print(f"[error] {e}")
        return json.dumps({"error": str(e)})


Bridge.provide("inferir", inferir)
App.run()
