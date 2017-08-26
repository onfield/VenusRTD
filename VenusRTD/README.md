# VenusRTD
Python Venus 7000 RTD Simulator for Daktronics AllSport 5000 Scoring Controllers

VenusServer.py --help

Usage: VenusServer.py [-h] [--address ADDRESS] [--port PORT] [--itf ITF]

Read Daktronics RTD.

optional arguments:

	  -h, --help         show this help message and exit
  
	  --address ADDRESS  ip address.
  
	  --port PORT        ip port.
  
	  --itf ITF          Daktronics Input Template File.

Sample Usage:

VenusServer.py --address localhost --port 17410 --itf 'ITF/Code 27 Cricket Scoreboard.itf'

Use a serial to network proxy or hardware to send RTD data from a serial device.

e.g.
 
	https://sourceforge.net/projects/ser2net/
	
	http://www.usconverters.com/serial-ethernet-converters

