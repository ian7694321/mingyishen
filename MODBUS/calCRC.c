#include <stdio.h>
#include <stdint.h>

uint16_t calCRC(uint8_t *data,int size){
    uint16_t crc=0XFFFF;
    for(int i=0;i<size;i++){
        crc ^= data[i];
        for(int j=0;j<8;j++){
            if(crc & 0X01){
                crc=(crc >> 1)^0xA001;
            }
            else{
                crc=(crc>>1);
            }
        }
    }
    return crc;
}

int main(){

    //printf("123\n");

    uint8_t frame[]={0x01,0x03,0x00,0x01,0x00,0x01};
    uint16_t crcvalue = calCRC(frame,sizeof(frame));
    printf("%04X\n",crcvalue);

    return 0;
    
}