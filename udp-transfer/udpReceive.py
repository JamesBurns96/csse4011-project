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
NUMBER_OF_NODES = 7

samplesPerPacket = 20
packetOffset = 3
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
        self.tagTypes = ["rigid", "acc", "brake", "clutch", "gear", "steer", "button"]
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
                data, address = self.sock.recvfrom(1024)
                start_byte = struct.unpack("B", data[0])
                packet_id = struct.unpack("B", data[1])
                packet_number = struct.unpack("H", data[2:4])
                time_stamp = struct.unpack("I", data[4:8])

                #if start_byte[0] != '(':
                    #continue

                # BUG:, gyro values are wrong, not sure why

                utc = datetime.datetime.fromtimestamp(time_stamp[0])
                print "-------------------------------NEW PACKET----------------------------"
                print " ID", packet_id[0], " UTC(s)", time_stamp[0], "Localtime:", utc.strftime("%Y-%m-%d %H:%M:%S"), \
                    "packetNumber:", packet_number[0]

                for x in range(samplesPerPacket):
                    acc_x = struct.unpack("b", data[x * 6 + 8])
                    acc_y = struct.unpack("b", data[x * 6 + 9])
                    acc_z = struct.unpack("b", data[x * 6 + 10])
                    gyr_x = struct.unpack("b", data[x * 6 + 11])
                    gyr_y = struct.unpack("b", data[x * 6 + 12])
                    gyr_z = struct.unpack("b", data[x * 6 + 13])
                    if packet_id[0] == 6:
                        print 'button pressed: ', gyr_x[0]

                    # save to CSV file
                    if packet_id[0] < NUMBER_OF_NODES:
                        self.outputFiles[packet_id[0]].write(
                            str(packet_id[0]) + ',' + str(time_stamp[0]) + ',' + str(packet_number[0]) + ',' +
                            str(x) + ','
                            + str(acc_x[0] * 2) + ',' + str(acc_y[0] * 2) + ',' + str(acc_z[0] * 2) + ','
                            + str(gyr_x[0] * 2) + ',' + str(gyr_y[0] * 2) + ',' + str(gyr_z[0] * 2) + '\n')

                    # update plot
                    if isinstance(self.graph, GraphFrame):
                        self.graph.update_data('t' + str(packet_id[0]) + '-ax', float(gyr_x[0] * 2))
                        self.graph.update_data('t' + str(packet_id[0]) + '-ay', float(gyr_y[0] * 2))
                        self.graph.update_data('t' + str(packet_id[0]) + '-az', float(gyr_z[0] * 2))

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
                       "aaaa::212:4b00:799:dd80", "aaaa::212:4b00:7b5:5601",
                       "aaaa::212:4b00:799:a402"]:
                self.sock.sendto(struct.pack("I", timestamp), (ip, UDP_TIMESYNC_PORT))  # ID n
                time.sleep(1)

    def close(self):
        print "Keyboard interrupt received. Exiting."
        self.isRunning = False
        self.t2.join()
        self.t1.join()
        for f in self.outputFiles:
            f.close()
        self.sock.close()


class Plot(object):
    def __init__(self):
        self.data = collections.deque(maxlen=500)
        self.axes = None
        self.plot = None


class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Demo'
    PLOT_KEYS = ['t0-ax', 't1-ax', 't2-ax', 't3-ax', 't4-ax', 't5-ax', 't6-ax',
                 't0-ay', 't1-ay', 't2-ay', 't3-ay', 't4-ay', 't5-ay', 't6-ay',
                 't0-az', 't1-az', 't2-az', 't3-az', 't4-az', 't5-az', 't6-az',
                 't0-filt-x', 't1-filt-x', 't2-filt-x', 'tilt3-filt-x', 't4-filt-x', 't5-filt-x', 't6-filt-ax',
                 't0-filt-y', 't1-filt-y', 't2-filt-y', 'tilt3-filt-y', 't4-filt-y', 't5-filt-y', 't6-filt-ay',
                 't0-filt-z', 't1-filt-z', 't2-filt-z', 'tilt3-filt-z', 't4-filt-z', 't5-filt-z', 't6-filt-az']
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

        self.fig = None

    def init_plot(self):
        self.fig = Figure((6.0, 3.0), dpi=100)
        plot_rows = 6
        plot_cols = 7
        assert(plot_rows * plot_cols == self.PLOT_COUNT)
        for (key, idx) in zip(self.PLOT_KEYS, range(self.PLOT_COUNT)):
            self.plots[key].axes = self.fig.add_subplot(plot_rows, plot_cols, idx+1)
            #self.plots[key].axes.set_facecolor('black')
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

            ymin = -250
            ymax = 250

            if key == 't6-ax':
                ymin = -0.5
                ymax = 2.5

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
