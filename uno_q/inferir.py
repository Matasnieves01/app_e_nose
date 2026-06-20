"""E-Nose · inferencia en el UNO Q (lado contenedor de App Lab).

Dos fases por sesion (la app manda los comandos por WiFi -> command.txt):

  FASE 1 - CALIBRACION (START, "Preparando", NO exhalar):
      Recolecta lecturas de aire limpio y promedia -> base de calibracion de
      esta sesion (robusto a la deriva del Ro entre arranques).

  FASE 2 - RECOLECCION PARA EL MODELO (MEASURE, "Detectando", 20 s, EXHALAS):
      Recolecta TODAS las lecturas mientras exhalas (no infiere por lectura).

  FINAL (STOP): limpieza + estimacion
      1) Limpieza: descarta las lecturas INICIALES y FINALES (estabilizacion del
         flujo y agotamiento de la exhalacion) -> quita outliers.
      2) Media: promedio del subconjunto central limpio.
      3) Estimacion: una sola inferencia sobre esa media -> niveles de glucosa.

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

# Guard de humedad: si esta en True, descarta lecturas con humedad/temp altas.
# Por ahora DESACTIVADO -> se dan valores aunque la humedad este alta.
FILTRAR_HUMEDAD = False
HUM_MAX = 85.0   # %
TEMP_MAX = 40.0  # °C

# Limpieza: fraccion de lecturas a descartar de CADA extremo (inicio y fin).
FRAC_RECORTE = 0.20   # 20% al inicio + 20% al final
MIN_RECORTE = 1       # al menos 1 de cada lado si hay suficientes

# --- Estado de la sesion ---
_fase = "idle"          # idle | calibrando | midiendo
_base_buf = []          # FASE 1: lecturas de aire limpio (calibracion)
_medir_buf = []         # FASE 2: lecturas durante la exhalacion (modelo)
_medias_sesion = None    # base de calibracion calculada


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
        _fase = "calibrando"
        _base_buf = []
        _medir_buf = []
        _medias_sesion = None
        print("[sesion] START - FASE 1 calibracion (NO exhalar)")
    elif cmd == "MEASURE" and _fase == "calibrando":
        _calcular_base()
        _fase = "midiendo"
        print("[sesion] MEASURE - FASE 2 recoleccion (exhala ahora)")
    elif cmd == "STOP" and _fase != "idle":
        _finalizar()
        _fase = "idle"


def _calcular_base() -> None:
    """FASE 1: promedio del aire limpio -> base de calibracion de la sesion."""
    global _medias_sesion
    if not _base_buf:
        _medias_sesion = None
        print("[base] sin lecturas de calibracion")
        return
    k = len(_base_buf)
    _medias_sesion = {
        "CO": sum(b[0] for b in _base_buf) / k,
        "Alcohol": sum(b[1] for b in _base_buf) / k,
        "Acetone": sum(b[2] for b in _base_buf) / k,
    }
    print(f"[base] calibracion lista ({k} lecturas): {_medias_sesion}")


def _limpiar(buf: list) -> list:
    """Limpieza: descarta las lecturas iniciales y finales (outliers)."""
    n = len(buf)
    r = max(MIN_RECORTE, int(n * FRAC_RECORTE))
    if n > 2 * r:
        return buf[r:n - r]
    if n >= 3:
        return buf[1:-1]
    return buf


def _finalizar() -> None:
    """Limpieza + media + UNA estimacion sobre los datos limpios."""
    if len(_medir_buf) < 2 or _medias_sesion is None:
        print("[FINAL] muestras insuficientes")
        _publicar({"valida": False, "motivo": "insuficiente"})
        return

    limpio = _limpiar(_medir_buf)
    k = len(limpio)
    co_m = sum(b[0] for b in limpio) / k
    alc_m = sum(b[1] for b in limpio) / k
    ace_m = sum(b[2] for b in limpio) / k

    # Una sola estimacion sobre la media limpia.
    cal = calibrar(co_m, alc_m, ace_m, medias=_medias_sesion)
    muestra = pd.DataFrame([cal])[FEATURES]
    muestra_scaled = pd.DataFrame(scaler.transform(muestra), columns=FEATURES)
    clase = int(clf.predict(muestra_scaled)[0])
    proba = clf.predict_proba(muestra_scaled)[0]
    bgl = float(reg.predict(muestra_scaled)[0])

    print("=" * 50)
    print(f"[FINAL] recolectadas={len(_medir_buf)}  limpias(centro)={k}")
    print(f"  media  CO={co_m:.2f}  Alc={alc_m:.2f}  Ace={ace_m:.2f}")
    print(f"  Clasificacion : {'DM — Diabetico' if clase == 1 else 'HI — Sano'}")
    print(f"  P(DM)         : {proba[1]:.3f}")
    print(f"  BGL estimado  : {bgl:.1f} mg/dL  (media de {k} lecturas limpias)")
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
        "limpias": k,
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

        # GUARD de humedad (DESACTIVADO por ahora). Si se reactiva, descarta las
        # lecturas saturadas de vapor para que no entren al promedio.
        if FILTRAR_HUMEDAD and (hum > HUM_MAX or temp > TEMP_MAX):
            print(f"  ⚠ saturado (hum {hum}% / temp {temp}°C) - descartada")
            _publicar({"valida": False, "motivo": "humedad_alta",
                       "hum": hum, "temp": temp, "fase": _fase})
            return json.dumps({"saturado": True})

        # Compensacion de humedad/temperatura.
        co_c, alcohol_c, acetone_c = compensar(
            co_raw, alcohol_raw, acetone_raw, temp=temp, hum=hum)

        if _fase == "calibrando":
            _base_buf.append((co_c, alcohol_c, acetone_c))
            print(f"[calibracion] n={len(_base_buf)}")
            _publicar({"valida": False, "motivo": "preparando", "n": len(_base_buf)})
            return json.dumps({"preparando": True, "n": len(_base_buf)})

        # FASE 2 (midiendo): solo recolecta para el modelo (no infiere por lectura).
        _medir_buf.append((co_c, alcohol_c, acetone_c))
        print(f"[recoleccion] n={len(_medir_buf)}  CO={co_c:.2f} Alc={alcohol_c:.2f} "
              f"Ace={acetone_c:.2f} hum={hum}%")
        _publicar({"valida": False, "motivo": "midiendo",
                   "n": len(_medir_buf), "hum": hum})
        return json.dumps({"midiendo": True, "n": len(_medir_buf)})

    except Exception as e:
        print(f"[error] {e}")
        return json.dumps({"error": str(e)})


Bridge.provide("inferir", inferir)
App.run()
