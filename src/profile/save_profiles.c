#define _POSIX_C_SOURCE 200809L
#include "save_profiles.h"
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#include <io.h>
#include <fcntl.h>
#define SP_MKDIR(p) _mkdir(p)
#define SP_RMDIR(p) _rmdir(p)
#define SP_ACCESS(p) _access(p, 0)
#else
#include <dirent.h>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
#define SP_MKDIR(p) mkdir(p, 0700)
#define SP_RMDIR(p) rmdir(p)
#define SP_ACCESS(p) access(p, F_OK)
#endif

static int path2(char dst[SP_PATH_CAP], const char *a, const char *b)
{
    int n;
    if (!a || !b || !*a || !*b) return 0;
    n=snprintf(dst,SP_PATH_CAP,"%s/%s",a,b);
    return n>=0 && n<SP_PATH_CAP;
}
int sp_valid_id(const char *id)
{
    size_t i,n;
    if (!id) return 0;
    n=strlen(id);
    if (!n || n>=SP_ID_CAP) return 0;
    for(i=0;i<n;i++){
        unsigned char c=(unsigned char)id[i];
        if (!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
              (c>='0'&&c<='9')||c=='_'||c=='-')) return 0;
    }
    return 1;
}
static uint16_t r16(const unsigned char *p)
{ return (uint16_t)p[0] | ((uint16_t)p[1]<<8); }
static uint32_t r32(const unsigned char *p)
{ return (uint32_t)r16(p) | ((uint32_t)r16(p+2)<<16); }

static SpStatus validate_stream(FILE *f)
{
    unsigned char block[4096];
    unsigned counts[2][14]={{0}};
    uint32_t save_counter[2][14]={{0}};
    long len;
    int sector,slot,id;
    if (fseek(f,0,SEEK_END)) return SP_IO;
    len=ftell(f);
    if (len!=(long)SP_EMERALD_SIZE &&
        len!=(long)(SP_EMERALD_SIZE+SP_EMULATOR_EXTRA_SIZE)) return SP_BAD_SAVE;
    if (fseek(f,0,SEEK_SET)) return SP_IO;
    for(sector=0;sector<28;sector++){
        if(fread(block,1,sizeof(block),f)!=sizeof(block)) return SP_IO;
        id=r16(block+0xff4);
        slot=sector/14;
        if(id>=0 && id<14 && r32(block+0xff8)==0x08012025u){
            counts[slot][id]++;
            save_counter[slot][id]=r32(block+0xffc);
        }
    }
    for(slot=0;slot<2;slot++){
        int full=1;
        uint32_t counter=save_counter[slot][0];
        for(id=0;id<14;id++){
            if(counts[slot][id]!=1 || save_counter[slot][id]!=counter){full=0;break;}
        }
        if(full) return SP_OK;
    }
    return SP_BAD_SAVE;
}
SpStatus sp_validate_file(const char *source)
{
    FILE *f;
    SpStatus r;
    if(!source || !*source) return SP_BAD_ARG;
    f=fopen(source,"rb");
    if(!f) return SP_IO;
    r=validate_stream(f);
    if(fclose(f)!=0 && r==SP_OK) r=SP_IO;
    return r;
}

static int close_sync(FILE *f)
{
    int ok=fflush(f)==0;
#ifdef _WIN32
    if(ok) ok=_commit(_fileno(f))==0;
#else
    if(ok) ok=fsync(fileno(f))==0;
#endif
    if(fclose(f)!=0) ok=0;
    return ok;
}
static int replace_file(const char *src,const char *dst)
{
#ifdef _WIN32
    return MoveFileExA(src,dst,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
#else
    return rename(src,dst)==0;
#endif
}
/* Verify the temporary copy before committing it. This guards against
 * divergent bytes from a failed/changed transfer, not sector payload bugs. */
static int same_file_bytes(const char *left,const char *right)
{
    FILE *a=fopen(left,"rb"),*b=NULL;
    unsigned char aa[8192],bb[8192];
    size_t na,nb;
    int same=1;
    if(!a) return 0;
    b=fopen(right,"rb");
    if(!b){fclose(a);return 0;}
    do {
        na=fread(aa,1,sizeof(aa),a);
        nb=fread(bb,1,sizeof(bb),b);
        if(na!=nb || memcmp(aa,bb,na)!=0){same=0;break;}
    } while(na==sizeof(aa));
    if(ferror(a)||ferror(b)) same=0;
    if(fclose(a)!=0) same=0;
    if(fclose(b)!=0) same=0;
    return same;
}
/* Copies without modifying source. Temp file uses .partial; caller ensures
 * the exclusive profile lock when targeting an existing profile. */
static SpStatus copy_atomic(const char *src,const char *dst,int require_valid_save)
{
    char temp[SP_PATH_CAP];
    unsigned char buf[8192];
    FILE *in,*out;
    size_t n;
    int good=1;
    if(snprintf(temp,sizeof(temp),"%s.partial",dst)>=(int)sizeof(temp)) return SP_BAD_ARG;
    in=fopen(src,"rb");
    if(!in) return SP_IO;
    out=fopen(temp,"wb");
    if(!out){fclose(in);return SP_IO;}
    while((n=fread(buf,1,sizeof(buf),in))>0){
        if(fwrite(buf,1,n,out)!=n){good=0;break;}
    }
    if(ferror(in)) good=0;
    if(fclose(in)!=0) good=0;
    if(!close_sync(out)) good=0;
    if(!good || !same_file_bytes(src,temp)){
        remove(temp);
        return SP_IO;
    }
    /* Never replace a profile with an invalid temporary save. The source
     * may change during a copy: first validate the copied bytes, THEN
     * commit them. Corrupt originals copied to .raw are intentionally
     * exempt: recovery files preserve evidence, not playable saves. */
    if(require_valid_save){
        SpStatus validation=sp_validate_file(temp);
        if(validation!=SP_OK){remove(temp);return validation;}
    }
    if(!replace_file(temp,dst)){remove(temp);return SP_IO;}
    return SP_OK;
}
static SpStatus ensure_profile(const char *root,const char *id,char directory[SP_PATH_CAP])
{
    if(!sp_valid_id(id) || !path2(directory,root,id)) return SP_BAD_ARG;
    if(SP_MKDIR(directory)!=0) return errno==EEXIST?SP_EXISTS:SP_IO;
    return SP_OK;
}
SpStatus sp_import(const char *root,const char *id,const char *source)
{
    char dir[SP_PATH_CAP],dst[SP_PATH_CAP];
    SpStatus st;
    if(!root || !source || !*root) return SP_BAD_ARG;
    st=sp_validate_file(source);
    if(st!=SP_OK) return st;
    st=ensure_profile(root,id,dir);
    if(st!=SP_OK) return st;
    if(!path2(dst,dir,"pokeemerald.sav")){SP_RMDIR(dir);return SP_BAD_ARG;}
    st=copy_atomic(source,dst,1);
    /* Verify after copy too: source may have changed during transfer. */
    if(st==SP_OK) st=sp_validate_file(dst);
    if(st!=SP_OK) {
        remove(dst);
        SP_RMDIR(dir);
    }
    return st;
}
SpStatus sp_create_empty(const char *root,const char *id)
{
    char dir[SP_PATH_CAP],file[SP_PATH_CAP];
    unsigned char buf[4096];
    FILE *f;
    int i,good=1;
    SpStatus st;
    if(!root || !*root) return SP_BAD_ARG;
    st=ensure_profile(root,id,dir);
    if(st!=SP_OK) return st;
    if(!path2(file,dir,"pokeemerald.sav")){
        SP_RMDIR(dir);
        return SP_BAD_ARG;
    }
    f=fopen(file,"wb");
    if(!f){SP_RMDIR(dir);return SP_IO;}
    memset(buf,0xff,sizeof(buf));
    for(i=0;i<32;i++) if(fwrite(buf,1,sizeof(buf),f)!=sizeof(buf)) {good=0;break;}
    if(!close_sync(f)) good=0;
    if(!good){remove(file);SP_RMDIR(dir);return SP_IO;}
    return SP_OK;
}
SpStatus sp_lock(const char *root,const char *id,SpProfileLock *lock)
{
    char directory[SP_PATH_CAP],lockfile[SP_PATH_CAP],savefile[SP_PATH_CAP];
    if(!lock || !root || !sp_valid_id(id) ||
       !path2(directory,root,id) ||
       !path2(lockfile,directory,".profile.lock") ||
       !path2(savefile,directory,"pokeemerald.sav")) return SP_BAD_ARG;
    if(SP_ACCESS(savefile)!=0) return SP_NOT_FOUND;
    memset(lock,0,sizeof(*lock));
#ifdef _WIN32
    lock->handle=CreateFileA(lockfile,GENERIC_READ|GENERIC_WRITE,0,NULL,
                             OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(lock->handle==INVALID_HANDLE_VALUE) return SP_BUSY;
#else
    lock->fd=open(lockfile,O_CREAT|O_RDWR,0600);
    if(lock->fd<0) return SP_IO;
    if(flock(lock->fd,LOCK_EX|LOCK_NB)!=0){close(lock->fd);return SP_BUSY;}
#endif
    strcpy(lock->directory,directory);
    lock->held=1;
    return SP_OK;
}
void sp_unlock(SpProfileLock *lock)
{
    if(!lock || !lock->held) return;
#ifdef _WIN32
    CloseHandle(lock->handle);
    lock->handle=INVALID_HANDLE_VALUE;
#else
    flock(lock->fd,LOCK_UN);
    close(lock->fd);
    lock->fd=-1;
#endif
    lock->held=0;
}
static int lock_paths(const SpProfileLock *l,char *save,char *backups)
{
    return l && l->held &&
           path2(save,l->directory,"pokeemerald.sav") &&
           path2(backups,l->directory,"backups");
}
static int backup_name(char *buf,size_t cap,unsigned seq)
{
    int n;
    if(seq==0 || seq>999999u) return 0;
    n=snprintf(buf,cap,"%06u.sav",seq);
    return n>0 && (size_t)n<cap;
}
static int read_backup_sequence(const char *name,unsigned *seq)
{
    unsigned n=0, i;
    if(!name || strlen(name)!=10 || strcmp(name+6,".sav")) return 0;
    for(i=0;i<6;i++){
        if(name[i]<'0'||name[i]>'9') return 0;
        n=n*10+(unsigned)(name[i]-'0');
    }
    if(!n) return 0;
    *seq=n;
    return 1;
}
static int compare_uint(const void *a,const void *b)
{
    unsigned x=*(const unsigned*)a,y=*(const unsigned*)b;
    return (x>y)-(x<y);
}
static SpStatus list_backup_numbers(const char *dir,unsigned **numbers,size_t *count)
{
    size_t cap=16;
    unsigned *items;
    *numbers=NULL; *count=0;
    items=(unsigned*)malloc(cap*sizeof(*items));
    if(!items) return SP_IO;
#ifdef _WIN32
    {
        char wildcard[SP_PATH_CAP];
        WIN32_FIND_DATAA data;
        HANDLE find;
        if(!path2(wildcard,dir,"*.sav")){free(items);return SP_BAD_ARG;}
        find=FindFirstFileA(wildcard,&data);
        if(find!=INVALID_HANDLE_VALUE){
            do {
                unsigned seq;
                if(!(data.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY) &&
                   read_backup_sequence(data.cFileName,&seq)){
                    if(*count==cap){unsigned *tmp;cap*=2;tmp=(unsigned*)realloc(items,cap*sizeof(*items));if(!tmp){FindClose(find);free(items);return SP_IO;}items=tmp;}
                    items[(*count)++]=seq;
                }
            }while(FindNextFileA(find,&data));
            FindClose(find);
        }
    }
#else
    {
        DIR *d=opendir(dir);
        struct dirent *entry;
        if(!d){free(items);return errno==ENOENT?SP_NOT_FOUND:SP_IO;}
        while((entry=readdir(d))!=NULL){
            unsigned seq;
            if(read_backup_sequence(entry->d_name,&seq)){
                if(*count==cap){unsigned *tmp;cap*=2;tmp=(unsigned*)realloc(items,cap*sizeof(*items));if(!tmp){closedir(d);free(items);return SP_IO;}items=tmp;}
                items[(*count)++]=seq;
            }
        }
        closedir(d);
    }
#endif
    qsort(items,*count,sizeof(*items),compare_uint);
    *numbers=items;
    return SP_OK;
}
SpStatus sp_backup(const SpProfileLock *lock,unsigned *sequence)
{
    char src[SP_PATH_CAP],backups[SP_PATH_CAP],out[SP_PATH_CAP],name[24];
    unsigned *numbers=NULL, next=1;
    size_t count=0;
    SpStatus st;
    if(sequence) *sequence=0;
    if(!sequence || !lock_paths(lock,src,backups)) return SP_BAD_ARG;
    /* Only a complete structurally valid save enters ordinary backups. */
    st=sp_validate_file(src);
    if(st!=SP_OK) return st;
    if(SP_MKDIR(backups)!=0 && errno!=EEXIST) return SP_IO;
    st=list_backup_numbers(backups,&numbers,&count);
    if(st!=SP_OK) return st;
    if(count) next=numbers[count-1]+1;
    free(numbers);
    if(!backup_name(name,sizeof(name),next) || !path2(out,backups,name)) return SP_IO;
    st=copy_atomic(src,out,1);
    if(st==SP_OK) st=sp_validate_file(out);
    if(st==SP_OK) *sequence=next;
    else remove(out); /* Do not retain an incomplete ordinary backup. */
    return st;
}
SpStatus sp_restore(const SpProfileLock *lock,unsigned sequence)
{
    char target[SP_PATH_CAP],backups[SP_PATH_CAP],source[SP_PATH_CAP],name[24];
    char recovery[SP_PATH_CAP];
    unsigned safety=0, i;
    SpStatus st;
    if(!lock_paths(lock,target,backups) || !backup_name(name,sizeof(name),sequence)
       || !path2(source,backups,name)) return SP_BAD_ARG;
    st=sp_validate_file(source);
    if(st!=SP_OK) return st;
    if(sp_validate_file(target)==SP_OK){
        st=sp_backup(lock,&safety);
    }else{
        /* Keep the invalid original for forensic recovery, without treating
         * corrupted bytes as an ordinary restorable save. */
        st=SP_IO;
        for(i=1;i<=999999u;i++){
            int n=snprintf(name,sizeof(name),"bad%06u.raw",i);
            if(n<0 || n>=(int)sizeof(name) || !path2(recovery,backups,name)) return SP_BAD_ARG;
            if(SP_ACCESS(recovery)!=0){st=copy_atomic(target,recovery,0);break;}
        }
    }
    if(st!=SP_OK) return st;
    return copy_atomic(source,target,1);
}
SpStatus sp_prune(const SpProfileLock *lock,unsigned keep)
{
    char save[SP_PATH_CAP],dir[SP_PATH_CAP],name[24],path[SP_PATH_CAP];
    unsigned *numbers=NULL;
    size_t i,count=0;
    SpStatus st;
    if(keep<1 || keep>1000 || !lock_paths(lock,save,dir)) return SP_BAD_ARG;
    st=list_backup_numbers(dir,&numbers,&count);
    if(st==SP_NOT_FOUND) return SP_OK;
    if(st!=SP_OK) return st;
    for(i=0;i+keep<count;i++){
        if(!backup_name(name,sizeof(name),numbers[i]) || !path2(path,dir,name)){
            free(numbers);return SP_BAD_ARG;
        }
        if(remove(path)!=0){free(numbers);return SP_IO;}
    }
    free(numbers);
    return SP_OK;
}
