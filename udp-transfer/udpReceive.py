#!/usr/bin/python

import socket
import datetime
import struct
from threading import Thread
import traceback

import wx
import time
import collections

import matplotlib

matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import numpy as np
import pylab

import pedaldetect

# runtime variables
UDP_TIMESYNC_PORT = 4003  # node listens for timesync packets on port 4003
UDP_REPLY_PORT = 7005  # node listens for reply packets on port 7005
NUMBER_OF_NODES = 7

samplesPerPacket = 20
packetOffset = 3
firstPacketNumber = 0
secondPacketNumber = 0


class PedalTracker(object):
    def __init__(self):
        self.start_time = time.time()
        self.time_at_last_rise = time.time()
        self.last_times = collections.deque(maxlen=100)
        self.risen = False
        self.count = 0

    def record_high(self):
        t = time.time()
        if self.time_at_last_rise - t > 0.2:
            self.time_at_last_rise = time.time()
        else:
            return

        if not self.risen:
            self.count += 1
        self.risen = True

    def record_low(self):
        t = time.time()
        dt = (t - self.time_at_last_rise)
        self.last_times.append(dt)
        self.risen = False

        return [np.mean(self.last_times), self.count/((t - self.start_time))]


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
        self.sock.settimeout(5)
        self.isRunning = True

        # CSV logging variables
        self.outputFiles = []
        self.tagTypes = ["rigid", "acc", "brake", "clutch", "gear", "steer", "button"]
        # tags ID correspond to device locations as follows
        # 0 = rigid body, 1 = accelerometer, 2 = brake, 3 = clutch
        # 4 = gear stick. 5 = steering wheel

        self.trackers = []
        for i in range(NUMBER_OF_NODES):
            self.outputFiles.append(open(self.tagTypes[i] + '.csv', 'w+'))
            self.outputFiles[i].write("ID" + ',' + "timeStamp" + ',' + "packetNumber" + ',' + "sampleNumber" + ','
                                      + "accX" + ',' + "accY" + ',' + "accZ" + ','
                                      + "gyrX" + ',' + "gyrY" + ',' + "gyrZ" + '\n')
            self.trackers.append(PedalTracker())

        self.pd = pedaldetect.PedalDetector()
        self.pd.train()

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
        # time.sleep(1)
        while self.isRunning:
            try:
                data, addr = self.sock.recvfrom(1024)
                start_byte = struct.unpack("B", data[0])
                id = struct.unpack("B", data[1])
                packet_number = struct.unpack("H", data[2:4])
                time_stamp = struct.unpack("I", data[4:8])

                utc = datetime.datetime.fromtimestamp(time_stamp[0])
                print "-------------------------------NEW PACKET----------------------------"
                print " ID", id[0], " UTC(s)", time_stamp[0], "Localtime:", utc.strftime("%Y-%m-%d %H:%M:%S"), \
                    "packetNumber:", packet_number[0]

                for x in range(samplesPerPacket):
                    accX = struct.unpack("b", data[x * 6 + 8])
                    accY = struct.unpack("b", data[x * 6 + 9])
                    accZ = struct.unpack("b", data[x * 6 + 10])

                    gyrX = struct.unpack("b", data[x * 6 + 11])
                    gyrY = struct.unpack("b", data[x * 6 + 12])
                    gyrZ = struct.unpack("b", data[x * 6 + 13])

                    # save to CSV file
                    if id[0] < NUMBER_OF_NODES:
                        self.outputFiles[id[0]].write(
                            str(id[0]) + ',' + str(time_stamp[0]) + ',' + str(packet_number[0]) + ',' +
                            str(x) + ','
                            + str(accX[0] * 2) + ',' + str(accY[0] * 2) + ',' + str(accZ[0] * 2) + ','
                            + str(gyrX[0] * 2) + ',' + str(gyrY[0] * 2) + ',' + str(gyrZ[0] * 2) + '\n')

                    if isinstance(self.graph, GraphFrame):
                        (x, y, z) = (float(gyrX[0] * 2), float(gyrY[0] * 2), float(gyrZ[0] * 2))
                        self.graph.update_data('t' + str(id[0]) + '-gyro-x', x)
                        self.graph.update_data('t' + str(id[0]) + '-gyro-y', y)
                        self.graph.update_data('t' + str(id[0]) + '-gyro-z', z)

                        pred =  None
                        if id[0] == 0:
                            pred = pedaldetect.predict_from_threshold([np.sum((x,y,z))], -50, 50)
                            self.graph.update_data('t0-filt-x', pred)
                        if id[0] == 1:#acc
                            pred = pedaldetect.predict_from_threshold([np.sum((x,y,z))], -10, 10)
                            self.graph.update_data('t1-filt-x', pred)
                        if id[0] == 2:#brake
                            pred = pedaldetect.predict_from_threshold([np.sum((x,y,z))], -7, 7)
                            self.graph.update_data('t2-filt-x', pred)
                        if id[0] == 3:#cltch
                            pred = pedaldetect.predict_from_threshold([np.sum((x,y,z))], -30, 40)
                            self.graph.update_data('t3-filt-x', pred)
                        if id[0] == 4:#gear stick
                            pred = pedaldetect.predict_from_threshold([np.sum((x,y,z))], -50, 50)
                            self.graph.update_data('t4-filt-x', pred)
                        if id[0] == 5:
                            pred = pedaldetect.predict_from_threshold([np.sum((x,y,z))], -50, 50)
                            self.graph.update_data('t5-filt-x', pred)
                        if id[0] == 6:
                            pred = pedaldetect.predict_from_threshold([np.sum((x,y,z))], -50, 50)
                            self.graph.update_data('t6-filt-x', pred)

                        if pred is not None:
                            if pred[0] > 0.5:
                                self.trackers[id[0]].record_high()
                            elif pred[0] < -0.5:
                                i = id[0]
                                print self.trackers
                                [avg, rate] = self.trackers[i].record_low()
                                print "Average time on pedal {0}: {1}".format(id[0], avg)
                                print "Pedal {0} rate: {1}".format(id[0], rate)


                # wx.CallAfter(self.graph.draw_plot)

            except socket.timeout:
                print "timeout on data reception"
                continue

    def udp_send_thread(self):
        # time.sleep(2)
        while self.isRunning:
            try:
                timestamp = int(time.time())
                print "Sending timesync packet with UTC[s]: {0}, Localtime: {1}".\
                    format(timestamp, time.strftime("%Y-%m-%d %H:%M:%S"))

                for ip in ["aaaa::212:4b00:c68:2d83", "aaaa::212:4b00:7b5:5c80",
                           "aaaa::212:4b00:7b5:4e06", "aaaa::212:4b00:799:af04",
                           "aaaa::212:4b00:799:dd80", "aaaa::212:4b00:7b5:5601",
                           "aaaa::212:4b00:799:a402"]:
                    self.sock.sendto(struct.pack("I", timestamp), (ip, UDP_TIMESYNC_PORT))  # ID n
                    time.sleep(1)

                    if not self.isRunning:
                        break
            except socket.error:
                print 'caught socket.error'
                traceback.print_exc()
                self.isRunning = False


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
    title = 'Gyroscope and Filter Monitor'
    PLOT_KEYS = ['t0-gyro-x', 't1-gyro-x', 't2-gyro-x', 't3-gyro-x', 't4-gyro-x', 't5-gyro-x', 't6-gyro-x',
                 't0-gyro-y', 't1-gyro-y', 't2-gyro-y', 't3-gyro-y', 't4-gyro-y', 't5-gyro-y', 't6-gyro-y',
                 't0-gyro-z', 't1-gyro-z', 't2-gyro-z', 't3-gyro-z', 't4-gyro-z', 't5-gyro-z', 't6-gyro-z',
                 't0-filt-x', 't1-filt-x', 't2-filt-x', 't3-filt-x', 't4-filt-x', 't5-filt-x', 't6-filt-x']
    PLOT_COUNT = len(PLOT_KEYS)

    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)

        # handle window close event
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        # creat plot objects to store data
        self.plots = dict()
        for key in self.PLOT_KEYS:
            self.plots[key] = Plot()

        # set data source
        self.source = UDPComs(self)

        self.panel = wx.Panel(self, 1)

        self.init_plot()
        self.canvas = FigureCanvasWxAgg(self.panel, -1, self.fig)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.EXPAND)

        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

        self.is_running = True
        self.update_thread = Thread(target=self.update_plot_thread)
        self.update_thread.start()

    def init_plot(self):
        self.fig = Figure()
        plot_rows = 4
        assert(plot_rows * NUMBER_OF_NODES == self.PLOT_COUNT)
        for (key, idx) in zip(self.PLOT_KEYS, range(self.PLOT_COUNT)):
            self.plots[key].axes = self.fig.add_subplot(plot_rows, NUMBER_OF_NODES, idx+1)
            #self.plots[key].axes.set_facecolor('black')
            self.plots[key].axes.set_title(key, size=12)

            pylab.setp(self.plots[key].axes.get_xticklabels(), fontsize=8)
            pylab.setp(self.plots[key].axes.get_yticklabels(), fontsize=8)

            # plot the data as a line series, and save the reference
            # to the plotted line series
            self.plots[key].plot = self.plots[key].axes.plot(self.plots[key].data)[0]

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

            if 'filt' in key:
                ymin = -1.5
                ymax = 1.5

            if key == 't6-gyro-x':
                ymin = -0.5
                ymax = 2.5

            self.plots[key].axes.set_xbound(lower=xmin, upper=xmax)
            self.plots[key].axes.set_ybound(lower=ymin, upper=ymax)
            self.plots[key].axes.grid(True, color='gray')

            pylab.setp(self.plots[key].axes.get_xticklabels(), visible=True)

            self.plots[key].plot.set_xdata(np.arange(len(self.plots[key].data)))
            self.plots[key].plot.set_ydata(np.array(self.plots[key].data))

        self.canvas.draw()

    def update_plot_thread(self):
        while self.is_running:
            wx.CallAfter(self.draw_plot)
            time.sleep(2)

    def on_exit(self, event):
        print 'quitting'
        self.source.close()
        self.is_running = False
        self.update_thread.join()
        self.Destroy()

if __name__ == '__main__':
    app = wx.App(False)
    app.frame = GraphFrame()
    app.frame.Maximize()
    app.frame.Show()
    app.MainLoop()
