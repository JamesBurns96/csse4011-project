#!/usr/bin/python

import socket
import time
import datetime
import struct
import StringIO
from threading import Thread
import sys
import csv


UDP_TIMESYNC_PORT = 4003 # node listens for timesync packets on port 4003
UDP_REPLY_PORT = 7005 # node listens for reply packets on port 7005

isRunning = True

sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, 0)
sock.bind(('',7005))


#open CSV writer object
nodeOneFile = open('nodeOne.csv', "w")
nodeOneWriter = csv.writer(nodeOneFile, delimiter = ',')

samplesPerPacket = 50
packetOffset = 3

x = 0
firstPacketNumber = 0
secondPacketNumber = 0


def udpListenThread():

  while isRunning:
    
    try:
      data, addr = sock.recvfrom( 1024 )
      #print "hi", data
            
      startByte = struct.unpack("B", data[0])      
      ID = struct.unpack("B", data[1])
      packetNumber= struct.unpack("B", data[2])
      timeStamp = struct.unpack("B", data[3])
      timeStamp2 = struct.unpack("B", data[4])

      #check for dropped packets and alert
      #if (ID[0] == 0) :
        #if (packetNumber != firstPacketNumber) :
          #print "*****************PACKET LOST!!!!!*****************"
        #firstPacketNumber = packetNumber + 1

      #if (ID[0] == 1) :
        #if (packetNumber != secondPacketNumber) :
          #print "*****************PACKET LOST!!!!!*****************"
        #secondPacketNumber = packetNumber + 1
      

      #bug, gyro values are wrong, not sure why
      print "-------------------------------NEW PACKET----------------------------"
      print " ID", ID[0], " samplesSinceSync", timeStamp[0]+255*timeStamp2[0], "packetNumber:", packetNumber[0]
      x = 0
      while (x < samplesPerPacket):
        accX = struct.unpack("b", data[x*6 + 7])
        accY = struct.unpack("b", data[x*6 + 8])
        accZ = struct.unpack("b", data[x*6 + 9])
        gyrX = struct.unpack("b", data[x*6 + 10])
        gyrY = struct.unpack("b", data[x*6 + 11])
        gyrZ = struct.unpack("b", data[x*6 + 12])
        print "sampNo:", x, "AccX:", accX[0], " AccY:", accY[0], " AccZ:", accZ[0], " gyrX:", gyrX[0], " gyrY:", gyrY[0], " gyrZ:", gyrZ[0]
        x = x + 1

      #write to csv file
      #nodeOneWriter.writerow(['Span'], ['dan'])

    except struct.error:
      pass
    except sock.timeout:
      pass
    
def udpSendThread():

  while isRunning:
    timestamp = int(time.time())
    print "Sending timesync packet with UTC[s]:", timestamp, "Localtime:", time.strftime("%Y-%m-%d %H:%M:%S")

    # send UDP packet to nodes - Replace addresses with your sensortag routing address (e.g. aaaa::<sensortag ID>)
    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:c68:2d83", UDP_TIMESYNC_PORT))
    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:7b5:5c80", UDP_TIMESYNC_PORT))
    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:7b5:6d01", UDP_TIMESYNC_PORT))
    
    # sleep for 10 seconds
    time.sleep(10)


# start UDP listener as a thread
t1 = Thread(target=udpListenThread)
t1.start()
print "Listening for incoming packets on UDP port", UDP_REPLY_PORT

time.sleep(1)

# start UDP timesync sender as a thread
t2 = Thread(target=udpSendThread)
t2.start()

print "Sending timesync packets on UDP port", UDP_TIMESYNC_PORT
print "Exit application by pressing (CTRL-C)"

try:
  while True:
    # wait for application to finish (ctrl-c)
    time.sleep(1)
except KeyboardInterrupt:
  print "Keyboard interrupt received. Exiting."
  isRunning = False  
  sock.close()
  raise SystemExit
  




