# !/usr/bin/python3
# BdController - BlueDot controller
"""
An implementation of CommsController using the BlueDot interface.
"""

import sys
from threading import Thread
from time import sleep

from bluedot import BlueDot

from CommsController import CommsServer, CommsListener, CommsReceiver, MessageReceiver


# no class BdController()
class BdServer(CommsServer):
    '''
    This is a server for links.

    It will listen on a receiver and wait for connections.
    All new connecions are used to create Listeners
    which are passed to controller (connected()) for aceptance or rejection.
    And new reciever created to wait for another connection.
    Server accepts listeners by calling startup() passing the connection id.
    Server can then close a connection, calling shutdown() on it.
    Children should override:
       makeReceiver(self)- returns a CommsReceiver using self.setup
          CommsReciever waits for connections on accept()
          returning the connection data
       makeListener(connection)- returns a CommsListener using connection and self.controller
    '''

    '''
    These methods must be overwritten
    '''

    def makeReceiver(self):
        # receiver object is BlueDot object
        bd = None
        port = 1
        while not bd:
            try:
                ### print("Trying BlueDot on port", port)
                bd = BlueDot(port=port)
            except:
                port += 1
                bd = None
        ### print("New BlueDot on port", port)
        return BdReceiver(bd)

    def makeListener(self, connection):
        # make a BdListener object from connection info - which is the BlueDot object
        # so need a new one after this ...
        ### print("makeListener", "connection=", connection)
        listener = None
        if connection:
            try:
                listener = BdListener(
                    connection, controller=self.controller)  # need controller?
            except Exception as e:
                print(e)
                print(sys.exc_info())
            self.receiver = None
        ### print("makeListener returns", listener)
        return listener


class BdReceiver(CommsReceiver):

    def setup(self, setup):
        self.bd = setup
        return

    def accept(self):
        self.bd.wait_for_connection()
        return self.bd

    def close(self):
        ### print("BdReciever.close() stopping BlueDot!")
        self.bd.stop()
        return


class BdListener(CommsListener):
    '''
    Listener is a threaded device to listen for messages.

    Listener is started with a receiver 
    (BlueDot object that has been connected) 
    and a defined server object.
    '''

    def makeReceiver(self, connection):
        # turn a connection (a BlueDot) into the receiver
        return BdMessageReceiver(setup=connection)

    def startup(self, connectionId, controller):
        ### print("BdListener.startup(): connectionId=", connectionId, "controller=", controller)
        if connectionId == 0:
            # navigate - green square
            ### print("BdListener.startup(): green square")
            self.receiver.bd.square = True
            self.receiver.bd.color = "green"
        else:
            # targetting gun number ...
            colour = ("green", "red", "orange", "yellow")[connectionId]
            ### print(f"BdListener.startup(): {colour} square")
            self.receiver.bd.square = False
            self.receiver.bd.color = colour
        ### print("BdListener.startup(): setting callbacks")
        self.receiver.bd.when_disconnected = self.disconnect
        self.receiver.bd.when_double_pressed = self.double
        self.receiver.bd.when_pressed = self.press
        self.receiver.bd.when_released = self.lift
        self.receiver.bd.when_moved = self.move
        ### print("BdListener.startup(): starting super()")
        super().startup(connectionId, controller)
        return

    def run(self):
        # print("BdListener.run()")
        while self.ok:
            try:
                # something to wait for ...
                ### print("Waiting for press")
                self.receiver.bd.wait_for_press()  # actually processed by callbacks
                ### print("Waiting for release")
                self.receiver.bd.wait_for_release()  # actually processed by callbacks
            except Exception as e:
                print("BdListener exception:", e)
                self.ok = False
        ### print("Listener stopped")
        if self.controller:
            self.controller.disconnected(self.connectionId)
        # if self.server:
        # self.server.disconnected(self.connectionId)
        return

    def disconnect(self):
        self.ok = false
        return

    def double(self, pos):
        x, y = pos.x, pos.y
        self.controller.double(self.connectionId, x, y)
        return

    def press(self, pos):
        x, y = pos.x, pos.y
        self.controller.press(self.connectionId, x, y)
        return

    def lift(self, pos):
        x, y = pos.x, pos.y
        self.controller.lift(self.connectionId, x, y)
        return

    def move(self, pos):
        x, y = pos.x, pos.y
        self.controller.move(self.connectionId, x, y)
        return


class BdMessageReceiver(MessageReceiver):

    def setup(self, setup):
        self.bd = setup
        return

    def getMessage(self):
        return None

    def close(self):
        ### print("BdMessageReciever.close() stopping BlueDot!")
        self.bd.stop()
        return


# no class BdConnection()


if __name__ == '__main__':
    # for testing
    print("server1:")
    server1 = CommsServer(None)
    print("controller:")
    controller = CommsController(server=server1)
    print("server2:")
    server2 = CommsServer(None)
    controller.addServer(server2)
