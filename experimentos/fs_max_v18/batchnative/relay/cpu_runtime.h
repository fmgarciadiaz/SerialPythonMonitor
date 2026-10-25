#pragma once
/* Isolated CPU policy for exact accepted ADC8/10/12/14 CH1 profiles. */
static bool spi40_active=false;
static cpu_set_t spi40_original_cpus;
static char spi40_original_governor[64];
static bool spi40_saved=false;
static int governor_read(char *value,size_t size) {
    FILE *f=fopen("/scope_cpu_governor","r");if(!f)return -1;
    bool ok=fgets(value,(int)size,f)!=NULL;int error=fclose(f);
    if(!ok || error)return -1;
    value[strcspn(value,"\r\n")]=0;return 0;
}
static int governor_write(const char *value) {
    FILE *f=fopen("/scope_cpu_governor","w");if(!f)return -1;
    int written=fprintf(f,"%s",value);int closed=fclose(f);
    char actual[64];
    return written<0 || closed || governor_read(actual,sizeof actual)<0 || strcmp(actual,value)?-1:0;
}
static int scope_cpu_runtime(bool enable) {
    if(enable==spi40_active)return 0;
    if(enable) {
        if(sched_getaffinity(0,sizeof spi40_original_cpus,&spi40_original_cpus)<0 ||
            governor_read(spi40_original_governor,sizeof spi40_original_governor)<0)return -1;
        spi40_saved=true;
        cpu_set_t target;CPU_ZERO(&target);CPU_SET(2,&target);
        if(governor_write("performance")<0 || sched_setaffinity(0,sizeof target,&target)<0)return -1;
        cpu_set_t actual;
        if(sched_getaffinity(0,sizeof actual,&actual)<0 || !CPU_EQUAL(&actual,&target))return -1;
        spi40_active=true;
        fprintf(stderr,"V17 CPU runtime: CPU2 performance verified\n");
    } else {
        int a=governor_write(spi40_original_governor);
        int b=sched_setaffinity(0,sizeof spi40_original_cpus,&spi40_original_cpus);
        if(a<0 || b<0)return -1;
        spi40_active=false;spi40_saved=false;
        fprintf(stderr,"V17 CPU runtime: original CPU policy restored\n");
    }
    return 0;
}
static int scope_cpu_restore(void) {
    if(!spi40_saved)return 0;
    int a=governor_write(spi40_original_governor);
    int b=sched_setaffinity(0,sizeof spi40_original_cpus,&spi40_original_cpus);
    spi40_active=false;spi40_saved=false;
    return a<0 || b<0?-1:0;
}
