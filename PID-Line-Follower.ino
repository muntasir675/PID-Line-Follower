// --- Battery voltage reading ---
const int batteryPin = A0;

float readBattery() {
  int raw = analogRead(batteryPin);       // 0-1023
  float voltageA0 = raw * (5.0 / 1023.0); // voltage at A0 pin
  float batteryVoltage = voltageA0 * (110.0 / 10.0); // undo divider ratio
  return batteryVoltage;
}

// ===========================================================
// ===                   BLUETOOTH                         ===
// ===========================================================

String buffer = "";
char currentVar = '\0';
int Kp = 75;
float Ki = 0.1;
int Kd = 10;
int max_speed = 100;     // <-- This will act as baseSpeed

void readBluetooth() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == ' ' || c == '\n') {
      if (currentVar != '\0' && buffer.length() > 0) {
        int value = buffer.toInt();
        char prefix = tolower(currentVar);

        switch (prefix) {
          case 'p': Kp = value; Serial.print("Kp = "); Serial.println(Kp); break;
          case 'd': Kd = value; Serial.print("Kd = "); Serial.println(Kd); break;
          case 'i': Ki = value*0.1; Serial.print("Ki = "); Serial.println(Ki); break;
          case 'v': max_speed = value; Serial.print("max_speed = "); Serial.println(max_speed); break;
          default:  Serial.print("Unknown variable: "); Serial.println(currentVar); break;
        }
      }
      buffer = "";
      currentVar = '\0';
    }
    else if (isAlpha(c) && buffer.length() == 0) {
      currentVar = c;
    }
    else if (isDigit(c)) {
      buffer += c;
      if (buffer.length() > 3) buffer = buffer.substring(0, 3);
    }
  }
}

// ===========================================================
// ======================== PID CODE =========================
// ===========================================================

// --- Pins ---
const int ENA = 3, ENB = 8;
const int LL = 53, L = 51, M = 49, R = 47, RR = 45;
const int pwmL = 5, dirL = 4;
const int pwmR = 6, dirR = 7;

// baseSpeed now comes from Bluetooth (max_speed)
int baseSpeed = 100;

float prevError = 0;
float lastError = 0;
float integral = 0;

void setup() {
  Serial.begin(115200);

  pinMode(LL, INPUT);
  pinMode(L, INPUT);
  pinMode(M, INPUT);
  pinMode(R, INPUT);
  pinMode(RR, INPUT);
  
  pinMode(pwmL, OUTPUT);
  pinMode(dirL, OUTPUT);
  pinMode(pwmR, OUTPUT);
  pinMode(dirR, OUTPUT);
  
  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);
  
  digitalWrite(ENA, HIGH);
  digitalWrite(ENB, HIGH);

  Serial.println("Send p/d/i/v followed by value, ending with space or newline");
}
void loop() {
  // --- Read Bluetooth ---
  readBluetooth();

  // --- Read battery ---
  float Vbat = readBattery();
  float voltageFactor = 12.6 / Vbat;

  // --- Scale baseSpeed to compensate for lower voltage ---
  baseSpeed = max_speed * voltageFactor;
  baseSpeed = constrain(baseSpeed, 0, 255);

  // --- Scale PID gains according to battery voltage ---
  float effectiveKp = Kp * voltageFactor;
  float effectiveKi = Ki * voltageFactor;
  float effectiveKd = Kd * voltageFactor;

  // --- Read sensors ---
  bool sLL = !digitalRead(LL);
  bool sL  = !digitalRead(L);
  bool sM  = !digitalRead(M);
  bool sR  = !digitalRead(R);
  bool sRR = !digitalRead(RR);

  int sensors[5] = { sLL, sL, sM, sR, sRR };
  int weights[5] = { -2, -1, 0, 1, 2 };

  int sumWeights = 0;
  int activeCount = 0;

  for (int i = 0; i < 5; i++) {
    if (sensors[i]) {
      sumWeights += weights[i];
      activeCount++;
    }
  }
  float error;
  // float error = (activeCount == 0) ? lastError : (float)sumWeights / activeCount;
  // if (activeCount != 0) lastError = error;
  if (activeCount == 0) {
    // No sensors active
    if (abs(lastError) < 0.5) {
        // lost on straight: go forward slowly
        error = 0;
    } else {
        // lost on corner: continue turning in the same direction
        error = lastError;
    }
  } else {
      // normal line detection
      error = (float)sumWeights / activeCount;
      lastError = error;
  }

  // --- PID calculation using scaled gains ---
  integral += error;
  integral = constrain(integral, -10, 10);
  float derivative = error - prevError;
  float correction = -(effectiveKp * error + effectiveKi * integral + effectiveKd * derivative);
  prevError = error;
  

  
  // --- Apply correction to motors ---
  int leftSpeed = baseSpeed - correction;
  int rightSpeed = baseSpeed + correction;

  leftSpeed = constrain(leftSpeed, 0, 255);
  rightSpeed = constrain(rightSpeed, 0, 255);

  analogWrite(pwmL, leftSpeed);
  analogWrite(pwmR, rightSpeed);
  digitalWrite(dirL, LOW);
  digitalWrite(dirR, LOW);

  // --- Optional: Print battery and baseSpeed ---
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 1000) {
    lastPrint = millis();
    Serial.print("Battery: ");
    Serial.println(Vbat);
    Serial.print("BaseSpeed: ");
    Serial.println(baseSpeed);
  }
}
