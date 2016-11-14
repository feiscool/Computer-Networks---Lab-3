/*
 * - File name: Slave.c
 * - Command line argument format: Slave MasterHostname MasterPortNumber
 *   (where "Slave" is the executable)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <pthread.h>

#define MAXDATASIZE 100 // Maximum number of bytes that can be received at once

// Constants
const uint8_t GID = 1;
const uint16_t magicNumber = 0x1234;

// Global variables
uint8_t myRID;
uint8_t master_GID;
uint16_t magicNumber_BigE;
uint32_t nextSlaveIP;
char nextSlaveIP_String[INET_ADDRSTRLEN];
int UDP_socketForSending;


// Get sockaddr, IPv4 or IPv6
void* get_in_addr(struct sockaddr *sa) {
    
    if (sa->sa_family == AF_INET) {
        return &(((struct sockaddr_in*)sa)->sin_addr);
    }
    
    return &(((struct sockaddr_in6*)sa)->sin6_addr);
}


void* sendUserMessage(void * blank) {
    
    // Variables to be sent for the messaging service
    uint8_t toSend_TtL;
    uint8_t toSend_destination_RID;
    uint8_t toSend_checksum;
    char toSend_message[64];
    
    // Packed struct that will be sent as the data in a packet. A packed struct
    // is used as it won't contain any "padding" added by the compiler
    struct packed_message {
        uint8_t GID_Struct;
        uint16_t magicNumber_Struct;
        uint8_t TtL_Struct;
        uint8_t RID_Dest_Struct;
        uint8_t RID_Source_Struct;
        char message_Struct[64];
        uint8_t checksum_Struct;
    } __attribute__((__packed__));
    
    while (1) {
        
        printf("Slave %d: Messages can now be sent along the ring \n", myRID);
        printf("Slave %d: Enter the Ring ID of a node to send a message to: ", myRID);
        scanf("%d", &toSend_destination_RID);
        
        // getchar() is needed to eliminate the newline character left in the
        // input buffer from the user pressing the return key to enter the ring ID
        getchar();
        
        printf("Slave %d: Enter a message to send: ", myRID);
        fgets(toSend_message, 64, stdin);
        
        // Remove the trailing newline character from the toSend_message string
        if ((strlen(toSend_message) > 0) && (toSend_message[strlen(toSend_message) - 1] == '\n')) {
            toSend_message[strlen(toSend_message) - 1] = '\0';
        }

        // Construct the packet to be sent
        struct packed_message message_packet;
        
        message_packet.GID_Struct = GID;
        message_packet.magicNumber_Struct = magicNumber_BigE;
        message_packet.TtL_Struct = toSend_TtL;
        message_packet.RID_Dest_Struct = toSend_destination_RID;
        message_packet.RID_Source_Struct = myRID;
        strcpy(message_packet.message_Struct, toSend_message);	// Needed for char array
        message_packet.checksum_Struct = toSend_checksum;
        
        
        
        printf("Slave %d: Message sent to node with Ring ID %d \n", myRID, toSend_destination_RID);
    }
}


int main(int argc, char *argv[]) {
    
    // Networking setup variables
    int sockfd, numbytes, rv, masterPortNumber;
    char buffer[MAXDATASIZE];
    struct addrinfo hints, *servinfo, *p;	// "hints" is a struct of the addrinfo type
    char s[INET6_ADDRSTRLEN];
    
    // Variables to be received from the master
    uint8_t received_GID;
    uint16_t received_MagicNumber;
    uint32_t received_nextSlaveIP;
    uint8_t received_myRID;
    
    // Threading variables
    pthread_t sendMessageThread;
    pthread_t receiveForwardThread;
    
    // Miscellaneous variables
    int* blank = 0;
    char nextSlavePort[100];
    
    // Packed struct that will be sent as the data in a packet. A packed struct
    // is used as it won't contain any "padding" added by the compiler
    struct packed_request {
        uint8_t GID_Struct;
        uint16_t magicNumber_Struct;
    } __attribute__((__packed__));
    
    magicNumber_BigE = htons(magicNumber);		// Convert to Big Endian
    
    // Ensure enough command line arguments are given
    if (argc != 3) {
        fprintf(stderr,"Slave: Error - inappropriate amount of arguments given \n");
        exit(1);
    }
    
    masterPortNumber = strtol(argv[2], NULL, 10);
    
    // Ensure the port number is valid (just for kicks)
    if (masterPortNumber < 0 || masterPortNumber > 65535) {
        fprintf(stderr,"Slave: Error - invalid port number given \n");
        exit(1);
    }
    
    /*
     * BEGIN: Establish TCP socket
     */
    
    // The "hints" struct is used in the call to getaddrinfo(). It gives hints about
    // the type of socket we will be using
    memset(&hints, 0, sizeof hints);	// Ensure the struct is empty
    hints.ai_family = AF_UNSPEC;		// No preference for IPv4 or IPv6
    hints.ai_socktype = SOCK_STREAM;	// We're using TCP, not UDP!
    
    // Creates a linked list of addrinfo structs, which are pointed to by servinfo. These
    // structs contain the address information for the server that we are connecting to
    if ((rv = getaddrinfo(argv[1], argv[2], &hints, &servinfo)) != 0) {
        fprintf(stderr, "Slave: Error - getaddrinfo() => %s \n", gai_strerror(rv));
        return 1;
    }
    
    // Loop through the linked list pointed to by servinfo until an addrinfo node is
    // found that can both create a socket and establish a connection. A loop is used
    // as a host can have multiple addresses - not all may work
    for(p = servinfo; p != NULL; p = p -> ai_next) {
        
        // Attempt to create a socket using the current addrinfo node. If the call
        // fails, jump to the next node in the iteration and try again. If succesful,
        // try to connect to the host (the master)
        if ((sockfd = socket(p -> ai_family, p -> ai_socktype,
                             p -> ai_protocol)) == -1) {
            perror("Slave: Error - socket() \n");
            continue;
        }
        
        // Attempt to connect to the host machine (the master)
        if (connect(sockfd, p->ai_addr, p->ai_addrlen) == -1) {
            close(sockfd);
            perror("Slave: Error - connect() \n");
            continue;
        }
        
        break;
    }
    
    // If 'p' is NULL at this point, then the entire linked list was iterated over and
    // no addrinfo nodes were able to create a socket and connect to the host
    if (p == NULL) {
        fprintf(stderr, "Slave: Error - failed to connect \n");
        return 2;
    }
    
    /*
     * END: Establish TCP socket
     */
    
    // Convert the IP address that 'p' contains to human readable form and display it
    inet_ntop(p -> ai_family, get_in_addr((struct sockaddr *)p -> ai_addr), s, sizeof s);
    printf("Slave: Connecting to %s \n", s);
    
    /*
     * BEGIN: Join Request
     */
    
    // Construct the packet to be sent
    struct packed_request packet = {GID, magicNumber_BigE};
    
    // Attempt to send the packet to the master
    if (send(sockfd, (void *)&packet, sizeof(packet), 0) == -1) {
        perror("Slave: Error - send() \n");
        close(sockfd);
        exit(1);
    }
    
    /*
     * END: Join Request
     */
    
    /*
     * BEGIN: Receive Response
     */
    
    // Receive the response from the master
    if ((numbytes = recv(sockfd, buffer, MAXDATASIZE - 1, 0)) == -1) {
        perror("Slave: Error - recv() \n");
        exit(1);
    }
    
    // Ensure the return packet is the correct size (8 bytes)
    if (numbytes != 8) {
        perror("Slave: Error - incorrect response packet size \n");
        // exit(1);
    }
    
    buffer[numbytes] = '\0';		// Mark the end of the buffer
    
    // Get the data from the buffer. Note: The second parentheses is where the data
    // is to begin to be parsed from. It will stop automatically based on the size of
    // the type that is specified
    received_GID = *(uint8_t *)(buffer);
    received_MagicNumber = *(uint16_t *)(buffer + 1);
    received_myRID = *(uint8_t *)(buffer + 3);
    received_nextSlaveIP = *(uint32_t *)(buffer + 4);
    
    // Assign local variables to global variables (for the threads)
    myRID = received_myRID;
    master_GID = received_GID;
    
    // Convert the received values larger than a byte to host byte order (Little Endian)
    received_MagicNumber = ntohs(received_MagicNumber);
    nextSlaveIP = ntohl(received_nextSlaveIP);
    
    // Convert the received next slave's IP Address to human readable form
    inet_ntop(AF_INET, &(nextSlaveIP), nextSlaveIP_String, INET_ADDRSTRLEN);
    
    // Ensure that the magic number sent from the Master is valid
    if (received_MagicNumber != magicNumber) {
        perror("Slave: Error - invalid magic number received from Master \n");
        // exit(1);
    }
    
    // Display the contents of the response packet
    printf("Slave: GID of Master = %d \n", received_GID);
    printf("Slave: My RID = %d \n", myRID);
    printf("Slave: Next Slave's IP Address = %s \n", nextSlaveIP_String);
    
    /*
     * END: Receive Response
     */
    
    freeaddrinfo(servinfo);		// Frees up the linked list pointed to by servinfo
    close(sockfd);				// Close the socket that we were using
    
    /*
     * BEGIN: Establish UDP socket for sending 
     */
    
    // Note that the variables from the setup of the TCP socket are being reused. This 
    // is okay since the socket was closed 
    memset(&hints, 0, sizeof hints);	// Ensure the struct is empty
    hints.ai_family = AF_UNSPEC;		// No preference for IPv4 or IPv6
    hints.ai_socktype = SOCK_DGRAM;		// We're using UDP!
    
    sprintf(nextSlavePort, "%d", (10010 + (master_GID * 5) + (myRID - 1)));
    
    // Creates a linked list of addrinfo structs, which are pointed to by servinfo. These
    // structs contain the address information for the server that we are connecting to
    if ((rv = getaddrinfo(nextSlaveIP_String, nextSlavePort, &hints, &servinfo)) != 0) {
        fprintf(stderr, "Slave: Error - getaddrinfo() => %s \n", gai_strerror(rv));
        return 1;
    }
    
    // Loop through the linked list pointed to by servinfo until an addrinfo node is
    // found that can both create a socket and establish a connection. A loop is used
    // as a host can have multiple addresses - not all may work
    for(p = servinfo; p != NULL; p = p -> ai_next) {
        
        // If the addrinfo node is valid, create a socket
        if ((UDP_socketForSending = socket(p -> ai_family, p -> ai_socktype,
                             p -> ai_protocol)) == -1) {
            perror("Slave: Error - socket() \n");
            continue;
        }
        
        break;
    }
    
    // If 'p' is NULL at this point, then the entire linked list was iterated over and
    // no addrinfo nodes were able to create a socket and connect to the host
    if (p == NULL) {
        fprintf(stderr, "Slave: Error - failed to connect \n");
        return 1;
    }
    
    /*
     * END: Establish UDP socket for sending 
     */
    
    // Create the thread that allows the user to send messages to other nodes
    if (pthread_create(&sendMessageThread, NULL, sendUserMessage, (void*)blank) != 0) {
        fprintf(stderr, "Slave: Error - threading failure \n");
        return 1;
    }
    
    // Wait for the threads to end (they won't, since they are infinite loops), otherwise
    // they will end once "return 0" is reached below
    pthread_join(sendMessageThread, NULL);
    
    return 0;
}
