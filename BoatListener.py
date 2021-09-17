# !/usr/bin/python3
# BoatListener - something to get feedback from a remote control boat
"""
Base class to allow testing and output values from the boat.

Originally intended to use the gpiozero values of ports it had to be 
mangled to support the stepper motors used for the turrets.
"""

class BoatListener():

    '''
    These methods need to be overridden by subclasses.
    '''

    def added(self, boat):
        '''
        After listener is added to controlled boat.

        It is passed the boat to do any set up it requires.
        '''
        return

    def update(self, *values):
        '''
        ControlledBoat has told us about it's state.

        Handle it.
        values are a tuple of Pin values (0.0 <= values <= 1.0).
        There should be ? of them:
        Left Motor Forward
        Left Motor Backward
        Right Motor Forward
        Right Motor Backward
        Center Motor Forward
        Center Motor Backward
        Rudder servo state (usually in range much less than 0.0 to 1.0), e.g. 0.05 to 0.1
        Also turrets: back middle and front taking step values (0 to 40)
        '''
        print("BoatListener: update", values)
        return
