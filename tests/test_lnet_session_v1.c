#include "lnet_session_v1.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void roundtrip(uint16_t size, unsigned fragment)
{
    EhlSessionFrame a, b;
    EhlSessionDecoder d;
    uint8_t bytes[EHL_SESSION_MAX_FRAME];
    size_t len = 0, off=0;
    int out=0;
    unsigned i;
    memset(&a, 0, sizeof(a));
    a.type=EHL_POSE; a.request_id=0x12345678u;
    a.session_id=UINT64_C(0x0fedcba987654321);
    a.payload_size=size;
    for(i=0;i<size;i++) a.payload[i]=(uint8_t)i;
    assert(!ehl_session_encode(&a,bytes,sizeof(bytes),&len));
    assert(len==EHL_SESSION_HEADER_SIZE+size);
    ehl_session_decoder_init(&d);
    while(off<len) {
        size_t used=0, take=fragment;
        if(take>len-off) take=len-off;
        out=ehl_session_decoder_feed(&d,bytes+off,take,&used,&b);
        assert(out>=0 && used<=take && used>0);
        off+=used;
    }
    assert(out==1 && b.type==a.type && b.payload_size==size &&
           b.request_id==a.request_id && b.session_id==a.session_id &&
           !memcmp(a.payload,b.payload,size));
}

int main(void)
{
    EhlSessionFrame a,b;
    EhlSessionDecoder d;
    uint8_t bytes[EHL_SESSION_MAX_FRAME*2];
    size_t len=0,got=0,n=0;
    unsigned i;
    for(i=1;i<=48;i++){roundtrip(0,i);roundtrip(1,i);roundtrip(128,i);roundtrip(4096,i);}
    memset(&a,0,sizeof(a));a.type=EHL_HELLO;
    assert(!ehl_session_encode(&a,bytes,sizeof(bytes),&len));
    assert(!ehl_session_encode(&a,bytes+len,sizeof(bytes)-len,&got));
    ehl_session_decoder_init(&d);
    assert(ehl_session_decoder_feed(&d,bytes,len*2,&n,&b)==1&&n==len);
    assert(ehl_session_decoder_feed(&d,bytes+n,len,&got,&b)==1&&got==len);
    bytes[0]='X';ehl_session_decoder_init(&d);
    assert(ehl_session_decoder_feed(&d,bytes,len,&got,&b)==-1);
    bytes[0]='E';bytes[4]=0;bytes[5]=2;ehl_session_decoder_init(&d);
    assert(ehl_session_decoder_feed(&d,bytes,len,&got,&b)==-1);
    bytes[5]=1;bytes[12]=0xff;bytes[13]=0xff;ehl_session_decoder_init(&d);
    assert(ehl_session_decoder_feed(&d,bytes,len,&got,&b)==-1);
    bytes[12]=0;bytes[13]=0;bytes[10]=1;ehl_session_decoder_init(&d);
    assert(ehl_session_decoder_feed(&d,bytes,len,&got,&b)==-1);
    bytes[10]=0;bytes[8]=0;bytes[9]=0;ehl_session_decoder_init(&d);
    assert(ehl_session_decoder_feed(&d,bytes,len,&got,&b)==-1);
    a.payload_size=4097;assert(ehl_session_encode(&a,bytes,sizeof(bytes),&got)==-1);
    a.payload_size=0;a.type=EHL_HELLO;
    assert(ehl_session_encode(&a,bytes,27,&got)==-1);
    puts("passed: EHL8 session framing boundaries, concatenated frames and fragmentation (192 roundtrips)");
    return 0;
}
