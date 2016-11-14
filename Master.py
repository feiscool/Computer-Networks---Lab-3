import socket
import sys
import string
import struct
import binascii
from threading import Thread, Lock
import time

previousNextSlaveIP = 0; #i think this is myIPaddress from before. needs to be tested
mutex = Lock()
socket_receiveAndForward = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
portNum = int(sys.argv[1])

#setting up token ring
def handleJoinRequests():
    myRID = 0
    slaveRID = 1
    myGID = 1
    magic_number = 0x1234
    packed_clientIP = -1

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #initially, both IP address variables are set to hostname
    #because the master is the only node in the ring
    global nextSlaveIP
    mutex.acquire()
    nextSlaveIP = myIPaddress = socket.gethostbyname(socket.gethostname())
    mutex.release()

    #get port number from argv
    portNum = int(sys.argv[1])
    # Bind the socket to the port
    server_address = ('', portNum)
    print 'Master-handleJoinRequests(): Starting up on port', sys.argv[1]
    sock.bind(server_address)
    # Listen for incoming connections
    sock.listen(1)

    while True:
        # Wait for a connection
        # print 'Master: Waiting for a connection'
        connection, slave_address = sock.accept()
        try:    # Receive the data in small chunks and retransmit it
            print 'Master-handleJoinRequests(): Received connection from', slave_address[0]

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
                print 'Master-handleJoinRequests(): Error - invalid magic number received from Slave'
                # exit(1)

            # Convert nextSlaveIP to integer format for sending
            packed_nextSlaveIP = struct.unpack("I", socket.inet_aton(nextSlaveIP))[0]

            # Send the response packet
            reply = struct.pack("!BHBI", myGID, magic_number, slaveRID, packed_nextSlaveIP)

            nextSlaveIP = slave_IP      # Next slave is the slave that just joined
            slaveRID = slaveRID + 1     # Increment slaveRID for the next slave

            if reply:
                print 'Master-handleJoinRequests(): Sending response back to Slave'
                connection.sendall(reply)
                # print 'Master: Sent %s bytes back to %s' % (len(reply), client_IP)

        finally:
            # Clean up the connection
            connection.close()

#get user input and send it
#loop until receive input then send it out to nextSlaveIP.
def receivePacketAndForward():
    #create global UDP socket
    global socket_receiveAndForward
    # Bind the socket to the port
    server_address = ('', portNum)
    print "server_address", server_address
    socket_receiveAndForward.bind(server_address)

    #loop until a message is received, then send it to nextSlaveIP
    while True:
        #Wait for a packet to arrive via UDP
        print ("Master- receiveandForward: Calling recvfrom()...")
        data, address = socket_receiveAndForward.recvfrom(1024)
        print "Master: Address:\n", address
        print "Master: Data from packet:\n", data
        dataCharArray = list(binascii.hexlify(data))
        #Unpack the packet
        GID_received = str(dataCharArray[0]) + str(dataCharArray[1])
        #ignore the request if the message is not valid (different from 3 bytes or not containing the magic number).
        received_magic_number = str(dataCharArray[2]) + str(dataCharArray[3]) + str(dataCharArray[4]) + str(dataCharArray[5])
        TTL = str(dataCharArray[6]) + str(dataCharArray[7])
        RID_dest = str(dataCharArray[8]) + str(dataCharArray[9])
        RID_src = str(dataCharArray[10]) + str(dataCharArray[11])
        #TODO: store up to 64 bytes for the message, then 1 byte checksum

        if myRID == RID_dest:
            print (message) #not defined yet
        else:
            self.send(packet) #not defined yet

#listen for a packet and possibly sending it
#When a message is received, it must check the destination ring ID.
#If the RID is 0, the thread should display the message.
#If not, then the packet should be sent to nextSlaveIP.
def sendUserMessage(packet):
    #check the RID by unpacking the packet

    #Send the new packet
     send(packet)

def send(packet):
    socket_send
     if (nextSlaveIP == previousNextSlaveIP):
         socket_receiveAndForward.sendto(packet, nextSlaveIP)
     elif (previousNextSlaveIP == 0):
        #Make a new UDP socket using nextSlaveIP
        socket_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #Send “Packet” using the new socket
        sent = socket_send.sendto(packet, nextSlaveIP)

     else:
          #Close the old UDP socket
          socket_receiveAndForward.close()
          #Make a new UDP socket using nextSlaveIP
          #this socket does not have to be gloabl
          socket_send_to_nodes = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
          #Send “Packet” using the new socket
          socket_send_to_nodes.sendto(packet, nextSlaveIP)
     previousNextSlaveIP = nextSlaveIP


thread_handleJoinRequests = Thread(name='handleJoinRequests', target=handleJoinRequests)
thread_receivePacketAndForward = Thread(name='receivePacketAndForward', target=receivePacketAndForward)
thread_sendUserMessage = threading.Thread(name='sendUserMessage', target=sendUserMessage)

thread_handleJoinRequests.start()
thread_receivePacketAndForward.start()
thread_sendUserMessage.start()
