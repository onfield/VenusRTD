# VenusRTD
Python Venus 7000 RTD Simulator for Daktronics AllSport 5000 Scoring Controllers

It depends on asyncio and is compatible with Python 3.7 and later.

VenusServer.py --help

Usage: VenusServer.py [-h] [--address ADDRESS] [--port PORT] [--itf ITF]

Read Daktronics RTD.

optional arguments:

	  -h, --help         show this help message and exit
  
	  --address ADDRESS  ip address. Default='localhost'
  
	  --port PORT        ip port. Default=17410
             
	  --itf ITF          Daktronics Input Template File. Defaut='ITF/Code 27 Cricket Scoreboard.itf'

Sample Usage:

VenusServer.py --address 0.0.0.0 --port 17410 --itf 'ITF/Code 27 Cricket Scoreboard.itf'

Use a serial to network proxy or hardware to send RTD data from a serial device to ip address:port.

e.g.
 
	https://sourceforge.net/projects/ser2net/
	
	http://www.usconverters.com/serial-ethernet-converters
	
