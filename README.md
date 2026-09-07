# PID Line Follower

Wireless PID-controlled line-following robot with dynamic battery voltage compensation and real-time over-the-air (BLE) telemetry and tuning.

Built with an **Arduino Mega 2560**, an **nRF5340 DK** running Zephyr RTOS as a BLE-to-UART bridge, a 5-channel IR reflectance array, and a custom **Python desktop GUI** (`asyncio` + `bleak`).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PC / Host Station                        │
│             Scanner.py (Tkinter + Bleak GUI)                │
└──────────────────────────────┬──────────────────────────────┘
                               │  BLE (Nordic UART Service - NUS)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               nRF5340 DK (Zephyr RTOS)                      │
│             BLE-to-UART Telemetry Bridge                    │
└──────────────────────────────┬──────────────────────────────┘
                               │  UART @ 115200 baud
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Arduino Mega 2560                         │
│  ├── 5-IR Sensor Array Centroid Calculation                 │
│  ├── Dynamic Battery Voltage Compensation (A0 Divider)      │
│  ├── PID Steering Controller (Anti-Windup & Corner Memory)  │
│  └── L298N Dual H-Bridge Driver ──► 4× DC Gear Motors       │
└─────────────────────────────────────────────────────────────┘
```

## Features & Engineering Highlights

### 1. Dynamic Battery Sag Compensation
DC motor output torque and speed drop as battery voltage decays across discharge cycles. On a standard 3S LiPo (12.6V fully charged down to ~11.0V cutoff), fixed PWM duty cycles and PID gains lead to progressively sluggish cornering.
- The system reads pack voltage through an onboard 11:1 resistor divider into analog pin `A0`:
  $$V_{\text{bat}} = V_{A0} \times \left(\frac{110\text{ k}\Omega}{10\text{ k}\Omega}\right)$$
- A dynamic scaling ratio continuously stabilizes steering authority and forward velocity:
  $$\text{voltageFactor} = \frac{12.6\text{ V}}{V_{\text{bat}}}$$
  $$\text{baseSpeed} = v_{\text{target}} \times \text{voltageFactor}$$
  $$K_{p,\text{eff}} = K_p \times \text{voltageFactor}, \quad K_{i,\text{eff}} = K_i \times \text{voltageFactor}, \quad K_{d,\text{eff}} = K_d \times \text{voltageFactor}$$

### 2. Weighted Centroid Position & Loss Recovery
- 5 active-low IR sensors are assigned discrete spatial weights:
  $$\vec{w} = [-2, -1, 0, 1, 2] \quad (\text{LL}, \text{L}, \text{M}, \text{R}, \text{RR})$$
- When the line is detected under one or more sensors, error is calculated via weighted average:
  $$\text{error} = \frac{\sum w_i \cdot s_i}{\sum s_i}$$
- **Corner Memory Recovery**: If all sensors lose the line (`activeCount == 0`):
  - If $|\text{lastError}| \ge 0.5$ (lost during a sharp curve), the robot **latches the previous error** to continue turning into the track until reacquired.
  - If $|\text{lastError}| < 0.5$ (lost on a straight), error drops to $0$ to coast straight ahead.

### 3. Wireless Real-Time PID Tuning
Tuning line followers typically requires plugging in a USB cable, re-uploading code, and unhooking the cable for every single gain adjustment.
- **Over-the-Air Bridge**: The nRF5340 DK receives parameters from a PC over Bluetooth Low Energy and forwards them directly to the Arduino over serial.
- **Live Desktop GUI (`Scanner.py`)**: Lets you adjust $K_p$, $K_i$, $K_d$, and motor speed on the fly with sliders while the robot is actively running on the track. Includes quick controls for emergency stop, resetting to defaults, and reverting to previous values.

## Hardware & Pinout

| Component | Pin / Channel | Connection to Arduino Mega | Description |
|---|---|---|---|
| **IR Array** | LL, L, M, R, RR | Pins 53, 51, 49, 47, 45 | Digital inputs (active low) |
| **L298N Driver** | ENA, ENB | Pins 3, 8 | Motor enable outputs (HIGH) |
| | pwmL, pwmR | Pins 5, 6 | Left & Right PWM speed control |
| | dirL, dirR | Pins 4, 7 | Direction control (forward/reverse) |
| **Battery Sense** | Divider Tap | Analog Pin A0 | 11:1 voltage divider for 3S LiPo sensing |
| **nRF5340 DK** | UART TX / RX | RX0 (Pin 0) / TX0 (Pin 1) | 115200 baud serial bridge |

*Note: The included circuit schematic (`assets/schematic.png`) illustrates the wiring topology. A generic battery holder and nRF breakout were used as visual stand-ins in Fritzing for the 3S LiPo battery pack and nRF5340 DK.*

<p align="center">
  <img src="assets/schematic.png" width="85%" alt="Circuit Schematic" />
</p>

## Telemetry Protocol

Commands are transmitted over BLE NUS (RX Characteristic UUID: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E`) as space-delimited ASCII strings:

| Parameter | Command Prefix | Value Range | Resolution / Mapping |
|---|---|---|---|
| **$K_p$** (Proportional) | `p` | 40 – 100 | Integer (Default: `75`) |
| **$K_i$** (Integral) | `i` | 0 – 10 | Mapped to $0.0 - 1.0$ (`val * 0.1`) |
| **$K_d$** (Derivative) | `d` | 0 – 50 | Integer (Default: `10`) |
| **Speed** ($v_{\text{base}}$) | `v` | 90 – 150 | Integer PWM base value (Default: `100`) |

**Packet Example**:
```
p75 d10 i1 v100 
```
The Arduino continuously parses variable prefixes, updates runtime control parameters, and returns confirmation over serial.

### nRF5340 Firmware Configurations
The board uses the standard Nordic UART Service (NUS) sample from the nRF Connect SDK as the wireless bridge, configured with three project-specific changes:
- **Pin Routing (`app.overlay`)**: Devicetree overlay routes `UART0` TX to Port 0 Pin 11 to wire directly to Arduino Mega `RX0`.
- **UART Isolation (`prj.conf`)**: Kernel logging over UART is disabled (`CONFIG_LOG_BACKEND_UART=n`) and rerouted to Segger RTT, ensuring system debug logs do not contaminate the motor command stream.
- **Device Name (`prj.conf`)**: Broadcasts as `"ZETA"` for automatic recognition by `Scanner.py`.

## Repository Structure

```
PID-Line-Follower/
├── PID-Line-Follower.ino     # Arduino sketch (sensing, PID loop, voltage compensation, motor PWM)
├── Scanner.py                # Python GUI (Tkinter + Bleak BLE NUS client for live tuning)
├── firmware/                 # Zephyr RTOS firmware for nRF5340 DK (Nordic UART Service bridge)
│   ├── src/main.c            # Zephyr NUS BLE peripheral application
│   ├── prj.conf              # Kernel & Bluetooth stack configuration
│   └── CMakeLists.txt        # Build definition
└── assets/
    └── schematic.png         # Hardware wiring & component interconnect diagram
```
