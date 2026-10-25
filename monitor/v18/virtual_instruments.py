"""Reduced physical instruments: modal stiff piano and shared bridge/body."""
import numpy as np
from functools import lru_cache
from scipy.signal import iirpeak
from monitor.v18.fm_feedback import njit
from monitor.v18.piano_profile import piano_profile

def _guitar_radiation(first,second,previous,rate,frequency):
    output=np.empty(len(first))
    for i in range(len(first)):
        raw=.72*first[i]+.28*second[i]
        delta=raw-previous
        output[i]=.65*raw+.22*np.tanh(delta*rate/(2*np.pi*frequency))
        previous=raw
    return output,previous

guitar_radiation_kernel=njit(cache=True,nogil=True)(_guitar_radiation) if njit else _guitar_radiation

def _modes(state, rotation, amplitudes, force, age, count, strings, coupling):
    output=np.zeros(count)
    coupling_step=1-(1-coupling)**8
    for i in range(count):
        drive=force[age+i] if age+i<len(force) else 0.0
        value=0.0
        for j in range(len(state)):
            real=state[j,0]*rotation[j,0]-state[j,1]*rotation[j,1]+drive
            imag=state[j,0]*rotation[j,1]+state[j,1]*rotation[j,0]
            state[j,0]=real;state[j,1]=imag
            value+=imag*amplitudes[j]
        if strings>1 and (age+i)%8==0:
            partials=len(state)//(2*strings)
            for plane in range(2):
                for partial in range(partials):
                    real_mean=0.0;imag_mean=0.0
                    for string in range(strings):
                        index=(plane*strings+string)*partials+partial
                        real_mean+=state[index,0];imag_mean+=state[index,1]
                    real_mean/=strings;imag_mean/=strings
                    for string in range(strings):
                        index=(plane*strings+string)*partials+partial
                        state[index,0]+=coupling_step*(real_mean-state[index,0])
                        state[index,1]+=coupling_step*(imag_mean-state[index,1])
        output[i]=value
    return output

def _hammer(rate, velocity, hardness, mass, impedance, stiffness, exponent, frequency, position, incoming_velocity=0.):
    # Nonlinear felt contact with waves returning from the two fixed ends.
    stiffness*=2**(4*(hardness-.78))
    speed=.45+3.5*velocity
    compression=0.0
    force=np.zeros(int(rate*.012))
    left=np.zeros(len(force));right=np.zeros(len(force))
    delay_left=max(1.,rate*position/frequency)
    delay_right=max(1.,rate*(1-position)/frequency)
    for i in range(len(force)):
        incoming_left=0.;incoming_right=0.
        for side in range(2):
            delay=delay_left if side==0 else delay_right
            history=left if side==0 else right
            at=i-delay
            lower=int(np.floor(at));fraction=at-lower
            returning=0.
            if lower>=0:returning+=(1-fraction)*history[lower]
            if lower+1>=0:returning+=fraction*history[lower+1]
            if side==0:incoming_left=returning
            else:incoming_right=returning
        contact=stiffness*max(0.0,compression)**exponent
        travelling=contact/impedance
        left[i]=-(travelling+incoming_right)
        right[i]=-(travelling+incoming_left)
        speed-=contact/(mass*rate)
        compression+=(speed-travelling-incoming_left-incoming_right-incoming_velocity)/rate
        force[i]=contact
        if compression<=0 and speed-incoming_velocity<0:break
    total=force.sum()
    if total>0:force/=total
    return force

def _resonate(signal, coefficients, state, weights):
    output=np.zeros(len(signal))
    for i in range(len(signal)):
        for j in range(len(weights)):
            b0,b1,b2,a1,a2=coefficients[j]
            value=b0*signal[i]+state[j,0]
            state[j,0]=b1*signal[i]-a1*value+state[j,1]
            state[j,1]=b2*signal[i]-a2*value
            output[i]+=weights[j]*value
    return output

def _zero_sos(coefficients,signal):
    output=np.empty(len(signal))
    state=np.zeros((len(coefficients),2))
    for i in range(len(signal)):
        value=signal[i]
        for j in range(len(coefficients)):
            row=coefficients[j]
            filtered=row[0]*value+state[j,0]
            state[j,0]=row[1]*value-row[4]*filtered+state[j,1]
            state[j,1]=row[2]*value-row[5]*filtered
            value=filtered
        output[i]=value
    return output

def _strain_highpass(output,previous):
    strain=np.empty(len(output))
    for i in range(len(output)):
        value=output[i]*output[i]
        filtered=value+previous
        previous=-value+.995*filtered
        strain[i]=filtered
    return strain,previous

def _contact_envelope(force,count,pole):
    """Causal convolution with an exponential, without FFT setup per band."""
    output=np.zeros(count)
    value=0.
    for i in range(count):
        value=value*pole+(force[i] if i<len(force) else 0.)
        output[i]=value
    return output

def _release_resonate(count,coefficients,state,weights,age,fade_samples,limit):
    """Free resonances and their absolute-clock fade in one compiled loop."""
    output=np.zeros(count)
    for i in range(count):
        for j in range(len(weights)):
            value=state[j,0]
            state[j,0]=-coefficients[j,3]*value+state[j,1]
            state[j,1]=-coefficients[j,4]*value
            output[i]+=weights[j]*value
        clock=age+i
        output[i]*=min(clock/fade_samples,1.) if clock<limit else 0.
    return output

def _bridge_unisons(state, strings, losses):
    # Passive rank-one bridge loss per partial/polarization. Only the common
    # motion radiates: differential motion is preserved, not synchronized.
    partials=len(state)//(2*strings)
    for plane in range(2):
        for partial in range(partials):
            real=0.;imag=0.
            for string in range(strings):
                index=(plane*strings+string)*partials+partial
                real+=state[index,0];imag+=state[index,1]
            real*=losses[plane*partials+partial]/strings
            imag*=losses[plane*partials+partial]/strings
            for string in range(strings):
                index=(plane*strings+string)*partials+partial
                state[index,0]-=real;state[index,1]-=imag

bridge_unisons_kernel=njit(cache=True,nogil=True)(_bridge_unisons) if njit else None

def _piano_motion(state,rotation,moving_rotation,amplitudes,force,age,count,angles,shift,relaxation,strings,losses,drive_phase):
    output=np.zeros(count)
    tension=shift
    step=np.exp(-relaxation)
    for i in range(count):
        # Update on the absolute sample clock, not on block boundaries.
        # Tension changes slowly; holding its rotation for 16 samples avoids
        # four extra multiplications per mode/sample at essentially the same
        # pitch trajectory. Saved coefficients also survive short blocks.
        if (age+i)%16==0:
            for j in range(len(state)):
                angle=angles[j]*tension
                cosine=1-.5*angle*angle
                moving_rotation[j,0]=rotation[j,0]*cosine-rotation[j,1]*angle
                moving_rotation[j,1]=rotation[j,1]*cosine+rotation[j,0]*angle
        drive=force[age+i] if age+i<len(force) else 0.
        value=0.
        for j in range(len(state)):
            real=state[j,0]*moving_rotation[j,0]-state[j,1]*moving_rotation[j,1]
            imag=state[j,0]*moving_rotation[j,1]+state[j,1]*moving_rotation[j,0]
            if drive!=0:
                real+=drive*drive_phase[j,0];imag+=drive*drive_phase[j,1]
            state[j,0]=real;state[j,1]=imag
            value+=state[j,1]*amplitudes[j]
        if strings>1 and (age+i)%16==15:
            bridge_unisons_kernel(state,strings,losses)
        output[i]=value
        tension*=step
    return output,tension

modal_kernel=njit(cache=True,nogil=True)(_modes) if njit else None
_hammer_kernel=njit(cache=True,nogil=True)(_hammer) if njit else None
@lru_cache(maxsize=256)
def hammer_kernel(rate, velocity, hardness, frequency, position=None, incoming_velocity=0.):
    profile=piano_profile(frequency)
    if _hammer_kernel is None:raise RuntimeError('Virtual requiere Numba')
    position=profile['position'] if position is None else position
    force=_hammer_kernel(rate,velocity,hardness,profile['mass'],profile['impedance'],profile['contact_k'],profile['exponent'],frequency,position,incoming_velocity)
    force.setflags(write=False)
    return force
body_kernel=njit(cache=True,nogil=True)(_resonate) if njit else None
contact_envelope_kernel=njit(cache=True,nogil=True)(_contact_envelope) if njit else _contact_envelope
strain_kernel=njit(cache=True,nogil=True)(_strain_highpass) if njit else _strain_highpass
attack_filter_kernel=njit(cache=True,nogil=True)(_zero_sos) if njit else _zero_sos
release_kernel=njit(cache=True,nogil=True)(_release_resonate) if njit else _release_resonate
piano_motion_kernel=njit(cache=True,nogil=True)(_piano_motion) if njit else None

@lru_cache(maxsize=256)
def _peak_bank(rate, modes):
    coefficients=[]
    for frequency,q in modes:
        b,a=iirpeak(frequency,q,fs=rate)
        coefficients.append((*b,a[1],a[2]))
    result=np.asarray(coefficients)
    result.setflags(write=False)
    return result

@lru_cache(maxsize=256)
def hammer_impact(rate, velocity, hardness, frequency, position):
    """Short structural contact sound, driven by felt force, not white noise.

    Frequencies/T60 are design values, not a measured hammer transfer.
    Precomputation keeps this component out of the per-sample voice loop.
    """
    contact_rate=max(80000,rate)
    force=hammer_kernel(contact_rate,velocity,hardness,frequency,position)
    if contact_rate!=rate:
        ratio=contact_rate//rate
        force=force[:len(force)//ratio*ratio].reshape(-1,ratio).sum(axis=1)
    driven=np.zeros(int(rate*.04))
    driven[:len(force)]=force
    modes=tuple((f,np.pi*f*t60/np.log(1000)) for f,t60 in
                ((190.,.012),(620.,.008),(1800.,.004)) if f<rate*.42)
    coefficients=_peak_bank(rate,modes)
    weights=np.array((.6,.3,.1))[:len(modes)]
    impact=body_kernel(driven,coefficients,np.zeros((len(modes),2)),weights)
    # A discrete unit-area force has amplitude proportional to 1/fs.
    impact*=rate*.00012*(.35+.65*velocity)
    impact.setflags(write=False)
    return impact

@lru_cache(maxsize=32)
def _attack_band(rate,low,high):
    from scipy.signal import butter
    return butter(2,(low,high),btype='bandpass',fs=rate,output='sos')

@lru_cache(maxsize=128)
def attack_texture(rate,frequency,velocity,brightness,levels):
    """Force-shaped, band-limited stochastic radiation; stores no recording."""
    count=round(rate*.12)
    result=np.zeros(count)
    if not any(levels):return result
    white=np.random.default_rng(round(frequency*100)+round(velocity*1000)).normal(size=count)
    time=np.arange(count)/rate
    force=hammer_kernel(80000,velocity,brightness,frequency)
    ratio=80000//rate
    force=force[:len(force)//ratio*ratio].reshape(-1,ratio).sum(axis=1)
    force.setflags(write=False)
    for gain,(low,high),decay in zip(levels,((100,400),(400,900),(900,1800),(1800,3500),(3500,6000),(6000,8400)),(.035,.028,.022,.018,.013,.009)):
        high=min(high,rate*.42)
        if gain==0 or low>=high:continue
        sos=_attack_band(rate,low,high)
        envelope=contact_envelope_kernel(force,count,float(np.exp(-1/(rate*decay))))
        result+=gain*attack_filter_kernel(sos,white)*envelope
    taper=np.clip((.12-time)/.02,0,1)
    result*=taper*taper*(3-2*taper)
    result.setflags(write=False)
    return result

def warmup():
    guitar_radiation_kernel(np.zeros(8),np.zeros(8),0.,80000,440.)
    if modal_kernel is not None:
        from monitor.v18.piano_room import warmup as warmup_room
        warmup_room()
        from monitor.v18.piano_calibration import _rows
        _rows()  # Load the small parameter file before the first MIDI note.
        modal_kernel(np.zeros((4,2)),np.zeros((4,2)),np.ones(4),np.zeros(8),0,8,1,.0)
        hammer_kernel(80000,.8,.75,220.)
        piano_motion_kernel(np.zeros((4,2)),np.zeros((4,2)),np.zeros((4,2)),np.ones(4),np.zeros(8),0,8,np.ones(4),.001,1/2800.,1,np.zeros(4),np.tile([1.,0.],(4,1)))
        bridge_unisons_kernel(np.zeros((12,2)),3,np.zeros(4))
        # Match cached read-only coefficients: otherwise Numba compiles a
        # new signature during the first note instead of startup.
        coefficients=np.zeros((4,5));coefficients.setflags(write=False)
        body_kernel(np.zeros(8),coefficients,np.zeros((4,2)),np.ones(4))
        force=np.zeros(8);force.setflags(write=False)
        contact_envelope_kernel(force,8,.9)
        strain_kernel(np.zeros(8),0.)
        release_kernel(8,coefficients,np.zeros((4,2)),np.ones(4),0,200,10000)
        for rate in (20000,40000):
            for low,high in ((100,400),(400,900),(900,1800),(1800,3500),(3500,6000),(6000,8400)):
                high=min(high,rate*.42)
                if low<high:attack_filter_kernel(_attack_band(rate,low,high),np.zeros(8))
            hammer_impact(rate,.8,.78,220.,.12)
            for model in ('piano','guitar'):
                InstrumentBody(rate,model).render(np.zeros(8),.45,.2)

class PianoStrings:
    def __init__(self,rate,frequency,position=.12,velocity=1.,bandlimit=None,calibrated=False):
        self.rate=rate;self.frequency=frequency;self.position=position
        self.velocity=velocity;self.bandlimit=bandlimit or rate*.42
        self.key=None;self.state=None;self.age=0
        self.force=None
        self.residual_strike=False;self.incoming_velocity=0.
        self.tension_shift=None
        self.profile=dict(piano_profile(frequency))
        self.correction=None
        if calibrated:
            from monitor.v18.piano_calibration import modal_correction
            self.correction=modal_correction(frequency,velocity)
            if self.correction is not None:
                self.profile['stiffness']*=self.correction['stiffness_scale']
                self.profile['position']*=self.correction['position_scale']
    def restrike(self,velocity):
        # Keep ringing modes; incoming contact velocity is frozen during the
        # short impact (a reduced commuted-contact approximation).
        self.incoming_velocity=float(np.clip(.03*np.dot(self.state[:,0],self.amplitudes),-.15,.15)) if self.state is not None else 0.
        self.velocity=velocity;self.age=0;self.key=None;self.force=None
        self.residual_strike=self.state is not None;self.tension_shift=None

    def render(self,count,brightness=.75,decay=4.,stiffness=.0003,bridge=.2,damper_t60=0.):
        if modal_kernel is None:raise RuntimeError('Virtual requiere Numba')
        key=(brightness,decay,stiffness,bridge,damper_t60)
        if key!=self.key:
            # Normal modes of a pinned stiff string, fundamental normalized.
            if not hasattr(self,'orders'):
                candidates=np.arange(1,min(128,max(1,int(self.bandlimit/self.frequency)))+1,dtype=float)
                b=self.profile['stiffness']*stiffness/.0003
                self.orders=candidates[self.frequency*candidates*np.sqrt((1+b*candidates*candidates)/(1+b))<self.bandlimit/2**(2.45/1200)]
            n=self.orders
            effective_stiffness=self.profile['stiffness']*stiffness/.0003
            # Fixed mode count permits phase-continuous live stiffness changes.
            offsets=((0.,),(-1.5,.9),(-2.,.28,1.3))[self.profile['strings']-1]
            if self.correction is not None:
                offsets=tuple(c*self.correction['unison_scale'] for c in offsets)
            self.strings=len(offsets)
            frequencies=np.concatenate([self.frequency*n*np.sqrt((1+effective_stiffness*(1+.025*string)*n*n)/(1+effective_stiffness*(1+.025*string)))*2**(c/1200) for string,c in enumerate(offsets)])
            order=np.tile(n,len(offsets))
            # Bridge force scales with modal slope; felt pulse supplies the
            # actual time-varying excitation instead of a prefilled sine bank.
            position=np.clip(self.profile['position']*self.position/.12,.01,.95)
            # Excitation at the hammer and observation at the bridge have
            # opposite-end parity. Frequency losses follow the modal force.
            excitation=np.sin(np.pi*order*position)/order
            observation=order*np.cos(np.pi*order)/order**.25
            amplitudes=excitation*observation
            amplitudes*=np.clip((self.bandlimit-frequencies)/(self.bandlimit*.1),0,1)
            # Output normalization for the bridge-force observation; preserve
            # patch loudness after replacing the old displacement weighting.
            amplitudes*=2.8/max(np.sum(abs(amplitudes)),1e-12)
            if self.correction is not None:
                amplitudes*=np.interp(order,np.arange(1,len(self.correction['gain'])+1),self.correction['gain'])
                # Gentle upper-partial voicing, leaving the first two modes
                # and the calibrated hammer/rise settings intact.
                upper_weight=np.clip((order-2)/6,0,1)
                amplitudes*=1+(self.correction['harmonic_gain']-1)*upper_weight
            register=np.clip((220/self.frequency)**.3,.45,2.)
            lifetime=decay*register/(1+(frequencies/2200)**1.3+bridge*.3)
            lifetime*=np.repeat(np.linspace(.94,1.08,self.strings),len(n))
            if self.correction is not None:
                lifetime*=np.interp(order,np.arange(1,len(self.correction['decay'])+1),self.correction['decay'])
                lifetime*=1+(self.correction['harmonic_decay']-1)*upper_weight
            # Fast energy radiates via bridge; weak orthogonal polarization
            # retains a slower tail, giving the characteristic double decay.
            polar_detune=self.correction['polar_detune_scale'] if self.correction is not None else 1.
            frequencies=np.concatenate((frequencies,frequencies*2**(.45*polar_detune/1200)))
            lifetime=np.concatenate((lifetime*.9,lifetime*2.2))
            if damper_t60>0:lifetime=1/(1/lifetime+1/damper_t60)
            tail_mix=self.correction['tail_mix'] if self.correction is not None else .22
            amplitudes=np.concatenate((amplitudes*(1-tail_mix),amplitudes*tail_mix))
            radius=10**(-3/(lifetime*self.rate))
            angle=2*np.pi*frequencies/self.rate
            self.motion_angles=angle/np.tile(1+effective_stiffness*order*order,2)
            phases=np.zeros(len(angle))
            if self.correction is not None:
                phases=np.interp(np.tile(order,2),np.arange(1,33),np.unwrap(self.correction['phase']))
            self.drive_phase=np.column_stack((np.cos(phases),np.sin(phases)))
            self.rotation=np.column_stack((radius*np.cos(angle),radius*np.sin(angle)))
            self.moving_rotation=self.rotation.copy()
            # Common bridge motion loses energy faster than differential
            # motion. This reduced narrow-band impedance is dissipative;
            # it does not model full cross-key soundboard feedback.
            common_t60=decay*register/(1+(self.frequency*n/2200)**1.3)
            loss_rate=np.log(1000)*np.clip(bridge,0,1)*2/common_t60
            self.bridge_losses=1-np.exp(-16*np.concatenate((loss_rate,loss_rate*.25))/self.rate)
            if self.state is None:
                self.state=np.zeros((len(amplitudes),2))
            if self.force is None:
                hammer_rate=max(80000,self.rate)
                self.force=hammer_kernel(hammer_rate,float(self.velocity),float(brightness),float(self.frequency),float(position),self.incoming_velocity)
                self.impact=hammer_impact(self.rate,float(self.velocity),float(brightness),float(self.frequency),float(position))
                levels=tuple(self.correction['noise']) if self.correction is not None else (0.,)*6
                self.texture=attack_texture(self.rate,float(self.frequency),float(self.velocity),float(brightness),levels)
                if hammer_rate!=self.rate:
                    ratio=hammer_rate//self.rate
                    self.force=self.force[:len(self.force)//ratio*ratio].reshape(-1,ratio).sum(axis=1)
            self.amplitudes=amplitudes
            self.frequencies=frequencies;self.key=key
        # Keep unison differences instead of forcibly synchronizing their states.
        # Relaxation of extra tension after impact, rather than a cyclic LFO.
        shift=2**(1.2*self.velocity*self.velocity/1200)-1
        relaxation=1/(self.rate*.14)
        if self.tension_shift is None:self.tension_shift=shift
        output,self.tension_shift=piano_motion_kernel(self.state,self.rotation,self.moving_rotation,self.amplitudes,self.force,self.age,count,self.motion_angles,self.tension_shift,relaxation,self.strings,self.bridge_losses,self.drive_phase)
        available=min(count,max(0,len(self.impact)-self.age))
        if available:output[:available]+=self.impact[self.age:self.age+available]
        if not hasattr(self,'longitudinal_coefficients'):
            fundamental=np.sqrt(210e9/7850)/(2*self.profile['length'])
            modes=tuple((float(fundamental*n),float(np.pi*fundamental*n*.12/np.log(1000))) for n in (1,2,3) if fundamental*n<self.bandlimit)
            self.longitudinal_coefficients=_peak_bank(self.rate,modes) if modes else None
            self.longitudinal_state=np.zeros((len(modes),2))
            self.longitudinal_weights=np.ones(len(modes))/max(1,len(modes))
            self.strain_previous=0.
        if self.longitudinal_coefficients is not None:
            # One-way nonlinear strain proxy; not a spatial string PDE.
            strain,self.strain_previous=strain_kernel(output,self.strain_previous)
            longitudinal=body_kernel(strain,self.longitudinal_coefficients,self.longitudinal_state,self.longitudinal_weights)
            output+=2*self.velocity*longitudinal
        if self.correction is not None and not self.residual_strike:
            # Acoustic build-up identified from the reference envelope. This
            # reduced radiation term is distinct from the editable ADSR.
            rise=self.correction['rise_seconds']
            available=min(count,max(0,int(12*rise*self.rate)-self.age))
            if available:
                time=(self.age+np.arange(available))/self.rate
                output[:available]*=-np.expm1(-time/rise)
        if self.correction is not None:
            # Register-specific voicing of the short strike; leave modal decay
            # and the calibrated acoustic rise unchanged. Do not amplify the
            # already ringing strings when a key is struck again.
            available=min(count,max(0,round(.12*self.rate)-self.age))
            if available and not self.residual_strike:
                time=(self.age+np.arange(available))/self.rate
                pulse=(time/.018)*np.exp(1-time/.018)
                pulse*=np.clip((.12-time)/.02,0,1)**2
                output[:available]*=1+(self.correction['attack_gain']-1)*pulse
            available=min(count,max(0,len(self.impact)-self.age))
            if available:
                output[:available]+=(self.correction['hammer_gain']-1)*self.impact[self.age:self.age+available]
        available=min(count,max(0,len(self.texture)-self.age))
        if available:output[:available]+=self.texture[self.age:self.age+available]
        self.age+=count
        return output

class InstrumentBody:
    def __init__(self,rate,model):
        self.model=model
        # Illustrative resonances, not measurements of a particular instrument.
        modes=((102,9,.28),(195,12,.22),(285,16,.18),(430,18,.13),(680,22,.11),(1100,25,.08)) if model=='guitar' else ((92,10,.12),(160,15,.15),(265,18,.16),(420,22,.17),(700,25,.16),(1200,28,.14),(2300,30,.10))
        modes=list(modes)
        # Thin-plate-inspired structural modes, synthetic dimensions/material.
        for m in range(1,7):
            for n in range(1,6):
                frequency=(72*m*m+43*n*n) if model=='guitar' else (39*m*m+28*n*n)
                if frequency>350 and frequency<min(6500,rate*.42):
                    modes.append((frequency,5+1.4*(m+n),.07/(m+n)))
        coeff=[];weights=[]
        for frequency,q,weight in modes:
            if frequency>=rate*.42:continue
            if model=='piano':
                t60=np.clip(.65*(160/frequency)**.35,.16,.9)
                q=np.pi*frequency*t60/np.log(1000)
            coeff.append((frequency,q));weights.append(weight)
        self.coefficients=_peak_bank(rate,tuple(coeff))
        self.weights=np.array(weights)
        self.weights/=np.linalg.norm(self.weights) if model=='piano' else self.weights.sum()
        self.state=np.zeros((len(weights),2));self.bridge_previous=0.
        self.rate=rate
        self.bridge_alpha=1-np.exp(-2*np.pi*(4500 if model=='guitar' else 6500)/rate)
        notes=range(36,97) if model=='piano' else (40,45,50,55,59,64)
        pairs=[(n,h,440*2**((n-69)/12)*h) for n in notes for h in ((1,2) if model=='piano' else (1,)) if 440*2**((n-69)/12)*h<rate*.42]
        self.sympathetic_notes=np.array([x[0] for x in pairs])
        self.sympathetic_frequencies=np.array([x[2] for x in pairs])
        self.sympathetic_state=np.zeros((len(self.sympathetic_frequencies),2))
        self.sympathetic_weights=np.ones(len(self.sympathetic_frequencies))/(np.sqrt(len(self.sympathetic_frequencies)) if model=='piano' else len(self.sympathetic_frequencies))
        if model=='piano':self.sympathetic_weights/=np.array([x[1] for x in pairs])
        self.open_notes=()
        self.release_tracks={}
        self.sympathetic_banks={}
        for pedal in (False,True):
            modes=[]
            for frequency in self.sympathetic_frequencies:
                t60=np.clip(5*(220/frequency)**.45,1.2,9.) if pedal else .12
                q=np.pi*frequency*t60/np.log(1000) if model=='piano' else 70
                modes.append((float(frequency),float(q)))
            self.sympathetic_banks[pedal]=_peak_bank(rate,tuple(modes))
        self.pedal=None;self.sympathetic_coefficients=None
        self.radiation_previous=0.
        self.radiation_pole=np.exp(-2*np.pi*(65 if model=='guitar' else 28)/rate)
        self.early_buffer=np.zeros(round(rate*.02));self.early_position=0
        self.early_taps=np.rint(np.array((.0017,.0043,.0089,.0147))*rate).astype(np.int64)
        self.early_weights=np.array((.045,-.025,.018,.012))
    def set_open_notes(self,notes,sustain=False):
        notes=tuple(sorted(set(notes)))
        if self.model=='piano':
            if sustain:
                notes=tuple(sorted(set(notes)|set(self.open_notes)))
            from monitor.v18.piano_calibration import modal_correction
            for note in set(self.open_notes)-set(notes):
                if sustain or note>=89:continue
                mask=self.sympathetic_notes==note
                if not np.any(mask):continue
                correction=modal_correction(440*2**((note-69)/12),.5)
                if correction is None or not correction['release_tail_mix']:continue
                t60=correction['release_t60']
                modes=tuple((float(f),float(np.pi*f*t60/np.log(1000))) for f in self.sympathetic_frequencies[mask])
                # Transfer existing resonance state, with no new impulse or
                # sample playback. A fixed note map bounds shared tail memory.
                self.release_tracks[note]=[_peak_bank(self.rate,modes),self.sympathetic_state[mask].copy(),
                    self.sympathetic_weights[mask]*.3*correction['release_tail_mix'],0,t60]
            for note in set(notes)-set(self.open_notes):
                self.release_tracks.pop(note,None)
        self.open_notes=notes
    def render(self,signal,mix,bridge,sustain=False):
        if body_kernel is None:return signal
        # Yielding bridge: dissipative one-pole mechanical transmission,
        # then feedforward resonances of top/air/enclosure. No active return.
        from scipy.signal import lfilter
        driven,state=lfilter([self.bridge_alpha],[1,-(1-self.bridge_alpha)],signal,zi=[self.bridge_previous])
        self.bridge_previous=float(state[0])
        driven=(1-bridge)*signal+bridge*driven
        # Radiation removes static displacement / non-radiating DC motion.
        driven,hp_state=lfilter([1,-1],[1,-self.radiation_pole],driven,zi=[self.radiation_previous])
        self.radiation_previous=float(hp_state[0])
        body=body_kernel(driven,self.coefficients,self.state,self.weights)
        pedal=bool(sustain) if self.model=='piano' else False
        key=(pedal,self.open_notes) if self.model=='piano' else pedal
        if self.pedal!=key:
            if self.model=='piano':
                active=np.ones(len(self.sympathetic_notes),dtype=bool) if pedal else np.isin(self.sympathetic_notes,self.open_notes)|(self.sympathetic_notes>=89)
                self.sympathetic_coefficients=self.sympathetic_banks[False].copy()
                self.sympathetic_coefficients[active]=self.sympathetic_banks[True][active]
                self.sympathetic_coefficients.setflags(write=False)
                self.active_sympathetic_weights=self.sympathetic_weights*np.where(active,.3,.08)
            else:
                self.sympathetic_coefficients=self.sympathetic_banks[pedal]
                self.active_sympathetic_weights=self.sympathetic_weights*.08
            self.pedal=key
        sympathetic=body_kernel(driven,self.sympathetic_coefficients,self.sympathetic_state,self.active_sympathetic_weights)
        output=(1-.45*mix)*driven+1.8*mix*body+mix*sympathetic
        if self.model=='piano':
            for note,track in list(self.release_tracks.items()):
                coefficients,state,weights,age,t60=track
                tail=release_kernel(len(signal),coefficients,state,weights,age,
                    max(1,round(.01*self.rate)),round(1.5*t60*self.rate))
                output+=mix*tail
                track[3]+=len(signal)
                if track[3]>=round(1.5*t60*self.rate):
                    del self.release_tracks[note]
            from monitor.v18.piano_room import reflections_kernel
            output,self.early_position=reflections_kernel(output,self.early_buffer,self.early_position,self.early_taps,self.early_weights*mix)
        return output


class GuitarStrings:
    def __init__(self,rate,frequency,position=.22,velocity=1.):
        from monitor.v18.virtual_string import PluckedString
        self.frequency=frequency;self.rate=rate;self.velocity=velocity
        self.age=0;self.last=0.;self.noise_state=0.
        self.random=np.random.default_rng(int(frequency*100)+round(position*100))
        self.strings=(PluckedString(rate,frequency,position),PluckedString(rate,frequency*2**(.8/1200),position))
    def render(self,count,brightness=.65,decay=3.,bridge=.2):
        # Two polarization planes with slightly different termination tuning.
        from scipy.signal import lfilter
        # Faster radiating and slower orthogonal polarization; harder plucks
        # retain more high-frequency string motion.
        color=np.clip(brightness*(.7+.3*self.velocity),.05,.95)
        first=self.strings[0].render(count,color,decay*.8,bridge)
        second=self.strings[1].render(count,max(.05,color*.92),decay*1.5,bridge)
        result,self.last=guitar_radiation_kernel(first,second,self.last,self.rate,self.frequency)
        noise=self.random.standard_normal(count)
        noise,z=lfilter([.25],[1,-.75],noise,zi=[self.noise_state]);self.noise_state=float(z[0])
        age=(self.age+np.arange(count))/self.rate
        result+=.025*(.3+.7*self.velocity)*noise*np.exp(-age/.004)
        self.age+=count
        return result
