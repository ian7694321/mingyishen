#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>
#include <termios.h>
#include <unistd.h>
#include "serial.c"
#include "RTU.c"


int main(int argc, char *argv[]){


    //printf("Test\n");
    uint8_t slaveAddr,functioncode;     //usigned char(0x00~0xFF)
    uint16_t Addr,count;                //unsigned short (0x0000~0xFFFF)
    uint8_t request[8];
    char data[1000];
    int i,len,len1;

    SerialOpen(0);
    
    printf("slaveAddr:");
    scanf("%hhu",&slaveAddr);       //指定signed char 或 unsigned char 
    
    printf("functioncode:");
    scanf("%hhu",&functioncode);

    printf("Addr:");
    scanf("%hu",&Addr);             //指定short int 或 unsigned short int

    printf("count:");
    scanf("%hu",&count);

    //printf("%02x\n",slaveAddr);
    //printf("%02x\n",functioncode);
    //printf("%02x\n",Addr);
    //printf("%02x\n",count);

    RTUsend(slaveAddr,functioncode,Addr,count,request); 
    RTUshow(request,sizeof(request));
    
    //HextoChar(request,sizeof(request),data);
    //printf("%s\n",data);

    SerialWrite(0, request, sizeof(request));
    //printf("recv: %d\n", len);
    sleep(1);
    
    len = SerialBlockRead(0, data, 1000);

    printf("recv: %d\n", len);
    printf("十進制表示:");
    for (i=0;i<len;i++)
        printf("%d ", data[i]);
    printf("\n");

    RTUresponse(data,len);

    SerialDataInInputQueue(0);
    SerialDataInOutputQueue(0);
    
    SerialClose(0);
    
    return 0;
}


/*
int SerialOpen(const char *port){
    int fd = open(port,O_RDWR | O_NOCTTY | O_NDELAY);
    if(fd == -1){
        perror("Error");
    }
    return fd;
}

void configureSerial(int fd, speed_t baudRate){
    struct termios serialsetting;
    tcgetattr(fd,&serialsetting);
    cfsetispeed(&serialsetting,baudRate);
    cfsetospeed(&serialsetting,baudRate);
    serialsetting.c_cflag &= ~PARENB;
    serialsetting.c_cflag &= ~CSTOPB;
    serialsetting.c_cflag &= ~CSIZE;
    serialsetting.c_cflag |= CS8;
    tcsetattr(fd,TCSANOW,&serialsetting);
}
*/