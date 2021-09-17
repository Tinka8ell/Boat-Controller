# !/usr/bin/python3
"""
GpioZeroBoat - A Boat using gpioZero pin control
Originally created as a implementation extending the gpiozero robot object.
It added a third motor and a ruder.

With the inclusion of the turrets that use stepper motors, 
not directly supported by gpiozero,
they had to be implemented in a more specific way.

"""

import math

from gpiozero import SourceMixin, CompositeDevice, Motor, Servo, Pin, Device, GPIOPinMissing

from Turret import Turret


def dp2(number):
    return format(number, "03.2f")


def checkMotor(name, pins, pwm=True, pin_factory=None):
    ### print("checkMotor:", name, pins, pwm, pin_factory)
    motor = None
    if isinstance(pins, tuple):
        ### print("pins are tuple")
        motor = Motor(*pins, pwm=pwm, pin_factory=pin_factory)
    elif isinstance(pins, Motor):
        ### print("pins are Motor")
        motor = pins
        # steal pins back from device
        pins = (motor.forward_device, motor.backward_device)
    ### print("motor is", motor)
    if not motor:
        raise GPIOPinMissing(
            name + ' motor pins must be given as tuple or a Motor object')
    pins = pins[0:2]  # just the first two
    return motor, pins


class GPIOZeroBoat(SourceMixin, CompositeDevice):
    """
    Extends :class:`CompositeDevice` to represent a generic tri-motor and rudder (servo) boat.

    This class is constructed with three tuples representing the forward and
    backward pins of the left, right and center controllers respectively. 

    :param tuple left:
       A tuple of two (or three) GPIO pins representing the forward and
       backward inputs of the left motor's controller. Use three pins if your
       motor controller requires an enable pin.

    :param tuple right:
       A tuple of two (or three) GPIO pins representing the forward and
       backward inputs of the right motor's controller. Use three pins if your
       motor controller requires an enable pin.

    :param tuple center:
       A tuple of two (or three) GPIO pins representing the forward and
       backward inputs of the center motor's controller. Use three pins if your
       motor controller requires an enable pin.

    :param servo rudder:
       A GPIO pin representing the input of the servo controlling the rudder.

    :param bool pwm:
       If :data:`True` (the default), construct :class:`PWMOutputDevice`
       instances for the motor controller pins, allowing both direction and
       variable speed control. If :data:`False`, construct
       :class:`DigitalOutputDevice` instances, allowing only direction
       control.

    :type pin_factory: Factory or None
    :param pin_factory:
       See :doc:`api_pins` for more information (this is an advanced feature
       which most users can ignore).

    .. attribute:: left_motor

       The :class:`Motor` on the left of the boat.

    .. attribute:: right_motor

       The :class:`Motor` on the right of the boat.

    .. attribute:: center_motor

       The :class:`Motor` in the center of the boat.

    .. attribute:: rudder

       The :class:`Servo` for the rudder of the boat.
    """

    def __init__(self, left=None, right=None, center=None, rudder=None, gun=None, pwm=True, pin_factory=None, *args):
        # *args is a hack to ensure a useful message is shown when pins are
        # supplied as sequential positional arguments e.g. 2, 3, 4, 5

        # Check each subdevise and add pins to monitoring ...
        left_motor, pins = checkMotor(
            "left", left, pwm=pwm, pin_factory=pin_factory)
        if left_motor:
            self.pins = list(pins)

        right_motor, pins = checkMotor(
            "right", right, pwm=pwm, pin_factory=pin_factory)
        if right_motor:
            self.pins += list(pins)

        center_motor, pins = checkMotor(
            "center", center, pwm=pwm, pin_factory=pin_factory)
        if center_motor:
            self.pins += list(pins)

        if left_motor and not right_motor:
            raise GPIOPinMissing('Right motor must be given as wll as left')
        if not left_motor and right_motor:
            raise GPIOPinMissing('Left motor must be given as wll as right')
        if not left_motor and not center_motor:
            raise GPIOPinMissing('At least one motor must be given')

        if rudder:
            if not isinstance(rudder, Servo):
                rudder = Servo(rudder)
        else:
            raise GPIOPinMissing('Must provide a Servo as a rudder')

        self.pins.append(rudder.pwm_device)
        for i in range(len(self.pins)):
            if isinstance(self.pins[i], Device):
                self.pins[i] = self.pins[i].pin
            elif not isinstance(self.pins[i], Pin):
                if pin_factory:
                    self.pins[i] = pin_factory.pin(self.pins[i])
                else:
                    self.pins[i] = Device.pin_factory.pin(self.pins[i])

        guns = []
        if isinstance(gun, tuple):
            if isinstance(gun[0], tuple):  # assume all are tuples
                for data in gun:
                    turret = Turret(*data)
                    guns.append(turret)
            elif isinstance(gun[0], Turret):
                for turret in gun:
                    guns.append(turret)
        elif isinstance(gun, Turret):
            guns.append(gun)
        elif gun:
            raise GPIOPinMissing(
                'Gun pins must be given as tuple or a Turret object')
        for turret in guns:
            # steal pins back from device
            self.pins.append(turret)  # will use position for update!
        self.centered = False  # so we only center once when connected

        # initialise parent
        motors = []
        items = {}
        order = []
        if left_motor:  # also must be right motor
            motors.append(left_motor)
            items["left_motor"] = left_motor
            order.append("left_motor")
            motors.append(right_motor)
            items["right_motor"] = right_motor
            order.append("right_motor")
        if center_motor:
            motors.append(center_motor)
            items["center_motor"] = center_motor
            order.append("center_motor")
        self.motors = tuple(motors)
        items["rudder"] = rudder
        order.append("rudder")
        ''' Turrets are not gpiozero devices!
        self.guns = tuple(guns)
        if len(guns) > 0:
            items["back"] = guns[0]
            order.append("back")
            guns = guns[1:]
        if len(guns) > 0:
            items["middle"] = guns[0]
            order.append("middle")
            guns = guns[1:]
        if len(guns) > 0:
            items["front"] = guns[0]
            order.append("front")
        '''
        items["pin_factory"] = pin_factory
        super(GPIOZeroBoat, self).__init__(**items)
        self.guns = guns

        '''
        balancing ratios:
        
        thrustDelta  - ratio from rudder setting to thrust modification
        leftDelta    - ratio to reduce left hand motor by to balance
        rightDelta   - ratio to reduce right hand motor by to balance
        centerDelta  - ratio to reduce center motor by to balance
        toServo      - ratio to adjust rudder setting to match servo range
        '''
        self.thrustDelta = 1.0
        self.leftDelta = 1.0
        self.rightDelta = 1.0
        self.centerDelta = 1.0
        self.toServo = 1.0

        # initialise the motors and servo
        if self.left_motor:
            self.left_motor.stop()
        if self.right_motor:
            self.right_motor.stop()
        if self.center_motor:
            self.center_motor.stop()
        self.rudder.mid()
        # LimmitedSteppers are assumed to be in default position
        self._debug = False
        return

    @property
    def value(self):
        """
        Represents the motion of the boat as a tuple of (left_motor_speed,
        right_motor_speed, center_motor_speed, rudder_angle) with ``(0, 0, 0, 0)``
        representing stopped.
        """
        return super(GPIOZeroBoat, self).value

    # what if there is bias? - multiplier for left/right/center so none > 1
    # this should be done on the gpioZeroBoat side of things ...
    @value.setter
    def value(self, value):
        values = tuple(value)
        for motor in self.motors:
            motor.value = values[0]
            values = values[1:]
        self.rudder.value = values[0]
        values = values[1:]
        for turret in self.guns:
            turret.set(values[0])
            values = values[1:]
        self.debug("set value:", self.value)
        return

    def navigate(self, x, y):
        """
        Control the boat by setting left/right to x , and forward/backward to y.

        Treat as a joystick setting.
        Take the position forward / backward, left / right joystick.
        0.0 < y <= 1.0 - amount of forward thrust
        0.0 > y >= -1.0 - amount of backward thrust
        0.0 < x <= 1.0 - amount of right turn
        0.0 > x >= -1.0 - amount of left turn
        All three motors will give an average of the forward or backward throttle,
        but the left and right motors will be modified by a delta based on the amount of requested turn.
        As the thrust of each motor is max'd out at 1.0,
        the delta has a cut off at the point any motor reaches full throttle.
        The ratio between turn and thrust delta is adjustable / defineable.
           self.thrustDelta will define this, default is 1 (1 to 1)
        The ration of thrust to actual power of the motors is also 
        adjustable / definable to balance any natural imperfections.
           self.leftDelta, self.rightDelta (and possibly) self.centerDelta covers this.
        """
        left, right, center = y, y, y  # straight ahead
        rudder = x
        if x < 0:  # turn left
            if y < 0:  # going backward
                cap = 1.0 + y  # max amount we change by
                delta = - min(-x * self.thrustDelta, cap)
            else:  # going forwards
                cap = 1.0 - y  # max amount we change by
                delta = min(-x * self.thrustDelta, cap)
            left -= delta
            right += delta
        else:  # turn right
            if y < 0:  # going backward
                cap = 1.0 + y  # max amount we change by
                delta = - min(x * self.thrustDelta, cap)
            else:  # going forwards
                cap = 1.0 - y  # max amount we change by
                delta = min(x * self.thrustDelta, cap)
            left += delta
            right -= delta
        # print("Setting LRC+:", int(100*left), int(100*right), 
        #       int(100*center), int(100*rudder))
        left *= self.leftDelta
        right *= self.rightDelta
        center *= self.centerDelta
        rudder *= self.toServo
        # print("Actual LRC+:", int(100*left), int(100*right), 
        #       int(100*center), int(100*rudder))
        if self.left_motor:
            self.left_motor.value = left
        if self.right_motor:
            self.right_motor.value = right
        if self.center_motor:
            self.center_motor.value = center
        self.rudder.value = rudder
        return

    def target(self, gun, angle):
        # point gun gun at angle
        '''
        # gun is int (0 to 2), and -pi <= angle <= pi
        # convert angle to fraction of a circle (clockwise)
        value = 0.5 + angle / (2 * math.pi)
        '''
        # gun is int (0 to 2), and 0 <= angle <= 1
        print("GpioZeroBoat.target: gun =", gun, "value =", dp2(angle))
        value = angle
        self.guns[gun].set(int(value))
        return

    def centerGuns(self):
        # one time centering of all guns
        if not self.centered:
            self.centered = True
            for gun in range(len(self.guns)):
                self.guns[gun].reset()
        return

    def forward(self, speed=1, **kwargs):
        """
        Drive the boat forward by running all motors forward.

        :param float speed:
           Speed at which to drive the motors, as a value between 0 (stopped)
           and 1 (full speed). The default is 1.

        :param float curve_left:
           The amount to curve left while moving forwards, by driving the
           left motor at a slower speed. Maximum *curve_left* is 1, the
           default is 0 (no curve). This parameter can only be specified as a
           keyword parameter, and is mutually exclusive with *curve_right*.

        :param float curve_right:
           The amount to curve right while moving forwards, by driving the
           right motor at a slower speed. Maximum *curve_right* is 1, the
           default is 0 (no curve). This parameter can only be specified as a
           keyword parameter, and is mutually exclusive with *curve_left*.
        """
        curve_left = kwargs.pop('curve_left', 0)
        curve_right = kwargs.pop('curve_right', 0)
        if kwargs:
            raise TypeError('unexpected argument %s' % kwargs.popitem()[0])
        if not 0 <= curve_left <= 1:
            raise ValueError('curve_left must be between 0 and 1')
        if not 0 <= curve_right <= 1:
            raise ValueError('curve_right must be between 0 and 1')
        if curve_left != 0 and curve_right != 0:
            raise ValueError("curve_left and curve_right can't be used at "
                             "the same time")
        self.joystick(curve_right - curve_left, speed)
        self.debug("forward:", self.value)
        return

    def backward(self, speed=1, **kwargs):
        """
        Drive the boat backward by running both motors backward.

        :param float speed:
           Speed at which to drive the motors, as a value between 0 (stopped)
           and 1 (full speed). The default is 1.

        :param float curve_left:
           The amount to curve left while moving backwards, by driving the
           left motor at a slower speed. Maximum *curve_left* is 1, the
           default is 0 (no curve). This parameter can only be specified as a
           keyword parameter, and is mutually exclusive with *curve_right*.

        :param float curve_right:
           The amount to curve right while moving backwards, by driving the
           right motor at a slower speed. Maximum *curve_right* is 1, the
           default is 0 (no curve). This parameter can only be specified as a
           keyword parameter, and is mutually exclusive with *curve_left*.
        """
        curve_left = kwargs.pop('curve_left', 0)
        curve_right = kwargs.pop('curve_right', 0)
        if kwargs:
            raise TypeError('unexpected argument %s' % kwargs.popitem()[0])
        if not 0 <= curve_left <= 1:
            raise ValueError('curve_left must be between 0 and 1')
        if not 0 <= curve_right <= 1:
            raise ValueError('curve_right must be between 0 and 1')
        if curve_left != 0 and curve_right != 0:
            raise ValueError("curve_left and curve_right can't be used at "
                             "the same time")
        self.joystick(curve_right - curve_left, -speed)
        self.debug("backward:", self.value)
        return

    def left(self, speed=1):
        """
        Make the boat turn left by running the right motor forward and left
        motor backward.

        :param float speed:
           Speed at which to drive the motors, as a value between 0 (stopped)
           and 1 (full speed). The default is 1.
        """
        self.joystick(-speed, 0)
        self.debug("left:", self.value)
        return

    def right(self, speed=1):
        """
        Make the boat turn right by running the left motor forward and right
        motor backward.

        :param float speed:
           Speed at which to drive the motors, as a value between 0 (stopped)
           and 1 (full speed). The default is 1.
        """
        self.joystick(speed, 0)
        self.debug("right:", self.value)
        return

    def reverse(self):
        """
        Reverse the boat's current motor directions. If the robot is currently
        running full speed forward, it will run full speed backward. If the
        robot is turning left at half-speed, it will turn right at half-speed.
        If the robot is currently stopped it will remain stopped.
        """
        self.left_motor.reverse()
        self.right_motor.reverse()
        self.center_motor.reverse()
        # don't change rudder
        self.debug("reverse:", self.value)
        return

    def stop(self):
        """
        Stop the boat.
        """
        self.left_motor.stop()
        self.right_motor.stop()
        self.center_motor.stop()
        self.rudder.mid()
        self.debug("stop:", self.value)
        return

    def debugOn(self):
        self._debug = True
        return

    def debugOff(self):
        self._debug = False
        return

    def debug(self, *args):
        if self._debug:
            print(*args)
        return

    def report(self):
        '''
        Report on the state of this device as list of pin values.
        '''
        result = []
        for pin in self.pins:
            if isinstance(pin, Turret):
                result.append(pin.position)  # use current position
            else:
                result.append(pin.state)
        return result


if __name__ == '__main__':
    from gpiozero import Device, Pin
    from gpiozero.pins.mock import MockFactory  # makes mock available
    from gpiozero.pins.mock import MockPWMPin  # to allow PWM
    from time import sleep

    Device.pin_factory = MockFactory(pin_class=MockPWMPin)

    left = (4, 14)
    right = (17, 18)
    center = (21, 22)
    servo = 24
    test = GPIOZeroBoat(left=left, right=right, center=center, rudder=servo)
    print("About to start")
    # test.debugOn()
    if True:
        test.forward()
        print("report:", test.report())
        sleep(1)
        test.left()
        print("report:", test.report())
        sleep(1)
        test.backward()
        print("report:", test.report())
        sleep(1)
        test.right()
        print("report:", test.report())
        sleep(1)
        test.value = (.5, -.5, .5, -.5)
        print("report:", test.report())
        sleep(1)
    test.stop()
    print("report:", test.report())
    print("Finished")
