# !/usr/bin/python3
"""
JohnBoat is the main implementation of remote control boat with Blue Dot.

It was created to match the spec for John's model boat.
Details are listed below.
"""

from gpiozero import LED

from BdController import BdServer
from ControlledBoat import ControlledBoat
from DisplayBoat import DisplayBoat
from GpioZeroBoat import GPIOZeroBoat
from Turret import Turret


if __name__ == '__main__':
    '''
    The raspberry pi pins (taken from outout from pinout with added *'s) are:
    J8:
        3V3  (1) (2)  5V
    **GPIO2  (3) (4)  5V
    **GPIO3  (5) (6)  GND
      GPIO4  (7) (8)  GPIO14
        GND  (9) (10) GPIO15
     GPIO17 (11) (12) GPIO18*
     GPIO27 (13) (14) GND
     GPIO22 (15) (16) GPIO23
        3V3 (17) (18) GPIO24
     GPIO10 (19) (20) GND
      GPIO9 (21) (22) GPIO25
     GPIO11 (23) (24) GPIO8
        GND (25) (26) GPIO7
      GPIO0 (27) (28) GPIO1
      GPIO5 (29) (30) GND
      GPIO6 (31) (32) GPIO12*
    *GPIO13 (33) (34) GND
    *GPIO19 (35) (36) GPIO16
     GPIO26 (37) (38) GPIO20
        GND (39) (40) GPIO21

    As
    ** I2C (for turrets) uses:
    Data:  (GPIO2)
    Clock: (GPIO3)
    and
    * hardware PWM is on pins:
    GPIO12, GPIO13, GPIO18, GPIO19

    Suggest use:
    GPIO14, GPIO15, GPIO18*
    GPIO5, GPIO6, GPIO13*
    GPIO20, GPIO26, GPIO19*
    for the H-bridge motors
    and GPIO12* for the servo for the ruder
    So you can make use of the hardware PWM
    and have each motor use 3 pins close to each other
    '''

    noDisplay = False  # True # if don't want a visualisation ...

    # for 3-pin motors:
    left = (20, 21, 19)
    right = (7, 1, 12)
    center = (23, 24, 18)

    # other pins
    servo = 13
    switchPin = 16  # used for pi on indicator

    # Turret controls
    expandor2 = 0  # should be 1 if 2 expanders ...
    # smaller rear facing port turret - 2nd expander, PortA, ls Nible (from 0 to 8)
    g1a = Turret(8, (expandor2, 0, 0))
    # smaller rear facing starboard turret - 2nd expander, PortB, ls Nible (from 0 to 8)
    g1b = Turret(8, (expandor2, 1, 0))
    g2 = Turret(8, (0, 0, 0))    # port pair - PortA, ls Nible (from 0 to 8)
    # starboard pair - PortB, ls Nible (from 0 to 8)
    g3 = Turret(8, (0, 1, 0))
    guns = (g1a, g1b, g2, g3)

    print("Boat about to start")
    # create and also start the boat:
    # old version: boat = BlueDotBoat(left, right, center, servo)
    boat = GPIOZeroBoat(left, right, center, servo,
                        gun=guns)  # boat with added turrets
    # GPIOZeroBoat is just the boat with no controller ...

    # add a blue dot controller, that knows about double clicking to swap function
    bdController = BdServer()

    if noDisplay:
        # create a test boat with controller
        test = ControlledBoat(boat=boat, controller=bdController)
    else:
        displayBoat = DisplayBoat()
        # create a test boat with controller
        test = ControlledBoat(
            boat=boat, listener=displayBoat, controller=bdController)

    # create a switch
    switch = LED(switchPin)
    # and turn it on
    switch.on()
    print(f"Switch on pin {switchPin}?")

    if noDisplay:
        # wait for input (which should never come)
        text = input("Wait Till Finished")
        print("received:", text)
        # stop the boat
        boat.stop()
    else:
        tk = displayBoat.tk
        tk.mainloop()
        test.shutdown()
    print("Boat stopped")

    # turn switch off
    switch.off()
    print(f"Switch off pin {switchPin}?")
