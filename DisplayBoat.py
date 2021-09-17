# !/usr/bin/python3
# DisplayBoat - boat listener with display
"""
To enable visualisation and so test the control code
a virtual boat was created to react to changes detected.
Originally intended to use the gpiozero values of ports it had to be 
mangled to support the stepper motors used for the turrets.

It also doubles as a threaded environment to allow the other code
to run without immediately terminating after starting. 
"""


import cmath
import math
import sys
from tkinter import Tk, Toplevel, Frame, Label, Canvas, IntVar, LAST

from BoatListener import BoatListener


def dp2(number):
    return format(number, "03.2f")


class DisplayDevice(Canvas):

    def __init__(self, parent, w, h, bg="blue"):
        Canvas.__init__(self, parent, width=w, height=h, bg=bg,
                        borderwidth=0, highlightthickness=0)
        self.width = w
        self.height = h
        self.parent = parent
        self.makeDisplay()
        return

    def makeDisplay(self):
        return

    def adjust(self, value, item=0):
        # adjust the display to show value for the item
        return


class DisplayMotor(DisplayDevice):

    def makeDisplay(self):
        self.create_rectangle(0, 0, self.width, self.height, fill="brown")
        self.forward = self.create_rectangle(
            0, 0, self.width, self.height // 2, fill="green")
        self.backward = self.create_rectangle(
            0, self.height // 2, self.width, self.height, fill="red")
        return

    def adjust(self, value, item=0):
        element = None
        w = self.width
        h = self.height // 2
        t = 0
        b = 0
        if item == 0:  # forward
            element = self.forward
            b = h
            t = (1 - value) * h
        elif item == 1:  # backward
            element = self.backward
            t = h
            b = (1 + value) * h
        self.coords(element, (0, t, w, b))
        return


class DisplayMotors(DisplayDevice):

    def __init__(self, parent, w, h, number, bg="blue"):
        self.motors = []
        self.number = number
        DisplayDevice.__init__(self, parent, w, h, bg=bg)
        return

    def makeDisplay(self):
        self.create_rectangle(0, 0, self.width, self.height,
                              fill="white", outline="white")
        number = self.number
        w = self.width // (2 * number - 1)
        if number == 1:  # only central motor
            motor = DisplayMotor(self.parent, w, self.height, bg="white")
            self.create_window(
                (self.width // 2,  self.height // 2), window=motor)
            self.motors.append(motor)
        elif number == 2:  # only left and right motors
            motor = DisplayMotor(self.parent, w, self.height, bg="white")
            self.create_window(
                ((self.width // 2) - w,  self.height // 2), window=motor)
            self.motors.append(motor)  # left
            motor = DisplayMotor(self.parent, w, self.height, bg="white")
            self.create_window(
                ((self.width // 2) + w,  self.height // 2), window=motor)
            self.motors.append(motor)  # right
        elif number == 3:  # all three
            motor = DisplayMotor(self.parent, w, self.height, bg="white")
            self.create_window(((self.width // 2) - 2 * w,
                                self.height // 2), window=motor)
            self.motors.append(motor)  # left
            motor = DisplayMotor(self.parent, w, self.height, bg="white")
            self.create_window(((self.width // 2) + 2 * w,
                                self.height // 2), window=motor)
            self.motors.append(motor)  # right
            motor = DisplayMotor(self.parent, w, self.height, bg="white")
            self.create_window(
                (self.width // 2,  self.height // 2), window=motor)
            self.motors.append(motor)  # center
        return

    def adjust(self, value, item=0):
        i = item // 2  # 0 - 5 => 0 - 2
        j = item % 2  # 0 - 5 => 0 or 1
        self.motors[i].adjust(value, j)
        return


class DisplayRudder(DisplayDevice):

    def makeDisplay(self):
        w = self.width // 2
        self.create_oval(0, -w, 2 * w, w, fill="white", outline="white")
        l = 3 * w // 4
        self.w = w
        self.l = l
        self.rudder = self.create_line(
            w, 0, w, l, fill="black", width=w // 10, arrow=LAST)
        return

    def adjust(self, value, item=0):
        ### print("angle (value * 10000): ", int(value * 10000))
        # value for rudder is 5/100 <= value <= 10/100
        self.rudderMin = 0.05
        self.rudderRange = 0.05
        w = self.w
        l = self.l
        offset = value - self.rudderMin
        fraction = (offset) / self.rudderRange  # value 0 - 1
        # angle in radians  pi + pi/4 to pi + 3pi/4
        angle = math.pi * (0.0 + (0.5 - fraction) / 2.0)
        ### print("rudder: offset =", int(1000*offset)/1000.0, 
        ###       "fraction =", int(100*fraction)/100.0, 
        ###       "angle =", int(100*angle)/100.0)
        cangle = cmath.exp(angle*1j)
        t = 0
        b = l
        c = w
        center = complex(c, t)  # top center
        coordinates = ((c, t), (c, b))  # top center to bottom center
        new = []
        for x, y in coordinates:
            v = cangle * (complex(x, y) - center) + center
            new.append(int(v.real))
            new.append(int(v.imag))
            ### print((x, y), "=>", (int(v.real), int(v.imag)))
        self.coords(self.rudder, *tuple(new))
        return


class DisplayGun(DisplayDevice):
    '''
    Represent a gun on the boat.
    The basic gun has size, it's width (diameter) and optional colour.
    '''

    def __init__(self, parent, diameter, size=3, colour=None, bg="white"):
        self.size = size
        self.colour = colour
        DisplayDevice.__init__(self, parent, diameter, diameter, bg=bg)
        return

    def makeDisplay(self):
        w = self.width
        colour = ("yellow", "orange", "red")[self.size - 1]
        if self.colour:
            colour = self.colour
        self.create_oval(0, 0, w, w, fill=colour, outline=colour)
        w2 = w // 2
        l = w2
        s = l // 3
        if self.size == 1:  # smallest
            s = 0
        self.t = w2 - l
        self.b = w2
        self.s = s
        self.t1 = self.create_line(
            w2 - s, self.t, w2 - s, self.b, fill="black", width=w // 10)
        self.t2 = None
        if self.size > 1:
            self.t2 = self.create_line(
                w2 + s, w2 - l, w2 + s, w2, fill="black", width=w // 10)
        return

    def adjust(self, value, item=0):
        ### print("angle:", value)
        # value for turret is -20 <= position <= 20 (value clockwise from 12 o'clock)
        # representing 0 >= angle >= 2pi (angle clockwise from 12 o'clock)
        a = 2 * math.pi
        w = self.width // 2
        t = self.t
        s = self.s
        b = self.b
        fraction = value / 20  # value 0.0 to 1.0
        angle = 2 * math.pi * fraction  # angle in radians  0 to 2pi
        # angle = - angle # + math.pi / 2 # convert to anlge measured from 3 o'clock anti-clockwise
        ### print("turret: fraction =", dp2(fraction), "angle =", dp2(angle))
        cangle = cmath.exp(angle*1j)
        c = b
        center = complex(c, b)  # bottom center
        # top center to bottom center left by s
        coordinates = ((c - s, t), (c - s, b))
        new = []
        for x, y in coordinates:
            v = cangle * (complex(x, y) - center) + center
            new.append(int(v.real))
            new.append(int(v.imag))
            # print((x, y), "=>", (int(v.real), int(v.imag)))
        self.coords(self.t1, *tuple(new))
        ### print("gun from:", coordinates, "to:", tuple(new))
        if self.t2:
            # top center to bottom center right by s
            coordinates = ((c + s, t), (c + s, b))
            new = []
            for x, y in coordinates:
                v = cangle * (complex(x, y) - center) + center
                new.append(int(v.real))
                new.append(int(v.imag))
                # print((x, y), "=>", (int(v.real), int(v.imag)))
            self.coords(self.t2, *tuple(new))
            ### print("gun2 from:", coordinates, "to:", tuple(new))
        return


class DisplayGuns(DisplayDevice):
    '''
    Represent a pair of guns on the front of the boat.
    The basic pair of guns have size, their width and height
    and whether on the port side or not (starboard).
    '''

    def __init__(self, parent, width, height, port, size=2, bg="white"):
        self.size = size
        self.port = port
        self.sarboard = not port
        self.guns = []
        DisplayDevice.__init__(self, parent, width, height, bg=bg)
        return

    def makeDisplay(self):
        colour = "green"
        if self.port:
            colour = "red"
        self.create_rectangle(0, 0, self.width, self.height,
                              fill="white", outline="white")
        w = self.width // 3
        if self.port:  # port arangement
            gun = DisplayGun(self.parent, 2 * w, size=self.size,
                             colour=colour, bg="white")
            self.create_window((2 * w,  w), window=gun)
            self.guns.append(gun)
            gun = DisplayGun(self.parent, 2 * w, size=self.size,
                             colour=colour, bg="white")
            self.create_window((w,  self.height - w), window=gun)
            self.guns.append(gun)
        else:  # starboard arrangement
            gun = DisplayGun(self.parent, 2 * w, size=self.size,
                             colour=colour, bg="white")
            self.create_window((w,  w), window=gun)
            self.guns.append(gun)
            gun = DisplayGun(self.parent, 2 * w, size=self.size,
                             colour=colour, bg="white")
            self.create_window((2 * w,  self.height - w), window=gun)
            self.guns.append(gun)
        return

    def adjust(self, value, item=0):
        # there are two linked guns
        # front (first) moves as per value (negative for port)
        # back (second) is swivelled by 30 degrees (port or starboard)
        # 1/12 of 40 half steps
        swivel = 3  # 40 // 12
        if self.port:
            self.guns[0].adjust(-value)
            self.guns[1].adjust(-value - swivel)
        else:
            self.guns[0].adjust(value)
            self.guns[1].adjust(value + swivel)
        return


class DisplayRearGun(DisplayDevice):
    '''
    Represent a gun on the rear of the boat.
    The basic gun has size, it's width (diameter) and
    whether on the port side or not (starboard).
    '''

    def __init__(self, parent, diameter, port, size=2, bg="white"):
        self.size = size
        self.port = port
        self.sarboard = not port
        DisplayDevice.__init__(self, parent, diameter, diameter, bg=bg)
        return

    def makeDisplay(self):
        colour = "green"
        if self.port:
            colour = "red"
        self.create_rectangle(0, 0, self.width, self.height,
                              fill="white", outline="white")
        w = self.width // 3
        if self.port:  # port arangement
            gun = DisplayGun(self.parent, 2 * w, size=self.size,
                             colour=colour, bg="white")
            self.create_window((2 * w,  w), window=gun)
        else:  # starboard arrangement
            gun = DisplayGun(self.parent, 2 * w, size=self.size,
                             colour=colour, bg="white")
            self.create_window((w,  w), window=gun)
        self.gun = gun
        return

    def adjust(self, value, item=0):
        # moves as per value (but negative for port)
        if self.port:
            self.gun.adjust(18 - value)
        else:
            self.gun.adjust(2 + value)
        return


class DisplayBoat(BoatListener):
    '''
    Represent the boat.
    The basic shape is
       a point at the front,
       a foredeck with one turret or pair of a pair or turrets,
       a reardeck with onr or two central turrets or a pair of side-by-side turrets
       an aft section containing 1, 2 or 3 engines and a rudder.
    The requirement is worked out from the related boat object.
    Motors are either:
       one central,
       two side-by-side, or
       two side-by-side with one central.
    Turrets are based on the boats, guns:
       1 gun => rear only;
       2 guns => one rear and one forard;
       3 guns => either:
          two pair forard and one rear, if second two are the same size or
          one forard and two central rear;
       4 guns => two pair forard and two side-by-side rear.
    '''

    def __init__(self, tk=None):
        # Sort out the graphics basis ...
        if tk:
            self.tk = Toplevel(tk)
        else:
            self.tk = Tk()

        # define model
        self.motorW = 8  # 20
        self.motorL = self.motorW * 12  # 10
        self.rudderL = 1 * self.motorL // 2
        self.rudderW = 2 * self.rudderL
        self.gunW = 3 * self.motorL // 4
        self.makeDisplay()
        x = 100
        y = 100
        self.tk.geometry(f"+{x}+{y}")

        self.rudderMin = 0.05
        self.rudderMid = 0.075
        self.rudderMax = 0.1
        self.rudderRange = self.rudderMax - self.rudderMin
        return

    def makeDisplay(self):
        # construct display in the "tk" toplevel window
        display = Frame(self.tk, bg="white")
        display.grid(row=1, column=1)
        boatWidth = max(7 * self.motorW, 2 * self.rudderL)
        width = boatWidth + self.motorW * 2
        # boat is triangle (length = width), mid section, engines and rudder
        w = width
        bw2 = boatWidth // 2       # half boatWidth
        c = w // 2                 # center line
        t = self.motorW            # top
        s = t                      # side gap
        m = t + boatWidth      # top of main section
        t1 = m + bw2               # center of front turrets
        t2 = t1 + boatWidth        # center of boat
        t3 = t2 + boatWidth        # center of rear turret
        a = m + 3 * boatWidth      # top of aft section
        e = a + self.motorL // 2   # center of engines
        b = a + self.motorL        # top of back end
        r = b + bw2 // 2           # center of rudder
        bb = b + bw2               # bottom of the boat
        boatLength = bb - self.motorW
        length = bb + self.motorW
        canvas = Canvas(display, width=width, height=length, bg="blue")
        canvas.grid(row=1, column=1)
        bow = canvas.create_polygon(
            ((c, t), (s, m), (w - s, m)), fill="white", outline="white")
        hull = canvas.create_rectangle(
            ((s, m), (w - s, b)), fill="white", outline="white")
        aft = canvas.create_oval(
            ((s, b - bw2), (w - s, b + bw2)), fill="white", outline="white")
        self.canvas = canvas  # Canvas in which we draw
        self.dims = (s, c, bw2, t1, t2, t3, e, r)  # for added
        return

    def getGunSize(self, number):
        gun = self.boat.guns[number]
        (steps, start, stop, middle) = gun.range
        size = 2  # medium
        if steps < 12:
            size = 1  # small
        return size

    def added(self, boat):
        # use boat to discover what we need to know to draw the moving parts...
        self.boat = boat
        # first look at number of engines ...
        self.number = len(boat.motors)
        # next look at number and size of turrets
        self.port = None
        self.starboard = None
        self.back = None
        self.rear = None
        self.middle = None
        self.front = None
        if len(boat.guns) > 3:  # 6-gun format
            self.back = self.getGunSize(0)
            self.rear = self.getGunSize(1)
            self.middle = self.getGunSize(2)
            self.front = self.getGunSize(3)
        else:
            if len(boat.guns) > 0:  # at least one rear
                # got a back turret
                gun = boat.guns[0]
                (steps, start, stop, middle) = gun.range
                self.back = 2  # medium
                if steps > 10:
                    self.back = 3  # big
            if len(boat.guns) > 1:  # possible middle turret
                # got a middle turret
                self.middle = self.getGunSize(1)
            if len(boat.guns) > 2:  # at least one forard
                # got a front turret
                self.front = self.getGunSize(2)

        # set up main dimensions (framework)
        canvas = self.canvas  # where to draw things
        s, c, bw2, t1, t2, t3, e, r = self.dims
        boatWidth = 2 * bw2
        w = 2 * c
        gb = 3 * boatWidth / 4     # size of big gun
        gm = 1 * boatWidth / 2     # size of medium gun
        gs = 1 * boatWidth / 3     # size of small gun
        sizes = (0, gs, gm, gb)

        # create aft section, motors and rudder
        number = self.number
        mw = (2 * number - 1) * self.motorW
        self.motors = DisplayMotors(
            canvas, mw, self.motorL, number, bg="white")
        canvas.create_window((c, e), window=self.motors)
        self.rudder = DisplayRudder(canvas, boatWidth, bw2, bg="blue")
        canvas.create_window((c, r), window=self.rudder)

        # create turret sections
        if self.rear:  # have 6 guns, with two side-by-side at rear:
            # self.rear is rear port and self.back is rear starboard
            width = sizes[self.rear]
            self.rear = DisplayRearGun(canvas, width, True, size=2, bg="white")
            canvas.create_window((s + width // 2, t3), window=self.rear)
            width = sizes[self.back]
            self.back = DisplayRearGun(
                canvas, sizes[self.back], False, size=2, bg="white")
            canvas.create_window((w - s - width // 2, t3), window=self.back)
        else:
            if self.back:
                self.back = DisplayGun(
                    canvas, sizes[self.back], size=self.back, bg="white")
                canvas.create_window((c, t3), window=self.back)
        if self.middle and self.front and self.middle == self.front:
            size = self.front
            if size > 2:
                size = 2
            self.middle = self.front = None
            width = sizes[size]
            height = 2 * width
            self.port = DisplayGuns(
                canvas, width, height, port=True, size=size, bg="white")
            canvas.create_window((s + width // 2, t1), window=self.port)
            self.starboard = DisplayGuns(
                canvas, width, height, port=False, size=size, bg="white")
            canvas.create_window((w - s - width // 2, t1),
                                 window=self.starboard)
        else:
            if self.middle:
                self.middle = DisplayGun(
                    canvas, sizes[self.middle], size=self.middle, bg="white")
                canvas.create_window((c, t2), window=self.middle)
            if self.front:
                self.front = DisplayGun(
                    canvas, sizes[self.front], size=self.front, bg="white")
                canvas.create_window((c, t1), window=self.front)

        # make sure all is drawn
        self.tk.update_idletasks()

        # then set default locations
        if self.rear:  # point straight back
            self.rear.adjust(0)
        if self.back:  # point straight back
            self.back.adjust(8)
        if self.port:  # point forward(ish)
            self.port.adjust(0)
            self.starboard.adjust(0)
        else:
            if self.middle:  # point straight back
                self.middle.adjust(10)
            if self.front:  # point straight forward
                self.front.adjust(0)
        for i in range(6):
            self.motors.adjust(0, item=i)
        self.rudder.adjust(self.rudderMid)
        return

    def update(self, *values):
        ### print("update: len", len(values), "values =", values)
        # update display
        number = self.number  # calcualte from actual motors provided!
        for i in range(number * 2):
            self.motors.adjust(values[i], item=i)
        self.rudder.adjust(values[number * 2])
        turrets = values[number * 2 + 1:]
        if self.rear:
            self.rear.adjust(turrets[0])
            turrets = turrets[1:]
            self.back.adjust(turrets[0])
            turrets = turrets[1:]
        elif self.back:
            self.back.adjust(turrets[0] + 10)
            turrets = turrets[1:]
        if self.port:
            self.port.adjust(turrets[0])
            self.starboard.adjust(turrets[1])
        else:
            if self.middle:
                self.middle.adjust(turrets[0] + 10)
                turrets = turrets[1:]
            if self.front:
                self.front.adjust(turrets[0])
        return


if __name__ == '__main__':
    # these imports for mock
    from gpiozero.pins.mock import MockFactory  # makes mock available
    from gpiozero.pins.mock import MockPWMPin  # to allow PWM
    from gpiozero import Device

    from GpioZeroBoat import GPIOZeroBoat
    from Turret import Turret
    from ControlledBoat import ControlledBoat
    from BdController import BdServer

    # comment out this line to use real pins
    Device.pin_factory = MockFactory(pin_class=MockPWMPin)

    # set these to the pins you want to use
    left = (1, 2)
    right = (3, 4)
    center = (5, 6)
    servo = 7
    guns = None

    # Turret controls
    g1 = Turret(-8, (0, 1, 0))   # big back facing turret
    g2 = Turret(8, (0, 0, 0))    # port pair
    g3 = Turret(8, (0, 0, 1))    # starboard pair
    guns = (g1, g2, g3)

    # this starts the boat
    boat = GPIOZeroBoat(left=left, right=right,
                        center=center, rudder=servo, gun=guns)
    displayBoat = DisplayBoat()
    tk = displayBoat.tk
    bdController = BdServer()  # None for testing
    test = ControlledBoat(boat=boat, listener=displayBoat,
                          controller=bdController)
    tk.mainloop()
    test.shutdown()
