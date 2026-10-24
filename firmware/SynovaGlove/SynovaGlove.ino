#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Fill these in only after measuring the actual glove on a bench.
// The shipped values deliberately keep motor outputs disabled.
constexpr int ESTOP_PIN = -1;          // Normally closed switch to ground; open = stop.
constexpr int MOTOR_ENABLE_PIN = -1;   // Active-high motor power gate.
constexpr int SERVO_PINS[5] = {-1, -1, -1, -1, -1};
constexpr int OPEN_US[5] = {0, 0, 0, 0, 0};
constexpr int CLOSE_US[5] = {0, 0, 0, 0, 0};
constexpr int REST_US[5] = {0, 0, 0, 0, 0};
constexpr bool CALIBRATION_REVIEWED = false;

constexpr uint32_t WATCHDOG_MS = 1500;
constexpr uint32_t MAX_MOTION_MS = 1200;
constexpr int PWM_BITS = 14;
constexpr int PWM_HZ = 50;

static BLECharacteristic* responseCharacteristic = nullptr;
static bool connected = false;
static bool armed = false;
static bool stopped = true;
static bool moving = false;
static bool pwmReady = false;
static uint32_t lastPacketAt = 0;
static uint32_t motionStartedAt = 0;

static bool configured() {
  if (!CALIBRATION_REVIEWED || !pwmReady || ESTOP_PIN < 0 || MOTOR_ENABLE_PIN < 0) return false;
  for (int i = 0; i < 5; i++) {
    if (SERVO_PINS[i] < 0 || OPEN_US[i] < 500 || OPEN_US[i] > 2500 ||
        CLOSE_US[i] < 500 || CLOSE_US[i] > 2500 || REST_US[i] < 500 || REST_US[i] > 2500) return false;
    if (SERVO_PINS[i] == ESTOP_PIN || SERVO_PINS[i] == MOTOR_ENABLE_PIN) return false;
    for (int j = 0; j < i; j++) if (SERVO_PINS[i] == SERVO_PINS[j]) return false;
  }
  if (ESTOP_PIN == MOTOR_ENABLE_PIN) return false;
  return true;
}

static bool estopReleased() {
  return ESTOP_PIN >= 0 && digitalRead(ESTOP_PIN) == LOW;
}

static void disableMotion() {
  for (int pin : SERVO_PINS) if (pin >= 0) ledcWrite(pin, 0);
  if (MOTOR_ENABLE_PIN >= 0) digitalWrite(MOTOR_ENABLE_PIN, LOW);
  moving = false;
}

static void emergencyStop() {
  disableMotion();
  armed = false;
  stopped = true;
}

static void reply(const String& text) {
  if (!connected || responseCharacteristic == nullptr) return;
  responseCharacteristic->setValue(text.c_str());
  responseCharacteristic->notify();
}

static bool setPose(const int pulseUs[5]) {
  if (!configured() || !estopReleased() || stopped || !armed) return false;
  digitalWrite(MOTOR_ENABLE_PIN, HIGH);
  for (int i = 0; i < 5; i++) {
    // At 50 Hz, a 20,000 us frame maps to 2^14 duty steps.
    const uint32_t duty = (uint32_t)pulseUs[i] * (1UL << PWM_BITS) / 20000UL;
    if (!ledcWrite(SERVO_PINS[i], duty)) { emergencyStop(); return false; }
  }
  moving = true;
  motionStartedAt = millis();
  return true;
}

class GloveServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer*) override {
    connected = true;
    emergencyStop();
    lastPacketAt = millis();
  }

  void onDisconnect(BLEServer* server) override {
    connected = false;
    emergencyStop();
    server->startAdvertising();
  }
};

class GloveCommandCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* characteristic) override {
    String command = characteristic->getValue();
    command.trim();
    if (!connected) return;
    lastPacketAt = millis();

    if (command == "PING") { reply(stopped ? "PONG STOPPED" : "PONG READY"); return; }
    if (command == "STOP") { emergencyStop(); reply("ACK STOP"); return; }
    if (command == "HELLO") {
      reply(configured() && estopReleased() ? stopped ? "ACK HELLO STOPPED" : "ACK HELLO READY" : "ERR CONFIG_OR_ESTOP");
      return;
    }
    if (command == "RESET") {
      if (!configured() || !estopReleased()) { reply("ERR CONFIG_OR_ESTOP"); return; }
      emergencyStop();
      stopped = false;
      reply("ACK RESET");
      return;
    }
    if (command == "DISARM") { disableMotion(); armed = false; reply("ACK DISARM"); return; }
    if (command == "ARM") {
      if (!configured() || !estopReleased() || stopped) { reply("ERR NOT_READY"); return; }
      armed = true;
      reply("ACK ARM");
      return;
    }
    if (!armed || stopped || !estopReleased()) { emergencyStop(); reply("ERR LOCKED"); return; }
    const int* target = command == "OPEN" ? OPEN_US : command == "CLOSE" ? CLOSE_US : command == "REST" ? REST_US : nullptr;
    if (target == nullptr) { reply("ERR UNKNOWN_COMMAND"); return; }
    reply(setPose(target) ? "ACK " + command : "ERR MOTION_FAILED");
  }
};

void setup() {
  Serial.begin(115200);
  if (ESTOP_PIN >= 0) pinMode(ESTOP_PIN, INPUT_PULLUP);
  if (MOTOR_ENABLE_PIN >= 0) { pinMode(MOTOR_ENABLE_PIN, OUTPUT); digitalWrite(MOTOR_ENABLE_PIN, LOW); }
  if (CALIBRATION_REVIEWED && ESTOP_PIN >= 0 && MOTOR_ENABLE_PIN >= 0) {
    pwmReady = true;
    for (int pin : SERVO_PINS) {
      if (pin < 0 || !ledcAttach(pin, PWM_HZ, PWM_BITS)) { pwmReady = false; Serial.println("PWM setup failed"); }
    }
  }
  emergencyStop();

  BLEDevice::init("Synova Glove");
  BLEServer* server = BLEDevice::createServer();
  server->setCallbacks(new GloveServerCallbacks());
  BLEService* service = server->createService("8F0C1000-7B24-4C6A-9E45-12DB72D30100");
  BLECharacteristic* command = service->createCharacteristic(
    "8F0C1001-7B24-4C6A-9E45-12DB72D30100", BLECharacteristic::PROPERTY_WRITE);
  command->setCallbacks(new GloveCommandCallbacks());
  responseCharacteristic = service->createCharacteristic(
    "8F0C1002-7B24-4C6A-9E45-12DB72D30100", BLECharacteristic::PROPERTY_NOTIFY);
  responseCharacteristic->addDescriptor(new BLE2902());
  service->start();
  server->getAdvertising()->addServiceUUID(service->getUUID());
  server->startAdvertising();
  Serial.println(configured() ? "Synova glove BLE ready" : "Synova glove needs pin and motion calibration");
}

void loop() {
  if (!configured() || !estopReleased()) emergencyStop();
  if (connected && millis() - lastPacketAt > WATCHDOG_MS) emergencyStop();
  if (moving && millis() - motionStartedAt > MAX_MOTION_MS) disableMotion();
  delay(10);
}
