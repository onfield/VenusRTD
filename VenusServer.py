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

import configparser
import sys
import argparse
import asyncio
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
        value = dakString[offset:offset+width].strip()
        if len(value) > 0:
            print("'{0}[{1}]'='{2}'".format(name, offset, dakString[offset:offset+width]))            
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
            # print("{0}. {1}[{2}, {3}]".format(i, name, dakSize, length))
            dakSize += int(length)
        dakSport['dakSize'] = [1, dakSize]
        dakString = " " * dakSize
        # print("Field={0}, Size={1}".format(fields-1, dakSize))
        loaded = True
    except Exception as ex:
        print("Exception: {0}".format(ex))
        
    return loaded

async def handle_itf(reader, writer):
    rtd = b''
    etb = True
    addr = writer.get_extra_info('peername')

    global dakSport
    global dakString
    global dakOffset
 
    while True:   
        c = b''
        try:
            while c != SYN_C:
                c = await reader.read(1)
            rtd = c

            while c != ETB_C:
                c = await reader.read(1)
                rtd += c
                etb = (c == ETB_C)
        except KeyboardInterrupt as ki:
            raise ki
        except:
            writer.close()
            print(f"Connection from {addr!r} closed")
            return

        data = rtd
        rtd = data.decode()

        print(f"RTD={rtd!r} + {rtd[0]!r}")

        if etb:
            if rtd[0] == SYN_C.decode():
                writer.write(SYN_C + b'20000000' + SOH_C + b'90000' + EOT_C + b'80' + ETB_C)
                await writer.drain()
                checksum = reduce(lambda x,y:x+y, data[1:len(rtd)-3]) % 256
                offset = int(rtd[16:20])
                text = rtd[21:len(rtd)-4]
                dakString = dakString[0:offset] + str(text) + dakString[offset + len(text):]
                if str(offset) in dakOffset:
                    displayITF(offset, offset+len(text))
                else:
                    print("Unknown offset {0}".format(offset))
                    print("Check sum = {0}, {1}, offset = {2}, text = '{3}'".format(format(checksum, '02X'), rtd[-3:-1], offset, text))
            else:
                print(f"Message does not start with SYN! {rtd[0]!r}")


async def itf_main(address, port):
    server = await asyncio.start_server(handle_itf, address, port)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    try:
        async with server:
            await server.serve_forever()
    except KeyboardInterrupt:
        print("\nCrtl+C pressed. Shutting down.")
        server.close()
        sys.exit()

async def main():
    parser = argparse.ArgumentParser(description='Read Daktronics RTD.\nCopyright (c) 2017 OnField Technology, LLC.') 
    parser.add_argument('--address', default='localhost', help='ip address.') 
    parser.add_argument('--port', default='17410', help='ip port.') 
    parser.add_argument('--itf', default='ITF/Code 27 Cricket Scoreboard.itf', help='Daktronics Input Template File.')
    args = parser.parse_args()

    address = args.address
    port = args.port
        
    loadITF(args.itf)

    print("Address {0}:{1}, ITF={2}".format(address, port, args.itf))

    server = await asyncio.start_server(handle_itf, address, port)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    try:
        async with server:
            await server.serve_forever()
    except KeyboardInterrupt:
        print("\nCrtl+C pressed. Shutting down.")
        server.close()
        sys.exit()
            
if __name__ == '__main__':
    asyncio.run(main())    
