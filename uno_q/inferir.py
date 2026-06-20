"""E-Nose · inferencia en el UNO Q (lado contenedor de App Lab).

Flujo de una medicion (la app manda los comandos por WiFi -> command.txt):
  START   -> fase BASE: captura aire limpio (NO exhalar) para la auto-calibracion.
  MEASURE -> fase MIDIENDO: recolecta lecturas mientras exhalas (~9 s).
  STOP    -> FINALIZA: recorta extremos, promedia el centro e infiere UNA vez.

Algoritmo de la medida final (sobre la serie recolectada al exhalar):
  Fase 1 - Recorte: descarta las primeras y ultimas lecturas (estabilizacion
           inicial del flujo y agotamiento final) para quitar outliers.
  Fase 2 - Media: promedio aritmetico del subconjunto central limpio.
  Fase 3 - Diagnostico: una sola inferencia sobre esa media = valor mas probable.

Escribe el resultado en result.json (lo sirve wifi_host.py por WiFi).
"""
import json
import os

import joblib
import pandas as pd

from arduino.app_utils import App, Bridge

from calibracion import calibrar
from compensacion import compensar

# --- Puente con el host por archivos compartidos ---
_HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = os.path.join(_HERE, "result.json")
CMD_FILE = os.path.join(_HERE, "command.txt")

MODELS_DIR = "python/models"
FEATURES = ["CO", "Alcohol", "Acetone", "CO_7"]

# Guard de humedad/temperatura: por encima de esto los MQ estan saturados de
# vapor; esas lecturas se descartan (no entran al promedio).
HUM_MAX = 85.0   # %
TEMP_MAX = 40.0  # °C

# Recorte de extremos: cuantas lecturas quitar de cada punta antes de promediar.
RECORTE = 2

# --- Estado de la sesion ---
_fase = "idle"          # idle | base | midiendo
_base_buf = []          # lecturas (compensadas) de aire limpio -> auto-base
_medir_buf = []         # lecturas (compensadas) durante la exhalacion
_medias_sesion = None    # base de calibracion de esta sesion


def _publicar(obj: dict) -> None:
    """Escribe el resultado en result.json (lo sirve wifi_host por WiFi)."""
    try:
        tmp = RESULT_FILE + ".tmp"
        with open(tmp, "w") as f:
            f.write(json.dumps(obj))
        os.replace(tmp, RESULT_FILE)
    except Exception as e:
        print(f"[publicar] error: {e}")


print("Cargando modelos...")
scaler = joblib.load(f"{MODELS_DIR}/nb1_scaler_clasificacion.pkl")
clf = joblib.load(f"{MODELS_DIR}/nb1_modelo_clasificacion.pkl")
reg = joblib.load(f"{MODELS_DIR}/nb2_modelo_regresion.pkl")
print(f"✓ {type(scaler).__name__} | {type(clf).__name__} | {type(reg).__name__}")


def _check_command() -> None:
    """Lee command.txt y cambia de fase (START / MEASURE / STOP)."""
    global _fase, _base_buf, _medir_buf, _medias_sesion
    try:
        with open(CMD_FILE) as f:
            cmd = f.read().strip().upper()
    except FileNotFoundError:
        return

    if cmd == "START" and _fase == "idle":
        _fase = "base"
        _base_buf = []
        _medir_buf = []
        _medias_sesion = None
        print("[sesion] START - capturando base (NO exhalar)")
    elif cmd == "MEASURE" and _fase == "base":
        _calcular_base()
        _fase = "midiendo"
        print("[sesion] MEASURE - exhala ahora")
    elif cmd == "STOP" and _fase != "idle":
        _finalizar()
        _fase = "idle"


def _calcular_base() -> None:
    """Promedia las lecturas de aire limpio -> base de calibracion de la sesion."""
    global _medias_sesion
    if not _base_buf:
        _medias_sesion = None
        print("[base] sin lecturas de base")
        return
    k = len(_base_buf)
    _medias_sesion = {
        "CO": sum(b[0] for b in _base_buf) / k,
        "Alcohol": sum(b[1] for b in _base_buf) / k,
        "Acetone": sum(b[2] for b in _base_buf) / k,
    }
    print(f"[base] lista ({k} lecturas): {_medias_sesion}")


def _recortar(buf: list) -> list:
    """Fase 1: descarta primeras y ultimas lecturas (outliers de extremos)."""
    n = len(buf)
    if n > 2 * RECORTE + 1:
        return buf[RECORTE:n - RECORTE]
    if n >= 3:
        return buf[1:-1]   # pocas muestras: quita solo 1 de cada lado
    return buf             # muy pocas: usa todas


def _finalizar() -> None:
    """Fases 2 y 3: media del centro + una sola inferencia = diagnostico final."""
    if len(_medir_buf) < 2 or _medias_sesion is None:
        print("[final] muestras insuficientes")
        _publicar({"valida": False, "motivo": "insuficiente"})
        return

    central = _recortar(_medir_buf)
    k = len(central)
    co_m = sum(b[0] for b in central) / k
    alc_m = sum(b[1] for b in central) / k
    ace_m = sum(b[2] for b in central) / k

    cal = calibrar(co_m, alc_m, ace_m, medias=_medias_sesion)
    muestra = pd.DataFrame([cal])[FEATURES]
    muestra_scaled = pd.DataFrame(scaler.transform(muestra), columns=FEATURES)
    clase = int(clf.predict(muestra_scaled)[0])
    proba = clf.predict_proba(muestra_scaled)[0]
    bgl = float(reg.predict(muestra_scaled)[0])

    print("=" * 50)
    print(f"[FINAL] recolectadas={len(_medir_buf)}  usadas(centro)={k}")
    print(f"  media  CO={co_m:.2f}  Alc={alc_m:.2f}  Ace={ace_m:.2f}")
    print(f"  Clasificacion : {'DM — Diabetico' if clase == 1 else 'HI — Sano'}")
    print(f"  P(DM)         : {proba[1]:.3f}")
    print(f"  BGL estimado  : {bgl:.1f} mg/dL  (media de {k} lecturas)")
    print("=" * 50)

    _publicar({
        "valida": True,
        "final": True,
        "co": round(co_m, 2),
        "alcohol": round(alc_m, 2),
        "acetone": round(ace_m, 2),
        "glucose": round(bgl, 1),
        "diabetes": 1 if clase == 1 else 0,
        "prob": round(float(proba[1]), 3),
        "muestras": len(_medir_buf),
        "usadas": k,
    })


def inferir(payload: str) -> str:
    try:
        _check_command()
        if _fase == "idle":
            return json.dumps({"midiendo": False})

        d = json.loads(payload)
        co_raw = float(d["rs_ro_7"])
        alcohol_raw = float(d["rs_ro_3"])
        acetone_raw = float(d["rs_ro_135"])
        hum = float(d.get("hum", 0))
        temp = float(d.get("temp", 0))

        # GUARD: lectura saturada de humedad -> se descarta (no entra al promedio).
        if hum > HUM_MAX or temp > TEMP_MAX:
            print(f"  ⚠ saturado (hum {hum}% / temp {temp}°C) - lectura descartada")
            _publicar({"valida": False, "motivo": "humedad_alta",
                       "hum": hum, "temp": temp, "fase": _fase})
            return json.dumps({"saturado": True})

        # Compensacion de humedad/temperatura.
        co_c, alcohol_c, acetone_c = compensar(
            co_raw, alcohol_raw, acetone_raw, temp=temp, hum=hum)

        if _fase == "base":
            _base_buf.append((co_c, alcohol_c, acetone_c))
            print(f"[base] capturando... n={len(_base_buf)}")
            _publicar({"valida": False, "motivo": "preparando", "n": len(_base_buf)})
            return json.dumps({"preparando": True, "n": len(_base_buf)})

        # fase MIDIENDO: solo recolectar (NO se infiere por lectura).
        _medir_buf.append((co_c, alcohol_c, acetone_c))
        print(f"[medir] n={len(_medir_buf)}  CO={co_c:.2f} Alc={alcohol_c:.2f} "
              f"Ace={acetone_c:.2f} hum={hum}%")
        _publicar({"valida": False, "motivo": "midiendo",
                   "n": len(_medir_buf), "hum": hum})
        return json.dumps({"midiendo": True, "n": len(_medir_buf)})

    except Exception as e:
        print(f"[error] {e}")
        return json.dumps({"error": str(e)})


Bridge.provide("inferir", inferir)
App.run()
