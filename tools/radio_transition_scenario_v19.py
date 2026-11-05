"""Pure state machine for deliberate Stop/restart and Scan-while-A0 GUI probes."""
class RadioTransitions:
    def __init__(self,restart=False,scan=False):
        self.restart=restart;self.scan=scan;self.restarted=False;self.scanned=False
        self.phase='playing';self.session=None;self.since=None;self.deadline=None
    @property
    def expected_pause(self):return self.phase in ('wait-stop','wait-play','scanning')
    @property
    def complete(self):return (not self.restart or self.restarted) and (not self.scan or self.scanned)
    def playing(self,session,now,scan_complete=False):
        if self.session==session:return False
        if self.session is None:
            self.session=session;self.since=now;return False
        if self.phase=='wait-play':self.restarted=True
        elif self.phase=='scanning' and scan_complete:self.scanned=True
        else:return False
        self.session=session;self.since=now;self.deadline=None;self.phase='playing'
        return True
    def action(self,now,idle):
        if self.expected_pause and now>self.deadline:raise TimeoutError('RADIO/A0 no reanudó después de la transición')
        if self.phase=='wait-stop' and idle:
            self.phase='wait-play';return 'start'
        if self.phase!='playing' or self.since is None or now-self.since<5:return None
        if self.restart and not self.restarted:
            self.phase='wait-stop';self.deadline=now+25;return 'stop'
        if self.scan and not self.scanned:
            self.phase='scanning';self.deadline=now+25;return 'scan'
        return None
