"""Offline policy tests; syscall cadence only, no hardware or networking."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from experimentos.adc8_relay_accept_v17.run import EXP

SOURCE=r'''
#include <assert.h>
#include "accept_policy.h"
int main(void){
 unsigned every=0;
 assert(scope_accept_interval(0,&every) && every==1);
 assert(scope_accept_interval("1",&every) && every==1);
 assert(scope_accept_interval("8",&every) && every==8);
 assert(!scope_accept_interval("",&every) && !scope_accept_interval("0",&every));
 assert(!scope_accept_interval("08",&every) && !scope_accept_interval("9",&every));
 assert(scope_accept_profile(8,1,100,3456) && scope_accept_profile(8,1,98,3456));
 assert(!scope_accept_profile(8,1,112,3456) && !scope_accept_profile(8,1,98,3455));
 assert(!scope_accept_profile(8,2,98,3456) && !scope_accept_profile(10,1,98,3456));
 struct ScopeAcceptPolicy p={.phase=0,.every=8};
 int client=42,closed_incoming=0,calls=0;
 for(unsigned frame=1;frame<=24;++frame){
  int due=scope_accept_due(&p,client>=0,1);assert(due==(frame%8==0));
  if(due){int incoming=77;++calls;if(client>=0)++closed_incoming;else client=incoming;}
  assert(client==42);
 }
 assert(calls==3 && closed_incoming==3);
 p.phase=7;assert(scope_accept_due(&p,0,1) && p.phase==0);
 for(unsigned i=0;i<16;++i)assert(scope_accept_due(&p,0,1));
 assert(!scope_accept_due(&p,1,1) && p.phase==1);
 for(unsigned i=0;i<16;++i)assert(scope_accept_due(&p,1,0) && p.phase==0);
 p.every=1;for(unsigned i=0;i<24;++i)assert(scope_accept_due(&p,1,1));
 return 0;
}
'''


class AcceptPolicyTests(unittest.TestCase):
    def test_c_cadence_exact_profiles_no_client_low_and_second_client_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'test.c').write_text(SOURCE)
            subprocess.run(['cc','-O2','-std=c11','-Wall','-Wextra','-Werror','-I',str(EXP/'relay'),str(root/'test.c'),'-o',str(root/'test')],check=True)
            subprocess.run([str(root/'test')],check=True)

    def test_stale_ack_guard_and_recv_send_paths_are_retained(self):
        original=EXP.parent/'adc8_relay_edge_v17/relay/unoq_config_stream.c'
        def guard(text):
            start=text.index('        if (client<0 && (pending ||')
            return text[start:text.index('            continue;\n        }',start)+len('            continue;\n        }')]
        current=(EXP/'relay/unoq_config_stream.c').read_text()
        self.assertEqual(guard(current),guard(original.read_text()))
        self.assertLess(current.index('ssize_t received=recv('),current.index('int accept_due=scope_accept_due'))
        self.assertGreater(current.index('if(scope_send_frame('),current.index('if(accept_due)'))
