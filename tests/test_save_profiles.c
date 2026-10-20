#define _POSIX_C_SOURCE 200809L
#include "save_profiles.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* Synthetic SECTOR-FOOTER-ONLY test fixture — NOT a playable Emerald save,
 * never place this mock fixture in a user's game or distribute as a save. */
static void make_fixture(const char *p, int variant, int extra)
{
    FILE *f=fopen(p,"wb");
    unsigned char b[4096];
    int sect,k;
    assert(f);
    for(sect=0;sect<32;sect++){
        memset(b,0xff,sizeof(b));
        if(sect<28){
            unsigned id=(unsigned)(sect%14);
            b[0]=(unsigned char)variant;
            b[0xff4]=(unsigned char)id; b[0xff5]=0;
            b[0xff8]=0x25;b[0xff9]=0x20;b[0xffa]=0x01;b[0xffb]=0x08;
            b[0xffc]=(unsigned char)(sect<14 ? 1 : 2);
            b[0xffd]=0;b[0xffe]=0;b[0xfff]=0;
        }
        assert(fwrite(b,1,sizeof(b),f)==sizeof(b));
    }
    for(k=0;k<extra;k++) assert(fputc(0xa0+k,f)!=EOF);
    assert(fclose(f)==0);
}
static int equal(const char *a,const char *b)
{
    FILE *x=fopen(a,"rb"),*y=fopen(b,"rb");
    int p,q;
    assert(x&&y);
    do {p=fgetc(x);q=fgetc(y);if(p!=q){fclose(x);fclose(y);return 0;}}while(p!=EOF);
    fclose(x);fclose(y);return 1;
}
static long filesize(const char *p)
{
    FILE *f=fopen(p,"rb");long n;
    assert(f);assert(!fseek(f,0,SEEK_END));n=ftell(f);fclose(f);return n;
}
int main(void)
{
    char dir[]="/tmp/emerald-profile-XXXXXX";
    char valid[512],changed[512],out[512],b1[512],b2[512],bad[512],empty[512],extra[512];
    SpProfileLock a,b;
    unsigned id;
    FILE *f;
    assert(mkdtemp(dir));
    snprintf(valid,sizeof(valid),"%s/emerald_source.sav",dir);
    snprintf(changed,sizeof(changed),"%s/different.sav",dir);
    snprintf(extra,sizeof(extra),"%s/extra.sav",dir);
    snprintf(bad,sizeof(bad),"%s/bad.sav",dir);
    snprintf(out,sizeof(out),"%s/profiles/Pokemon_A/pokeemerald.sav",dir);
    snprintf(b1,sizeof(b1),"%s/profiles/Pokemon_A/backups/000001.sav",dir);
    snprintf(b2,sizeof(b2),"%s/profiles/Pokemon_A/backups/000002.sav",dir);
    snprintf(empty,sizeof(empty),"%s/profiles/New_Player/pokeemerald.sav",dir);
    {char root[512];snprintf(root,sizeof(root),"%s/profiles",dir);assert(!mkdir(root,0700));}
    make_fixture(valid,17,0);make_fixture(changed,98,0);make_fixture(extra,45,16);
    assert(sp_validate_file(valid)==SP_OK);
    assert(sp_validate_file(extra)==SP_OK);
    f=fopen(bad,"wb");assert(f);assert(fputs("BAD DATA",f)>=0);assert(!fclose(f));
    assert(sp_validate_file(bad)==SP_BAD_SAVE);
    assert(!sp_valid_id("../hello")&&!sp_valid_id("with.dot")&&!sp_valid_id(""));
    assert(sp_valid_id("Pokemon_A"));
    {
        char root[512];snprintf(root,sizeof(root),"%s/profiles",dir);
        assert(sp_import(root,"../escape",valid)==SP_BAD_ARG);
        assert(sp_import(root,"Corrupt",bad)==SP_BAD_SAVE);
        assert(sp_import(root,"Pokemon_A",valid)==SP_OK);
        assert(sp_import(root,"Pokemon_A",changed)==SP_EXISTS);
        assert(sp_import(root,"Extra",extra)==SP_OK);
        assert(sp_create_empty(root,"New_Player")==SP_OK);
        assert(filesize(empty)==131072);
        f=fopen(empty,"rb");assert(f);assert(fgetc(f)==0xff);fclose(f);
        assert(sp_validate_file(empty)==SP_BAD_SAVE); /* blank, start New Game */
        assert(sp_lock(root,"Pokemon_A",&a)==SP_OK);
        assert(sp_lock(root,"Pokemon_A",&b)==SP_BUSY);
    }
    assert(equal(valid,out));
    assert(sp_backup(&a,&id)==SP_OK && id==1);
    assert(equal(out,b1));
    /* Simulates only a completed manual flash-save event, not concurrent write. */
    { FILE *src=fopen(changed,"rb"),*dst=fopen(out,"wb");int c;assert(src&&dst);
      while((c=fgetc(src))!=EOF)assert(fputc(c,dst)!=EOF);
      assert(!fclose(dst));fclose(src); }
    assert(sp_backup(&a,&id)==SP_OK && id==2);
    assert(equal(out,b2));
    assert(sp_restore(&a,1)==SP_OK);
    assert(equal(out,valid));
    /* An invalid backup must NEVER replace the active .sav. These fixtures
     * exercise container/footer handling only; they are NOT playable saves. */
    {
        char invalid_backup[512];
        snprintf(invalid_backup,sizeof(invalid_backup),
                 "%s/profiles/Pokemon_A/backups/000003.sav",dir);
        f=fopen(invalid_backup,"wb");
        assert(f && fputs("BROKEN_BACKUP",f)>=0 && fclose(f)==0);
        assert(sp_restore(&a,3)==SP_BAD_SAVE);
        assert(equal(out,valid));
        assert(remove(invalid_backup)==0);
    }
    assert(sp_prune(&a,2)==SP_OK);
    assert(access(b1,F_OK)!=0);
    assert(equal(b2,changed));
    assert(sp_backup(&a,&id)==SP_OK && id==4); /* do not reuse pruned IDs */
    assert(sp_restore(&a,1)==SP_IO); /* pruned backup cannot be restored */
    /* Corrupt the active file: restoration must preserve it as .raw first. */
    f=fopen(out,"wb");assert(f);assert(fputs("CORRUPT",f)>=0);assert(!fclose(f));
    assert(sp_restore(&a,2)==SP_OK);
    assert(equal(out,changed));
    {char recovery[512];snprintf(recovery,sizeof(recovery),"%s/profiles/Pokemon_A/backups/bad000001.raw",dir);
     assert(filesize(recovery)==7);}
    sp_unlock(&a);
    {char root[512];snprintf(root,sizeof(root),"%s/profiles",dir);
     assert(sp_lock(root,"Pokemon_A",&a)==SP_OK);sp_unlock(&a);}
    puts("passed: source-preserving import, multi-profiles, exclusive lock, backups, restore from corrupt, pruning");
    return 0;
}
