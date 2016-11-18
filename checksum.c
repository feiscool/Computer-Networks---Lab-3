#include <stdint.h>
#include <stdio.h>

unsigned char compute_checksum(const char *buf, unsigned size)
{
	uint16_t sum = 0;
	int i;

	/* Accumulate checksum */
	for (i = 0; i < size - 1; i++)
	{
		sum += *(uint8_t *) &buf[i];
    sum = (sum >> 8) + (sum & 0xFF);
	}
  sum += (sum >> 8);
  unsigned char checksum = (~sum) & 0xFF;

  printf("\nAnswer = %d\n\n", checksum);
	return checksum;
}

void main(){
  char arr[4];
  arr[0] = 112;
  arr[1] = 176;
  arr[2] = 240;
  arr[3] = 15;
  compute_checksum(arr, 5);
}
