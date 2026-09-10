/*
  Autor: MSc. Ing. Fabian Palacios Pereira
*/

//---------------------------------------------------------------------------------------

#include "config.h"

// Debug interno de la librería Notecard.
// 0 = desactivado para operación normal; 1 = activado para diagnóstico.
#define NOTECARD_DEBUG 0

const int analogPin = A2;
const int led = D5;
const int rele4 = D3;   // camara
const int rele3 = D2;   // power modulo lora
const int rele2 = D6;   // raspberry
const int rele1 = D4;   // jetson
const int trig = D10;   // forzar recepcion de json boton de force lora read en la pcb

const float R1 = 29910.0;
const float R2 = 7500.0;

//---------------------------------------------------------------------------------------

unsigned long previousMillis = 0;  // debe ser unsigned long
const unsigned long interval = 5UL * 60UL * 1000UL;  // 10 o 15 minutos en milisegundos

// Heartbeat UART hacia node.py. Se mantiene activo también durante setup()
// y durante esperas largas para detectar/reparar pérdidas del enlace serial.
unsigned long previousHeartbeatMillis = 0;
const unsigned long HEARTBEAT_INTERVAL_MS = 5000UL;
bool heartbeatEnabled = false;

// Supervisión del Notecard
const byte NOTECARD_MAX_INTENTOS = 3;
const unsigned long NOTECARD_ESPERA_REINTENTO_MS = 5000UL;
const unsigned long NOTECARD_APAGADO_MS = 10000UL;
const unsigned long NOTECARD_ARRANQUE_MS = 15000UL;

String objeto = "";
int valor = 0;

//---------------------------------------------------------------------------------------

#include <Notecard.h>

const byte RXD2 = D11; // Agregamos la "D" para evitar confusiones de mapeo
const byte TXD2 = D12; // Agregamos la "D"

HardwareSerial usbSerial(1); // Usar canal UART 1 por hardware

#define myProductID PRODUCT_UID   //nombre del proyecto en notehub definido en config.h

Notecard notecard;

String string_entrada= "";  
bool fin_string= false;
int value = 0;
unsigned long rstlora = 0;

//----------------------------------------------------------------------------------------
// FUNCIONES AUXILIARES PARA LEER JSON SIMPLE DESDE LA JETSON
//----------------------------------------------------------------------------------------

String getJsonStringValue(const String &json, const String &key) {
  String pattern = "\"" + key + "\"";
  int keyIndex = json.indexOf(pattern);
  if (keyIndex == -1) return "";

  int colonIndex = json.indexOf(':', keyIndex + pattern.length());
  if (colonIndex == -1) return "";

  int firstQuote = json.indexOf('"', colonIndex + 1);
  if (firstQuote == -1) return "";

  int secondQuote = json.indexOf('"', firstQuote + 1);
  if (secondQuote == -1) return "";

  return json.substring(firstQuote + 1, secondQuote);
}

int getJsonIntValue(const String &json, const String &key, int defaultValue) {
  String pattern = "\"" + key + "\"";
  int keyIndex = json.indexOf(pattern);
  if (keyIndex == -1) return defaultValue;

  int colonIndex = json.indexOf(':', keyIndex + pattern.length());
  if (colonIndex == -1) return defaultValue;

  int startIndex = colonIndex + 1;
  while (
    startIndex < json.length() &&
    (json[startIndex] == ' ' || json[startIndex] == '\t' || json[startIndex] == '\r')
  ) {
    startIndex++;
  }

  int endIndex = startIndex;
  while (
    endIndex < json.length() &&
    (isDigit(json[endIndex]) || json[endIndex] == '-')
  ) {
    endIndex++;
  }

  if (endIndex == startIndex) return defaultValue;

  return json.substring(startIndex, endIndex).toInt();
}

//----------------------------------------------------------------------------------------
// HEARTBEAT DEL ENLACE ARDUINO -> JETSON
//----------------------------------------------------------------------------------------

void serviceHeartbeat() {
  if (!heartbeatEnabled) {
    return;
  }

  unsigned long now = millis();

  if (now - previousHeartbeatMillis >= HEARTBEAT_INTERVAL_MS) {
    previousHeartbeatMillis = now;
    usbSerial.println("heartbeat");
  }
}

void delayWithHeartbeat(unsigned long durationMs) {
  unsigned long start = millis();

  while (millis() - start < durationMs) {
    serviceHeartbeat();
    delay(25);
  }

  serviceHeartbeat();
}


void setup() {

  pinMode(rele1, OUTPUT);
  pinMode(rele2, OUTPUT);
  pinMode(rele3, OUTPUT);
  pinMode(rele4, OUTPUT);
  digitalWrite(rele1 , HIGH);
  digitalWrite(rele2 , HIGH);
  digitalWrite(rele3, HIGH);
  digitalWrite(rele4 , LOW);

  string_entrada.reserve(256);               // Reserva un espacio seguro de 256 bytes para el JSON largo
  
  usbSerial.begin(19200, SERIAL_8N1, RXD2, TXD2); // puerto del adaptador UART-USB
  Serial.begin(19200);

  heartbeatEnabled = true;
  previousHeartbeatMillis = millis();
  usbSerial.println("setup:start");

  // Espera inicial, manteniendo vivo el heartbeat
  delayWithHeartbeat(10000);

  // Asegurar resolución de 12 bits para lecturas de voltaje (0-4095)
  analogReadResolution(12);

  pinMode(led, OUTPUT);
  digitalWrite(led, LOW);

  indicator();
  pinMode(trig, INPUT_PULLUP);
  indicator();
  points();

  #if NOTECARD_DEBUG
    notecard.setDebugOutputStream(usbSerial);
  #endif

  // Configuración inicial completa. card.restore se ejecuta solamente aquí.
  inicializarNotecard(true);

  usbSerial.println("Ready");
  previousHeartbeatMillis = millis();
}

void loop() {
  // En ESP32, es obligatorio llamar a serialEvent explicitamente
  serialEvent();

  unsigned long currentMillis = millis();

  // Mantener vivo el enlace serial durante la operación normal
  serviceHeartbeat();

  if ( (currentMillis - previousMillis >= interval) || (digitalRead(trig) == LOW ) ) {
    previousMillis = currentMillis;

    // Antes de consultar inbound, comprobar que el Notecard responde.
    if (verificarNotecardConReintentos()) {
      consultarInbound();
    } else {
      usbSerial.println("Notecard sin respuesta. Iniciando power cycle por rele VMAIN...");

      if (recuperarNotecard()) {
        usbSerial.println("Notecard recuperado. Se realiza la consulta inbound pendiente.");
        consultarInbound();
      } else {
        usbSerial.println("No fue posible recuperar el Notecard. Se reintentara en el proximo ciclo.");
      }
    }
  }

  if (fin_string) {
    string_entrada.trim();
    fin_string = false;

    String stream_key = "";
    int car_to_sl = 0;
    int bike_to_sl = 0;
    int heavy_to_sl = 0;
    int total_to_sl = 0;
    int car_from_sl = 0;
    int bike_from_sl = 0;
    int heavy_from_sl = 0;
    int total_from_sl = 0;

    // Formato nuevo esperado desde Python
    if (string_entrada.startsWith("{")) {
      stream_key = getJsonStringValue(string_entrada, "stream_key");
      car_to_sl = getJsonIntValue(string_entrada, "car_to_sl", 0);
      bike_to_sl = getJsonIntValue(string_entrada, "bike_to_sl", 0);
      heavy_to_sl = getJsonIntValue(string_entrada, "heavy_to_sl", 0);
      total_to_sl = getJsonIntValue(string_entrada, "total_to_sl", 0);
      car_from_sl = getJsonIntValue(string_entrada, "car_from_sl", 0);
      bike_from_sl = getJsonIntValue(string_entrada, "bike_from_sl", 0);
      heavy_from_sl = getJsonIntValue(string_entrada, "heavy_from_sl", 0);
      total_from_sl = getJsonIntValue(string_entrada, "total_from_sl", 0);
    } else {
      // Compatibilidad con el formato anterior
      stream_key = "legacy";
      int cars = 0;
      int trucks = 0;
      int buses = 0;
      int motorcycles = 0;
      int start = 0;

      while (start < string_entrada.length()) {
        int commaIndex = string_entrada.indexOf(',', start);
        String token;

        if (commaIndex == -1) {
          token = string_entrada.substring(start);
          start = string_entrada.length();
        } else {
          token = string_entrada.substring(start, commaIndex);
          start = commaIndex + 1;
        }

        token.trim();

        int colonIndex = token.indexOf(':');
        if (colonIndex != -1) {
          String key = token.substring(0, colonIndex);
          String valueStr = token.substring(colonIndex + 1);
          valueStr.trim();
          int value = valueStr.toInt();

          if (key == "cars") {
            cars = value;
          } else if (key == "trucks") {
            trucks = value;
          } else if (key == "buses") {
            buses = value;
          } else if (key == "motorcycles") {
            motorcycles = value;
          }
        }
      }

      car_to_sl = cars;
      bike_to_sl = motorcycles;
      heavy_to_sl = trucks + buses;
      total_to_sl = car_to_sl + bike_to_sl + heavy_to_sl;
    }

    if (stream_key.length() == 0) {
      stream_key = "unknown";
    }

    indicator();

    int car_to_sl_tx = (car_to_sl == 0) ? -1 : car_to_sl;
    int bike_to_sl_tx = (bike_to_sl == 0) ? -1 : bike_to_sl;
    int heavy_to_sl_tx = (heavy_to_sl == 0) ? -1 : heavy_to_sl;
    int total_to_sl_tx = (total_to_sl == 0) ? -1 : total_to_sl;
    int car_from_sl_tx = (car_from_sl == 0) ? -1 : car_from_sl;
    int bike_from_sl_tx = (bike_from_sl == 0) ? -1 : bike_from_sl;
    int heavy_from_sl_tx = (heavy_from_sl == 0) ? -1 : heavy_from_sl;
    int total_from_sl_tx = (total_from_sl == 0) ? -1 : total_from_sl;
    long rstlora_tx = (rstlora == 0) ? -1 : rstlora;

    usbSerial.print("stream_key: ");
    usbSerial.print(stream_key);
    usbSerial.print(" | car_to_sl: ");
    usbSerial.print(car_to_sl_tx);
    usbSerial.print(" | bike_to_sl: ");
    usbSerial.print(bike_to_sl_tx);
    usbSerial.print(" | heavy_to_sl: ");
    usbSerial.print(heavy_to_sl_tx);
    usbSerial.print(" | total_to_sl: ");
    usbSerial.print(total_to_sl_tx);
    usbSerial.print(" | car_from_sl: ");
    usbSerial.print(car_from_sl_tx);
    usbSerial.print(" | bike_from_sl: ");
    usbSerial.print(bike_from_sl_tx);
    usbSerial.print(" | heavy_from_sl: ");
    usbSerial.print(heavy_from_sl_tx);
    usbSerial.print(" | total_from_sl: ");
    usbSerial.println(total_from_sl_tx);

    float adc = analogRead(analogPin);
    float vPin = (adc / 4095.0) * 3.3;
    float voltage  = vPin * (R1 + R2) / R2;

    J *req4 = notecard.newRequest("note.add");
    if (req4 != NULL) {
      JAddStringToObject(req4, "file", "count.qo");
      JAddBoolToObject(req4, "sync", true);

      J *body2 = JAddObjectToObject(req4, "body");
      if (body2) {
        JAddStringToObject(body2, "stream_key", stream_key.c_str());
        JAddNumberToObject(body2, "car_to_sl", car_to_sl_tx);
        JAddNumberToObject(body2, "bike_to_sl", bike_to_sl_tx);
        JAddNumberToObject(body2, "heavy_to_sl", heavy_to_sl_tx);
        JAddNumberToObject(body2, "total_to_sl", total_to_sl_tx);
        JAddNumberToObject(body2, "car_from_sl", car_from_sl_tx);
        JAddNumberToObject(body2, "bike_from_sl", bike_from_sl_tx);
        JAddNumberToObject(body2, "heavy_from_sl", heavy_from_sl_tx);
        JAddNumberToObject(body2, "total_from_sl", total_from_sl_tx);
        JAddNumberToObject(body2, "voltage", voltage);
        JAddNumberToObject(body2, "rstlora", rstlora_tx);
      }
      notecard.sendRequest(req4);
    }
    
    points();
    points();
    indicator();
    
    string_entrada = "";
  }
}

//----------------------------------------------------------------------------------------
// SUPERVISIÓN, INICIALIZACIÓN Y RECUPERACIÓN DEL NOTECARD
//----------------------------------------------------------------------------------------

bool respuestaNotecardValida(J *rsp) {
  if (rsp == NULL) {
    return false;
  }

  const char *error = JGetString(rsp, "err");
  return (error == NULL || error[0] == '\0');
}

bool notecardResponde() {
  J *req = notecard.newRequest("card.version");
  if (req == NULL) {
    return false;
  }

  J *rsp = notecard.requestAndResponse(req);
  bool correcto = respuestaNotecardValida(rsp);

  if (rsp != NULL) {
    JDelete(rsp);
  }

  return correcto;
}

bool verificarNotecardConReintentos() {
  for (byte intento = 1; intento <= NOTECARD_MAX_INTENTOS; intento++) {
    usbSerial.print("Verificacion Notecard, intento ");
    usbSerial.print(intento);
    usbSerial.print(" de ");
    usbSerial.println(NOTECARD_MAX_INTENTOS);

    if (notecardResponde()) {
      usbSerial.println("Notecard responde correctamente.");
      return true;
    }

    usbSerial.println("Notecard no respondio.");

    if (intento < NOTECARD_MAX_INTENTOS) {
      delayWithHeartbeat(NOTECARD_ESPERA_REINTENTO_MS);
    }
  }

  return false;
}

bool inicializarNotecard(bool restaurar) {
  #ifdef txRxPinsSerial
    notecard.begin(txRxPinsSerial, 9600);
  #else
    notecard.begin();
  #endif

  if (restaurar) {
    J *req = notecard.newRequest("card.restore");
    if (req != NULL) {
      JAddBoolToObject(req, "delete", true);
      notecard.sendRequest(req);
    }

    indicator();
    points();
  }

  if (!verificarNotecardConReintentos()) {
    usbSerial.println("No se pudo iniciar la configuracion del Notecard.");
    return false;
  }

  indicator();
  points();

  J *req1 = notecard.newRequest("hub.set");
  if (req1 == NULL) {
    return false;
  }
  if (myProductID[0]) {
    JAddStringToObject(req1, "product", myProductID);
  }
  if (!notecard.sendRequestWithRetry(req1, 5)) {
    usbSerial.println("Fallo hub.set durante la configuracion del Notecard.");
    return false;
  }

  indicator();
  points();
  points();
  points();

  J *req2 = notecard.newRequest("hub.sync");
  if (req2 != NULL) {
    notecard.sendRequest(req2);
  }

  indicator();
  points();
  points();

  J *req3 = notecard.newRequest("note.template");
  if (req3 != NULL) {
    JAddStringToObject(req3, "file", "datain.qi");
    JAddStringToObject(req3, "format", "compact");
    JAddNumberToObject(req3, "port", 1);
    J *body1 = JAddObjectToObject(req3, "body");
    if (body1) {
      JAddStringToObject(body1, "command", "example");
      JAddStringToObject(body1, "hash", "example");
    }
    notecard.sendRequest(req3);
  }

  indicator();
  points();
  points();

  J *req4 = notecard.newRequest("note.template");
  if (req4 != NULL) {
    JAddStringToObject(req4, "file", "count.qo");
    JAddStringToObject(req4, "format", "compact");
    JAddNumberToObject(req4, "port", 2);
    J *body2 = JAddObjectToObject(req4, "body");

    if (body2) {
      JAddStringToObject(body2, "stream_key", "carsbikebustruck");
      JAddNumberToObject(body2, "car_to_sl", 12);
      JAddNumberToObject(body2, "bike_to_sl", 12);
      JAddNumberToObject(body2, "heavy_to_sl", 12);
      JAddNumberToObject(body2, "total_to_sl", 12);
      JAddNumberToObject(body2, "car_from_sl", 12);
      JAddNumberToObject(body2, "bike_from_sl", 12);
      JAddNumberToObject(body2, "heavy_from_sl", 12);
      JAddNumberToObject(body2, "total_from_sl", 12);
      JAddNumberToObject(body2, "voltage", 14.1);
      JAddNumberToObject(body2, "rstlora", 12);
    }
    notecard.sendRequest(req4);
  }

  indicator();
  points();
  points();

  J *req5 = notecard.newRequest("hub.sync");
  if (req5 != NULL) {
    notecard.sendRequest(req5);
  }

  points();
  points();
  indicator_final();

  return notecardResponde();
}

bool recuperarNotecard() {
  rstlora++;

  digitalWrite(rele3, LOW);
  delayWithHeartbeat(NOTECARD_APAGADO_MS);

  digitalWrite(rele3, HIGH);
  delayWithHeartbeat(NOTECARD_ARRANQUE_MS);

  return inicializarNotecard(false);
}

void consultarInbound() {
  // === CHECKPOINT: INICIO ===
  usbSerial.println("Iniciando ciclo Inbound...");

  J *req0 = notecard.newRequest("hub.sync");
  if (req0 != NULL) {
    notecard.sendRequest(req0);
  }

  indicator_read();
  points();
  points();
  points();
  points();
  indicator_read();

  J *req1 = notecard.newRequest("file.changes");
  if (req1 != NULL) {
    J *files = JCreateArray();
    if (files != NULL) {
      JAddItemToArray(files, JCreateString("datain.qi"));
      JAddItemToObject(req1, "files", files);
      J *rsp = notecard.requestAndResponse(req1);

      if (rsp != NULL) {
        J *info = JGetObject(rsp, "info");
        if (info != NULL) {
          J *datain = JGetObject(info, "datain.qi");
          if (datain != NULL) {
            J *req2 = notecard.newRequest("note.get");
            if (req2 != NULL) {
              JAddStringToObject(req2, "file", "datain.qi");
              JAddBoolToObject(req2, "delete", true);
              J *rsp2 = notecard.requestAndResponse(req2);

              if (rsp2 != NULL) {
                J *body1 = JGetObject(rsp2, "body");
                if (body1 != NULL) {
                  const char* command = JGetString(body1, "command");
                  if (command != NULL) {
                    usbSerial.print("Comando recibido: ");
                    usbSerial.println(command);

                    if (strcmp(command, "oncam") == 0) {
                      digitalWrite(rele4, LOW);
                    }
                    if (strcmp(command, "offcam") == 0) {
                      digitalWrite(rele4, HIGH);
                    }
                    if (strcmp(command, "resetpi") == 0) {
                      digitalWrite(rele1, LOW);
                      delayWithHeartbeat(1000);
                      digitalWrite(rele1, HIGH);
                    }
                    if (strcmp(command, "resetjet") == 0) {
                      digitalWrite(rele2, LOW);
                      delayWithHeartbeat(1000);
                      digitalWrite(rele2, HIGH);
                    }

                    const char* hash = JGetString(body1, "hash");
                    if (hash != NULL && strcmp(hash, "-") != 0) {
                      usbSerial.print("hash ");
                      usbSerial.println(hash);
                    } else {
                      usbSerial.println("Sin hash");
                    }
                  }
                }
                JDelete(rsp2);
              }
            }
          }
        }
        JDelete(rsp);
      }
    }
  }

  J *req3 = notecard.newRequest("file.changes");
  if (req3 != NULL) {
    J *files3 = JCreateArray();
    if (files3 != NULL) {
      JAddItemToArray(files3, JCreateString("datain.qi"));
      JAddItemToObject(req3, "files", files3);
      notecard.sendRequest(req3);
    }
  }
  
  // === CHECKPOINT: FIN ===
  usbSerial.println("Ciclo Inbound finalizado.");
}

void points(){
  usbSerial.println(".");
  delayWithHeartbeat(1000);
  usbSerial.println(".");
  delayWithHeartbeat(1000);
  usbSerial.println(".");
  delayWithHeartbeat(1000);
  usbSerial.println(".");
  delayWithHeartbeat(1000);
}

void points60(){
  for(int i=0; i<60; i++){
    usbSerial.println(".");
    delayWithHeartbeat(1000);
  }
}

void indicator(){
  digitalWrite(led, LOW);
  delayWithHeartbeat(300);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(300);
  digitalWrite(led, LOW);
  delayWithHeartbeat(300);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(300);
  digitalWrite(led, LOW);
  delayWithHeartbeat(300);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(300);
  digitalWrite(led, LOW);
  delayWithHeartbeat(300);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(300);
  digitalWrite(led, LOW);
  delayWithHeartbeat(300);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(300);
  digitalWrite(led, LOW);
}

void indicator_read(){
  digitalWrite(led, LOW);
  delayWithHeartbeat(80);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(80);
  digitalWrite(led, LOW);
  delayWithHeartbeat(80);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(80);
  digitalWrite(led, LOW);
  delayWithHeartbeat(80);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(80);
  digitalWrite(led, LOW);
  delayWithHeartbeat(300);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(300);
  digitalWrite(led, LOW);
  delayWithHeartbeat(300);
  digitalWrite(led, HIGH);
}

void indicator_final(){
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
  digitalWrite(led, LOW);
  delayWithHeartbeat(100);
  digitalWrite(led, HIGH);
  delayWithHeartbeat(100);
}

void serialEvent(){
  // El ESP32 cuenta con la suficiente memoria para procesar,
  // pero igual evitamos desbordamientos por seguridad
  while(Serial.available() && !fin_string){
    char char_entrada = (char)Serial.read();
    
    if (string_entrada.length() < 250) {
      string_entrada += char_entrada;
    }
    
    if(char_entrada == '\n'){
      fin_string = true;    
    } 
  }
}