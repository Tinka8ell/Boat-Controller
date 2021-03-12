# !/usr/bin/python3
"""
CommsController - base classed for a linked controller
Overview:
Controller  - does what it says on the tin.  Accepts attaching of Servers
            - Allocates listeners to ID's, where 0 is the navigator, and the rest (>0) are targeting
Servers     - Once accepted, wait for connections.  And creates them into listeners and passes them to the controller.
Listener    - Listen for messages from clients and translates them into actions on the controller.
Message     - Specific to client, but interpreted as action (press, move, lift, double) and location
"""

import math
from threading import Thread, enumerate
from time import sleep


def dp2(number):
    return format(number, "03.2f")


def xy2ra(x, y):
    '''
    Convert (x, y) to (r, a).

    -1.0 <= x, y <= 1.0 are cartesian coordinates.
    Convert to r (radius) and a (angle), where 0.0 <= r, a <= 1.0
    So a is a fraction of the whole circle, and r is distance from the center, capped at 1.0
    '''
    a = 0
    r = math.sqrt(x * x + y * y)
    if r > 1.0:
        r = 1.0
    if r > 0.1:  # angle only relevant if a distance from the center!
        ax, ay = abs(a), abs(y)
        sx = sy = 1  # +ve
        if x < 0:
            sx = -1
        if y < 0:
            sy = -1
        ss = sx * sy
        # to avoid divide by zero and rediculously big numbers ...
        if ax > ay:
            f = y / x
            aTanXY = math.atan(f) / math.pi
            aTanXY = ss * (1 - aTanXY)
        else:
            f = x / y
            aTanXY = math.atan(f) / math.pi
        h = ((1 - sx) + (1 - ss)) / 2  # I call it the half number
        a = (h + aTanXY) / 2
    return r, a


class CommsController():
    '''
    This is a server for controller links.

    CommsController accepts registations, either on construction
    or after (addServer()) from CommsServers.  They recieve a call back
    (startup()) passing back the controller reference and the server ID.
    It will wait for connections from those servers, which will call back
    (connected()) and wait for a reaponse.  The controller will either accept
    by calling the server's startup() passing a connection ID, or rejecting
    by calling the server's shutdown().
    Once connected, the server can call the response methods.
    Boats must support:
       getNavigation() - returns navigation object, or None
       getTargeting() - returns targeting object, or None
       connected() - or delegats to navigation / targeting object
       disconnected() - or delegats to navigation / targeting object
       navigate() - or delegats to navigation / targeting object
       double() - or delegats to navigation / targeting object
    '''

    def __init__(self, server=None, boat=None):
        '''
        # debug info:
        print("CommsController:")
        print("server=", server)
        print("boat=", boat)
        print("navigation=", navigation)
        print("targeting=", targeting)
        '''
        self.servers = []
        if server:
            self.addServer(server)
        self.listeners = []
        # uncomment the following line to stop navigation connection ...
        # self.listeners.append(CommsListener(None)) # temp fix to get to targets
        self.targets = 0
        self.addBoat(boat)
        return

    def addBoat(self, boat):
        self.boat = boat
        # need to know that number and layout of guns
        # for now assume 0 to 3 guns, either linear or 
        # if 3 and front to "same" then they are port and starboard
        guns = []
        for gun in boat.guns:
            guns.append(gun.range)  # steps, start, stop, middle
        # if 1 gun - back
        # if 2 guns - back and middle
        self.square = (len(guns) > 3)  # if at least 4
        self.triangle = False
        if not self.square and len(guns) > 2:  # so only 3
            left = guns[1][2] - guns[1][1]  # stop - start = range
            right = guns[2][2] - guns[2][1]  # stop - start = range
            if left == right:  # same size
                self.triangle = True
        # if 3 guns - back and middle and front, unless triangle:
        #           - back and port and starboard
        self.guns = guns
        self.boat.centerGuns()
        return

    def shutdown(self):
        # try and close neatly ...
        for server in self.servers:
            server.shutdown()
        self.servers = []
        for connectionId in range(len(self.listeners)):
            if self.listeners[connectionId]:
                self.disconnect(connectionId)
        self.listeners = []
        print("Threads:", enumerate())
        return

    #
    # Internal (server) methods
    #

    def stopping(self, serverID):
        # handle server stopping?
        return

    def addServer(self, server):
        serverId = len(self.servers)
        self.servers.append(server)
        server.startup(serverId, self)
        return

    #
    # External (connection) methods
    #

    def connected(self, listener):
        # server calls this with new listener
        # calls back to listener with id
        connectionId = -1
        if None in self.listeners:
            connectionId = self.listeners.index(None)
            self.listeners[connectionId] = (listener)
        else:
            connectionId = len(self.listeners)
            self.listeners.append(listener)
        ### print("connected, connectionId=", connectionId)
        # inform server that connection accpted
        listener.startup(connectionId, self)
        if connectionId > 0:  # targetting
            self.targets += 1
        return

    def disconnect(self, connectionId):
        # request from boat to sever the connection
        # calls listern to shut it down
        ### print("disconnect", connectionId)
        self.disconnected(connectionId)
        return

    def disconnected(self, connectionId):
        # listener calls here when connection is broken to release it
        # calls back to shut down the listener
        # also lets the boat know
        ### print("disconnected", connectionId)
        listener = self.listeners[connectionId]
        if listener:
            self.listeners[connectionId] = None  # remove it
            listener.shutdown()
            if connectionId > 0:  # targetting
                self.targets -= 1
        return

    def press(self, connectionId, x, y):
        # called by a listener that recieves a press at a position
        ### print("press", connectionId, (dp2(x), dp2(y)))
        self.navigate(connectionId, x, y)
        return

    def move(self, connectionId, x, y):
        # called by a listener that recieves a move to a position
        ### print("move", connectionId, (dp2(x), dp2(y)))
        self.navigate(connectionId, x, y)
        return

    def lift(self, connectionId, x, y):
        # called by a listener that recieves a lift from a position
        ### print("lift", connectionId, (dp2(x), dp2(y)))
        if connectionId == 0:  # navigate - stop when lift
            self.navigate(connectionId, 0, 0)  # all stop on lift!
        else:  # tagetting stops where you leave it
            self.navigate(connectionId, x, y)  # just the final move location
        return

    def navigate(self, connectionId, x, y):
        ### print("CommsController.navigate: connectionId =", connectionId, 
        ###       "(x, y) =", (dp2(x), dp2(y)))
        # default action is to call the boat's navigation with ID and position
        if connectionId > 0:
            if self.boat:
                self.target(connectionId, x, y)
        else:
            if self.boat:
                self.boat.navigate(x, y)
        return

    def target(self, connectionId, x, y):
        radius, angle = xy2ra(x, y)
        # print("CommsController.target: connectionId =", connectionId, "angle =", dp2(angle), "radius=", dp2(radius))
        # print("self.targets =", self.targets, "self.triangle =", self.triangle)
        if self.targets == 1:
            # one to do all guns
            if self.square:  # split four ways
                print("square: angle =", dp2(angle), "radius=", dp2(radius))
                if radius > 0.3:  # only react if outside the middle circle
                    # divide in to four quadrants
                    # allow a separation of 5% of section
                    gun = 3  # starboard
                    size = 0.25
                    a = angle  # map onto quarter
                    print("try first: angle =", dp2(
                        angle), "a>.25", angle > 0.25)
                    if angle > 0.25:  # not 1st quarter
                        print("not first: angle =", dp2(
                            angle), "a<.5", angle < 0.5)
                        gun = 1  # rear starboard
                        if angle > 0.5:  # not 2nd quarter
                            print("not second: angle =", dp2(
                                angle), "a<.75", angle < 0.75)
                            a = 1 - angle  # map onto other half
                            gun = 0  # back port
                            if angle > 0.75:  # not 3rd quarter
                                print("not third")
                                gun = 2  # port
                    print("square: a=", dp2(a), "abs(a)=", dp2(abs(a)),
                          "size=", size, "new a=", dp2(a - size * a / abs(a)))
                    if abs(a) > size:
                        # map angle on to quarter circle
                        a += -size * a / abs(a)
                    # abs((2 * a - size) / size) # distance from center of range (size)
                    d = abs((2 * a / size) - 1)
                    print("square: gun=", gun, "size=",
                          size, "a=", dp2(a), "d=", dp2(d))
                    if d <= 0.9:  # lop off biggest 10% left or right to give separation from other sections
                        # express a as fraction of 5% - 95% of the size
                        f = ((a - (0.05 * size)) / 0.9) / size
                        steps, start, stop, middle = self.guns[gun]
                        # steps using fraction of full steps
                        s = int(f * steps)
                        value = start + s   # convert to step value
                        print("square: tagetting gun=", gun, "value=", value)
                        self.boat.target(gun, value)
            elif self.triangle:  # split three ways
                if radius > 0.3:  # only react if outside the middle circle
                    # divide in to front quadrants and back semicircle
                    # allow a separation of 5% of section
                    gun = 2  # starboard
                    size = 0.25
                    a = angle  # map onto quarter
                    if angle > 0.25:  # not 1st quarter
                        gun = 1  # port
                        a = 1 - angle  # map onto quarter
                        if angle < 0.75:  # not 4th quarter
                            gun = 0  # back
                            size = 0.5
                            a = angle - 0.25  # map angle on to semicircle
                    # abs((2 * a - size) / size) # distance from center of range (size)
                    d = abs((2 * a / size) - 1)
                    print("triangle: gun=", gun, "size=",
                          size, "a=", dp2(a), "d=", dp2(d))
                    if d <= 0.9:  # lop off biggest 10% left or right to give separation from other sections
                        # express a as fraction of 5% - 95% of the size
                        f = ((a - (0.05 * size)) / 0.9) / size
                        steps, start, stop, middle = self.guns[gun]
                        # steps using fraction of full steps
                        s = int(f * steps)
                        value = start + s   # convert to step value
                        self.boat.target(gun, value)
            else:  # split into concentric circles
                # 0 to number of guns+1
                gun = math.ceil(radius * (len(self.guns) + 1))
                ### print("concentric: gun=", gun, "angle=", dp2(angle))
                if gun > 1:  # skip middle bit
                    self.boat.target(gun - 2, angle)
        elif self.targets == 2:
            # more dificult, 2 to split over all
            gun = 0
            for i in range(1, connectionId):
                if self.listeners[i]:
                    gun += 1  # count up active listeners to find associated gun number
            gun -= 1
            # gun 0 = back, 1 = port and 2 = starboard
            steps, start, stop, middle = self.guns[gun]
            pass  # not written yet
        else:
            # one to one maping
            if radius > 0.3:  # only react if outside the midle circle
                gun = 0
                for i in range(1, connectionId):
                    if self.listeners[i]:
                        gun += 1  # count up active listeners to find associated gun number
                gun -= 1
                # gun 0 = back, 1 = port and 2 = starboard
                ### print("1-1: gun=", gun, "angle=", dp2(angle))
                self.boat.target(connectionId - 1, angle)
        return

    def double(self, connectionId, x, y):
        # called by a listener that recieves a double-click at a position
        # allow doble click to swap listener from Navigate to Target and back
        listener = self.listeners[connectionId]
        newId = 1 - connectionId  # swap to the other
        if connectionId == 0:  # navigate
            if len(self.listeners) < 2:
                # prettend we connected as second time
                self.connected(listener)
                newId = -1  # already given newId
        if newId >= 0:
            listener.startup(newId, self)
        return


class CommsServer(Thread):
    '''
    This is a server generatine listeners from connections.

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

    def __init__(self, setup=None):
        ### print("CommsServer", "setup=", setup)
        Thread.__init__(self)
        self.setup = setup
        self.receiver = self.makeReceiver()  # for receiving connections
        self.serverId = None
        self.controller = None
        self.connections = {}
        return

    def shutdown(self):
        ### print("shutdown called")
        self.ok = False
        while len(self.connections.keys()) > 0:
            connection = self.connections.keys(0)
            connection.shutdown()
            self.connections.remove(connection)
        if self.receiver:
            self.receiver.close()
            self.receiver = None
        return

    def startup(self, serverId, controller):
        ### print("CommsServer.startup called", "serverId=", serverId, 
        ###       "controller=", controller)
        self.serverId, self.controller = serverId, controller
        if self.receiver:
            self.start()
        else:
            self.ok = False
        return self.ok

    def run(self):
        self.ok = True
        loop = 0
        ### print(f"CommsServer.run({loop}) Starting server")
        while self.ok:
            try:
                loop += 1
                # wait for connection on the receiver
                ### print(f"CommsServer.run({loop}) Waiting for connection")
                connection = self.receiver.accept()
                # convert connection into a listener
                ### print(f"CommsServer.run({loop}) Connection received, making Listener ...")
                listener = self.makeListener(connection)
                # let the controller know and start it listening
                ### print(f"CommsServer.run({loop}) Controller given Listener ...")
                self.controller.connected(listener)
                # some receivers need to be recrated after a connection
                if not self.receiver:
                    ### print(f"CommsServer.run({loop}) Making new receiver ...")
                    self.receiver = self.makeReceiver()
            except Exception as e:
                print(f"CommsServer.run({loop}) conection exception:", e)
                self.ok = False
        ### print(f"CommsServer.run{loop} Server stopped")
        self.controller.stopping(self.serverId)
        return

    '''
    These methods must be overwritten
    '''

    def makeReceiver(self):
        # make a receiver object using self.setup
        # print("CommServer.makeReceiver()")
        return CommsReceiver(self.setup)

    def makeListener(self, connection):
        # make a CommsListener object from connection info
        # this can also reset self.receiver to cause a new one to start
        listener = None
        if connection:
            # do we need controller here?
            listener = CommsListener(connection, controller=self.controller)
        return listener


class CommsReceiver():

    def __init__(self, setup=None):
        # print("CommsReceiver")
        if setup:
            self.setup(setup)
        return

    def setup(self, setup):
        return

    def accept(self):
        # wait for a connection and return it
        return None

    def close(self):
        ### print("ConnsReciever.close() does nothing!")
        return


class CommsListener(Thread):
    '''
    Listener is a threaded device to listen for messages.

    Listener is started with a receiver and a defined controller object.
    '''

    def __init__(self, connection, controller=None):
        ### print("CommsListener", "connection=", connection, 
        ###       "controller=", controller)
        Thread.__init__(self)
        self.receiver = None
        if connection:
            self.receiver = self.makeReceiver(connection)
        self.controller = controller
        return

    def shutdown(self):
        ### print("shutdown called")
        self.ok = False
        if self.receiver:
            self.receiver.close()
            self.receiver = None
        return

    def startup(self, connectionId, controller):
        ### print("CommsListener.startup() connectionId=", connectionId, 
        ###       "controller=", controller)
        self.connectionId = connectionId
        self.controller = controller
        if self.receiver:
            self.ok = True
            if not self.is_alive():  # not yet started ...
                self.start()  # start it
        else:
            self.ok = False
        return self.ok

    def run(self):
        # print("CommsListener.run()")
        while self.ok:
            try:
                ### print("Waiting for message")
                message = self.receiver.getMessage()
                ### print("Message received, trying to execute ...")
                if message:
                    self.execute(message)
                else:
                    self.ok = False
            except Exception as e:
                print("CommsListener exception:", e)
                self.ok = False
        ### print("Listener stopped")
        if self.controller:
            self.controller.disconnected(self.connectionId)
        return

    #
    # these should be overridden
    #

    def makeReceiver(self, connection):
        # turn a connection into the receiver
        return MessageReceiver(setup=connection)

    def execute(self, message):
        # should be overridden
        x = 1
        y = -1
        if message[0].lower() == "p":
            self.controller.press(self.connectionId, x, y)
        elif message[0].lower() == "m":
            self.controller.move(self.connectionId, x, y)
        elif message[0].lower() == "l":
            self.controller.lift(self.connectionId, x, y)
        elif message[0].lower() == "d":
            self.controller.double(self.connectionId, x, y)
        elif message[0].lower() == "c":
            self.receiver.close()
        elif message[0].lower() == "e":
            raise Exception("Disconnected by exception")
        return


class MessageReceiver():

    def __init__(self, setup=None):
        # print("CommsReceiver")
        if setup:
            self.setup(setup)
        return

    def setup(self, setup):
        return

    def getMessage(self):
        # wait for a message and return it
        return None

    def close(self):
        ### print("MessageReciever.close() does nothing!")
        return


class CommsConnection():

    def accept(self):
        return CommsConnection()

    def close(self):
        ### print("CommsConnection.close() does nothing!")
        return


if __name__ == '__main__':
    # for testing
    '''
    ### print("server1:")
    server1 = CommsServer(None)
    ### print("controller:")
    controller = CommsController(server=server1)
    ### print("server2:")
    server2 = CommsServer(None)
    controller.addServer(server2)
    '''
    x, y = 0.01, 1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = 0.5, 1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = 1, 1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = 1, .5
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = 1, .01
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = 1, -.01
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = 1, -.5
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = 1, -1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = .5, -1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = 0.01, -1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -0.01, -1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -0.5, -1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -1, -1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -1, -.5
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -1, -0.01
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -1, 0.01
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -1, .5
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -1, 1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -.5, 1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
    x, y = -0.01, 1
    r, a = xy2ra(x, y)
    print((dp2(x), dp2(y)), dp2(r), dp2(a))
