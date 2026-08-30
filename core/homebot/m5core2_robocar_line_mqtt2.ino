// M5Core2 ESP32 Robocar - SATURDAY Full Control + MQTT2 + Autonomous Driving
// Ultrasonic HC-SR04 + 3x Line Detector (TCRT5000) + GoPlus2/Motor Driver
// Works with SATURDAY HomeBotIntegration via MQTT (primary + MQTT2) and Serial COM4
// Autonomous: obstacle avoidance + line follow, controllable via SATURDAY website or voice
#include <M5Core2.h>
#include <WiFi.h>
#include <PubSubClient.h>

// CONFIG - Update these
const char* WIFI_SSID = "CHANGE_ME";
const char* WIFI_PASSWORD = "CHANGE_ME";
const char* MQTT_BROKER = "192.168.0.1";      // Primary
const int   MQTT_PORT = 1883;
const char* MQTT_BROKER2 = "192.168.0.180";   // MQTT2 secondary
const int   MQTT_PORT2 = 1883;

// Pins - M5Core2 Robocar (adjust for your chassis)
#define ULTRASONIC_TRIG 32
#define ULTRASONIC_ECHO 33
#define LINE_L 36  // Left
#define LINE_C 26  // Center
#define LINE_R  35  // Right
// Motors via GoPlus2 I2C or direct - using analogWrite on M5Core2 pins
#define M_FL1 26  // Placeholder - set to your motor driver pins or use M5GoPlus2
#define M_FL2 25
#define M_FR1 33
#define M_FR2 32

WiFiClient wifiClient, wifiClient2;
PubSubClient mqtt(wifiClient);
PubSubClient mqtt2(wifiClient2);
unsigned long lastSensor = 0, lastAutonomous = 0;
bool autonomousMode = false;
int targetX = 0, targetY = 0;

void setup() {
  M5.begin();
  Serial.begin(115200);
  pinMode(ULTRASONIC_TRIG, OUTPUT);
  pinMode(ULTRASONIC_ECHO, INPUT);
  pinMode(LINE_L, INPUT);
  pinMode(LINE_C, INPUT);
  pinMode(LINE_R, INPUT);
  pinMode(M_FL1, OUTPUT); pinMode(M_FL2, OUTPUT);
  pinMode(M_FR1, OUTPUT); pinMode(M_FR2, OUTPUT);
  stopMotors();
  M5.Lcd.setRotation(1);
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setTextColor(WHITE); M5.Lcd.setTextSize(2);
  M5.Lcd.println("SATURDAY M5Core2");
  M5.Lcd.println("Robocar Ready");
  connectWiFi();
  connectMQTT();
  Serial.println("AEGIS_HOMEBOT_READY");
  Serial.println("M5Core2 Robocar: FWD REV LFT RGT RTL RTR STP AUTO LINE");
}

void loop() {
  M5.update();
  handleSerial();
  if (!mqtt.connected() && !mqtt2.connected()) connectMQTT();
  mqtt.loop(); mqtt2.loop();
  // Autonomous every 200ms if enabled
  if (autonomousMode && millis() - lastAutonomous > 200) {
    autonomousStep();
    lastAutonomous = millis();
  }
  // Sensors publish every 1s
  if (millis() - lastSensor > 1000) {
    publishSensors();
    lastSensor = millis();
  }
  // Buttons: A=autonomous toggle, B=stop, C=line calibrate
  if (M5.BtnA.wasPressed()) { autonomousMode = !autonomousMode; M5.Lcd.println(autonomousMode?"AUTO ON":"AUTO OFF"); if(!autonomousMode) stopMotors(); }
  if (M5.BtnB.wasPressed()) { autonomousMode=false; stopMotors(); }
  // Display status
  if (millis() % 1000 < 50) {
    float dist = readUltrasonic();
    int line = readLine();
    M5.Lcd.fillRect(0,120,320,20,BLACK);
    M5.Lcd.setCursor(0,120); M5.Lcd.printf("D:%.0fcm L:%d %s", dist, line, autonomousMode?"AUTO":"");
  }
}

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int tries=0;
  while (WiFi.status()!=WL_CONNECTED && tries<20) { delay(500); tries++; }
  if (WiFi.status()==WL_CONNECTED) {
    Serial.print("WIFI OK "); Serial.println(WiFi.localIP());
    M5.Lcd.setTextColor(GREEN); M5.Lcd.println(WiFi.localIP()); M5.Lcd.setTextColor(WHITE);
  }
}

void connectMQTT() {
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt2.setServer(MQTT_BROKER2, MQTT_PORT2);
  mqtt2.setCallback(mqttCallback);
  String id = "SATURDAY-M5Core2-" + String(random(1000,9999));
  if (mqtt.connect(id.c_str())) {
    mqtt.subscribe("homebot/motors/#"); mqtt.subscribe("homebot/motor/#");
    mqtt.subscribe("homebot/nav/#"); mqtt.subscribe("homebot/sensors/#");
    mqtt.subscribe("homebot/cmd/#"); mqtt.subscribe("homebot/auto/#");
    Serial.println("MQTT1 OK");
  }
  if (mqtt2.connect((id+"2").c_str())) {
    mqtt2.subscribe("homebot/#");
    Serial.println("MQTT2 OK");
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int len) {
  String t=String(topic), m="";
  for(int i=0;i<len;i++) m+=(char)payload[i];
  m.trim(); t.trim();
  Serial.printf("MQTT %s <- %s\n", t.c_str(), m.c_str());
  if (t=="homebot/motors/omni" || t=="homebot/motor/omni") {
    // JSON {"x":0,"y":80,"rotation":0}
    int x=0,y=0,r=0;
    if (m.indexOf("x")!=-1) { x = m.substring(m.indexOf("x")+3, m.indexOf(",", m.indexOf("x"))).toInt(); }
    // Simple parse: expect x,y,rotation
    // Use ArduinoJson if available, else parse manually
    // For now, handle direct commands via other topics
    if (m.indexOf("y")!=-1) {
      // crude
      if (m.indexOf("\"y\": 80")!=-1 || m.indexOf("\"y\":80")!=-1) y=80;
      else if (m.indexOf("\"y\": -80")!=-1) y=-80;
    }
    omni(x,y,r);
  } else if (t=="homebot/motors/stop" || m=="STP") stopMotors();
  else if (m=="FWD") moveForward();
  else if (m=="REV") moveBackward();
  else if (m=="LFT") moveLeft();
  else if (m=="RGT") moveRight();
  else if (m=="RTL") rotateLeft();
  else if (m=="RTR") rotateRight();
  else if (m=="STP") stopMotors();
  else if (m=="AUTO") autonomousMode=true;
  else if (m=="MANUAL") autonomousMode=false;
  else if (t=="homebot/nav/autonomous") { // {"x":10,"y":20}
    autonomousMode=true;
  }
}

void handleSerial() {
  static String cmd="";
  while (Serial.available()) {
    char c=Serial.read();
    if (c=='\n' || c=='\r') { if(cmd.length()>0){ processSerial(cmd); cmd="";}} else cmd+=c;
  }
}
void processSerial(String cmd) {
  cmd.trim(); cmd.toUpperCase();
  if(cmd=="PING") Serial.println("PONG");
  else if(cmd=="STATUS") { Serial.println("STATUS:OK"); Serial.print("DIST:"); Serial.println(readUltrasonic()); Serial.print("LINE:"); Serial.println(readLine()); }
  else if(cmd=="INFO") Serial.println("M5Core2 Robocar V2.0 Ultrasonic+Line MQTT2 Auto");
  else if(cmd=="FWD") moveForward();
  else if(cmd=="REV") moveBackward();
  else if(cmd=="LFT") moveLeft();
  else if(cmd=="RGT") moveRight();
  else if(cmd=="RTL") rotateLeft();
  else if(cmd=="RTR") rotateRight();
  else if(cmd=="STP") stopMotors();
  else if(cmd=="AUTO") autonomousMode=true;
  else if(cmd=="LINE") { int l=readLine(); Serial.print("LINE:"); Serial.println(l); }
  else Serial.println("UNKNOWN:"+cmd);
}

float readUltrasonic(){
  digitalWrite(ULTRASONIC_TRIG, LOW); delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG, LOW);
  long dur = pulseIn(ULTRASONIC_ECHO, HIGH, 25000);
  return dur*0.0343/2;
}
int readLine(){
  int l=digitalRead(LINE_L), c=digitalRead(LINE_C), r=digitalRead(LINE_R);
  return (l<<2)|(c<<1)|r; // 0-7 bitmask
}

void moveForward(){ digitalWrite(M_FL1,HIGH); digitalWrite(M_FL2,LOW); digitalWrite(M_FR1,HIGH); digitalWrite(M_FR2,LOW); }
void moveBackward(){ digitalWrite(M_FL1,LOW); digitalWrite(M_FL2,HIGH); digitalWrite(M_FR1,LOW); digitalWrite(M_FR2,HIGH); }
void moveLeft(){ digitalWrite(M_FL1,LOW); digitalWrite(M_FL2,HIGH); digitalWrite(M_FR1,HIGH); digitalWrite(M_FR2,LOW); }
void moveRight(){ digitalWrite(M_FL1,HIGH); digitalWrite(M_FL2,LOW); digitalWrite(M_FR1,LOW); digitalWrite(M_FR2,HIGH); }
void rotateLeft(){ digitalWrite(M_FL1,LOW); digitalWrite(M_FL2,HIGH); digitalWrite(M_FR1,LOW); digitalWrite(M_FR2,HIGH); }
void rotateRight(){ digitalWrite(M_FL1,HIGH); digitalWrite(M_FL2,LOW); digitalWrite(M_FR1,HIGH); digitalWrite(M_FR2,LOW); }
void stopMotors(){ digitalWrite(M_FL1,LOW); digitalWrite(M_FL2,LOW); digitalWrite(M_FR1,LOW); digitalWrite(M_FR2,LOW); }
void omni(int x,int y,int rot){ // for SATURDAY omni compatibility
  if(y>0) moveForward(); else if(y<0) moveBackward();
  else if(x<0) moveLeft(); else if(x>0) moveRight();
  else if(rot<0) rotateLeft(); else if(rot>0) rotateRight(); else stopMotors();
}

void autonomousStep(){
  float dist=readUltrasonic();
  int line=readLine();
  // Priority: obstacle > line > wander
  if(dist>0 && dist<18){
    // Obstacle - back and turn
    moveBackward(); delay(300); rotateRight(); delay(400); stopMotors();
  } else if(line & 0b010){
    // Center on line - go forward
    moveForward();
  } else if(line & 0b100){
    moveLeft(); delay(80);
  } else if(line & 0b001){
    moveRight(); delay(80);
  } else if(line==0){
    // No line - wander slightly
    moveForward();
  }
}

void publishSensors(){
  float d=readUltrasonic();
  int l=readLine();
  String json="{\"distance\":"+String(d,1)+",\"line\":"+String(l)+",\"autonomous\":"+(autonomousMode?"true":"false")+",\"rssi\":"+String(WiFi.RSSI())+"}";
  if(mqtt.connected()) mqtt.publish("homebot/sensors/data", json.c_str());
  if(mqtt2.connected()) mqtt2.publish("homebot/sensors/data", json.c_str());
  Serial.println(json);
}
