/*
 * E-Nose · Lado microcontrolador del Arduino UNO Q
 * ------------------------------------------------
 * Lee los 3 sensores de la nariz electronica y los envia por SERIE (Serial)
 * como una linea JSON. El lado Linux del UNO Q (uno_q/enose_uno_q.py) lee esa
 * linea, ejecuta los dos modelos (clasificacion + regresion) y notifica el
 * resultado a la app por BLE.
 *
 * Sensores que usan los modelos (ver notebooks nb1/nb2):
 *   MQ-7    -> CO       (Monoxido de carbono)  -> A0   [alimenta CO y CO_7]
 *   MQ-3    -> Alcohol                          -> A1
 *   TGS1820 -> Acetona                          -> A2
 *
 * NOTA: los modelos fueron entrenados con las unidades del dataset
 * (CO ~ 40-50, Alcohol ~ 280-320, Acetone ~ 30). Calibra/escala la lectura
 * cruda del ADC (0-1023) a ese rango antes de enviarla, o hazlo en Python.
 *
 * Librerias: ArduinoJson (Benoit Blanchon).
 */

#include <ArduinoJson.h>

const int PIN_MQ7 = A0;  // CO
const int PIN_MQ3 = A1;  // Alcohol
const int PIN_TGS = A2;  // Acetona (TGS1820)

void setup() {
  Serial.begin(115200);
}

void loop() {
  // Lectura cruda del ADC. Sustituye por tu conversion calibrada a las
  // unidades del dataset si haces la calibracion aqui.
  float co = analogRead(PIN_MQ7);
  float alcohol = analogRead(PIN_MQ3);
  float acetone = analogRead(PIN_TGS);

  StaticJsonDocument<128> doc;
  doc["co"] = co;
  doc["alcohol"] = alcohol;
  doc["acetone"] = acetone;

  serializeJson(doc, Serial);
  Serial.println(); // '\n' delimita cada lectura

  delay(2000); // una lectura cada 2 s
}
