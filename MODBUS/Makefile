#
#ifeq ($(CFLAGS),660)
#	PREFIXPATH=/usr/local/mxscaleb/bin
#	CC=$(PREFIXPATH)/mxscaleb-gcc
#	CCS=$(PREFIXPATH)/mxscaleb-strip
#else
#	PREFIXPATH=/usr/local/arm-linux-4.4.2-v4/bin
#	CC=$(PREFIXPATH)/arm-none-linux-gnueabi-gcc
#	CCS=$(PREFIXPATH)/arm-none-linux-gnueabi-strip
#endif
CC=gcc
CCS=strip
NAME=sample

all: release

release:	$(NAME).c
	$(CC) -o  $(NAME) $(NAME).c 
	$(CCS) $(NAME)
