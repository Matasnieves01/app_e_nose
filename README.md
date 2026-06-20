# E-Nose · App de monitoreo de glucosa

App Flutter para el prototipo de **nariz electronica (E-Nose)** de monitoreo
**no invasivo** de diabetes mediante el analisis de compuestos organicos
volatiles (COV) en el aliento.

La app es un **cliente delgado**: la inferencia corre en el Arduino UNO Q.

1. El **Arduino UNO Q** lee los sensores, ejecuta **los dos modelos de Machine
   Learning** (clasificacion sano/diabetico + regresion de glucosa mg/dL) en su
   lado Linux, y envia por **Bluetooth Low Energy (BLE)** las lecturas junto con
   el resultado.
2. La app se conecta por BLE, recibe ese JSON y **muestra** la estimacion de
   glucosa, la clasificacion, los sensores y la tendencia en tiempo real.

## Arquitectura

```
Arduino UNO Q
 ├─ MCU: lee 3 sensores  ──(Serial)──┐
 └─ Linux (Python):                  ▼
     uno_q/enose_uno_q.py  ── corre los 2 modelos ── notifica por BLE ──> App Flutter
                                                          (FFE0/FFE1)        ├─ BleService (escanea + recibe)
                                                                             └─ UI         (muestra resultados)
```

El codigo del lado UNO Q (modelos + BLE) esta en [`uno_q/`](uno_q/README.md).

| Capa            | Archivo                                  |
|-----------------|------------------------------------------|
| Bluetooth (BLE) | `lib/services/ble_service.dart`          |
| Parseo + estado | `lib/state/app_state.dart`               |
| Modelos (datos) | `lib/models/` (`SensorReading`, `PredictionResult`) |
| UI              | `lib/screens/`, `lib/widgets/`           |
| Lado UNO Q      | `uno_q/` (Python: modelos + BLE)         |

> **BLE, no Bluetooth Classic.** iOS no permite SPP/HC-05; por eso usamos BLE
> (`flutter_blue_plus`), que funciona en iOS y Android. UUID por defecto:
> servicio **FFE0**, caracteristica **FFE1** (configurables en la app).

## Sensores y modelos

Los **dos modelos** (clasificacion HI/DM y regresion BGL, notebooks nb1/nb2)
usan el mismo vector de 4 features `[CO, Alcohol, Acetone, CO_7]`, donde **CO_7
es la misma lectura del MQ-7** (un solo sensor). En hardware son **3 sensores**:

| Sensor   | Feature(s)     | Clave JSON  |
|----------|----------------|-------------|
| MQ-7     | `CO` y `CO_7`  | `co`        |
| MQ-3     | `Alcohol`      | `alcohol`   |
| TGS1820  | `Acetone`      | `acetone`   |

El UNO Q envia por BLE una **linea de texto JSON terminada en `\n`** (BLE
fragmenta los datos; la app reensambla por salto de linea) con los sensores
**y** el resultado de los modelos:

```json
{ "co": 45.0, "alcohol": 280.0, "acetone": 30.0,
  "glucose": 142.0, "diabetes": 1, "prob": 0.78 }
```

| Campo        | Significado                                  | Claves aceptadas                         |
|--------------|----------------------------------------------|------------------------------------------|
| `glucose`    | Glucosa estimada (mg/dL) — regresion         | `glucose`, `glucosa`, `bgl`, `glucemia`  |
| `diabetes`   | Clasificacion: `0`/`1` o `"sano"`/`"diabetico"` | `diabetes`, `class`, `clase`, `diabetic` |
| `prob`       | Probabilidad de diabetes `[0,1]` (opcional)  | `prob`, `probability`, `diabetes_prob`   |

Los campos de resultado son **opcionales**: si solo llegan sensores, la app los
muestra y deja el resultado en "esperando...". El parseo es tolerante a las
distintas claves de la tabla.

## Los modelos (corren en el UNO Q, no en la app)

Los dos modelos `.pkl` (clasificador HI/DM + regresor BGL) y sus scalers ya
estan en `uno_q/models/`. El script `uno_q/enose_uno_q.py` los carga, infiere y
envia el resultado por BLE. La DNN del repo original **no se usa**. Detalles en
[`uno_q/README.md`](uno_q/README.md).

## Como usarlo

1. **Lado UNO Q** (Linux): instala dependencias y corre el puente BLE.
   ```bash
   cd uno_q
   pip3 install -r requirements.txt
   python3 enose_uno_q.py --sim     # simulado; sin --sim usa sensores reales
   ```
   (El MCU lee los sensores con `arduino/enose_uno_q_mcu.ino` y los pasa por
   Serial; implementa `read_sensors()` para leer ese Serial.)
2. **App:** corre en un **dispositivo fisico** (el BLE no funciona en simulador):
   ```bash
   flutter run
   ```
3. Pulsa **Buscar Arduino**, selecciona `E-Nose` y la app empieza a mostrar
   resultados.

> **Importante:** BLE requiere un dispositivo real (no el simulador de iOS) y
> Bluetooth encendido. En Android, la app pedira permisos de Bluetooth.

## Firmware del Arduino

`arduino/enose_uno_q_mcu.ino`: el MCU del UNO Q lee los 3 sensores y los envia
por Serial al lado Linux. Usa la libreria `ArduinoJson`.
