#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecure.h>
#include <SPI.h>
#include <SD.h>
#include <time.h>

// WIFI
const char* ssid = "Airtel_56";
const char* password = "Raviuma5658";

// SERVER
String serverName = "https://mahajansensor6.onrender.com/api/data";
String apiKey = "12b5112c62284ea0b3da0039f298ec7a85ac9a1791044052b6df970640afb1c5";

// SD
#define SD_CS D8
#define FILE_APPEND  (sdfat::O_READ | sdfat::O_WRITE | sdfat::O_CREAT | sdfat::O_APPEND)
WiFiClientSecure client;

// -------- GLOBAL ID --------
unsigned long recordID = 1;

// -------- TIME FUNCTION --------
String getTimeStamp() {
  time_t now = time(nullptr);
  struct tm* t = localtime(&now);

  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", t);

  return String(buf);
}

// -------- SD CHECK --------
bool isSDConnected() {
  if (!SD.begin(SD_CS)) return false;

  File f = SD.open("/data.csv", FILE_APPEND);
  if (!f) return false;

  f.close();
  return true;
}

// -------- CREATE HEADER --------
void ensureCSVHeader() {
  if (!SD.exists("/data.csv")) {
    File file = SD.open("/data.csv", FILE_WRITE);
    if (file) {
      file.println("id,sensor1,sensor2,sensor3,time");
      file.close();
      Serial.println("✔ CSV Header Created");
    }
  }
}

// -------- GET LAST ID --------
void loadLastID() {
  File file = SD.open("/data.csv", FILE_READ);
  if (!file) return;

  String lastLine = "";

  while (file.available()) {
    lastLine = file.readStringUntil('\n');
  }

  file.close();

  if (lastLine.length() > 10) {
    int commaIndex = lastLine.indexOf(',');
    if (commaIndex > 0) {
      recordID = lastLine.substring(0, commaIndex).toInt() + 1;
    }
  }

  Serial.print("Starting ID: ");
  Serial.println(recordID);
}

// -------- SEND --------
void sendData(unsigned long id, float s1, float s2, float s3, String timeStamp) {

  if (WiFi.status() != WL_CONNECTED) return;

  client.setInsecure();
  HTTPClient http;

  String url = serverName +
               "?key=" + apiKey +
               "&id=" + String(id) +
               "&s1=" + String(s1) +
               "&s2=" + String(s2) +
               "&s3=" + String(s3) +
               "&time=" + timeStamp;

  Serial.println("Sending: " + url);

  http.begin(client, url);
  int code = http.GET();

  Serial.print("HTTP Code: ");
  Serial.println(code);

  if (code > 0) {
    Serial.println(http.getString());
  }

  http.end();
}

// -------- SD WRITE --------
void writeSD(unsigned long id, float s1, float s2, float s3, String timeStamp) {

  File file = SD.open("/data.csv", FILE_APPEND);

  if (file) {
    file.print(id);
    file.print(",");
    file.print(s1);
    file.print(",");
    file.print(s2);
    file.print(",");
    file.print(s3);
    file.print(",");
    file.println(timeStamp);

    file.close();

    Serial.println("✔ Saved to SD (CSV)");
  }
}

// -------- SETUP --------
void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  configTime(19800, 0, "pool.ntp.org");

  Serial.print("Syncing time");
  time_t now = time(nullptr);

  while (now < 100000) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }

  Serial.println("\nTime Synced!");
  Serial.println("WiFi Connected");

  if (SD.begin(SD_CS)) {
    ensureCSVHeader();
    loadLastID();
    Serial.println("✅ SD Ready");
  } else {
    Serial.println("❌ SD Failed");
  }
}

// -------- LOOP --------
void loop() {

  if (!isSDConnected()) {
    Serial.println("❌ No SD → Stop");
    delay(5000);
    return;
  }

  float s1 = random(200, 300);
  float s2 = random(500, 700);
  float s3 = random(400, 600);

  String timeStamp = getTimeStamp();

  // SAVE FIRST
  writeSD(recordID, s1, s2, s3, timeStamp);

  // SEND TO SERVER
  sendData(recordID, s1, s2, s3, timeStamp);

  recordID++;  // ✅ increment ID

  delay(5000);
}
