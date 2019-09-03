#!/usr/bin/python
# R2D2 Python source code to control the Sphero R2D2 droic
# Author: Enrico Miglino
# Version: 1.0
# Date: Sept, 2019
# License: LGPL 3.0
#
# Based on the reverse engineering work
# "Scripting Sphero's Star Wars Droids"
# by ~bbraun.
#
# Thanks to Arnaud Coolsaet who inspired the live chroma key
# methodological approach with openCV
# <http://www.synack.net/~bbraun/spherodroid/>
#
# Credits: 
#
# * Sphero (Sphero/inc) for the precious documentation on 
# low-level APIs for their Sphero robots 
# <https://github.com/sphero-inc/DeveloperResources>
#
# * Christopher Peplin for the pygatt Python library
# <https://github.com/peplin/pygatt>
#
# * Pimoroni for the complete and exhaustive documentation on their
# PiCade HAT <https://github.com/pimoroni/picade-hat>
#
# * Phil Hutchinson and Tariq Ahmad by Element14.com for providing the
# hardware
 
import pygatt
import time
import sys
import tty
import getopt
import ctypes

# Import specific BLE libraries. Pygatt should be installed in your
# Python environment.
from pygatt.backends import BLEBackend, Characteristic, BLEAddressType

# Initial command status
command = None
# Specify the Bluetooth address of the droid. Can be changed during
# the call to a command.
address = 'FD:F9:CA:74:DC:DA'
sendbytes = None
# If the flag is set the droid is set to sleep when the program exits
sleeponexit = False

# Commands dictionary in human redable form
commandmap = dict([
	("laugh", [0x0A,0x18,0x00,0x1F,0x00,0x32,0x00,0x00,0x00,0x00,0x00]),
	("yes", [0x0A,0x17,0x05,0x41,0x00,0x0F]),
	("no", [0x0A,0x17,0x05,0x3F,0x00,0x10]),
	("alarm", [0x0A,0x17,0x05,0x17,0x00,0x07]),
	("angry", [0x0A,0x17,0x05,0x18,0x00,0x08]),
	("annoyed", [0x0A,0x17,0x05,0x19,0x00,0x09]),
	("ionblast", [0x0A,0x17,0x05,0x1A,0x00,0x0E]),
	("sad", [0x0A,0x17,0x05,0x1C,0x00,0x11]),
	("scared", [0x0A,0x17,0x05,0x1D,0x00,0x13]),
	("chatty", [0x0A,0x17,0x05,0x17,0x00,0x0A]),
	("confident", [0x0A,0x17,0x05,0x18,0x00,0x12]),
	("excited", [0x0A,0x17,0x05,0x19,0x00,0x0C]),
	("happy", [0x0A,0x17,0x05,0x1A,0x00,0x0D]),
	("laugh2", [0x0A,0x17,0x05,0x1B,0x00,0x0F]),
	("surprise", [0x0A,0x17,0x05,0x1C,0x00,0x18]),
	("tripod", [0x0A,0x17,0x0D,0x1D,0x01]),
	("bipod", [0x0A,0x17,0x0D,0x1C,0x02]),
	("rot+", [0x8D,0x0A,0x17,0x0F,0x1C,0x42,0xB4,0x00,0x00,0xBD,0xD8]),
	("rot0", [0x8D,0x0A,0x17,0x0F,0x1E,0x00,0x00,0x00,0x00,0xB1,0xD8])
	])

# Generate the CRC 256 modulus sum of all the bytes bitwise inverted
def GenCrc(bytes):
	ret = 0;
	for b in bytes:
		ret += b
		ret = ret % 256
	
	return ~ret % 256

# Create the data packet to send to the droid
def BuildPacket(bytes):
	# 0x8D marks the start of a packet
	ret = [0x8D]
	for b in bytes:
		ret.append(b)

	# CRC is always the 2nd to last byte
	ret.append(GenCrc(bytes))

	# 0xD8 marks the end of a packet
	ret.append(0xD8)
	return ret

# Initialize the communication with the droid. If sleeping awake it
def r2d2_init():
	# Initialize the BLE Gatt adapter and start the connection
	# Note: no address type is specified.
	adapter = pygatt.GATTToolBackend()
	adapter.start()
	device = adapter.connect(address = address, address_type = BLEAddressType.random)
	# 'usetheforce...band' tells the droid we're a controller and prevents disconnection.
	device.char_write_handle(0x15, [0x75,0x73,0x65,0x74,0x68,0x65,0x66,0x6F,0x72,0x63,0x65,0x2E,0x2E,0x2E,0x62,0x61,0x6E,0x64], True)
	# wake from sleep?  Droid is responsive and front led flashes blue/red
	device.char_write_handle(0x1c, [0x8D,0x0A,0x13,0x0D,0x00,0xD5,0xD8], True)
	# Turn on holoprojector led, 0xff (max) intensity
	device.char_write_handle(0x1c, [0x8D,0x0A,0x1A,0x0E,0x1C,0x00,0x80,0xFF,0x32,0xD8], True)
	
	return device, adapter
	
###############
# Main program
###############

def main():
	
	sequences = []
	pexit = False	# Exit condition, never set to true. For future devel.

	# Init the connection
	r2d2, ble = r2d2_init()

	# Start reading the pad
	tty.setcbreak(sys.stdin)

	# Control loop
	while pexit == False:
		# Get the scancode from the mapped pad
		scancode = ord(sys.stdin.read(1))
		# In case of wrong scancode, command is set to False
		valid_command = True
		
		# Create the commands sequence
		if scancode == 65:		# Up
			sequences.append(commandmap["tripod"])
			sequences.append(commandmap["yes"])
		elif scancode == 66:		# Down
			sequences.append(commandmap["bipod"])
			sequences.append(commandmap["yes"])
		elif scancode == 67:		# Rot left
			sequences.append(commandmap["rot0"])
			sequences.append(commandmap["no"])
		elif scancode == 68:		# Rot right
			sequences.append(commandmap["rot+"])
			sequences.append(commandmap["surprise"])
		elif scancode == 122:		# Button 3, 4
			sequences.append(commandmap["laugh"])
			sequences.append(commandmap["happy"])
			sequences.append(commandmap["excited"])
		elif scancode == 32:		# Button 5
			sequences.append(commandmap["surprise"])
			sequences.append(commandmap["sad"])
			sequences.append(commandmap["scared"])
		elif scancode == 120:		# Button 6
			sequences.append(commandmap["confident"])
			sequences.append(commandmap["laugh2"])
		elif scancode == 105:		# Front left
			sequences.append(commandmap["angry"])
			sequences.append(commandmap["alarm"])
		elif scancode == 111:		# Front right
			sequences.append(commandmap["chatty"])
			sequences.append(commandmap["ionblast"])
		else:
			valid_command = False

		# Executes the command sequence
		if valid_command == True:		
			for seq in sequences:
				#device.char_write_handle(0x1c, commandmap[command], True)
				r2d2.char_write_handle(0x1c, BuildPacket(seq), True)

		# Empty the sequence list
		del sequences[:]

	ble.stop()

if __name__ == '__main__':
    main()
