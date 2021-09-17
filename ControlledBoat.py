# !/usr/bin/python3
"""
ControlledBoat - remote control boat
This is an implementation of the CommsController to allow
a controller object to be linked to a boat object and optionally
have a listener display the status of the boat.
"""

import math
import sys

from CommsController import CommsController


NAVIGATION = 0
TARGETTING = 1


class ControlledBoat(CommsController):

    def __init__(self, boat=None, controller=None, listener=None):
        # initialise control boat and add any controller
        '''
        # debug info
        print("ControlledBoat:")
        print("boat=", boat)
        print("controller=", controller)
        print("listener=", listener)
        print("super()=", super())
        print("super().__init__=", super().__init__)
        '''
        super().__init__(boat=boat, server=controller)
        '''
        if controller:
           self.addServer(controller)
        '''

        # add in any listener
        self.boatListeners = []
        if listener:
            self.addBoatListener(listener)
        return

    def addBoatListener(self, listener):
        self.boatListeners.append(listener)
        # and then pass back relevant info ...
        listener.added(self.boat)
        return

    def report(self):
        if self.boat and len(self.boatListeners) > 0:
            values = self.boat.report()
            for listener in self.boatListeners:
                # let each listener get the data
                listener.update(*values)
        return

    '''
    Using servers for BoatControllers
    Might want to override stopping(serverID)

    navigate(self, x, y)
    target(self, gun, angle)
    '''
    #
    # Overridden methods ...
    #

    def navigate(self, connectionId, x, y):
        super().navigate(connectionId, x, y)
        # then report oy back up to the boat listeners
        self.report()
        return


if __name__ == '__main__':
    def waitABit():
        print("Wait a bit")
        for i in range(10):
            sleep(1)
            print("waited", i, "seconds")
        sleep(1)
        text = input("Wait Till Someone presses enter:\n")
        print("... received:", text)
        return

    from GpioZeroBoat import GPIOZeroBoat
    from gpiozero.pins.mock import MockFactory  # makes mock available
    from gpiozero.pins.mock import MockPWMPin  # to allow PWM
    from gpiozero import Device

    Device.pin_factory = MockFactory(pin_class=MockPWMPin)

    left = (4, 14)
    right = (17, 18)
    center = (21, 22)
    servo = 24
    boat = GPIOZeroBoat(left, right, center, servo)

    from TestController import TestController
    testController = TestController()

    from TestListener import TestListener
    testListener = TestListener()

    print("About to create controled boat")
    print("adding the test controller should start it")
    test = ControlledBoat(boat, testController, testListener)
    from time import sleep
    from threading import Thread
    thread = Thread(target=waitABit)
    thread.start()
    thread.join()
    print("Shut down controller")
    testController.stopMe()
    sleep(1)
    print("Wait for the controller to stop ...")
    # testController.join()
    print("it stopped, so stop the boat and finish")
    test.boat.stop()
    print("Stopped")
