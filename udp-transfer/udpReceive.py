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

NUMBER_OF_NODES = 6

isRunning = True

sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, 0)
#sock.setsockopt(AF_INET)
sock.bind(('',7005))


#open CSV writer object
nodeOneFile = open('nodeOne.csv', "w")
nodeOneWriter = csv.writer(nodeOneFile, delimiter = ',')

samplesPerPacket = 20
packetOffset = 3

x = 0
firstPacketNumber = 0
secondPacketNumber = 0

outputFiles = []
tagTypes = ["rigid", "acc", "brake", "clutch", "gear", "steer"]
#0 = rigid body, 1 = accelerometer, 2 = brake, 3 = clutch
#4 = gear stick. 5 = steering wheel

for i in range(NUMBER_OF_NODES):
  outputFiles.append(open(tagTypes[i] + '.csv', 'w+'))
  outputFiles[i].write("ID" + ',' + "timeStamp" + ','  + "packetNumber" + ',' + "sampleNumber" + ','
                          + "accX" + ',' + "accY" + ',' + "accZ" + ','
                          + "gyrX" + ',' + "gyrY" + ',' + "gyrZ" + '\n')
  


def udpListenThread():

  while isRunning:
    
    try:
      data, addr = sock.recvfrom( 1024 )
      #print "hi", data
            
      startByte = struct.unpack("B", data[0])      
      ID = struct.unpack("B", data[1])
      packetNumber= struct.unpack("H", data[2:4])      
      timeStamp = struct.unpack("I", data[4:8])

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
      utc = datetime.datetime.fromtimestamp(timeStamp[0])
      print "-------------------------------NEW PACKET----------------------------"
      print " ID", ID[0], " UTC(s)", timeStamp[0], "Localtime:", utc.strftime("%Y-%m-%d %H:%M:%S"), "packetNumber:", packetNumber[0]
      x = 0
      while (x < samplesPerPacket):
        accX = struct.unpack("b", data[x*6 + 8])
        accY = struct.unpack("b", data[x*6 + 9])
        accZ = struct.unpack("b", data[x*6 + 10])
        gyrX = struct.unpack("b", data[x*6 + 11])
        gyrY = struct.unpack("b", data[x*6 + 12])
        gyrZ = struct.unpack("b", data[x*6 + 13])
        #print "sampNo:", x, "AccX:", accX[0], " AccY:", accY[0], " AccZ:", accZ[0], " gyrX:", gyrX[0]*2*90/95, " gyrY:", gyrY[0]*2*90/95, " gyrZ:", gyrZ[0]*2*90/95
        x = x + 1

        if ID[0] < NUMBER_OF_NODES:  
          outputFiles[ID[0]].write(str(ID[0]) + ',' + str(timeStamp[0]) + ',' + str(packetNumber[0]) + ',' + str(x) + ','
                          + str(accX[0]) + ',' + str(accY[0]) + ',' + str(accZ[0]) + ','
                          + str(gyrX[0]*2*90/95) + ',' + str(gyrY[0]*2*90/95) + ',' + str(gyrZ[0]*2*90/95) + '\n')

    except struct.error:
      pass
    except socket.timeout:
      print "FUUUUKKK"
    
def udpSendThread():

  while isRunning:
    timestamp = int(time.time())
    print "Sending timesync packet with UTC[s]:", timestamp, "Localtime:", time.strftime("%Y-%m-%d %H:%M:%S")

    # send UDP packet to nodes - Replace addresses with your sensortag routing address (e.g. aaaa::<sensortag ID>)
    #sock.sendto(struct.pack("I", timestamp), ("ff02::1", UDP_TIMESYNC_PORT))

    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:c68:2d83", UDP_TIMESYNC_PORT))#ID 0
    time.sleep(1)
    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:7b5:5c80", UDP_TIMESYNC_PORT))#ID 1
    time.sleep(1)
    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:7b5:4e06", UDP_TIMESYNC_PORT))#ID 2
    time.sleep(1)
    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:799:af04", UDP_TIMESYNC_PORT))#ID 3
    time.sleep(1)
    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:799:dd80", UDP_TIMESYNC_PORT))#ID 4
    time.sleep(1)
    sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:7b5:5601", UDP_TIMESYNC_PORT))#ID 5

    #sock.sendto(struct.pack("I", timestamp), ("aaaa::212:4b00:7b5:6d01", UDP_TIMESYNC_PORT))#ID 5

    
    # sleep for 10 seconds
    time.sleep(5)


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
  for i in range(NUMBER_OF_NODES):
    outputFiles[i].close() 
  sock.close()
  
  raise SystemExit
  




