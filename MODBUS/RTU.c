#include <stdio.h>
#include <stdint.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>
#include <math.h>
/*
int id;
void connectTo(char *ip, int port){
    //建立套接字
    id = socket(AF_INET,SOCK_STREAM,0); //IPV4,TCP協議,一般形式

    struct sockaddr_in info;
    bzero(&info,sizeof(info));     //將 C 語言中的記憶體區域清零，記憶體地址 / 常量位元組，用於填充記憶體 / 要覆蓋的位元組數
    info.sin_family = PF_INET;               //輸入的ip的型別AF_INET，IPV4             
    info.sin_addr.s_addr = inet_addr(ip);    
    info.sin_port = htons(port);

    connect(id,(struct sockaddr *)&info, sizeof(info));    //前面socket的返回的套接字，伺服器端位置，位置長度
       
}


void sendTo(char *data, int size){
    send(id,data,size,0);   // 套接字 / 指向要傳送資料的指標 / 資料長度 / flags，一般為0
}

int receiveFrom(char *data, int size){
    return recv(id,data,size,0);    // 套接字 / 存放接收資料的緩衝區 / 資料長度 / flags，一般為0
}


void disconnect(){
    close(id);
}

*/

/*
uint16_t CRC(uint8_t *data,int size){
    uint16_t crc=0XFFFF;
    for(int i=0;i<size;i++){
        crc ^= data[i];
        for(int j=0;j<8;j++){
            if(crc & 0X01){
                crc >>= 1;
                crc ^= 0XA001;
            }
            else{
                crc >>= 1;
            }
        }
    }
    return crc;
}
*/

void RTUsend(uint8_t slaveAddr, uint8_t functioncode, uint16_t Addr,uint16_t count,uint8_t *request){
    request[0]=slaveAddr;
    request[1]=functioncode;
    request[2]=(Addr >> 8);               //addr hi  位元右移8位
    request[3]=(Addr & 0xFF);             //addr low 取Addr的最低位值的運算，保留低8位 (Addr AND 1111 1111)
    request[4]=(count >> 8);
    request[5]=(count & 0xFF);

    uint16_t crc=0xFFFF;        //無符號整數所代表最大值 
    for(int i=0;i<6;i++){
        crc ^= request[i];      //以位元xor賦值
        for(int j=0;j<8;j++){
            if(crc & 0x01){     //將i的的值轉为二進制，假若最低位是1
                crc >>= 1;      //以位元右移賦值
                crc ^= 0xA001;  //0xA001=1010 0000 0000 0001
            }
            else{
                crc >>= 1;
            }
        }
    }
    //calCRC(request,6);
    request[6]=(crc & 0XFF);     //crc lo
    request[7]=(crc >> 8);       //crc hi

}

/*
void calCRC(const unsigned char *data, int size,uint16_t *crc){
    *crc=0XFFFF;
    for(int i=0;i<size;++i){
        *crc ^= data[i];
        for(int j=0;j<8;++j){
            if(*crc & 0X0001){
                *crc >>= 1;
                *crc ^= 0XA001;
            }
            else{
                *crc >>= 1;
            }
        }
    }
}
*/

void RTUshow(uint8_t *request,uint8_t size){
    printf("十六進制表示:");
    for(int i=0;i<size;++i){
        printf("%hx ",request[i]);
    }   
    printf("\n");
}

void RTUresponse(uint8_t *request, int size){

    int cnt = request[2];
    int length = cnt+5;
    //printf("%d\n",cnt);

    if(size<length){
        printf("Invalid RTU response size\n");
    }
    //uint8_t SlaveAddr = request[0];
    //uint8_t functioncode = request[1];
    /*
    if(size==6){
        int temp=0;
        int tmp=size/2;
        temp+= request[tmp]*256+request[tmp+1];
        printf("value1:%d\n",temp);
        printf("Hex:%x\n",temp);
        printf("scale0.1:%d\n",temp/10);
    }*/
    else{
        for(int i=1;i<=cnt/2;i++){
            int temp=0;
            int j=i*2+1;
            temp+= request[j]*256+request[j+1];
            //printf("%02x",request[i]);
            printf("value%d:%d\n",i,temp);
            printf("Hex:%x\n",temp);
            printf("scale0.1:%d\n",temp/10);
            printf("\n");
        }  
    }
}

/*
    uint16_t receiveCRC = (request[size-2]) << 8 | request[size-1];
    uint16_t calCRC = CRC(request,size-2);

    if(receiveCRC == calCRC){
        printf("CRC is valid\n");
    }
    else{
        printf("CRC is invalid\n");   
    }
    */


/*
}

int DectoHex(int dec, unsigned char *hex, int length) 
{ 
	for(int i=length-1; i>=0; i--) 
	{ 
		hex[i] = (dec%256)&0xFF; 
		dec /= 256; 
	} 
	
	return 0; 
} 
*/


/*
void HextoChar(uint8_t *request,uint8_t size,char *ch){
    uint8_t tmp = 0x00;
    for(int i=0;i<size;i++){
        for(int j=0;j<2;j++){
            tmp = (*(request+i) >> 4)*(1-j) + (*(request+i)&0x0F)*j;
            if(tmp >= 0 && tmp <= 9){
                ch[2*i+j]=tmp+'0';
            }
            else if(tmp >= 0x0A && tmp <= 0x0F){
                ch[2*i+j] = tmp - 0x0A + 'A';
            }
        }
    }

}
*/


/*
void OctalToDecimal(int octalNumber)
{
    int decimalNumber = 0, i = 0;
 
    while(octalNumber != 0)
    {
        decimalNumber += (octalNumber%10) * pow(8,i);
        ++i;
        octalNumber/=10;
    }
 
    i = 1;
}
*/