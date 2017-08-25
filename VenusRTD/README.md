# VenusRTD
Python Venus 7000 RTD Simulator for Daktronics AllSport 5000 Scoring Controllers

VenusServer.py --help

usage: VenusServer.py [-h] [--address ADDRESS] [--port PORT] [--itf ITF]

Read Daktronics RTD.

optional arguments:
  -h, --help         show this help message and exit
  --address ADDRESS  ip address.
  --port PORT        ip port.
  --itf ITF          Daktronics Input Template File.

Sample Usage:

VenuServer.py --serial /dev/ttyS0 --itf ITF/AS5-Cricket.itf

or

VenusServer.py --address localhost --port 17410 --itf 'ITF/Code 27 Cricket Scoreboard.itf'

