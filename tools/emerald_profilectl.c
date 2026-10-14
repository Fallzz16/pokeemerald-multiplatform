/* Developer-facing safe CLI around the v0.8 profile core. Not a launcher. */
#include "save_profiles.h"
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void usage(void)
{
    puts("Emerald Hybrid v0.8 profile tool (developer CLI, no gameplay integration)");
    puts("  emerald_profilectl validate SOURCE.sav");
    puts("  emerald_profilectl new ROOT ID");
    puts("  emerald_profilectl import ROOT ID SOURCE.sav");
    puts("  emerald_profilectl backup ROOT ID");
    puts("  emerald_profilectl restore ROOT ID SEQUENCE");
    puts("  emerald_profilectl prune ROOT ID KEEP (1..1000)");
    puts("Notes: ROOT must already exist. Never operate while the game writes.");
}
static int number(const char *text,unsigned *value)
{
    char *end;unsigned long val;
    if(!text||!*text||*text=='-')return 0;
    errno=0;val=strtoul(text,&end,10);
    if(errno||*end||val==0||val>999999ul||val>UINT_MAX)return 0;
    *value=(unsigned)val;return 1;
}
static int result(SpStatus status)
{
    if(status==SP_OK){puts("OK");return 0;}
    fprintf(stderr,"Profile operation failed (%d). Source never modified.\n",(int)status);
    return 1;
}
int main(int argc,char **argv)
{
    SpStatus status=SP_BAD_ARG;
    SpProfileLock lock;unsigned n=0;
    if(argc==2&&(!strcmp(argv[1],"help")||!strcmp(argv[1],"--help"))){
        usage();return 0;
    }
    if(argc==3&&!strcmp(argv[1],"validate"))
        return result(sp_validate_file(argv[2]));
    if(argc==4&&!strcmp(argv[1],"new"))
        return result(sp_create_empty(argv[2],argv[3]));
    if(argc==5&&!strcmp(argv[1],"import"))
        return result(sp_import(argv[2],argv[3],argv[4]));
    if(argc>=4&&argc<=5&&(!strcmp(argv[1],"backup")||
       !strcmp(argv[1],"restore")||!strcmp(argv[1],"prune"))){
        if(argc==5&&!number(argv[4],&n))return result(SP_BAD_ARG);
        if(argc==4&&strcmp(argv[1],"backup"))return result(SP_BAD_ARG);
        status=sp_lock(argv[2],argv[3],&lock);
        if(status!=SP_OK)return result(status);
        if(!strcmp(argv[1],"backup")){
            status=sp_backup(&lock,&n);
            if(status==SP_OK)printf("Created backup sequence: %u\n",n);
        }else if(!strcmp(argv[1],"restore")){
            status=sp_restore(&lock,n);
        }else if(n<=1000u){
            status=sp_prune(&lock,n);
        }else status=SP_BAD_ARG;
        sp_unlock(&lock);
        return result(status);
    }
    usage();return 2;
}
