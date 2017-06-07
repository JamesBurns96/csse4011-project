#!/usr/bin/python

import socket
import time
import datetime
import struct
import StringIO
from threading import Thread
import sys
import csv

import os
import random
import wx
import serial
import threading
import json
import time

import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import numpy as np
import pylab
import math

#runtime variables
UDP_TIMESYNC_PORT = 4003 # node listens for timesync packets on port 4003
UDP_REPLY_PORT = 7005 # node listens for reply packets on port 7005
NUMBER_OF_NODES = 6

samplesPerPacket = 20
packetOffset = 3
x = 0
firstPacketNumber = 0
secondPacketNumber = 0


class UDPComs(object):
    """ The main frame of the application
    """
    title = 'Demo'

    def __init__(self, graphFrame):      
      #generate socket connection
      self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, 0)
      self.sock.bind(('',7005))
      #self.sock.settimeout(2)
      self.isRunning = True

      #CSV logging variables
      self.outputFiles = []
      self.tagTypes = ["rigid", "acc", "brake", "clutch", "gear", "steer"]
      #tags ID correspond to device locations as follows
      #0 = rigid body, 1 = accelerometer, 2 = brake, 3 = clutch
      #4 = gear stick. 5 = steering wheel

      for i in range(NUMBER_OF_NODES):
        self.outputFiles.append(open(self.tagTypes[i] + '.csv', 'w+'))
        self.outputFiles[i].write("ID" + ',' + "timeStamp" + ','  + "packetNumber" + ',' + "sampleNumber" + ','
                                + "accX" + ',' + "accY" + ',' + "accZ" + ','
                                + "gyrX" + ',' + "gyrY" + ',' + "gyrZ" + '\n')

      # start UDP listener as a thread
      t1 = Thread(target=self.udpListenThread)
      t1.start()
      print "Listening for incoming packets on UDP port", UDP_REPLY_PORT      

      # start UDP timesync sender as a thread
      t2 = Thread(target=self.udpSendThread)
      t2.start()

      print "Sending timesync packets on UDP port", UDP_TIMESYNC_PORT
      print "Exit application by pressing (CTRL-C)"                              


    def udpListenThread(self):
      while self.isRunning:        
        try:
          data, addr = self.sock.recvfrom(1024)
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

          #*******************************************************TO DO********************************************************
          #look in notebook          

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
              self.outputFiles[ID[0]].write(str(ID[0]) + ',' + str(timeStamp[0]) + ',' + str(packetNumber[0]) + ',' + str(x) + ','
                              + str(accX[0]) + ',' + str(accY[0]) + ',' + str(accZ[0]) + ','
                              + str(gyrX[0]*2*90/95) + ',' + str(gyrY[0]*2*90/95) + ',' + str(gyrZ[0]*2*90/95) + '\n')

        except socket.timeout:
          print "FUUUk"
          continue
      for f in self.outputFiles:
        f.close() 

      self.sock.close()

    def udpSendThread(self):
      while self.isRunning:
        timestamp = int(time.time())
        print "Sending timesync packet with UTC[s]:", timestamp, "Localtime:", time.strftime("%Y-%m-%d %H:%M:%S")

        # send UDP packet to nodes - Replace addresses with your sensortag routing address (e.g. aaaa::<sensortag ID>)
        for ip in ["aaaa::212:4b00:c68:2d83", "aaaa::212:4b00:7b5:5c80", 
                  "aaaa::212:4b00:7b5:4e06", "aaaa::212:4b00:799:af04", 
                  "aaaa::212:4b00:799:dd80", "aaaa::212:4b00:7b5:5601"]:
          self.sock.sendto(struct.pack("I", timestamp), (ip, UDP_TIMESYNC_PORT))#ID n
          time.sleep(1)

#TODO fuck this off
        # sleep for 5 seconds
        time.sleep(5) 

    def close(self):
      
        print "Keyboard interrupt received. Exiting."
        self.isRunning = False 
        
        
          






####################################graphing###########################
class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Demo'
    
    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)
        
    # handle window close event    
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        # set data source
        self.source = UDPComs(self)
        
        self.data_temp = []
        self.data_pres = []
        self.data_alt = []
        
        self.create_main_panel()
        
        

    def create_main_panel(self):

        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigureCanvasWxAgg(self.panel, -1, self.fig)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)        
        
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)
   

    def init_plot(self):
        self.fig = Figure((6.0, 3.0), dpi=100)

        self.axes_temp = self.fig.add_subplot(3,1,1)
        self.axes_temp.set_axis_bgcolor('black')
        self.axes_temp.set_title('Temperature', size=12)

        pylab.setp(self.axes_temp.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes_temp.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        self.plot_data_temp = self.axes_temp.plot(self.data_temp, linewidth=1, color=(1, 1, 0))[0]


        self.axes_pres = self.fig.add_subplot(3,1,2)
        self.axes_pres.set_axis_bgcolor('black')
        self.axes_pres.set_title('Pressure', size=12)
        
        pylab.setp(self.axes_pres.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes_pres.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        self.plot_data_pres = self.axes_pres.plot(self.data_pres, linewidth=1, color=(1, 1, 0))[0]

        self.axes_alt = self.fig.add_subplot(3,1,3)
        self.axes_alt.set_axis_bgcolor('black')
        self.axes_alt.set_title('Altitude', size=12)

        pylab.setp(self.axes_alt.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes_alt.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        self.plot_data_alt = self.axes_alt.plot(self.data_alt, linewidth=1, color=(1, 1, 0))[0]




    def update_data(self, sensor, pres, alt):
    
       self.data_temp.append(sensor)
       self.data_pres.append(pres)
       self.data_alt.append(alt)


    def draw_plot(self):
        """ Redraws the plot
        """

        xmax = len(self.data_temp) if len(self.data_temp) > 50 else 50
        xmin = xmax - 50

        ymin = round(min(self.data_temp), 0) - 1
        ymax = round(max(self.data_temp), 0) + 1
       
        self.axes_temp.set_xbound(lower=xmin, upper=xmax)
        self.axes_temp.set_ybound(lower=ymin, upper=ymax)
        
        self.axes_temp.grid(True, color='gray')
        pylab.setp(self.axes_temp.get_xticklabels(), visible=True)
       
        self.plot_data_temp.set_xdata(np.arange(len(self.data_temp)))
        self.plot_data_temp.set_ydata(np.array(self.data_temp))




        xmax = len(self.data_pres) if len(self.data_pres) > 50 else 50
        xmin = xmax - 50

        ymin = round(min(self.data_pres), 0) - 1
        ymax = round(max(self.data_pres), 0) + 1
       
        self.axes_pres.set_xbound(lower=xmin, upper=xmax)
        self.axes_pres.set_ybound(lower=ymin, upper=ymax)
        
        self.axes_pres.grid(True, color='gray')
        pylab.setp(self.axes_pres.get_xticklabels(), visible=True)
       
        self.plot_data_pres.set_xdata(np.arange(len(self.data_pres)))
        self.plot_data_pres.set_ydata(np.array(self.data_pres))




        xmax = len(self.data_alt) if len(self.data_alt) > 50 else 50
        xmin = xmax - 50

        ymin = round(min(self.data_alt), 0) - 1
        ymax = round(max(self.data_alt), 0) + 1
       
        self.axes_alt.set_xbound(lower=xmin, upper=xmax)
        self.axes_alt.set_ybound(lower=ymin, upper=ymax)
        
        self.axes_alt.grid(True, color='gray')
        pylab.setp(self.axes_alt.get_xticklabels(), visible=True)
       
        self.plot_data_alt.set_xdata(np.arange(len(self.data_alt)))
        self.plot_data_alt.set_ydata(np.array(self.data_alt))
        
        self.canvas.draw()

    
    def on_exit(self, event):
        self.source.close()
        self.Destroy()


if __name__ == '__main__':
    app = wx.App(False)
    app.frame = GraphFrame()
    app.frame.Show()
    app.MainLoop()



