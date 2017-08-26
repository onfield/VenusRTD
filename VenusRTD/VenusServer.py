#!/usr/bin/python

# MIT License
#
# Copyright (c) 2017 OnField Technology, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import asyncore
import socket
import ConfigParser
import sys
import argparse

# RTD Packet format -
#
# <SYN> + HEADER + <SOH> + CONTROL + <STX> + TEXT + <EOT> + SUM + <ETB>
#
# Where:
#
# <SYN> = 0x16
# <SOH> = 0x01
# <STX> = 0x02
# <EOT> = 0x04
# <ETB> = 0x17
# HEADER = '20000000'
# CONTROL = '004010NNNN'
# (NNNN is the decimal offset to place text)
# TEXT = message to be sent to screen
# SUM = sum of character values from header to (and including) <EOT> mod 256 as hex string
 
SOH_C = b'\x01'
EOT_C = b'\x04'
SYN_C = b'\x16'
ETB_C = b'\x17'

dakSport = {}
dakOffset = {}
dakString = ''

class VenusHandler(asyncore.dispatcher_with_send):

#    def __init__(self, sock):
#        super(self.__class__, self).__init__(sock)       
#        self.rtd = ''
#        self.etb = False

    def checksum256(self, st):
        return reduce(lambda x,y:x+y, map(ord, st)) % 256

    def displayITF(self, offset, limit):
        while offset < limit and str(offset) in dakOffset:
            name = dakOffset[str(offset)]
            width = dakSport[name][1]
            print("'{0}[{1}]'='{2}".format(name, offset, dakString[offset:offset+width]))            
            offset += width
            
    def handle_read(self):
        self.rtd = b''
        self.etb = False

        global dakSport
        global dakString
        global dakOffset
        
        c = b''       
        while c != SYN_C:
            c = self.recv(1)
        self.rtd = SYN_C
        while c != ETB_C:
            c = self.recv(1)
            self.rtd += c
            self.etb = (c == ETB_C)
            
        if self.etb:
            if self.rtd[0] == SYN_C:
                self.send(SYN_C)
                self.send('20000000')
                self.send(SOH_C)
                self.send('90000')
                self.send(EOT_C)
                self.send('80')
                self.send(ETB_C)
                checksum = self.checksum256(self.rtd[1:len(self.rtd)-3])
                offset = int(self.rtd[16:20])
                text = self.rtd[21:len(self.rtd)-4]
                dakString = dakString[0:offset] + text + dakString[offset + len(text):]
                if str(offset) in dakOffset:
                    self.displayITF(offset, offset+len(text))
                else:
                    print("Unknown offset {0}".format(offset))
                    print("Check sum = {0}, {1}, offset = {2}, text = '{3}'".format(format(checksum, '02X'), self.rtd[-3:-1], offset, text))
                
class VenusServer(asyncore.dispatcher):

    def __init__(self, host, port, itf=None):
        asyncore.dispatcher.__init__(self)
        self.loadITF(itf)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        handler = None
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print 'Incoming connection from %s' % repr(addr)
            handler = VenusHandler(sock)
        else:
            print 'Incoming connection not accepted!'
            
        return handler
            
    def loadITF(self, itf):
        if itf is None:
            return

        global dakSport
        global dakString
        global dakOffset
               
        config = ConfigParser.ConfigParser()
        try:
            config.read(itf)
            fields = int(config.get("TEMPLATE", "NUMFIELDS")) + 1
            dakSize = 0
            for i in xrange(1, fields):
                field = "FIELD" + str(i)
                length = config.get(field, "LENGTH")
                name = config.get(field, "NAME")
#                justify = config.get(field, "JUSTIFY")
                dakSport[name] = [dakSize, int(length)]
                dakOffset[str(dakSize)] = name 
                print("{0}. {1}[{2}, {3}]".format(i, name, dakSize, length))
                dakSize += int(length)
            dakSport['dakSize'] = [1, dakSize]
            dakString = " " * dakSize
            print("Field={0}, Size={1}".format(fields-1, dakSize))
        except Exception as ex:
            print("Exception: {0}".format(ex))

def main():
    parser = argparse.ArgumentParser(description='Read Daktronics RTD.\nCopyright (c) 2017 OnField Technology, LLC.')
    parser.add_argument('--address', default='localhost', help='ip address.')
    parser.add_argument('--port', default='17410', help='ip port.')
    parser.add_argument('--itf', default='ITF/Code 27 Cricket Scoreboard.itf', help='Daktronics Input Template File.')
    args = parser.parse_args()
    
    address = args.address
    port = args.port
    itf = args.itf
    
    server = VenusServer(address, int(port), itf)
    
    print("Address {0}:{1}, ITF={2}".format(address, port, itf))
    
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print "\nCrtl+C pressed. Shutting down."
        server.shutdown(socket.SHUT_RDWR)
        server.close()
        sys.exit()
    
if __name__ == '__main__':
    main()    
