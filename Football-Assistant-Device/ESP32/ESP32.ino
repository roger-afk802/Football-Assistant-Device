#include <WiFi.h>
#include <WebServer.h>
#include <LiquidCrystal_I2C.h>
#include <ESP32Servo.h>
#include <DFRobotDFPlayerMini.h>

// =====================
// DFPlayer Mini
// =====================

// DFPlayer TX → ESP32 GPIO16
// DFPlayer RX ← ESP32 GPIO17
const int DFPLAYER_RX_PIN = 16;
const int DFPLAYER_TX_PIN = 17;

HardwareSerial dfSerial(2);
DFRobotDFPlayerMini dfPlayer;

bool dfPlayerReady = false;


// =====================
// 音量旋鈕
// =====================

const int VOLUME_PIN = 34;

int lastVolume = -1;
unsigned long lastVolumeReadTime = 0;

const unsigned long VOLUME_READ_INTERVAL = 200;


// =====================
// 音效與主題曲
// =====================

// /mp3/0001.mp3 → whistle
// /mp3/0002.mp3 → reminder
// /mp3/0011.mp3 → IShowSpeed
// /mp3/0012.mp3 → theme2
// /mp3/0013.mp3 → theme3

const int SONG_TRACKS[] = {11, 12, 13};

const int SONG_COUNT =
    sizeof(SONG_TRACKS) / sizeof(SONG_TRACKS[0]);

int nextSongIndex = 0;

// 哨聲長度，要之後依實際音檔微調
const unsigned long WHISTLE_DURATION = 900;
const unsigned long WHISTLE_GAP = 250;


//=====================
// LCD
//=====================
LiquidCrystal_I2C lcd(0x27, 16, 2);

//=====================
// WiFi
//=====================
const char* ssid = "Bee Lo 的 iPhone";
const char* password = "12345677";

WebServer server(80);

//=====================
// Servo
//=====================
Servo footballServo;
const int SERVO_PIN = 25;

//=====================
// RGB LED（共陽）
// LOW = 亮，HIGH = 滅
//=====================
const int RED_PIN = 26;
const int GREEN_PIN = 27;
const int BLUE_PIN = 33;

// 記住目前顏色
String currentLedColor = "off";


//=====================
// LCD
//=====================
void showLCD(String line1, String line2) {
  lcd.clear();

  lcd.setCursor(0, 0);
  lcd.print(line1.substring(0, 16));

  lcd.setCursor(0, 1);
  lcd.print(line2.substring(0, 16));
}


//=====================
// RGB LED
//=====================
void turnLedOff() {
  digitalWrite(RED_PIN, HIGH);
  digitalWrite(GREEN_PIN, HIGH);
  digitalWrite(BLUE_PIN, HIGH);
}


void setLED(String color) {
  turnLedOff();

  if (color == "red") {
    digitalWrite(RED_PIN, LOW);
  }
  else if (color == "green") {
    digitalWrite(GREEN_PIN, LOW);
  }
  else if (color == "yellow") {
    // 黃色 = 紅 + 綠
    digitalWrite(RED_PIN, LOW);
    digitalWrite(GREEN_PIN, LOW);
  }
  else if (color == "blue") {
    digitalWrite(BLUE_PIN, LOW);
  }

  currentLedColor = color;
}


//=====================
// Servo
//=====================
void servoGoal() {
  String savedColor = currentLedColor;

  // 避免 Servo 和 LED 同時耗電
  turnLedOff();
  delay(200);

  footballServo.write(90);
  delay(500);

  footballServo.write(0);
  delay(500);

  delay(200);

  setLED(savedColor);
}


void servoCelebrate() {
  String savedColor = currentLedColor;

  turnLedOff();
  delay(200);

  for (int i = 0; i < 2; i++) {
    footballServo.write(90);
    delay(350);

    footballServo.write(0);
    delay(350);
  }

  delay(200);

  setLED(savedColor);
}


void controlServo(String action) {
  if (action == "goal") {
    servoGoal();
  }
  else if (action == "celebrate") {
    servoCelebrate();
  }

  // none 或其他字串：不動
}


//=====================
// Sound
// DFPlayer 尚未接入
//=====================
void playNextSong() {
  if (!dfPlayerReady) {
    return;
  }

  int trackNumber = SONG_TRACKS[nextSongIndex];

  dfPlayer.playMp3Folder(trackNumber);

  Serial.print("Playing song track: ");
  Serial.println(trackNumber);

  nextSongIndex++;

  if (nextSongIndex >= SONG_COUNT) {
    nextSongIndex = 0;
  }
}
void playSound(String action) {
  // none = 不做任何事，也不停止目前播放
  if (action == "" || action == "none") {
    return;
  }

  if (!dfPlayerReady) {
    Serial.print("DFPlayer unavailable, ignored: ");
    Serial.println(action);
    return;
  }

  if (action == "goal") {
    // 吹哨一次
    dfPlayer.playMp3Folder(1);
    delay(WHISTLE_DURATION);

    // 接著播放下一首主題曲
    playNextSong();
  }

  else if (action == "event") {
    // 吹哨一次
    dfPlayer.playMp3Folder(1);
  }

  else if (action == "fulltime") {
    // 吹哨三次
    for (int i = 0; i < 3; i++) {
      dfPlayer.playMp3Folder(1);
      delay(WHISTLE_DURATION);

      if (i < 2) {
        delay(WHISTLE_GAP);
      }
    }
  }

  else if (action == "warning") {
    dfPlayer.playMp3Folder(2);
  }

  else if (action == "relax") {
    dfPlayer.playMp3Folder(2);
  }

  else if (action == "stop") {
    dfPlayer.stop();
  }

  else {
    Serial.print("Unknown sound action: ");
    Serial.println(action);
  }
}
void updateVolume() {
  if (!dfPlayerReady) {
    return;
  }

  unsigned long now = millis();

  if (now - lastVolumeReadTime < VOLUME_READ_INTERVAL) {
    return;
  }

  lastVolumeReadTime = now;

  int rawValue = analogRead(VOLUME_PIN);

  int newVolume = map(
    rawValue,
    0,
    4095,
    0,
    30
  );

  newVolume = constrain(newVolume, 0, 30);

  if (
    lastVolume == -1 ||
    abs(newVolume - lastVolume) >= 2
  ) {
    dfPlayer.volume(newVolume);
    lastVolume = newVolume;

    Serial.print("Volume: ");
    Serial.println(newVolume);
  }
}


//=====================
// HTTP /update
//=====================
void handleUpdate() {
  String line1 = server.arg("line1");
  String line2 = server.arg("line2");
  String ledColor = server.arg("led");
  String servoAction = server.arg("servo");
  String soundAction = server.arg("sound");

  // 沒傳就給預設值
  if (line1 == "") {
    line1 = "World Cup";
  }

  if (line2 == "") {
    line2 = "Guardian";
  }

  if (ledColor == "") {
    ledColor = currentLedColor;
  }

  if (servoAction == "") {
    servoAction = "none";
  }

  if (soundAction == "") {
    soundAction = "none";
  }

  Serial.println();
  Serial.println("===== New Command =====");

  Serial.print("line1: ");
  Serial.println(line1);

  Serial.print("line2: ");
  Serial.println(line2);

  Serial.print("led: ");
  Serial.println(ledColor);

  Serial.print("servo: ");
  Serial.println(servoAction);

  Serial.print("sound: ");
  Serial.println(soundAction);

  // 依序執行
// 先更新畫面
  showLCD(line1, line2);
  setLED(ledColor);

  // 先回覆 Python，避免 Servo、哨聲的 delay 導致連線逾時
  server.send(200, "text/plain", "OK");

  // 再執行聲音與 Servo
  playSound(soundAction);
  controlServo(servoAction);
}


//=====================
// Setup
//=====================
void setup() {
  lcd.init();
  lcd.backlight();

  Serial.begin(115200);
  delay(1000);

  // RGB LED
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  turnLedOff();

  // Servo
  footballServo.setPeriodHertz(50);
  footballServo.attach(SERVO_PIN, 500, 2400);
  footballServo.write(0);
  delay(500);

  // WiFi
  WiFi.begin(ssid, password);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Connecting...");
  pinMode(VOLUME_PIN, INPUT);

  dfSerial.begin(
    9600,
    SERIAL_8N1,
    DFPLAYER_RX_PIN,
    DFPLAYER_TX_PIN
  );

  if (dfPlayer.begin(dfSerial)) {
    dfPlayerReady = true;

    dfPlayer.volume(15);
    lastVolume = 15;

    Serial.println("DFPlayer ready.");
  }
  else {
    dfPlayerReady = false;

    Serial.println(
      "DFPlayer not detected. "
      "System continues without sound."
    );
  }



  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  String ip = WiFi.localIP().toString();

  Serial.println();
  Serial.println("WiFi connected!");

  Serial.print("ESP32 IP: ");
  Serial.println(ip);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi connected");

  lcd.setCursor(0, 1);
  lcd.print(ip.substring(0, 16));

  server.on("/update", HTTP_GET, handleUpdate);
  server.begin();

  delay(2000);

  showLCD("Server started", ip);
}


//=====================
// Loop
//=====================
void loop() {
  server.handleClient();
  updateVolume();
}