"""Refit captured fundamental; ADC observations are not calibrated DAC THD."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
folder=Path(sys.argv[1]);r=json.loads((folder/'report.json').read_text())
rows=[]
for c in r['cases']:
 raw=np.load(folder/c['raw']);raw=raw[:16384]
 rate=160000000/253
 t=np.arange(len(raw))/rate;y=raw[:,2]*3.3/255
 # Shorter bounded window avoids fitting timer drift over a long capture.
 center=c['measured_hz'];width=rate/len(raw)*2
 def fit(f):
  m=np.column_stack((np.sin(2*np.pi*f*t),np.cos(2*np.pi*f*t),np.ones(len(t))))
  coef=np.linalg.lstsq(m,y,rcond=None)[0];res=y-m@coef
  return np.mean(res**2),coef
 optimum=minimize_scalar(lambda f:fit(f)[0],bounds=(center-width,center+width),method='bounded',options={'xatol':.001})
 residual,coef=fit(optimum.x)
 rows.append(dict(wave=c['wave'],requested_hz=c['requested_hz'],measured_hz=float(optimum.x),frequency_error_percent=100*(optimum.x/c['requested_hz']-1),fundamental_vpp=float(2*np.hypot(*coef[:2])),mean_v=float(coef[2]),residual_rms_v=float(np.sqrt(residual)),observed_sample_vpp=float(np.ptp(y)),samples=len(y)))
(folder/'analog_summary.json').write_text(json.dumps({'scope':'ADC8 CH2; fundamental fit, not calibrated THD or edge speed','cases':rows},indent=2)+'\n')
for c in rows:print(c)
