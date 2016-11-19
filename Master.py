import socket
import sys
import string
import struct
import binascii
from threading import Thread, Lock
import time

# Global variables
TTL = 20
previousNextSlaveIP = -1;
portNum = int(sys.argv[1])
myRID = 0
myGID = 1
slaveRID = 1
nextSlaveIP = -1
nextSlavePort = -1
socket_UDP = -1
magic_number = 0x1234
mutex = Lock()

#Compute the checksum of an item
def compute_checksum(buf):
    chksum = 0
    pointer = 0
    for element in buf:
        chksum += int(element, 16)
        chksum = (chksum >> 8) + (chksum & 0xff)
    chksum += (chksum >> 8)
    return (~chksum) & 0xff

# Receive and handle requests from Slaves to join the ring
def handleJoinRequests():

	packed_clientIP = -1
	global nextSlaveIP
	global nextSlavePort
	global slaveRID

	# Create a TCP socket
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	except socket.error:
		print 'Master (receiving function): Error - socket creation failure'
		exit(1)

	# Initially, both IP address variables are set to hostname
	# because the master is the only node in the ring.
	# Mutex is needed for threading
	mutex.acquire()
	nextSlaveIP = myIPaddress = socket.gethostbyname(socket.gethostname())
	mutex.release()

	server_address = ('', portNum)

	# Attempt to bind the socket to the specified port
	try:
		sock.bind(server_address)

	except socket.error:
		print 'Master (receiving function): Error - socket bind failure'
		exit(1)

	print 'Master: Starting up on port', sys.argv[1]

	# Listen for incoming connections
	sock.listen(1)

	# Continuously loop so that any number of Slaves can request to join
	while True:

		# Receive and accept a connection
		connection, slave_address = sock.accept()

		try:
			print 'Master (join function): Received connection from', slave_address[0]

			slave_IP = slave_address[0]
			slave_Port = slave_address[1]

			data = connection.recv(16)
			dataCharArray = list(binascii.hexlify(data))

			#GID_received is the GID of the creator or the slave
			GID_received = str(dataCharArray[0]) + str(dataCharArray[1])

			#magic_number is used by the nodes to test the validity of messages using this protocol
			#ignore the request if the message is not valid (different from 3 bytes or not containing the magic number).
			received_magic_number = str(dataCharArray[2]) + str(dataCharArray[3]) + str(dataCharArray[4]) + str(dataCharArray[5])

			GID_received = int(GID_received)
			received_magic_number = int(received_magic_number, 16)

			# print 'Master: GID_received =', GID_received
			# print 'Master: magic_number = 0x%x' % received_magic_number

			if received_magic_number != magic_number:
				print 'Master (join function): Error - invalid magic number received from Slave'
				# exit(1)

			# Convert nextSlaveIP to integer format for sending
			packed_nextSlaveIP = struct.unpack("I", socket.inet_aton(nextSlaveIP))[0]

			# Send the response packet
			reply = struct.pack("!BHBI", myGID, magic_number, slaveRID, packed_nextSlaveIP)

			mutex.acquire()
			nextSlaveIP = slave_IP      # The next slave in the ring is the slave that just joined
			nextSlavePort = slave_Port
			slaveRID = slaveRID + 1     # Increment slaveRID for the next slave
			mutex.release()

			if reply:
				print 'Master (join function): Sending response back to Slave'
				connection.sendall(reply)

		finally:
			# Close the connection to the slave.
			# It's no longer needed since the slave has already joined
			connection.close()


# Receive packets from the slave "behind" the Master on the ring. Display the message in
# in the packet if this node is the intended destination. Otherwise, forward it to the
# next node on the ring
def receivePacketAndForward():

	# Continuously receive messages and handle them accordingly
    while True:
		# Begin to receive data. This function will block until data arrives. Note
		# that 1024 is the size of the buffer in bytes
        data, sourceAddress = socket_UDP.recvfrom(1024)
        dataCharArray = list(binascii.hexlify(data))

        print("MESSAGE RECIEVED")
        checksumArr = list()
        for i in range (len(dataCharArray) - 2):
            checksumArr[i] = dataCharArray[i]
        incomingCalcChecksum = compute_checksum(list(binascii.hexlify(checksumArr)))
        #if (incomingCalcChecksum == int(dataCharArray[len(dataCharArray)]-1)):
        if(incomingCalcChecksum == dataCharArray[len(dataCharArray) - 1]):
		    # Unpack the received data
            GID_received = int(str(dataCharArray[0]) + str(dataCharArray[1]))
            received_magic_number = int(str(dataCharArray[2]) + str(dataCharArray[3]) + str(dataCharArray[4]) + str(dataCharArray[5]))
            TTL = int(str(dataCharArray[6]) + str(dataCharArray[7]))
            destination_RID = int(str(dataCharArray[8]) + str(dataCharArray[9]))
            RID_src = int(str(dataCharArray[10]) + str(dataCharArray[11]))

            # If the packet's destination was this node, then display the packet's message
            if myRID == destination_RID:
                message = ""
                for i in range(12, len(dataCharArray) - 2):
                    message += str(dataCharArray[i])
                print 'Master (receiving function): Received message - ', message

		    # Otherwise, forward the packet onward
            else:
                mutex.acquire()
                socket_UDP.sendto(data, (nextSlaveIP, (10010 + (myGID * 5) + slaveRID)))
                mutex.release()


# Allow the user to send a message to a specified node
def sendUserMessage():

	# Continuously prompt the user for data to send
	while True:

		print 'Master: Messages can now be sent along the ring'
		destination_RID = raw_input('Master: Enter the Ring ID of a node to send a message to: ')
		message = raw_input('Master: Enter a message to send: ')
        if sys.getsizeof(message) > 64:
            print 'Master: Message is too long to be sent.'
        else:
            packet = struct.pack("!BhBBBp" + charlength + "c", 0, GID, 0x1234, TTL, destination_RID, 0, message)
            checksum = compute_checksum(list(packet))
            packet = packet = struct.pack("!BhBBBpB" + charlength + "c", 0, GID, 0x1234, TTL, destination_RID, 0, message, checksum)

            # Send the message to the next node on the ring
            #mutex.acquire()
            socket_UDP.sendto(packet, (nextSlaveIP, (10010 + (myGID * 5) + (slaveRID - 1))))
            #mutex.release()


# Create a UDP socket for sending and receiving data at
try:
	socket_UDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

except socket.error:
	print 'Master (main function): Error - socket creation failure'
	exit(1)

myAddress = ('', (10010 + (myGID * 5) + myRID))

# Attempt to bind the socket to the appropriate port
try:
	socket_UDP.bind(myAddress)

except socket.error:
	print 'Master (main function): Error - socket bind failure'
	exit(1)

thread_handleJoinRequests = Thread(name='handleJoinRequests', target=handleJoinRequests)
thread_receivePacketAndForward = Thread(name='receivePacketAndForward', target=receivePacketAndForward)
thread_sendUserMessage = Thread(name='sendUserMessage', target=sendUserMessage)

# Start the threads
thread_handleJoinRequests.start()
time.sleep(1)	# Wait for the thread to set up
thread_receivePacketAndForward.start()
time.sleep(1)	# Wait for the thread to set up
thread_sendUserMessage.start()
