#!/usr/bin/python

import socket
import datetime
import struct
from threading import Thread

import wx
import time
import collections

import matplotlib

matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import numpy as np
import pylab

# runtime variables
UDP_TIMESYNC_PORT = 4003  # node listens for timesync packets on port 4003
UDP_REPLY_PORT = 7005  # node listens for reply packets on port 7005
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

    def __init__(self, graph_frame):
        # generate graph object
        self.graph = graph_frame

        # generate socket connection
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, 0)
        self.sock.bind(('', 7005))
        self.sock.settimeout(0.5)
        self.isRunning = True

        # CSV logging variables
        self.outputFiles = []
        self.tagTypes = ["rigid", "acc", "brake", "clutch", "gear", "steer"]
        # tags ID correspond to device locations as follows
        # 0 = rigid body, 1 = accelerometer, 2 = brake, 3 = clutch
        # 4 = gear stick. 5 = steering wheel

        for i in range(NUMBER_OF_NODES):
            self.outputFiles.append(open(self.tagTypes[i] + '.csv', 'w+'))
            self.outputFiles[i].write("ID" + ',' + "timeStamp" + ',' + "packetNumber" + ',' + "sampleNumber" + ','
                                      + "accX" + ',' + "accY" + ',' + "accZ" + ','
                                      + "gyrX" + ',' + "gyrY" + ',' + "gyrZ" + '\n')

        # start UDP listener thread
        self.t1 = Thread(target=self.udp_listen_thread)
        self.t1.start()
        print "Listening for incoming packets on UDP port", UDP_REPLY_PORT

        # start UDP timesync sender thread
        self.t2 = Thread(target=self.udp_send_thread)
        self.t2.start()

        print "Sending timesync packets on UDP port", UDP_TIMESYNC_PORT
        print "Exit application by pressing (CTRL-C)"

    def udp_listen_thread(self):
        while self.isRunning:
            try:
                data, addr = self.sock.recvfrom(1024)
                start_byte = struct.unpack("B", data[0])
                id = struct.unpack("B", data[1])
                packet_number = struct.unpack("H", data[2:4])
                time_stamp = struct.unpack("I", data[4:8])

                # BUG:, gyro values are wrong, not sure why
                utc = datetime.datetime.fromtimestamp(time_stamp[0])
                print "-------------------------------NEW PACKET----------------------------"
                print " ID", id[0], " UTC(s)", time_stamp[0], "Localtime:", utc.strftime("%Y-%m-%d %H:%M:%S"), \
                    "packetNumber:", packet_number[0]
                x = 0
                while (x < samplesPerPacket):
                    accX = struct.unpack("b", data[x * 6 + 8])
                    accY = struct.unpack("b", data[x * 6 + 9])
                    accZ = struct.unpack("b", data[x * 6 + 10])
                    gyrX = struct.unpack("b", data[x * 6 + 11])
                    gyrY = struct.unpack("b", data[x * 6 + 12])
                    gyrZ = struct.unpack("b", data[x * 6 + 13])
                    x += 1

                    # save to CSV file
                    if id[0] < NUMBER_OF_NODES:
                        self.outputFiles[id[0]].write(
                            str(id[0]) + ',' + str(time_stamp[0]) + ',' + str(packet_number[0]) + ',' +
                            str(x) + ','
                            + str(accX[0] * 2) + ',' + str(accY[0] * 2) + ',' + str(accZ[0] * 2) + ','
                            + str(gyrX[0] * 2) + ',' + str(gyrY[0] * 2) + ',' + str(gyrZ[0] * 2) + '\n')

                    # update plot
                    if isinstance(self.graph, GraphFrame):
                        self.graph.update_data('t' + str(id[0]) + '-ax', float(gyrX[0] * 2))
                        self.graph.update_data('t' + str(id[0]) + '-ay', float(gyrY[0] * 2))
                        self.graph.update_data('t' + str(id[0]) + '-az', float(gyrZ[0] * 2))
                        wx.CallAfter(self.graph.draw_plot)

            except socket.timeout:
                print "timeout on data reception"
                continue

    def udp_send_thread(self):
        while self.isRunning:
            timestamp = int(time.time())
            print "Sending timesync packet with UTC[s]:", timestamp, "Localtime:", time.strftime("%Y-%m-%d %H:%M:%S")

            for ip in ["aaaa::212:4b00:c68:2d83", "aaaa::212:4b00:7b5:5c80",
                       "aaaa::212:4b00:7b5:4e06", "aaaa::212:4b00:799:af04",
                       "aaaa::212:4b00:799:dd80", "aaaa::212:4b00:7b5:5601"]:
                self.sock.sendto(struct.pack("I", timestamp), (ip, UDP_TIMESYNC_PORT))  # ID n
                time.sleep(1)

            # TODO fuck this off
            # sleep for 5 seconds
            time.sleep(5)

    def close(self):
        print "Keyboard interrupt received. Exiting."
        self.isRunning = False
        self.t2.join()
        self.t1.join()
        for f in self.outputFiles:
            f.close()
        self.sock.close()


####################################graphing###########################
class Plot(object):
    def __init__(self):
        self.data = collections.deque(maxlen=500)
        self.axes = None
        self.plot = None


class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Demo'
    PLOT_KEYS = ['t0-ax', 't1-ax', 't2-ax', 't3-ax', 't4-ax', 't5-ax',
                 't0-ay', 't1-ay', 't2-ay', 't3-ay', 't4-ay', 't5-ay',
                 't0-az', 't1-az', 't2-az', 't3-az', 't4-az', 't5-az',
                 't0-filtx', 't1-filtx','t2-filtx', 'tilt3-filtx', 't4-filtx', 't5-filtx',
                 't0-filty', 't1-filty','t2-filty', 'tilt3-filty', 't4-filty', 't5-filty',
                 't0-filtz', 't1-filtz','t2-filtz', 'tilt3-filtz', 't4-filtz', 't5-filtz']
    PLOT_COUNT = len(PLOT_KEYS)

    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)

        # handle window close event
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        # set data source
        self.source = UDPComs(self)

        self.plots = dict()
        for key in self.PLOT_KEYS:
            self.plots[key] = Plot()

        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigureCanvasWxAgg(self.panel, -1, self.fig)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)

        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

    def init_plot(self):
        self.fig = Figure((6.0, 3.0), dpi=100)
        plot_rows = 6
        plot_cols = 6
        assert(plot_rows * plot_cols == self.PLOT_COUNT)
        for (key, idx) in zip(self.PLOT_KEYS, range(self.PLOT_COUNT)):
            self.plots[key].axes = self.fig.add_subplot(plot_rows, plot_cols, idx+1)
            self.plots[key].axes.set_facecolor('black')
            self.plots[key].axes.set_title(key, size=12)

            pylab.setp(self.plots[key].axes.get_xticklabels(), fontsize=8)
            pylab.setp(self.plots[key].axes.get_yticklabels(), fontsize=8)

            # plot the data as a line series, and save the reference
            # to the plotted line series
            self.plots[key].plot = self.plots[key].axes.plot(self.plots[key].data, linewidth=1, color=(1, 1, 0))[0]

    def update_data(self, key, val):
        self.plots[key].data.append(val)

    def draw_plot(self):
        """ Redraws the plot
        """
        for key in self.PLOT_KEYS:
            xmax = len(self.plots[key].data) if len(self.plots[key].data) > 200 else 200
            xmin = xmax - 200

            # ymin = round(min(self.plots[key].data), 0) - 1
            # ymax = round(max(self.plots[key].data), 0) + 1
            ymin = -250
            ymax = 250

            self.plots[key].axes.set_xbound(lower=xmin, upper=xmax)
            self.plots[key].axes.set_ybound(lower=ymin, upper=ymax)
            self.plots[key].axes.grid(True, color='gray')

            pylab.setp(self.plots[key].axes.get_xticklabels(), visible=True)

            self.plots[key].plot.set_xdata(np.arange(len(self.plots[key].data)))
            self.plots[key].plot.set_ydata(np.array(self.plots[key].data))

        self.canvas.draw()

    def on_exit(self, event):
        self.source.close()
        self.Destroy()


if __name__ == '__main__':
    app = wx.App(False)
    app.frame = GraphFrame()
    app.frame.Show()
    app.MainLoop()
