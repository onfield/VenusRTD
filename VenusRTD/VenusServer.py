#!/usr/bin/python3

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
import configparser
import sys
import argparse
import asyncio
import serial_asyncio
from functools import reduce

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
STX_C = b'\x02'
EOT_C = b'\x04'
SYN_C = b'\x16'
ETB_C = b'\x17'

dakSport = {}
dakOffset = {}
dakString = ''

def displayITF(offset, limit):
    while offset < limit and str(offset) in dakOffset:
        name = dakOffset[str(offset)]
        width = dakSport[name][1]
        print("'{0}[{1}]'='{2}".format(name, offset, dakString[offset:offset+width]))            
        offset += width
            
def loadITF(itf):
    loaded = False
    
    if itf is None:
        return loaded

    config = configparser.ConfigParser()
    try:
        config.read(itf)
        fields = int(config.get("TEMPLATE", "NUMFIELDS")) + 1
        dakSize = 0
        for i in range(1, fields):
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
        loaded = True
    except Exception as ex:
        print("Exception: {0}".format(ex))
        
    return loaded


class VenusSerialHandler(asyncio.Protocol):
    
    def __init__(self):
        self.rtd = b''
        
    def connection_made(self, transport):
        self.transport = transport
        print('port opened', transport)
        transport.serial.rts = False

    def data_received(self, data):
        global dakSport
        global dakString
        global dakOffset
               
        print('data received', repr(data))
        
        self.rtd += data
        end = self.rtd.find(ETB_C)
        if end >= 0:
            start = self.rtd.find(SYN_C)
            
            if end < start:
                self.rtd = self.rtd[start:]
                return
                
            if start >=0:
                self.transport.write(SYN_C + b'20000000' + SOH_C + b'90000' + EOT_C + b'80' + ETB_C)
                length = 1 + (end - start)
                if len(self.rtd) >= length:
                    checksum = reduce(lambda x,y:x+y, self.rtd[start+1:end - 2]) % 256
                    offset = int(self.rtd[start + 16:start + 20])
                    text = self.rtd[start + 21:end - 3]
                    dakString = dakString[0:offset] + str(text) + dakString[offset + len(text):]
                    print("Check sum = {0}, {1}, offset = {2}, text = '{3}', length={4}/{5}, start={6}, end={7}".format(format(checksum, '02X'), self.rtd[end-2:end], offset, text, length, len(self.rtd), start, end))
                    if str(offset) in dakOffset:
                        displayITF(offset, offset+len(text))
                    else:
                        print("Unknown offset {0}".format(offset))

                    if len(self.rtd) == length:
                        self.rtd = b''
                    else:                                                
                        self.rtd = self.rtd[end+1:]
                else:
                    self.rtd = b''
#                self.transport.close()

    def connection_lost(self, exc):
        print('port closed')
        asyncio.get_event_loop().stop()

class VenusHandler(asyncore.dispatcher_with_send):

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
                self.send(SYN_C + b'20000000' + SOH_C + b'90000' + EOT_C + b'80' + ETB_C)
                checksum = reduce(lambda x,y:x+y, self.rtd[1:len(self.rtd)-3]) % 256
                offset = int(self.rtd[16:20])
                text = self.rtd[21:len(self.rtd)-4]
                dakString = dakString[0:offset] + str(text) + dakString[offset + len(text):]
                if str(offset) in dakOffset:
                    displayITF(offset, offset+len(text))
                else:
                    print("Unknown offset {0}".format(offset))
                    print("Check sum = {0}, {1}, offset = {2}, text = '{3}'".format(format(checksum, '02X'), self.rtd[-3:-1], offset, text))
                
class VenusServer(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        if port <= 0:
            return
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        handler = None
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print("Incoming connection from %s" % repr(addr))
            handler = VenusHandler(sock)
        else:
            print('Incoming connection not accepted!')
            
        return handler
            
def main():
    parser = argparse.ArgumentParser(description='Read Daktronics RTD.\nCopyright (c) 2017 OnField Technology, LLC.')
    parser.add_argument('--address', default='localhost', help='ip address.')
    parser.add_argument('--port', default='17410', help='ip port.')
    parser.add_argument('--serial', default=None, help='Serial port. Overrides address/port')
    parser.add_argument('--itf', default='ITF/Code 27 Cricket Scoreboard.itf', help='Daktronics Input Template File.')
    args = parser.parse_args()
    
    if args.serial is None:
        address = args.address
        port = args.port
    else:
        address = args.serial
        port = "-1"
        
    loadITF(args.itf)
    
    if args.serial is None:
        server = VenusServer(address, int(port))
    
        print("Address {0}:{1}, ITF={2}".format(address, port, args.itf))
    
        try:
            asyncore.loop()
        except KeyboardInterrupt:
            print("\nCrtl+C pressed. Shutting down.")
            server.close()
            sys.exit()
    else:
        print("Port {0}, ITF={1}".format(args.serial, args.itf))
        loop = asyncio.get_event_loop()
        coro = serial_asyncio.create_serial_connection(loop, VenusSerialHandler, args.serial, baudrate=19200)
        loop.run_until_complete(coro)
        loop.run_forever()
        loop.close()
        
if __name__ == '__main__':
    main()    
