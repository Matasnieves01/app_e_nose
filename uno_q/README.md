# E-Nose · Lado UNO Q (lo que necesitas)

Estos son **todos** los archivos que usa el sistema. Nada más.

## Archivos

| Archivo                  | Dónde corre        | Para qué                                              |
|--------------------------|--------------------|------------------------------------------------------|
| `inferir.py` → **`main.py`** | Contenedor (App Lab) | Lee sensores, calibra, infiere, escribe `result.json` y lee `command.txt`. |
| `calibracion.py`         | (lo importa main)  | Mapea tus lecturas al espacio del dataset (auto-base por sesión). |
| `compensacion.py`        | (lo importa main)  | Corrige humedad/temperatura con el DHT22.            |
| `wifi_host.py`           | Host (SSH)         | Servidor WiFi: pasa los resultados al teléfono y recibe START/STOP. |
| `models/class/*.pkl`     | (los carga main)   | Modelo de clasificación HI/DM + su scaler.           |
| `models/regre/*.pkl`     | (los carga main)   | Modelo de regresión de glucosa (BGL).                |

> `inferir.py` es el contenido de tu `main.py`. En el UNO Q el archivo se llama
> `main.py`; en este repo se llama `inferir.py`.

## Cómo correr (2 procesos)

**1. La app (contenedor)** — desde Arduino App Lab, botón Run. Corre `main.py`.

**2. El puente WiFi (host)** — en una terminal SSH, déjalo abierto:
```bash
cd ~/ArduinoApps/prueba/python
python3 wifi_host.py        # debe decir: servidor TCP escuchando en 0.0.0.0:8765
```

**3. En el teléfono** (misma WiFi): IP del UNO Q (`hostname -I` → la 192.168.x.x),
puerto 8765 → Conectar → **Iniciar medición**.
- Durante "Preparando" **no exhales** (captura tu base de aire limpio).
- Exhala en "Detectando" (~9 s).

## Cómo calcula la medida (algoritmo)

1. **START** (Preparando): promedia el aire limpio → base de calibración de la sesión.
2. **MEASURE** (Detectando, ~9 s): recolecta todas las lecturas mientras exhalas
   (no infiere por lectura).
3. **STOP**: **recorta** las primeras y últimas lecturas (outliers de
   estabilización/agotamiento), **promedia** el centro, e **infiere una sola
   vez** sobre esa media → diagnóstico final (el valor más probable).

> **Para que el promedio sea bueno necesitas más muestras en esos 9 s.** Reduce
> el `delay()` del loop en tu `sketch.ino` (p. ej. de 2000 ms a ~400-500 ms) para
> tener ~18-22 lecturas por medición. Con pocas muestras el recorte deja muy poco.
> Ajusta `RECORTE` en `inferir.py` si quieres recortar más/menos.

## Flujo
```
main.py (App Lab) ──result.json──► wifi_host.py (host :8765) ──WiFi──► App
                  ◄──command.txt──                            ◄──START/STOP──
```

## Si quieres afinar (opcional)
- La **media** de calibración es automática por sesión (no hay que tocarla).
- La **sensibilidad** (`std` en `calibracion.py` → `USUARIO`) y los coeficientes
  de **humedad** (`compensacion.py` → `COEF`) están estimados. Si necesitas
  medirlos con datos reales, pídeme los scripts de medición (`log_crudo.py`,
  `estimar_compensacion.py`) y te los devuelvo.
