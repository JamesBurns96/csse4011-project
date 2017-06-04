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




def udpListenThread():

  while isRunning:
    
    try:
      data, addr = sock.recvfrom( 1024 )
      #print "hi", data
      
      startByte = struct.unpack("B", data[0])      
      ID = struct.unpack("B", data[1])
      ##timeStamp = struct.unpack("H", data[2:3])   
      accX = struct.unpack("B", data[4])
      accY = struct.unpack("B", data[5])
      accZ = struct.unpack("B", data[5])
      gyrX = struct.unpack("B", data[6])
      gyrY = struct.unpack("B", data[7])
      gyrZ = struct.unpack("B", data[8])
      stopByte = struct.unpack("B", data[9])
      print " ID", ID[0], " AccX:", accX[0], " AccY:", accY[0], " AccZ:", accZ[0], " gyrX:", gyrX[0], " gyrY:", gyrY[0], " gyrZ:", gyrZ[0]

      #write to csv file
      #nodeOneWriter.writerow(['Span'], ['dan'])


      #timestamp = (struct.unpack("I", data[0:4]))[0]
      #utc = datetime.datetime.fromtimestamp(timestamp)
      #print "Reply from:", addr[0], "UTC[s]:", timestamp, "Localtime:", utc.strftime("%Y-%m-%d %H:%M:%S")

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
  




