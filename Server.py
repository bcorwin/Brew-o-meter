#Arguments:
##minLog
##comPort (do not need testMode if this is declared)
##testMode (Y/N)
###Examples: python Server.py minLog=15 comPort=3, python Server.py testMode=Y
###No spaces around the =

#Keys: temp_beer, light_amb, temp_amb, key = "beer", instant_override (time stamp)

import socket
import datetime
import time
import serial
import msvcrt
import csv
import re
import requests
import sys

def chkArduino():
	minLog, testMode, ser = initialize()
	
	sensorVars = [x for x in vars2pass(True, testMode)]
	sensorVars.sort()
	fileName = genCompLog("Logs\SENSOR LOG " + str(datetime.datetime.now().strftime("%Y%m%d_%H%M")) + ".csv", sensorVars)
	fileName_h = genCompLog(re.sub(".csv", "_h.csv", fileName), sensorVars)
	fileName_s = genCompLog(re.sub(".csv", "_s.csv", fileName), sensorVars)
	#Initialize vars
	lastLogAttempt = time.time()-60*minLog - 1
	allSums = vars2pass(True, testMode)
	allCnts = vars2pass(True, testMode)
	data = vars2pass(False, testMode)
	allSums_h = vars2pass(True, testMode)
	allCnts_h = vars2pass(True, testMode)
	data_h = vars2pass(False, testMode)
	allSums_s = vars2pass(True, testMode)
	allCnts_s = vars2pass(True, testMode)
	data_s = vars2pass(False, testMode)
	
	logEvent("Starting:minLog=" + str(minLog) + ":testMode=" + testMode + ":fileName=" + fileName)
	
	forceLog = "N"
	loggingOn = "Y"

	try: queuedLogsCnt = sum(1 for row in csv.reader(open("Logs\QUEUED LOGS.csv"))) - 1
	except:
		genCompLog("Logs\QUEUED LOGS.csv", sensorVars)
		queuedLogsCnt = 0
	try: open("Logs\FAILED QUEUES.csv")
	except: genCompLog("Logs\FAILED QUEUES.csv", sensorVars)
	
	genCompLog("Logs\READ VALUES.csv", sensorVars)
		
	#print("\nPress 'c' to cancel.")
	print("\nReading...")
	while True:
		currTime = time.time()
		
		evnt,val,con = evntListener(testMode)
		rr = None
		if evnt == "R":
			if val == None: rr = ("Success", "Current values:" + str(data))
			elif val.upper() in [x.upper() for x in sensorVars]: rr = ("Success", str(val) + ":" + str(data[val]))
			else: rr = ("Fail", str(val) + " is not valid.")
		elif evnt == "O":
			if loggingOn == "Y": rr = ("Success", "Data collection off.")
			else: rr = ("Fail", "Was already off.")
			loggingOn = "N"
		elif evnt == "L":
			if loggingOn == "N": rr = ("Success", "Data collection on.")
			else: rr = ("Fail", "Was already on.")
			loggingOn = "Y"
		elif evnt == "F":
			if loggingOn == "Y":
				forceLog = "Y"
				rr = ("Success", "Forcing log...")
			else: rr = ("Fail", "Must be on to force log.")
		elif evnt == "M":
			if loggingOn == "Y":
				if (val == None or val == "") and con != None: rr = ("Success", "Log frequency=" + str(minLog))
				else:
					if val == None and con == None: newVal = input("Current log time is " + str(minLog) + ". Enter new value: ")
					else: newVal = val
					try:
						if newVal != "":
							minLog = int(newVal)
							rr = ("Success", "Changed now minLog=" + str(minLog))
						else: rr = ("Success", "Not changed from minLog=" + str(minLog))
					except ValueError: rr = ("Fail", "Please enter a number. minLog=" + str(minLog))
			else: rr = ("Fail", "Must be on to change frequency.")
		elif evnt != None: rr = ("Fail", "Command does not exist:" + str(evnt))
		#elif evnt == "C": rr = ("Success", "Cancelled.")
		
		if con != None:
			try: con.sendall("|".join(rr).encode())
			except: logEvent("Failed to send response to Django")
			finally: con.close()
		if rr != None:
			logEvent(rr[1])
			if evnt != "F" and loggingOn == "Y": print("Reading...")
			#elif evnt == "C": break
			
		if loggingOn == "Y":
			#Reading and aggregate
			data, allSums, allCnts = readData(allSums, allCnts, ser, testMode, sensorVars)
			data_h, allSums_h, allCnts_h = readData(allSums_h, allCnts_h, ser, testMode, sensorVars, method = "H")
			data_s, allSums_s, allCnts_s = readData(allSums_s, allCnts_s, ser, testMode, sensorVars, method = "S")
				
			#Logging
			if currTime > (lastLogAttempt + 60*minLog) or forceLog == "Y":
				queuedLogsCnt = logData(queuedLogsCnt, data, fileName, sensorVars, testMode)
				log2computer(fileName_h, [-1,"NONE"], data_h, sensorVars)
				log2computer(fileName_s, [-1,"NONE"], data_s, sensorVars)
					
				#Reset
				lastLogAttempt = currTime
				allSums = vars2pass(True, testMode)
				allCnts = vars2pass(True, testMode)
				allSums_h = vars2pass(True, testMode)
				allCnts_h = vars2pass(True, testMode)
				forceLog = "N"
def logData(queuedLogsCnt, data, fileName, sensorVars, testMode):
	genCompLog("Logs\READ VALUES.csv", sensorVars)
	data["instant_override"] = int(round(datetime.datetime.now().timestamp(),0))
	
	response = logValues2django(data)
	log2computer(fileName, response, data, sensorVars)
	
	print(str(datetime.datetime.fromtimestamp(data["instant_override"]).strftime('%Y-%m-%d %H:%M:%S')) + "\t" + response[1])
	
	#Log failed attempts for later upload
	if  response[0] != 200:
		log2computer("Logs\QUEUED LOGS.csv", response, data, sensorVars)
		queuedLogsCnt += 1
		logEvent("Failed Upload:" + str(response[0]) + ":" + response[1] + ":" + str(data["instant_override"]))
	elif queuedLogsCnt > 0:
		logEvent("Attempting to upload queued files...")
		queuedLogsCnt = postQueued("Logs\QUEUED LOGS.csv", sensorVars, testMode)
	if response[0] == 200 and re.search("Success", response[1]) == None:
		logEvent("Failed Post:" + response[1] + ":" + str(data["instant_override"]))
	return(queuedLogsCnt)
def readData(allSums, allCnts, ser, testMode, sensorVars, method = "A"):
	tempVals = vars2pass(True, testMode)
	data = vars2pass(False, testMode)
	if testMode != "Y": ardVal = readArduino(ser)
	else: ardVal = "{'chk_sum':96.80, 'light_amb':21,.00 'temp_amb':75.80}"

	for var in sensorVars:
		readVal = readJSON(var, ardVal)
		if readVal != None:
			#if var.split("_")[0].upper() == "TEMP" and readVal > 80:
			#	logEvent("Large temp reading:" + ardVal)
			tempVals[var] = readVal
	
	try:
		chk_sum = int(readJSON("chk_sum", ardVal))
		r_chk_sum = int(sum([tempVals[n] for n in tempVals]))
	except:
		chk_sum = None
		r_chk_sum = None
	
	if chk_sum == None or r_chk_sum == None or chk_sum != r_chk_sum:
		logEvent("Error: chk_sum does not match:" + str(ardVal))
	else:
		for var in sensorVars:
			allCnts[var] = allCnts[var] + 1.0
			if method == "A":
				allSums[var] = allSums[var] + tempVals[var]
				data[var] = round(allSums[var]/allCnts[var],1)
			elif method == "H":
				try: allSums[var] = allSums[var] + 1.0/tempVals[var]
				except: allSums[var] = allSums[var] + 0.0
				try: data[var] = round(allCnts[var]/allSums[var],1)
				except: data[var] = 0.0
			elif method == "S":
				allSums[var] = allSums[var] + tempVals[var]
				data[var] = round(tempVals[var],1)

		log2computer("Logs\READ VALUES.csv", [-1,"NONE"], tempVals, sensorVars)
	return([data, allSums, allCnts])
def evntListener(testMode):
	#Input status (code location) so that can be sent back to server if asked
	if msvcrt.kbhit() == 1:
		try: out = msvcrt.getch().decode().upper()
		except: out = (None, None, None)
		return((out, None, None))
	else:
		r, val, con = socketListener(1, testMode)
		if r == "Success":
			logEvent("Remote request:" + str(val))
			s = val.split("=")
			if len(s) > 1: return(s[0].upper(),s[1], con)
			else: return((val.upper(),None, con))
		else: return((None, None, None))
def socketListener(timeout, testMode):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	if testMode != "Y":
		server_ip = socket.gethostbyname(socket.gethostname())
		server_address = (server_ip, 6005)
	else: server_address = ('localhost', 6005)
	
	sock.bind(server_address)
	sock.listen(1)
	if timeout != None: sock.settimeout(timeout)
	
	try: connection, client_address = sock.accept()
	except: return(("Timeout", None, None))
	
	try:
		data = connection.recv(32).decode()
		if data != "": return(("Success", data, connection))
	except:
		connection.close()
		return(("No data", None, None))
	return(("Unknown", None, None))
def postQueued(file, sensorVars, testMode):
	f = open(file)
	vals = [row for row in csv.reader(f)]
	f.close()
	genCompLog(file, sensorVars)
	header = [x.lower() for x in vals[0]]
	
	columns = vars2pass(True, testMode)
	for var in columns: columns[var] = header.index(var)
	columns["instant_override"] = header.index("instant_override")
	
	for r in range(1, len(vals)):
		row = vals[r]
		data = vars2pass(False, testMode)
		for var in sensorVars: data[var] = row[columns[var]]
		data["instant_override"] = int(row[columns["instant_override"]])
		
		response = logValues2django(data)
		if response[0] != 200 or re.search("Success", response[1]) == None:
			log2computer("Logs\FAILED QUEUES.csv", response, data, sensorVars)
			logEvent("Failed Queued Upload:" + response[1] + ":" + str(data["instant_override"]))
		else: logEvent("Successful Queued Push:" + str(data["instant_override"]))
	return(0)
def readArduino(ser):
	ser.flushInput()
	ser.write(b'R')
	msg = ser.readline().decode()
	return msg
def readJSON(var, str):
	pattern = "'" + var + "':([^,]*)[,}]"
	try: out = float(re.search(pattern, str, re.IGNORECASE ).group(1))
	except:
		#logEvent("Bad reading.")
		out = None
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
def log2computer(fileName, response, vals, sensorVars):
	if "instant_override" not in vals or vals["instant_override"] == 0:
		timestamp = int(round(datetime.datetime.now().timestamp(),0))
	else: timestamp = vals["instant_override"]
	
	addRow  = str(datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')) + "," + str(timestamp) + ","
	addRow += str(response[0]) + "," + response[1]
	for var in sensorVars: addRow += "," + str(vals[var])
	
	fd = open(fileName,'a')
	fd.write(addRow + "\n")
	fd.close()
def logEvent(msg):
	msg = str(msg).replace('\n', ' ').replace('\r', '').replace('\t', '    ')
	msg = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "\tLogged: " + msg
	print(msg)
def vars2pass(sensorVarsOnly, testMode):
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
		"temp_amb": 0.0,
		"pres_beer": 0.0
		##ADD NEW VAR HERE##
	}
	if sensorVarsOnly == True: out = sensorVars
	else: 
		out = otherVars.copy()
		out.update(sensorVars)
	return(out)
def initialize():
	minLog = 15 #Number of minutes between logs to Django (data under this is aggregated)
	testMode = None
	comPort = None
	
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
		ser = serial.Serial(comPort, 9600, timeout = 1)
		
		ser.flushInput()
		ser.write(b'E')
		ser.readline()
	else: ser = None
	return([minLog, testMode, ser])

chkArduino()