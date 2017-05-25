#!/usr/bin/python

import socket
import time
import datetime
import struct
import StringIO
from threading import Thread
import sys


TCP_RECEIVE_PORT = 4003 # node listens for timesync packets on port 4003
TCP_REPLY_PORT = 7005 # node listens for reply packets on port 7005

class TcpServer(object):
    isRunning = True

    def tcpListenThread(self):
        # listen on UDP socket port UDP_TIMESYNC_PORT
        print "[+] Started listening on ", TCP_REPLY_PORT
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 7005))
        self.sock.listen(50)

        while self.isRunning:        
            try:
                conn, addr = self.sock.accept()        
                print "[+] Got a connection from ", addr[0], ":", addr[1]

                t = Thread(target=self.tcpConnectionThread, args=[conn])
                t.start()
                
            except socket.timeout:
                self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
                print "Timeout on sock.accept"


    def tcpConnectionThread(self, sck):
        #sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, 0)
        print 'ayylmao ', sck
        sck.send('hello\r\n')

    def start(self):
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)

        self.isRunning = True

        # start UDP listener as a thread
        t1 = Thread(target=self.tcpListenThread)
        t1.start()

        try:
            while True:
                # wait for application to finish (ctrls-c)
                time.sleep(1)

        except KeyboardInterrupt:
            print "Keyboard interrupt received. Exiting."
            self.isRunning = False
        
        # start UDP listener as a thread
        t1 = Thread(target=tcpListenThread)
        t1.start()

        try:
            while True:
                # wait for application to finish (ctrl-c)
                time.sleep(1)

        except KeyboardInterrupt:
            print "Keyboard interrupt received. Exiting."
            isRunning = False

if __name__ == '__main__':
    tcp = TcpServer()
    tcp.start()
