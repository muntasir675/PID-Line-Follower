# PID-Line-Follower

nRF24L01-based wireless PID line-following robot using Arduino.

Receives PID tuning parameters via nRF wireless link and controls
motor speed based on 5-channel IR sensor input with battery voltage compensation.

## Structure
- `PID-Line-Follower.ino` — Arduino sketch (sensors, PID, nRF reception, motor control)
- `assets/schematic.png` — Circuit schematic

## Hardware
- Arduino Mega
- 5× IR sensors for line detection
- L298N motor driver
- nRF24L01 module for wireless control
- Voltage divider for battery monitoring

## Controls
PID gains (Kp, Ki, Kd) and max speed are adjustable wirelessly
via the nRF link. The Linux-side nRF transmitter code is not
included here yet.

![Schematic](assets/schematic.png)
