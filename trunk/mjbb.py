# Copyright (c) 2012 Caleb Crome
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions: 
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software. 
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. 
#
# *
# * MeggyJr serial format is simple:
# *   host              meggy                   description
# *   'h'               responds with 0xff      hello
# *   'd' x y color     no response             draw a pixel at x y in
# *                                             color.  colors are:
# *                                             0=dark, 
# *                                             1=red,
# *                                             2=orange
# *                                             3=yellow,
# *                                             4=green,
# *                                             5=blue,
# *                                             6=vilot,
# *                                             7=white,
# *                                             8=dim red,
# *                                             9=dim orange
# *                                             10=dim yellow,
# *                                             11=dim green,
# *                                             12=dim aqua
# *                                             13=dim blue,
# *                                             14=dim vilot,
# *                                             15=extra bright
# *
# *   'a' 'A' aux-leds     no response          set the top row LEDS to
# *                                             <aux-leds>
# *  
#
import time
import urllib2 as urllib
import json
import serial
import sys
from struct import pack, unpack
import threading
import argparse
import ConfigParser

parser = argparse.ArgumentParser(description="Monitor a Buildbot server")
parser.add_argument('ini_file', type=str, nargs='?', help="builder .ini file")
args = parser.parse_args()

cp = ConfigParser.RawConfigParser()

cp.read(args.ini_file)
port     = cp.getint('main', 'port')
host     = cp.get   ('main', 'host')
tty      = cp.get   ('main', 'tty')
builders = cp.get   ('main', 'builders')
builds = builders.split(',')
url = "http://%s:%d/json/builders" % (host, port)

class MeggyJr:
    colors = {
        "dark"                : 0 ,
        "red"                 : 1 ,
        "orange"              : 2 ,
        "yellow"              : 3 ,
        "green"               : 4 ,
        "blue"                : 5 ,
        "vilot"               : 6 ,
        "white"               : 7 ,
        "dim red"             : 8 ,
        "dim orange"          : 9 ,
        "dim yellow"          : 10,
        "dim green"           : 11,
        "dim aqua"            : 12,
        "dim blue"            : 13,
        "dim vilot"           : 14,
        "extra bright"        : 15,
        }

    dark                = 0 
    red                 = 1 
    orange              = 2 
    yellow              = 3 
    green               = 4 
    blue                = 5 
    vilot               = 6 
    white               = 7 
    dim_red             = 8 
    dim_orange          = 9 
    dim_yellow          = 10
    dim_green           = 11
    dim_aqua            = 12
    dim_blue            = 13
    dim_vilot           = 14
    extra_bright        = 15
    def __init__(self, tty, baud=115200):
        self.tty = tty
        try:
            self.ser = serial.Serial(tty, baudrate=baud, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                     stopbits=serial.STOPBITS_ONE,
                                     timeout=1,
                                     xonxoff=False,
                                     rtscts=False,
                                     dsrdtr=False,
                                     )
        except ValueError:
            print("Couldn't open port, value error");
            sys.exit(1)
        except serial.SerialException:
            print("Couldn't open port, SerialException");
            sys.exit(1)

        self.say_hi()
    def say_hi(self):
        time.sleep(2) # need a sleep because the rts line causes a reset upon open.
        self.ser.write("h")
        r = self.ser.read(1)
        if (r == ''):
            print "Couldn't say hi to meggy."
            sys.exit(1)
    def sendPx(self, x, y, color):
        x = int(x) % 8
        y = int(y) % 8
        color = int(color) % 16
        msg = pack("cBBBc", 'd', x, y, color, 'D')
        self.ser.write(msg)

    def lightRow(self, row, color):
        for x in range(8):
            self.sendPx(x, row, color)
    def eraseRow(self, row):
        for x in range(8):
            self.sendPx(x, row, 0)

mj = MeggyJr(tty)
mj.lightRow(0, mj.red)

states = {
    "idle" : mj.green,
    "building" : mj.yellow,
    "failed"   : mj.red,
    }


class Cylon:
    
    def __init__(self):
        self.dir=-1
        self.val=8
        self.last=8
    def next(self):
        self.last = self.val
        self.val = self.val+self.dir
        if (self.val < 0) or (self.val > 7):
            self.dir = -self.dir
            self.val = self.val + 2 * self.dir
        return self.last, self.val

class CylonThread(threading.Thread):
    def run(self):
        while(1):
            last, this = self.cylon.next()
            self.mj.sendPx(this, 7, self.mj.vilot)
            self.mj.sendPx(last, 7, self.mj.dark)
            time.sleep(0.1)
    def __init__(self, mj):
        threading.Thread.__init__(self)
        self.mj = mj
        self.cylon = Cylon()
        
        
ct = CylonThread(mj)
ct.start()

while (1):
    f = urllib.urlopen(url)
    j = json.load(f)
    i = 0
    for build in builds:
        state = j[build]['state']
        color = states[state]
        mj.lightRow(i, color)
        i = i + 1
    time.sleep(1)

