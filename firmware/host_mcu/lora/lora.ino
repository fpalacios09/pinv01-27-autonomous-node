/*
  Autor: MSc. Ing. Fabian Palacios Pereira
*/

//---------------------------------------------------------------------------------------

#include "config.h"

const int analogPin = A2;
const int led = D5;
const int rele4 = D3;   // camara
const int rele3 = D2;	  // power modulo lora
const int rele2 = D6;   // raspberry
const int rele1 = D4;   // jetson
const int trig = D10; // forzar recepcion de json boton de force lora read en la pcb

const float R1 = 29910.0;
const float R2 = 7500.0;



//---------------------------------------------------------------------------------------

unsigned long previousMillis = 0;  // debe ser unsigned long
const unsigned long interval = 5UL * 60UL * 1000UL;  // 10 o 15 minutos en milisegundos

// Supervisión del Notecard
const byte NOTECARD_MAX_INTENTOS = 3;
const unsigned long NOTECARD_ESPERA_REINTENTO_MS = 5000UL;
const unsigned long NOTECARD_APAGADO_MS = 10000UL;
const unsigned long NOTECARD_ARRANQUE_MS = 15000UL;

String objeto = "";
int valor = 0;

//---------------------------------------------------------------------------------------

#include <Notecard.h>

const byte RXD2 = 11; //
const byte TXD2 = 12; //

HardwareSerial usbSerial(1); // Use UART channel 1

#define myProductID PRODUCT_UID   //nombre del proyecto en notehub definido en config.h

Notecard notecard;

String string_entrada= "";  
bool fin_string= false;
int value = 0;
unsigned long rstlora = 0;

//----------------------------------------------------------------------------------------

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


void setup() {

  pinMode(rele1, OUTPUT);
  pinMode(rele2, OUTPUT);
  pinMode(rele3, OUTPUT);
  pinMode(rele4, OUTPUT);
  digitalWrite(rele1 , HIGH);
  digitalWrite(rele2 , HIGH);
  digitalWrite(rele3, HIGH);
  digitalWrite(rele4 , LOW);

  delay(10000);

  string_entrada.reserve(64);               //Reserva un espacio de hasta 64bytes
  
  usbSerial.begin(115200, SERIAL_8N1, RXD2, TXD2);
  Serial.begin(115200);

  pinMode(led, OUTPUT);
  digitalWrite(led, LOW);

  indicator();

  pinMode(trig, INPUT_PULLUP);

  indicator();
  points();

  notecard.setDebugOutputStream(usbSerial);

  // Configuración inicial completa. card.restore se ejecuta solamente aquí.
  inicializarNotecard(true);

  usbSerial.println("Ready");
}

void loop() {
  unsigned long currentMillis = millis();

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

    // Formato nuevo esperado desde Python:
    // {"stream_key":"carsbikebustruck","car_to_sl":1,"bike_to_sl":0,"heavy_to_sl":0,"total_to_sl":1,"car_from_sl":0,"bike_from_sl":0,"heavy_from_sl":0,"total_from_sl":0}
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
      // Compatibilidad con el formato anterior:
      // cars:1,trucks:0,buses:0,motorcycles:2
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
        JAddNumberToObject(body2, "rstlora", rstlora);
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

  // requestAndResponse utiliza el timeout de transacción de la librería Notecard.
  // Si no recibe una respuesta, retorna NULL y este intento se considera fallido.
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
      delay(NOTECARD_ESPERA_REINTENTO_MS);
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

  // card.restore solamente se ejecuta durante el arranque normal del Arduino.
  if (restaurar) {
    J *req = notecard.newRequest("card.restore");
    if (req != NULL) {
      JAddBoolToObject(req, "delete", true);
      notecard.sendRequest(req);
    }

    indicator();
    points();
  }

  // Verificar que el Notecard está accesible antes de configurarlo.
  if (!verificarNotecardConReintentos()) {
    usbSerial.println("No se pudo iniciar la configuracion del Notecard.");
    return false;
  }

  indicator();
  points();

  // Conectar con el proyecto de Notehub.
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

  // Sincronizar con el proyecto de Notehub.
  J *req2 = notecard.newRequest("hub.sync");
  if (req2 != NULL) {
    notecard.sendRequest(req2);
  }

  indicator();
  points();
  points();

  // Template inbound.
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

  // Template outbound. Se conserva exactamente la estructura existente.
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

  // Confirmación final: la inicialización solo se considera exitosa si responde.
  return notecardResponde();
}

bool recuperarNotecard() {
  // Contabilizar cada accionamiento del rele de recuperacion del Notecard.
  rstlora++;

  // LOW corta VMAIN y HIGH vuelve a alimentar el Notecard.
  digitalWrite(rele3, LOW);
  delay(NOTECARD_APAGADO_MS);

  digitalWrite(rele3, HIGH);
  delay(NOTECARD_ARRANQUE_MS);

  // Se repite toda la configuración, excepto card.restore.
  return inicializarNotecard(false);
}

void consultarInbound() {
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

  // Solicitar cambios en el archivo y verificar solo si hay cambios.
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
                      delay(1000);
                      digitalWrite(rele1, HIGH);
                    }
                    if (strcmp(command, "resetjet") == 0) {
                      digitalWrite(rele2, LOW);
                      delay(1000);
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

  // Verifica de nuevo si hay algo en cola.
  J *req3 = notecard.newRequest("file.changes");
  if (req3 != NULL) {
    J *files3 = JCreateArray();
    if (files3 != NULL) {
      JAddItemToArray(files3, JCreateString("datain.qi"));
      JAddItemToObject(req3, "files", files3);
      notecard.sendRequest(req3);
    }
  }
}


void points(){
  usbSerial.println(".");
  delay(1000);
  usbSerial.println(".");
  delay(1000);
  usbSerial.println(".");
  delay(1000);
  usbSerial.println(".");
  delay(1000);
}

void points60(){
  for(int i=0; i<60; i++){
    usbSerial.println(".");
    delay(1000);
  }
}

void indicator(){
  digitalWrite(led, LOW);
  delay(300);
  digitalWrite(led, HIGH);
  delay(300);
  digitalWrite(led, LOW);
  delay(300);
  digitalWrite(led, HIGH);
  delay(300);
  digitalWrite(led, LOW);
  delay(300);
  digitalWrite(led, HIGH);
  delay(300);
  digitalWrite(led, LOW);
  delay(300);
  digitalWrite(led, HIGH);
  delay(300);
  digitalWrite(led, LOW);
  delay(300);
  digitalWrite(led, HIGH);
  delay(300);
  digitalWrite(led, LOW);
}

void indicator_read(){
  digitalWrite(led, LOW);
  delay(80);
  digitalWrite(led, HIGH);
  delay(80);
  digitalWrite(led, LOW);
  delay(80);
  digitalWrite(led, HIGH);
  delay(80);
  digitalWrite(led, LOW);
  delay(80);
  digitalWrite(led, HIGH);
  delay(80);
  digitalWrite(led, LOW);
  delay(300);
  digitalWrite(led, HIGH);
  delay(300);
  digitalWrite(led, LOW);
  delay(300);
  digitalWrite(led, HIGH);
}

void indicator_final(){
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
  digitalWrite(led, LOW);
  delay(100);
  digitalWrite(led, HIGH);
  delay(100);
}

void serialEvent(){
  while(Serial.available()){
    char char_entrada=(char)Serial.read();   //Lee lo que se introduce y lo convierte a char
    string_entrada+=char_entrada;            //Agrega el char que se leyo al string
    
    if(char_entrada=='\n'){                  //Si se aprieta enter lo toma como un salto de linea y determina que se completo el string 
      fin_string=true;    
    } 
  }
}