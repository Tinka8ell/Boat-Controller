# Boat-Controller
Raspberry Pi model boat controller.

Attempt to controll a model boat with:

3 motors (propeller drives, left, centre and right) - h-bridge controlled dc motors

1 rudder - survo controlled

6 turrets - (2 forward pairs (port and starboard) and 2 rear (port and starboard)) - stepper controlled

Control is via the "BlueDot" app available on Android devices, motor control via the GPIOZero api and survos controlled via SPI interface.
