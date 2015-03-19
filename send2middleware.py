def send2middleware(message, testMode = False):
	import socket	
	
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	if testMode == False:
		server_ip = socket.gethostbyname('benjeye.ddns.net')
		server_address = (server_ip, 6005)
	else: server_address = ('localhost', 6005)
	
	try: sock.connect(server_address)
	except: return(("Timeout", None))

	try:
		# Send data
		sock.sendall(message.encode())
		# Look for the response
		data = sock.recv(32).decode()
		sock.close()
		r,msg = data.split("|")
		return((r, msg))
	except:
		sock.close()
		return(("No response", None))
	return(("Unknown", None))

# messages:
## F - force a log or attempt to rerun main loop (depends on state)
## M=1 - set the log period to 1 minutes (value required)
## C - turns off server permanently
## R=var_name - get the averages that are currently in memory for var_name

# Example usage:
## response, msg = send2middleware("f")
## response, msg = send2middleware("m=1")
