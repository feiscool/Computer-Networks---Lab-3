def compute_checksum(buf):
	chksum = 0
	pointer = 0
	for element in buf:
        chksum += int(str("%02x" % element), 16)
	    chksum = (chksum >> 8) + (chksum & 0xff)
	chksum += (chksum >> 8)
	return (~chksum) & 0xff
