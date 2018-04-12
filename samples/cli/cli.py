# *****************************************************************************
# Copyright (c) 2014, 2016 IBM Corporation and other Contributors.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html 
#
# Contributors:
#   David Parker 			- Initial Contribution
#   Amit M Mangalvedkar		- Modified as per ReST v2
# *****************************************************************************

import argparse
import time
import sys
import platform
import json
import signal
import iso8601
import pytz
from datetime import datetime
from uuid import getnode as get_mac


try:
	import ibmiotf.application
except ImportError:
	# This part is only required to run the sample from within the samples
	# directory when the module itself is not installed.
	#
	# If you have the module installed, just use "import ibmiotf"
	import os
	import inspect
	cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"../../src")))
	if cmd_subfolder not in sys.path:
		sys.path.insert(0, cmd_subfolder)
	import ibmiotf.application



def interruptHandler(signal, frame):
	client.disconnect()
	sys.exit(0)


def typeList(maxResults = 100):
	_typeListPage(maxResults, None, 0)

def _typeListPage(maxResults, bookmark, count=0):
	global client, cliArgs
	# Check whether we've already met the request
	if count >= maxResults:
		return
	
	# Only retrieve the number of results that we need to complete the request
	# Maximum page size of 10 at a time (no need to be this low, however it's
	# useful to demonstrate how paging works to set this to a low value)
	limit = min(maxResults-count, 10)
	
	typeList = client.api.getDeviceTypes(parameters = {"_limit": limit, "_bookmark": bookmark, "_sort": "id"})
	resultArray = typeList['results']
	for deviceType in resultArray:
		if cliArgs.json:
			print(deviceType)
		else:
			count += 1;
			if 'description' not in deviceType:
				deviceType['description'] = None
			print("%3s %-24s %-32s" % (count, deviceType['id'], deviceType['description']))
	# Next page
	if "bookmark" in typeList and len(resultArray) > 0:
		bookmark = typeList["bookmark"]
		_typeListPage(maxResults, bookmark, count)

def deviceList(maxResults = 100):
	today = datetime.now(pytz.timezone('UTC'))
	_deviceListPage(maxResults, None, today, 0)

def _deviceListPage(maxResults, bookmark, today, count=0):
	global client, cliArgs
	# Check whether we've already met the request
	if count >= maxResults:
		return
	
	# Only retrieve the number of results that we need to complete the request
	# Maximum page size of 10 at a time (no need to be this low, however it's
	# useful to demonstrate how paging works to set this to a low value)
	limit = min(maxResults-count, 10)
	
	deviceList = client.api.getDevices(parameters = {"_limit": limit, "_bookmark": bookmark, "_sort": "typeId,deviceId"})
	resultArray = deviceList['results']
	for device in resultArray:
		if cliArgs.json:
			print(device)
		else:
			count += 1;
			#print("Device = ",device['uuid'])
			delta = today - iso8601.parse_date(device['registration']['date'])
			print("%3s %-60sRegistered %s days ago by %s" % (count, device['typeId'] + ":" + device['deviceId'], delta.days, device['registration']['auth']['id']))
	# Next page
	if "bookmark" in deviceList:
		bookmark = deviceList["bookmark"]
		_deviceListPage(maxResults, bookmark, today, count)
	

def deviceGet(typeId, deviceId):
	global client, cliArgs
	device = client.api.getDevice(typeId, deviceId)
	if cliArgs.json:
		print(device)
	else:
		today = datetime.now(pytz.timezone('UTC'))
		delta = today - iso8601.parse_date(device['registration']['date'])
		print("%-40sRegistered %s days ago by %s" % (device['deviceId'], delta.days, device['registration']['auth']['id']))


def deviceAdd(typeId, deviceId, metadata):
	global client, cliArgs
	device = client.api.registerDevice(typeId, deviceId, metadata)
	if cliArgs.json:
		print(device)
	else:
		print("%-40sGenerated Authentication Token = %s" % (device['deviceId'], device['authToken']))

def deviceRemove(typeId, deviceId):
	global client
	try:
		client.api.deleteDevice(typeId, deviceId)
	except Exception as e:
		print(str(e))

def connectionLogsForDevice(args):
	global client
	result = client.api.getConnectionLogs({"typeId": args[0], "deviceId": args[1]})
	
	if cliArgs.json:
		print(result)
	else:
		for log in result:
			print("%-30s %s" % (log["timestamp"], log["message"]))

def lastEvent(args):
	global client
	result = []
	print("args: " + args[0] + " " + args[1])
	if len(args) == 2:
		result = client.api.getLastEvents(args[0], args[1])
	elif len(args) == 3:
		result.append(client.api.getLastEvent(args[0], args[1], args[2]))
	
	if cliArgs.json:
		print(result)
	else:
		for event in result:
			if "data" in event:
				# The API will attempt to parse the payload back into a python dictionary, if it 
				# was able to then the content of the payload will be available as a python 
				# dictionary as well ... so let's print that out instead of the base64 encoded payload
				print("%-20s %s" % (event["eventId"], json.dumps(event["data"])))
			else:
				# The library wasn't able to parse the payload itself, it's up to your application to decide
				# how to decode the payload
				print("%-20s %s // %s" % (event["eventId"], event["format"], event["payload"]))

def metering(args):
	global client
	period = {'start' : args[0], 'end' : args[1] }
	
	adc = client.api.getActiveDevices(options = period)
	traffic = client.api.getDataTraffic(options = period)
	storage = client.api.getHistoricalDataUsage(options = period)
	
	print("Average daily active devices = %.2f" % (adc["average"]))
	print("Average daily data usage     = %s kb" % (traffic["average"]/1024))
	print("Total data usage             = %s mb" % (traffic["total"]/1024/1024))
	print("Average daily storage usage  = %.2f gb" % (storage["average"]/1024))
	
	
def usage():
	print("""
usage: cli -h
       cli -c CONFIG [-j] COMMAND
       cli -c CONFIG -i [-j]

Simple CLI for IBM Watson IoT Platform

options:
  -h, --help                   show this help message and exit
  -c CONFIG, --config CONFIG   path to application config file  
  -i, --interactive            enable interactive mode
  -j, --json                   enable raw JSON response output""")
	cmdUsage()
	
	
def cmdUsage():
	print("""
commands:
  type list [MAX RESULTS(100)]
  device list [MAX RESULTS(100)]
  device add TYPE_ID DEVICE_ID
  device get TYPE_ID DEVICE_ID
  device remove TYPE_ID DEVICE_ID
  device update TYPE_ID DEVICE_ID METADATA
  device log connection TYPE_ID DEVICE_ID
  lastevent TYPE_ID DEVICE_ID [EVENT_ID]
  usage START_DATE END_DATE""")

def processCommandInput(words):
	if len(words) < 1:
		cmdUsage()
		return False
	
	elif words[0] == "usage":
		if len(words) < 3:
			cmdUsage()
			return False
		metering(words[1:])
		return True
	
	elif words[0] == "lastevent":
		if len(words) < 3:
			cmdUsage()
			return False
		lastEvent(words[1:])
		return True
		
	elif words[0] == "type":
		if len(words) < 2:
			cmdUsage()
			return False
			
		elif words[1] == "list":
			if len(words) == 2:
				typeList()
			else:
				try:
					maxResults = int(words[2])
					typeList(maxResults)
				except ValueError:
					cmdUsage()
					return False
                
			return True
	
	elif words[0] == "device":
		if len(words) < 2:
			cmdUsage()
			return False
			
		elif words[1] == "log":
			if len(words) < 5:
				cmdUsage()
				return False
			else:
				if words[2] == "connection" or words[2] == "connect":
					connectionLogsForDevice(words[3:])
					return True
				else:
					cmdUsage()
					return False				
					
		elif words[1] == "list":
			if len(words) == 2:
				deviceList()
			else:
				try:
					maxResults = int(words[2])
					deviceList(maxResults)
				except ValueError:
					cmdUsage()
					return False
                
			return True
			
		elif words[1] == "get":
			if len(words) < 4:
				cmdUsage()
				return False
			deviceGet(words[2], words[3])
			return True
			
		elif words[1] == "add":
			if len(words) < 4:
				cmdUsage()
				return False
			metadata = None
			if len(words) == 5:
				metadata = json.loads(words[4])
			deviceAdd(words[2], words[3], metadata)
			return True
			
		elif words[1] == "remove":
			if len(words) < 4:
				cmdUsage()
				return False
			deviceRemove(words[2], words[3])
			return True
			
		elif words[1] == "update":
			if len(words) < 4:
				cmdUsage()
				return False
			metadata = None
			if len(words) == 5:
				metadata = json.loads(words[4])
			updateDevice(words[2], words[3], metadata)
			return True
	
	cmdUsage()
	return False

if __name__ == "__main__":
	signal.signal(signal.SIGINT, interruptHandler)

	parser = argparse.ArgumentParser(description='Simple CLI for IBM IOT Foundation', add_help=False)
	parser.add_argument('-h', '--help', action='store_true')
	parser.add_argument('-c', '--config')
	parser.add_argument('-i', '--interactive', action='store_true')
	parser.add_argument('-j', '--json', action='store_true')
	parser.add_argument('commands', nargs='*', type=str)

	cliArgs = parser.parse_args()
	
	if cliArgs.help:
		usage()
		sys.exit(0)
	
	client = None
	try:
		if cliArgs.config is not None:
			options = ibmiotf.application.ParseConfigFile(cliArgs.config)
		else:
			sys.exit(1)
		client = ibmiotf.application.Client(options)
	except ibmiotf.ConfigurationException as e:
		print(str(e))
		sys.exit()
	except ibmiotf.UnsupportedAuthenticationMethod as e:
		print(str(e))
		sys.exit()
	except ibmiotf.ConnectionException as e:
		print(str(e))
		sys.exit()
	
	if not cliArgs.interactive:
		rc = processCommandInput(cliArgs.commands)
		if rc:
			sys.exit(0)
		else:
			sys.exit(1)
	else:
		print("(Press Ctrl+C to disconnect)")
		
		while True:
			try:
#				command = raw_input("%s@%s > " % (options['auth-key'], options['org']))
				command = input("%s@%s > " % (options['auth-key'], options['org']))
				words = command.split()
				processCommandInput(words)

			except KeyboardInterrupt:
				client.disconnect()
				sys.exit(0)

