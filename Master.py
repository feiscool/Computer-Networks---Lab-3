import socket
import sys
import string
import struct
import binascii

# Create a TCP/IP socket
myRID = 0
slaveRID = 1
myGID = 1
magic_number = 0x1234
packed_clientIP = -1

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#initially, both IP address variables are set to hostname
#because the master is the only node in the ring
nextSlaveIP = myIPaddress = socket.gethostbyname(socket.gethostname())

#get port number from argv
portNum = int(sys.argv[1])
# Bind the socket to the port
server_address = ('', portNum)
print 'Master: Starting up on port', sys.argv[1]
sock.bind(server_address)
# Listen for incoming connections
sock.listen(1)

while True:
    # Wait for a connection
    # print 'Master: Waiting for a connection'
    connection, slave_address = sock.accept()
    try:    # Receive the data in small chunks and retransmit it
        print 'Master: Received connection from', slave_address[0]
        connection.sendall("0")

        slave_IP = slave_address[0]
        slave_Port = slave_address[1]
        # print 'Master: IP address of slave =', client_IP
        # print 'Master: Port number of slave =', client_Port

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
            print 'Master: Error - invalid magic number received from Slave'
            # exit(1)

        # Convert nextSlaveIP to integer format for sending
        packed_nextSlaveIP = struct.unpack("I", socket.inet_aton(nextSlaveIP))[0]

        # Send the response packet
        reply = struct.pack("!BHBI", myGID, magic_number, slaveRID, packed_nextSlaveIP)

        nextSlaveIP = slave_IP      # Next slave is the slave that just joined
        slaveRID = slaveRID + 1     # Increment slaveRID for the next slave

        if reply:
            print 'Master: Sending response back to Slave'
            connection.sendall(reply)
            # print 'Master: Sent %s bytes back to %s' % (len(reply), client_IP)

    finally:
        # Clean up the connection
        connection.close()
