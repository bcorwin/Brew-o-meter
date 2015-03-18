#Arguments:
##minLog
##comPort (do not need testMode if this is declared)
##testMode (Y/N)
###Examples: python Server.py minLog=15 comPort=3, python Server.py testMode=Y
###No spaces around the =

#Keys: temp_beer, light_amb, temp_amb, key = "beer", instant_override (time stamp)

import datetime
import time
import serial
import msvcrt
import csv
import re
import requests
import sys

#Defaults
minLog = 15 #Number of minutes between logs to Django (data under this is aggregated)
testMode = None
comPort = None

def chkArduino(minLog, testMode, ser):
	sensorVars = [x for x in vars2pass(True)]
	sensorVars.sort()
	fileName = genCompLog("Logs\SENSOR LOG " + str(datetime.datetime.now().strftime("%Y%m%d_%H%M")) + ".csv", sensorVars)
	#Initialize vars
	lastLogAttempt = time.time()-60*minLog - 1
	allSums = vars2pass(True)
	allCnts = vars2pass(True)
	data = vars2pass(False)
	
	logEvent("Starting|minLog=" + str(minLog) + "|testMode=" + testMode + "|fileName=" + fileName)
	
	forceLog = "N"
	queuedLogs = "Logs\QUEUED LOGS.csv"
	try:
		queuedLogsCnt = sum(1 for row in csv.reader(open(queuedLogs))) - 1
	except:
		genCompLog(queuedLogs, sensorVars)
		queuedLogsCnt = 0		
	
	print("Press 'c' to cancel.")
	while True:
		currTime = time.time()
		
		evnt = evntListener()
		if evnt == "C":
			print(logEvent("Cancelled."))
			return("Y")
		elif evnt == "F":
			forceLog = "Y"
			print(logEvent("Forcing log..."))
		elif evnt == "M":
			newVal = input("Current log time is " + str(minLog) + ". Enter new value: ")
			try:
				if newVal != "":
					minLog = int(newVal)
					print(logEvent("minLog changed to " + str(minLog)))
			except ValueError: print("Please enter a number")
			print("\nReading...")
		elif evnt == "B":
			print("Test break.")
			return(None)
				
		#Reading and aggregate
		if testMode != "Y": readValue = readArduino(ser)
		else: readValue = "{'light_amb':21, 'temp_amb':75.80}"
		
		for var in sensorVars:
			allSums[var] = allSums[var] + readJSON(var, readValue)
			allCnts[var] = allCnts[var] + 1
			data[var] = round(allSums[var]/allCnts[var],1)
			
		#Logging
		if currTime > (lastLogAttempt + 60*minLog) or forceLog == "Y":
			data["instant_override"] = int(round(datetime.datetime.now().timestamp(),0))
			
			response = logValues2django(data)
			log2computer(fileName, response, data, sensorVars)
			
			
			print(str(datetime.datetime.fromtimestamp(data["instant_override"]).strftime('%Y-%m-%d %H:%M')) + " " + response[1])
			
			#Log failed attempts for later upload
			if  response[0] != 200:
				log2computer(queuedLogs, response, data, sensorVars)
				queuedLogsCnt += 1
				logEvent("Failed Upload|" + str(response[0]) + "|" + response[1] + "|" + str(data["instant_override"]))
			elif queuedLogsCnt > 0:
				print(logEvent("Attempting to upload queued files..."))
				queuedLogsCnt = postQueued(queuedLogs, sensorVars)
			if response[0] == 200 and re.search("Success", response[1]) == None:
				logEvent("Failed Post|" + response[1] + "|" + str(data["instant_override"]))
				
			
			#Reset
			lastLogAttempt = currTime
			allSums = vars2pass(True)
			allCnts = vars2pass(True)
			forceLog = "N" 
			print("\nReading...")

def evntListener():
	#Return tuples key code and value if value is to be changed
	#Input status (code location) so that can be sent back to server if asked
	if msvcrt.kbhit() == 1:
		try: out = msvcrt.getch().decode().upper()
		except: out = None
		return(out)
	else: return(socketListener())
	

def socketListener():
	return(None)
	
def postQueued(file, sensorVars):
	out = 0
	f = open(file)
	vals = [row for row in csv.reader(f)]
	f.close()
	genCompLog(file, sensorVars)
	header = [x.lower() for x in vals[0]]
	
	columns = vars2pass(True)
	for var in columns: columns[var] = header.index(var)
	columns["instant_override"] = header.index("instant_override")
	
	for r in range(1, len(vals)):
		row = vals[r]
		data = vars2pass(False)
		for var in sensorVars: data[var] = row[columns[var]]
		data["instant_override"] = int(row[columns["instant_override"]])
		
		response = logValues2django(data)
		if response[0] != 200:
			log2computer(file, response, data, sensorVars)
			out += 1
			print(logEvent("Failed Queued Upload|" + response[1] + "|" + str(data["instant_override"])))
		elif re.search("Success", response[1]) == None:
			print(logEvent("Failed Queued Post|" + response[1] + "|" + str(data["instant_override"])))
		else:
			print(logEvent("Successful Queued Push|" + str(data["instant_override"])))
	return(out)
def readArduino(ser):
	fromArduino = ser.readline()
	message = fromArduino.decode("utf-8")
	return message

def readJSON(var, str):
	pattern = "'" + var + "':([^,]*)[,}]"
	if re.search(pattern, str) != None:
		out = float(re.search(pattern, str, re.IGNORECASE ).group(1))
	else:
		out = 0.0
	return(out)

def logValues2django(data):	
	try:
		response = requests.post('https://cutreth.herokuapp.com/monitor/api/', data=data)
		return[response.status_code, response.text	]
	except:
		return[-1, "Unknown Error"]

def genCompLog(fileName, sensorVars):
	with open(fileName, 'w', newline='') as csvfile:
		logfile = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
		logfile.writerow(['Timestamp'] + ['instant_override'] + ['Server Code'] +  ['Server Response Text'] + [x for x in sensorVars])
	return fileName

def log2computer(fileName, response, data, sensorVars):
	addRow  = str(datetime.datetime.fromtimestamp(data["instant_override"]).strftime('%Y-%m-%d %H:%M:%S')) + "," + str(data["instant_override"]) + ","
	addRow += str(response[0]) + "," + response[1]
	for var in sensorVars: addRow += "," + str(data[var])
	
	fd = open(fileName,'a')
	fd.write(addRow + "\n")
	fd.close()
	
def logEvent(msg):
	logfile = open("Logs\EVENT LOG.csv", "a")
	logfile.write(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "," + msg + "\n")	
	return(msg)
	
def vars2pass(sensorVarsOnly):
	if sensorVarsOnly == None: sensorVarsOnly = False
	if testMode == "Y": key = "test"
	else: key = "beer"
	otherVars = {
		"key": key,
		"instant_override": 0,
		"temp_unit": "F"
	}
	sensorVars = {
		"temp_beer": 0.0,
		"light_amb": 0.0,
		"temp_amb": 0.0
		##ADD NEW VAR HERE##
	}
	if sensorVarsOnly == True: out = sensorVars
	else: 
		out = otherVars.copy()
		out.update(sensorVars)
	return(out)
	
def keepRunning(minLog, testMode, ser):
	exitServer = "N"
	forceAttempt = "N"
	attemptWaitTime = 5
	
	exitServer = chkArduino(minLog, testMode, ser)
	print("Waiting to try again...\n")
	lastAttempt = time.time()
	while exitServer != "Y":
		evnt = evntListener()
		if evnt == 'C':
			print("Cancelled.")
			exitServer = "Y"
		if evnt == "F":
			print("Forcing attempt...")
			forceAttempt = "Y"
			
		if time.time() > (lastAttempt + 60*attemptWaitTime) or forceAttempt == "Y":
			lastAttempt = time.time()
			forceAttempt = "N"
			print(logEvent("Attempting to restart chkArduino.\n"))
			try: exitServer = chkArduino(minLog, testMode, ser)
			except:
				print(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " " + logEvent("chkArduino failed for unknown reason"))
				print("Waiting to try again...\n")

#Get arguments:
if len(sys.argv) > 1:
	for a in sys.argv:
		arg = a.split("=")
		if len(arg) > 1:
			if(arg[0].upper() == "MINLOG"): minLog = int(arg[1])
			if(arg[0].upper() == "COMPORT"): comPort = int(arg[1])
			if(arg[0].upper() == "TESTMODE"): testMode = arg[1].upper()

if comPort != None: testMode = "N"
if testMode == None: testMode = input("Test mode? (Y/N) ").upper()
if testMode != "Y":
	if comPort == None: comPort = input("Enter COM port: ").upper()
	comPort = "COM" + str(comPort)
	ser = serial.Serial(comPort, 9600)
else: ser = None

keepRunning(minLog, testMode, ser)