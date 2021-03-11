#!/usr/bin/env python
# Turret.py - implemnet moving the turrets as steppers on the MCP23017 I2C Port Expander 

from threading import Thread
from queue import Queue, Empty 
from smbus import SMBus
from time import sleep

mcp = [None, None] # singletons


class Turret(): 
   '''
   Turret(size, address)
   Where "size" = max number of cycles of turning:
      size > 0: turret turns from 0 to size cycles
      size < 0: turret turns from size to -size cycles for center mounted turrets.
         Note that reversing the 4 pins will revers the direction of turn.
         When created each turret  will assume it is in position 0.
   and the "address" of the turret is (A, B, C):
      A = 0 for default expander, and 1 second (assuming A0,A1,A2 set to 1, 0, 0)
      B = 0 for port A pins and 1 for port B
      C = 0 for 1st 4 (0-3) pins and 1 for 2nd (4-7) pins
   Also need to define whether we are using whole or half phase cycles.
   Also need to define how quick we will turn.
   Both these may be defined at a lower level.

   Posible methods:
      turret.set(x) will move the turret to position x,
         where 0 <= x <= size, or size <= x <= -size.
         Moves outside of the range will be OutOfRangeErrors.
      turret.reset() will effectively try to reset the turret
         by moving too far below 0,
         back to full sweep
         and then back to 0.
         So for size > 0 it will be the equivalent of:
            turret.set(-size), set internal pos to 0, 
            turret.set(size)
            turret.set(0)
            This assumes a hard stop below 0'th position!
         And for size < 0:
            turret.set(size*2), set internal pos = size,
            turret.set(-size),
            turret.set(0)
            This assumes a hard stop below size'th position and above -size'th position.

   Internally, each turret will share one of 2 (or 4) MCP23017 objects
   for each expander (and possibly port) that will actually send
   the appropriate signals to move the relevant turret.
   '''

   # class fields
   DEVICE = 0x20 # Base device address (A0-A2)
   IOCON = 0x0A  # Configuration register - set to 0x02 so no interrupts and sequential ports
   IODIRA = 0x00 # Pin direction register
   IODIRB = 0x01 # Pin direction register
   OLATA  = 0x14 # Register for outputs
   OLATB  = 0x15 # Register for outputs
   PHASES = (0b0001,
             0b0011,
             0b0010,
             0b0110,
             0b0100,
             0b1100,
             0b1000,
             0b1001
             )
   
   PHASES = (0b0001,
             0b0010,
             0b0100,
             0b1000
             )

   def __init__(self, size, address=(0, 0, 0)):
      expander, port, nibble = address
      if not mcp[expander]:
         mcp[expander] = MCP23017(expander)
      self.expander = mcp[expander]
      # port number is 0 to 3 based on address port (A or B) and nibbler (lsn or msn)
      self.port = port # * 2 + nibble
      
      # set up range
      self.min = 0
      self.max = size
      if size < 0:
         self.min = size
         self.max = -size
      self.position = 0
      self.mid = 0 # always 0 is default position
      self.range = (self.max - self.min + 1, self.min, self.max, self.mid)
      return

   def requestStop(self):
      '''
      Set Turret back to zero and request stop.
      '''
      self.set(0)
      self.expander.requestStop()
      return

   def waitForStop(self):
      '''
      Wait for the underlying MCP23017 to shutdown
      '''
      self.expander.waitForStop()
      return

   def set(self, pos):
      '''
      Set Turret to pos.
      '''
      if pos < self.min:
         raise ValueError("Less than minimum value") 
      if pos > self.max:
         raise ValueError("Greater than maximum value") 
      print("Turret moving from", self.position, "to", pos)
      self.expander.addCycles(self.port, self.position, pos)
      self.position = pos
      return
   
   def reset(self):
      '''
      Reset Turret to 0 after swiping through min and max.
      '''
      self.expander.addCycles(self.port, self.max, self.min)
      self.expander.addCycles(self.port, self.min, self.max)
      self.expander.addCycles(self.port, self.max, 0)
      self.position = 0
      return

   
   '''
   To test the expander on rev 2 pi's (most of them are now rev2):
   sudo i2cdetect -y 1 
       0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
   00:        -- -- -- -- -- -- -- -- -- -- -- -- --
   10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
   20: 20 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
   30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
   40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
   50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
   60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
   70: -- -- -- -- -- -- -- --
   
   # SMBus set up data: 
   # bus = smbus.SMBus(0)  # Rev 1 Pi uses 0
   bus = smbus.SMBus(1) # Rev 2 Pi uses 1
   DEVICE = 0x20 # Device address (A0-A2)
   IOCON  = 0x0A # Configuration register - set to 0x02 so no interrupts and sequential ports
   IODIRA = 0x00 # Pin direction register
   OLATA  = 0x14 # Register for outputs
   GPIOA  = 0x12 # Register for inputs
   '''

class MCP23017:
   '''
   The "address" of MCP23017 is expander where
      expander = 0 for default expander, and 1 second (assuming A0,A1,A2 set to 1, 0, 0)
   Each MCP23017 expander can handle 4 steppers, so have a queue for each.
   Combine the data from all 4 queues into a single word for each cycle.
   '''

   # class fields
   DEVICE = 0x20 # Base device address (A0-A2)
   IOCON = 0x0A  # Configuration register - set to 0x02 so no interrupts and sequential ports
   IODIRA = 0x00 # Pin direction register
   IODIRB = 0x01 # Pin direction register or second byte of pin direction word
   OLATA  = 0x14 # Register for outputs
   OLATB  = 0x15 # Register for outputs or second byte of pin output word
   
   PHASES = (0b0001,
             0b0010,
             0b0100,
             0b1000
             )

   def __init__(self, address=0):
      self.device = address + self.DEVICE
      self.bus = SMBus(1)
      self.bus.write_byte_data(self.device, self.IOCON, 0x02)  # Update configuration register
      self.bus.write_word_data(self.device, self.IODIRA, 0) # make all pins of both ports output

      self.period = 0.05 # length of a cycle = 5 milliseconds - 4 may be possible 
      return

   def requestStop(self):
      self.stopping = True
      return

   def waitForStop(self):
      return

   def addCycles(self, port, start, stop):
      '''
      Add the cycles to move from start to stop for port.
      Request the cycles for the relevant port
      starting from the start position up to and inclucing the stop position.
      '''
      print("addCycles(", port, ",", start, ",", stop, ")")
      step = 1
      if start > stop:
         step = -1 # reverse the directrion
      for index in range(start, stop, step):
         phase = index % len(self.PHASES)
         word = self.PHASES[phase]
         word *= 257 # duplicate to msb nibble
         self.bus.write_byte_data(self.device, self.OLATA + port, word)
         sleep(self.period) # give steppers chance to react
      phase = stop % len(self.PHASES)
      word = self.PHASES[phase]
      word *= 257 # duplicate to msb nibble
      self.bus.write_byte_data(self.device, self.OLATA + port, word)
      sleep(self.period) # give steppers chance to react
      self.bus.write_byte_data(self.device, self.OLATA + port, 0) # switch off all coils
      return
      

class ThreadedMCP23017:
   '''
   The "address" of MCP23017 is expander where
      expander = 0 for default expander, and 1 second (assuming A0,A1,A2 set to 1, 0, 0)
   Each MCP23017 expander can handle 4 steppers, so have a queue for each.
   Combine the data from all 4 queues into a single word for each cycle.
   '''

   # class fields
   DEVICE = 0x20 # Base device address (A0-A2)
   IOCON = 0x0A  # Configuration register - set to 0x02 so no interrupts and sequential ports
   IODIRA = 0x00 # Pin direction register
   IODIRB = 0x01 # Pin direction register or second byte of pin direction word
   OLATA  = 0x14 # Register for outputs
   OLATB  = 0x15 # Register for outputs or second byte of pin output word
   
   PHASES = (0b0001,
             0b0010,
             0b0100,
             0b1000
             )

   def __init__(self, address=0):
      self.device = address + self.DEVICE
      self.bus = SMBus(1)
      self.bus.write_byte_data(self.device, self.IOCON, 0x02)  # Update configuration register
      self.bus.write_word_data(self.device, self.IODIRA, 0) # make all pins of both ports output

      self.queues = (Queue(),
                     Queue(),
                     Queue(),
                     Queue()
                     )
      self.period = 0.05 # length of a cycle = 5 milliseconds - 4 may be possible 
      self.thread = Thread(group=None, target=self.sendCycles)
      self.thread.start()
      return

   def sendCycles(self):
      self.running = True
      self.stopping = False
      self.last = 0
      while self.running:
         readSomething = False
         word = 0
         for port in range(len(self.queues)):
            phase = 0
            try:
               phase = self.queues[port].get_nowait()
               readSomething = True
            except Empty as e:
               # queue is empty
               phase = 0
            shifted = phase << (port * 4) # shift for relevant nibble / port
            word |= shifted    # or together
            # print("port", port, "phase", phase, "shifted", shifted, "word", word)
         if readSomething:
            # print("{0:b}".format(word))
            self.bus.write_word_data(self.device, self.OLATA, word)
            self.last = word
         else: # nothing to send
            if self.last != 0:
               # ensure we do not leave stepper active
               self.bus.write_word_data(self.device, self.OLATA, 0) # set all to off
               self.last = 0
            else:
               if self.stopping: # requested to shut down and nothing active
                  self.running = False
         sleep(self.period) # give steppers chance to react
      return

   def requestStop(self):
      self.stopping = True
      return

   def waitForStop(self):
      self.thread.join() # and wait for thread to stop
      return

   def addCycles(self, port, start, stop):
      '''
      Add the cycles to move from start to stop for port.
      Add the cycles to the queue forthe relevant port
      starting from the start position up to and inclucing the stop position.
      '''
      print("addCycles(",port, ",", start, ",", stop, ")")
      step = 1
      if start > stop:
         step = -1 # reverse the directrion
      for index in range(start, stop, step):
         phase = index % len(self.PHASES)
         self.queues[port].put_nowait(self.PHASES[phase])
      self.queues[port].put_nowait(self.PHASES[stop % len(self.PHASES)])
      return
      

def mainSingle():
   '''
   Main program function
   '''
   delay = 1
   print("starting at 0")
   maxi = 8
   test = Turret(maxi, (0, 0, 1)) # default port and nibble
   print("going to 2/3")
   test.set(int(maxi * 2 / 3))
   sleep(delay)
   print("going to 1/3")
   test.set(int(maxi / 3))
   sleep(delay)
   print("going to max")
   test.set(maxi)
   sleep(delay)
   print("going to min")
   test.set(0)
   sleep(delay)
   print("stepping to half")
   for i in range(int(maxi / 2)):
      print("stepping to", i + 1)
      test.set(i + 1)
      sleep(delay)
   print("going to max")
   test.set(maxi)
   sleep(delay)
   print("stopping")
   test.requestStop()
   test.waitForStop()
   print("stopped")
   return
      

def mainDouble():
   '''
   Main program function
   '''
   delay = 1
   maxi = 8
   test1 = Turret(maxi) # default port and nibble
   print("setting program on 1st")
   test1.set(int(maxi * 2 / 3))
   test1.set(int(maxi / 3))
   test1.set(maxi)
   test1.set(0)
   for i in range(int(maxi / 2)):
      test1.set(i + 1)
   test1.set(maxi)

   print("Wait a bit")
   sleep(delay)

   test2 = Turret(maxi, (0, 0, 1)) # default port and alternate nibble
   print("setting program on 2nd")
   test2.set(int(maxi * 2 / 3))
   test2.set(int(maxi / 3))
   test2.set(maxi)
   test2.set(0)
   for i in range(int(maxi / 2)):
      test2.set(i + 1)
   test2.set(maxi)

   print("request stopping for first")
   test1.requestStop()
   print("request stopping for second")
   test2.requestStop()

   print("Wait for 1st to stop")
   test1.waitForStop()
   print("Wait for 2nd to stop")
   test2.waitForStop()
   print("stopped")
   return


if __name__ == "__main__":
   mainSingle()
