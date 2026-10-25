#pragma once
/* Gate only redundant accepts while an exact ADC8 high-rate client is active. */
struct ScopeAcceptPolicy { unsigned phase,every; };
static inline int scope_accept_interval(const char *text,unsigned *every) {
    if(!text || (text[0]=='1' && !text[1])){*every=1;return 1;}
    if(text[0]=='8' && !text[1]){*every=8;return 1;}
    return 0;
}
static inline int scope_accept_profile(unsigned bits,unsigned channels,unsigned ticks,unsigned pairs) {
    return bits==8 && channels==1 && (ticks==100 || ticks==98) && pairs==3456;
}
static inline int scope_accept_due(struct ScopeAcceptPolicy *p,int active,int eligible) {
    if(!active || !eligible){p->phase=0;return 1;}
    if(++p->phase==p->every){p->phase=0;return 1;}
    return 0;
}
