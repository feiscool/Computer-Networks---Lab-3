import sys
import string

def compute_checksum(buffer, buffer_len):
	sum = 0;
	while(buffer_len < 0):
		#TODO adding up the bytes
	if(count > 0):
		#TODO adding carries
	while(sum >> 8):
		sum = (sum & 0xFF) + (sum >> 8)
	return ~sum
