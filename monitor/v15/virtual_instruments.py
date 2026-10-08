"""Reduced physical instruments: modal stiff piano and shared bridge/body."""
import numpy as np
from scipy.signal import iirpeak
from monitor.v15.fm_feedback import njit
from monitor.v15.piano_profile import piano_profile

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

def _hammer(rate, velocity, hardness, mass, impedance, stiffness, exponent):
    # Felt spring hitting a passive characteristic string impedance.
    stiffness*=2**(4*(hardness-.78))
    speed=.45+3.5*velocity
    compression=0.0
    force=np.zeros(int(rate*.012))
    for i in range(len(force)):
        contact=stiffness*max(0.0,compression)**exponent
        speed-=contact/(mass*rate)
        compression+=(speed-contact/impedance)/rate
        force[i]=contact
        if compression<=0 and speed<0:break
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

modal_kernel=njit(cache=True,nogil=True)(_modes) if njit else None
_hammer_kernel=njit(cache=True,nogil=True)(_hammer) if njit else None
def hammer_kernel(rate, velocity, hardness, frequency):
    profile=piano_profile(frequency)
    if _hammer_kernel is None:raise RuntimeError('Virtual requiere Numba')
    return _hammer_kernel(rate,velocity,hardness,profile['mass'],profile['impedance'],profile['contact_k'],profile['exponent'])
body_kernel=njit(cache=True,nogil=True)(_resonate) if njit else None

def warmup():
    if modal_kernel is not None:
        modal_kernel(np.zeros((4,2)),np.zeros((4,2)),np.ones(4),np.zeros(8),0,8,1,.0)
        hammer_kernel(80000,.8,.75,220.)
        body_kernel(np.zeros(8),np.zeros((4,5)),np.zeros((4,2)),np.ones(4))

class PianoStrings:
    def __init__(self,rate,frequency,position=.12,velocity=1.,bandlimit=None):
        self.rate=rate;self.frequency=frequency;self.position=position
        self.velocity=velocity;self.bandlimit=bandlimit or rate*.42
        self.key=None;self.state=None;self.age=0
        self.force=None
        self.profile=piano_profile(frequency)
    def render(self,count,brightness=.75,decay=4.,stiffness=.0003,bridge=.2):
        if modal_kernel is None:raise RuntimeError('Virtual requiere Numba')
        key=(brightness,decay,stiffness,bridge)
        if key!=self.key:
            # Normal modes of a pinned stiff string, fundamental normalized.
            n=np.arange(1,min(64,max(1,int(self.bandlimit/self.frequency)))+1,dtype=float)
            effective_stiffness=self.profile['stiffness']*stiffness/.0003
            base=self.frequency*n*np.sqrt((1+effective_stiffness*n*n)/(1+effective_stiffness))
            # Fixed mode count permits phase-continuous live stiffness changes.
            offsets=((0.,),(-1.5,1.5),(-2.,0.,2.))[self.profile['strings']-1]
            self.strings=len(offsets)
            frequencies=np.concatenate([base*2**(c/1200) for c in offsets])
            order=np.tile(n,len(offsets))
            # Bridge force scales with modal slope; felt pulse supplies the
            # actual time-varying excitation instead of a prefilled sine bank.
            position=np.clip(self.profile['position']*self.position/.12,.01,.95)
            amplitudes=np.sin(np.pi*order*position)/order**.55
            amplitudes*=np.clip((self.bandlimit-frequencies)/(self.bandlimit*.1),0,1)
            amplitudes*=1.4/max(np.sum(abs(amplitudes)),1e-12)
            register=np.clip((220/self.frequency)**.22,.45,1.8)
            lifetime=decay*register/(1+.035*(order-1)**1.25+bridge*.65)
            # Fast energy radiates via bridge; weak orthogonal polarization
            # retains a slower tail, giving the characteristic double decay.
            frequencies=np.concatenate((frequencies,frequencies*2**(.45/1200)))
            lifetime=np.concatenate((lifetime*.7,lifetime*1.8))
            amplitudes=np.concatenate((amplitudes*.78,amplitudes*.22))
            radius=10**(-3/(lifetime*self.rate))
            angle=2*np.pi*frequencies/self.rate
            self.rotation=np.column_stack((radius*np.cos(angle),radius*np.sin(angle)))
            if self.state is None:
                self.state=np.zeros((len(amplitudes),2))
                hammer_rate=max(80000,self.rate)
                self.force=hammer_kernel(hammer_rate,float(self.velocity),float(brightness),float(self.frequency))
                if hammer_rate!=self.rate:
                    ratio=hammer_rate//self.rate
                    self.force=self.force[:len(self.force)//ratio*ratio].reshape(-1,ratio).sum(axis=1)
            self.amplitudes=amplitudes
            self.frequencies=frequencies;self.key=key
        output=modal_kernel(self.state,self.rotation,self.amplitudes,self.force,self.age,count,self.strings,float(1-np.exp(-(0.2+4*bridge)/self.rate)))
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
            b,a=iirpeak(frequency,q,fs=rate)
            coeff.append((*b,a[1],a[2]));weights.append(weight)
        self.coefficients=np.array(coeff);self.weights=np.array(weights);self.weights/=self.weights.sum()
        self.state=np.zeros((len(weights),2));self.bridge_previous=0.
        self.rate=rate
        self.bridge_alpha=1-np.exp(-2*np.pi*(4500 if model=='guitar' else 6500)/rate)
        notes=range(36,85) if model=='piano' else (40,45,50,55,59,64)
        self.sympathetic_frequencies=np.array([440*2**((n-69)/12) for n in notes])
        self.sympathetic_frequencies=self.sympathetic_frequencies[self.sympathetic_frequencies<rate*.42]
        self.sympathetic_state=np.zeros((len(self.sympathetic_frequencies),2))
        self.sympathetic_weights=np.ones(len(self.sympathetic_frequencies))/len(self.sympathetic_frequencies)
        self.pedal=None;self.sympathetic_coefficients=None
        self.radiation_previous=0.
        self.radiation_pole=np.exp(-2*np.pi*(65 if model=='guitar' else 28)/rate)
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
        if self.pedal!=pedal:
            coefficients=[]
            for frequency in self.sympathetic_frequencies:
                b,a=iirpeak(frequency,180 if pedal else 14 if self.model=='piano' else 70,fs=self.rate)
                coefficients.append((*b,a[1],a[2]))
            self.sympathetic_coefficients=np.array(coefficients);self.pedal=pedal
        sympathetic=body_kernel(driven,self.sympathetic_coefficients,self.sympathetic_state,self.sympathetic_weights)
        return (1-.45*mix)*driven+1.8*mix*body+mix*(.3 if pedal else .08)*sympathetic


class GuitarStrings:
    def __init__(self,rate,frequency,position=.22,velocity=1.):
        from monitor.v15.virtual_string import PluckedString
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
        raw=.72*self.strings[0].render(count,color,decay*.8,bridge)+.28*self.strings[1].render(count,max(.05,color*.92),decay*1.5,bridge)
        delta=np.diff(np.concatenate(([self.last],raw)));self.last=float(raw[-1]) if len(raw) else self.last
        # Mix displacement and bridge-velocity proxy, with bounded gain.
        result=.65*raw+.22*np.tanh(delta*self.rate/(2*np.pi*self.frequency))
        noise=self.random.standard_normal(count)
        noise,z=lfilter([.25],[1,-.75],noise,zi=[self.noise_state]);self.noise_state=float(z[0])
        age=(self.age+np.arange(count))/self.rate
        result+=.025*(.3+.7*self.velocity)*noise*np.exp(-age/.004)
        self.age+=count
        return result
