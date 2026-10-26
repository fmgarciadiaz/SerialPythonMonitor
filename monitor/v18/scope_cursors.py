"""Two interactive scope cursors measured on the unreduced displayed frame."""
from dataclasses import dataclass,replace
import math
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore,QtWidgets,QtGui

def reading(value,unit):
    """Compact Spanish readout; acquisition coordinates remain unrounded."""
    if not math.isfinite(value):return '—'
    if unit in ('µs','s'):
        seconds=value/1e6 if unit=='µs' else value
        magnitude=abs(seconds)
        if magnitude>=1:value,unit=seconds,'s'
        elif magnitude>=.001:value,unit=seconds*1000,'ms'
        else:value,unit=seconds*1e6,'µs'
    elif unit=='V' and 0<abs(value)<1:value,unit=value*1000,'mV'
    elif unit=='Hz':
        if abs(value)>=1e6:value,unit=value/1e6,'MHz'
        elif abs(value)>=1000:value,unit=value/1000,'kHz'
    if unit.startswith('dB'):unit='dB'
    places=max(0,min(2,2-int(math.floor(math.log10(abs(value)))))) if value else 0
    text=f'{value:.{places}f}'
    if '.' in text:text=text.rstrip('0').rstrip('.')
    if text=='-0':text='0'
    return f'{text.replace(".",",")} {unit}'


@dataclass
class Cursor:
    enabled:bool=False
    x:float=0.
    y:float=float('nan')
    valid:bool=False

class ScopeCursors(QtWidgets.QWidget):
    def __init__(self,owner,combo_type=QtWidgets.QComboBox):
        super().__init__();self.owner=owner;self.plot=owner.plot_widget
        self.setObjectName('scopeCursorPanel')
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground,True)
        self.setStyleSheet('QWidget#scopeCursorPanel {background-color:#21252f;}')
        self.states=[Cursor(),Cursor()];self.active=None;self.previous=None
        self.frame=None;self.us_per_x=1.;self._updating=False;self.plots=[self.plot,self.plot]
        self.levels=[float("nan"),float("nan")];self._analysis_mode=0;self._analysis_key=(0,None);self._banks={}
        box=QtWidgets.QVBoxLayout(self);box.setContentsMargins(6,4,6,4);box.setSpacing(4)
        self.link=QtWidgets.QCheckBox('Vincular A/B')
        from pathlib import Path
        check=(Path(__file__).parent/'assets/check_neutral.svg').as_posix()
        self.link.setStyleSheet(f'QCheckBox {{background:transparent;border:none;spacing:6px;color:#d4dde8;}} QCheckBox::indicator {{width:14px;height:14px;border:1px solid #737d8d;border-radius:3px;background:#171920;}} QCheckBox::indicator:checked {{image:url("{check}");}} QCheckBox::indicator:unchecked {{image:none;}}')
        self.buttons=[];self.channels=[];self.modes=[];self.items=[];self.status_labels=[];self.measurements=[]
        colors=('#62bfae','#c1b76c')  # Muted teal/olive, distinct from CH1 cyan and CH2 yellow.
        for i,name in enumerate(('A','B')):
            card=QtWidgets.QFrame()
            card.setStyleSheet('QFrame {background:#21252f;border:1px solid #3a4150;border-radius:6px;} QLabel {border:none;background:transparent;}')
            row=QtWidgets.QHBoxLayout(card);row.setContentsMargins(6,4,6,4);row.setSpacing(8)
            button=QtWidgets.QToolButton();button.setCheckable(True);button.setFixedSize(12,12)
            button.setAccessibleName(f'Cursor {name} · encender/apagar')
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            led=QtGui.QColor(colors[i]).darker(135).name()
            highlight=QtGui.QColor(colors[i]).darker(110).name()
            button.setStyleSheet(f'QToolButton {{padding:0;border:1px solid #657080;border-radius:6px;background:qradialgradient(cx:.35,cy:.3,radius:.8,stop:0 #536071,stop:.55 #2b3440,stop:1 #151b23);}} QToolButton:checked {{border-color:{led};background:qradialgradient(cx:.35,cy:.3,radius:.8,stop:0 {highlight},stop:.3 {led},stop:.7 {led},stop:1 #303b48);}} QToolButton:hover {{border-color:#8b98aa;}}')
            label=QtWidgets.QLabel(name);label.setStyleSheet(f'color:{colors[i]};font-weight:600;')
            status=QtWidgets.QLabel('Apagado');status.setStyleSheet('color:#8f98a8;font-size:10px;')
            status.hide();self.status_labels.append(status)
            button.setToolTip(f'Activar {name}, mover el mouse sobre el gráfico y hacer clic para fijar')
            channel=combo_type();channel.addItems(['CH1','CH2','FILTER','RADIO']);channel.setCurrentText('CH1' if i==0 else 'CH2')
            channel.setProperty('centerInWholeBox',True)
            mode=combo_type();mode.addItems(['Seguir','Libre']);mode.setProperty('centerInWholeBox',True)
            mode.setToolTip(f'Cursor {name}: seguir la señal o colocar libremente con el mouse')
            for control in (channel,mode):
                control.setFixedHeight(owner.btn_xaxis_toggle.height())
                control.setMinimumWidth(0)
                control.setStyleSheet('background-color:#171920;border:1px solid #3a4150;border-radius:6px;font-size:11px;')
            self.modes.append(mode);mode.currentIndexChanged.connect(self.refresh)
            row.addWidget(button);row.addWidget(label);row.addWidget(channel,1);row.addWidget(mode,1)
            box.addWidget(card)
            self.buttons.append(button);self.channels.append(channel)
            color=colors[i];pen=pg.mkPen(color,width=1,style=QtCore.Qt.PenStyle.DashLine)
            vertical=pg.InfiniteLine(angle=90,pen=pen);horizontal=pg.InfiniteLine(angle=0,pen=pen)
            marker=pg.ScatterPlotItem(size=9,pen=pg.mkPen(color,width=2),brush=pg.mkBrush('#171c24'),symbol='+')
            text=pg.TextItem(text=name,color=color,anchor=(.5,0))
            for item in (vertical,horizontal,marker,text):
                item.setZValue(200);self.plot.addItem(item,ignoreBounds=True);item.hide()
            self.items.append((vertical,horizontal,marker,text))
            button.toggled.connect(lambda enabled,i=i:self.enable(i,enabled))
            channel.currentTextChanged.connect(lambda _,i=i:self.channel_changed(i))
        self.screen=QtWidgets.QFrame();self.screen.setObjectName('cursorReadout')
        self.screen.setStyleSheet('QFrame#cursorReadout {background:#171c24;border:1px solid #3a4150;border-radius:6px;} QLabel {background:transparent;border:none;padding:0;}')
        screen_grid=QtWidgets.QGridLayout(self.screen);screen_grid.setContentsMargins(10,8,10,8)
        screen_grid.setHorizontalSpacing(8);screen_grid.setVerticalSpacing(6)
        for row,(name,color) in enumerate((('A',colors[0]),('B',colors[1]),('B − A','#aeb8c8'))):
            tag=QtWidgets.QLabel(name);tag.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter);tag.setStyleSheet(f'color:{color};font-size:11px;font-weight:700;')
            screen_grid.addWidget(tag,row*2,0)
            fields=[]
            for col,title in enumerate(('t','V','Nivel') if row<2 else ('Δt','ΔV','1/|Δt|')):
                cell=QtWidgets.QWidget();cell.setStyleSheet("background:transparent;border:none;")
                layout=QtWidgets.QVBoxLayout(cell)
                layout.setContentsMargins(0,0,0,0);layout.setSpacing(2)
                heading=QtWidgets.QLabel(title);heading.setStyleSheet('color:#768396;font-size:9px;')
                value=QtWidgets.QLabel('—');value.setMinimumWidth(0)
                value.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Preferred)
                value.setStyleSheet(f'color:{color};font-size:11px;font-weight:600;')
                heading.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                value.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(heading);layout.addWidget(value)
                screen_grid.addWidget(cell,row*2,col+1)
                fields.append((cell,heading,value))
            if row<2:
                self.measurements.append(fields)
                separator=QtWidgets.QFrame();separator.setFixedHeight(1)
                separator.setStyleSheet('background:#303846;border:none;')
                screen_grid.addWidget(separator,row*2+1,0,1,4)
            else:self.differences=fields
        for col in (1,2,3):screen_grid.setColumnStretch(col,1)
        self.delta=QtWidgets.QLabel(self);self.delta.hide()

        bottom=QtWidgets.QHBoxLayout();bottom.setSpacing(0)
        center=QtWidgets.QPushButton('Centrar')
        for control in (self.link,center):
            column=QtWidgets.QHBoxLayout();column.addStretch();column.addWidget(control);column.addStretch()
            bottom.addLayout(column,1)
        center.clicked.connect(self.center)
        box.addWidget(self.screen)
        box.addStretch(1)
        box.addLayout(bottom)
        box.addStretch(1)
        self.plot.viewport().setMouseTracking(True);self.plot.viewport().installEventFilter(self)
        self.escape=QtGui.QShortcut(QtGui.QKeySequence('Escape'),self.plot)
        self.escape.activated.connect(self.cancel_move)
        self.plot.getViewBox().sigRangeChanged.connect(self.refresh)
        owner.display_stack.currentChanged.connect(self.analysis_changed)
        owner.spectral.widget.viewport().setMouseTracking(True)
        owner.spectral.widget.viewport().installEventFilter(self)
        self.spectral_escape=QtGui.QShortcut(QtGui.QKeySequence("Escape"),owner.spectral.widget)
        self.spectral_escape.activated.connect(self.cancel_move)
        for plot in owner.spectral.plots:plot.getViewBox().sigRangeChanged.connect(self.refresh)
        self.refresh()

    def invalidate(self):
        self.frame=None
        for state in self.states:state.valid=False;state.y=float("nan")
        self.refresh()

    def temporal(self):return self.owner.spectral.mode==0

    def analysis_changed(self,*_):
        if not hasattr(self,'delta'):return
        mode=self.owner.spectral.mode
        kind=self.owner.spectral._fft_kind() if mode==1 else None
        if mode==1 and any(self.owner.spectral.radio_crop_active(j) for j in range(2)):kind='Radio recortada'
        key=(mode,kind)
        changed=key!=self._analysis_key
        saved=None
        if changed:
            self._banks[self._analysis_key]=dict(states=[replace(state) for state in self.states],
                channels=[control.currentText() for control in self.channels],
                modes=[control.currentIndex() for control in self.modes],
                linked=self.link.isChecked(),us_per_x=self.us_per_x)
            saved=self._banks.get(key)
            self._analysis_key=key;self._analysis_mode=mode;self.active=None;self.previous=None
            self.states=([replace(state) for state in saved['states']] if saved else
                         [Cursor(),Cursor()])
            if saved:self.us_per_x=saved['us_per_x']
        transfer=mode==1 and self.owner.spectral._fft_kind()=='Transfer'
        names=['Ganancia','Fase'] if mode==3 else (['Ganancia',self.owner.spectral.transfer_view.currentText()] if transfer else ['CH1','CH2','FILTER','RADIO'])
        for i,combo in enumerate(self.channels):
            if [combo.itemText(j) for j in range(combo.count())]!=names:
                old=combo.currentText()
                with QtCore.QSignalBlocker(combo):
                    combo.clear();combo.addItems(names);combo.setCurrentText(old if old in names else names[min(i,len(names)-1)])
        if changed:
            for i,state in enumerate(self.states):
                with QtCore.QSignalBlocker(self.buttons[i]):self.buttons[i].setChecked(state.enabled)
                if saved:
                    with QtCore.QSignalBlocker(self.channels[i]):self.channels[i].setCurrentText(saved['channels'][i])
                    with QtCore.QSignalBlocker(self.modes[i]):self.modes[i].setCurrentIndex(saved['modes'][i])
            if saved:
                with QtCore.QSignalBlocker(self.link):self.link.setChecked(saved['linked'])
        self.refresh()

    def target(self,i):
        mode=self.owner.spectral.mode
        if mode==0:return self.plot
        source=self.channels[i].currentText();spectral=self.owner.spectral
        if mode==3 or (mode==1 and spectral._fft_kind()=='Transfer'):
            index=self.channels[i].currentIndex()
            return spectral.plots[index] if 0<=index<2 else None
        for j,control in enumerate(spectral.channels):
            if control.currentText()==source and j in spectral.attached:return spectral.plots[j]
        return None

    def attach(self,i,plot):
        if plot is None or plot is self.plots[i]:return
        for item in self.items[i]:self.plots[i].removeItem(item);plot.addItem(item,ignoreBounds=True)
        self.plots[i]=plot

    def units(self,i):
        mode=self.owner.spectral.mode
        if mode==0:return 'µs','V'
        if mode==2:return 's','Hz'
        plot=self.target(i) or self.plots[i]
        return 'Hz',plot.getAxis('left').labelUnits or plot.getAxis('left').labelText or 'valor'

    @staticmethod
    def linear(value):
        return 10.**value if math.isfinite(value) and -300<=value<=300 else float("nan")

    def read(self,i):
        state=self.states[i];mode=self.owner.spectral.mode;plot=self.plots[i]
        x=state.x*self.us_per_x if mode==0 else (self.linear(state.x) if mode in (1,3) and plot.getAxis('bottom').logMode else state.x)
        if mode==1 and plot in self.owner.spectral.plots:
            index=self.owner.spectral.plots.index(plot)
            if self.owner.spectral.radio_crop_active(index):
                from monitor.v18.radio_fft_crop import frequency_at
                x=frequency_at(self.owner.spectral.radio_crop_columns(),state.x)
                if x is None:x=float('nan')
        y=self.linear(state.y) if mode==2 and plot.getAxis('left').logMode and math.isfinite(state.y) else state.y
        return x,y

    def update_frame(self,x,ys,channels):
        if not any(s.enabled for s in self.states) or not self.temporal():return
        self.frame=(x,ys,tuple(channels))
        audio=bool(channels) and all(self.owner._is_audio_channel(c) for c in channels)
        rate=(getattr(getattr(self.owner,'radio_stream',None),'rate',0) if audio else
              getattr(self.owner,'current_fs_hz',0))
        factor=1. if self.owner.x_axis_time_mode else (1e6/rate if rate>0 else 0.)
        if factor>0 and self.us_per_x>0 and factor!=self.us_per_x:
            for state in self.states:state.x*=self.us_per_x/factor
        self.us_per_x=factor
        for state in self.states:state.valid=False
        self.refresh()

    def enable(self,i,enabled):
        self.states[i].enabled=enabled
        if enabled:self.arm(i)
        elif self.active==i:self.active=None
        self.refresh()

    def arm(self,i):
        if not self.states[i].enabled:
            self.buttons[i].setChecked(True);return
        self.active=i;self.previous=[(s.x,s.y) for s in self.states]
        frame=getattr(self.owner,'_last_display_frame',None)
        if frame is not None:self.update_frame(*frame)
        target=self.target(i)
        if target is None and self.owner.spectral.mode in (1,2):
            source=self.channels[i].currentText()
            control=self.owner.spectral.channels[i]
            index=control.findText(source)
            if index>=0 and control.model().item(index).isEnabled():
                control.setCurrentIndex(index);self.owner.spectral.configure_plots();target=self.target(i)
        if target is not None:self.attach(i,target)
        low,high=self.plots[i].getViewBox().viewRange()[0]
        if not low<=self.states[i].x<=high:self.states[i].x=(low+high)/2
        self.refresh()

    def channel_changed(self,i):
        self.states[i].valid=False
        if self.states[i].enabled:self.arm(i)
        self.refresh()

    def sample(self,i,x):
        if not self.temporal():return self.spectral_sample(i,x,self.states[i].y)
        if self.frame is None:return x,float('nan')
        xs,ys,channels=self.frame;channel=self.channels[i].currentText()
        if channel not in channels:return x,float('nan')
        values=ys.get(channel,[]);positions=xs.get(channel,[]) if isinstance(xs,dict) else xs
        if not len(positions) or len(values)!=len(positions) or x<positions[0] or x>positions[-1]:return x,float('nan')
        j=int(np.searchsorted(positions,x));j=min(j,len(positions)-1)
        if j and abs(positions[j-1]-x)<abs(positions[j]-x):j-=1
        value=float(values[j])
        # Match the displayed RADIO volume, using one sample rather than copying a frame.
        value=float(self.owner._radio_display_values(channel,np.array([value]))[0])
        return float(positions[j]),value

    def spectral_sample(self,i,x,y):
        spectral=self.owner.spectral;plot=self.target(i)
        if plot is None:return x,float('nan')
        index=spectral.plots.index(plot);mode=spectral.mode
        if mode==2:
            self.levels[i]=float("nan")
            image=spectral.images[index];raster=image.image
            if raster is None or not math.isfinite(x) or not math.isfinite(y):return x,y
            rect=image.mapRectToParent(image.boundingRect())
            if not rect.contains(QtCore.QPointF(x,y)):return x,y
            col=min(raster.shape[1]-1,int((x-rect.left())/rect.width()*raster.shape[1]))
            row=min(raster.shape[0]-1,int((y-rect.top())/rect.height()*raster.shape[0]))
            self.levels[i]=float(raster[row,col])
            return x,y
        if mode==1:
            cached=getattr(spectral,'_fft_trace_cache',{}).get(index)
            if cached is None:return x,float('nan')
            positions,values=cached[1:3]
        else:
            bode=spectral.bode
            if not bode.result:return x,float('nan')
            data=bode.display_data(np.asarray(bode.result),len(bode.history_profiles),bode.result_profile)
            positions,values=data[:,0],data[:,index+1]
        physical=self.linear(x) if plot.getAxis('bottom').logMode else x
        if not math.isfinite(physical):return x,float('nan')
        if len(positions)==0 or physical<positions[0] or physical>positions[-1]:return x,float('nan')
        j=min(int(np.searchsorted(positions,physical)),len(positions)-1)
        if j and abs(positions[j-1]-physical)<abs(positions[j]-physical):j-=1
        actual=float(positions[j]);value=float(values[j])
        return (math.log10(actual) if plot.getAxis('bottom').logMode and actual>0 else actual),value

    def place(self,i,x,y):
        state=self.states[i];old=state.x
        if self.modes[i].currentIndex()==0:
            x,y=self.sample(i,x) if self.temporal() else self.spectral_sample(i,x,y)
        state.x=x;state.y=y;state.valid=math.isfinite(y)
        if self.link.isChecked():
            other=self.states[1-i]
            if other.enabled:
                other.x+=x-old
                if self.modes[1-i].currentIndex()==0:other.x,other.y=self.sample(1-i,other.x)
                other.valid=math.isfinite(other.y)
        self.refresh()

    def center(self):
        for i,s in enumerate(self.states):
            if s.enabled:
                target=self.target(i)
                if target is not None:self.attach(i,target)
                low,high=self.plots[i].getViewBox().viewRange()[0]
                s.x=low+(high-low)*(i+1)/3;s.y=sum(self.plots[i].getViewBox().viewRange()[1])/2
        self.refresh()
    def clear(self):
        for button in self.buttons:button.setChecked(False)
        self.active=None;self.frame=None;self.refresh()

    def refresh(self,*_):
        if not hasattr(self,'delta') or self._updating:return
        self._updating=True
        try:
            for i,s in enumerate(self.states):
                self.status_labels[i].setText('Apagado' if not s.enabled else 'Colocando' if self.active==i else 'Fijado')
                target=self.target(i)
                if target is not None:self.attach(i,target)
                shown=s.enabled and target is not None
                if shown and (self.modes[i].currentIndex()==0 or self.owner.spectral.mode==2):s.x,s.y=self.sample(i,s.x)
                s.valid=shown and math.isfinite(s.y) and self.us_per_x>0
                if self.owner.spectral.mode==2:s.valid=s.valid and math.isfinite(self.levels[i])
                x,y=self.read(i);xu,yu=self.units(i)
                s.valid=s.valid and math.isfinite(x) and math.isfinite(y)
                vertical,horizontal,marker,text=self.items[i]
                for item in self.items[i]:item.setVisible(shown)
                self._update_measurement_tiles(i,x,y,xu,yu,s.valid)
                if not shown:continue
                vertical.setValue(s.x);horizontal.setVisible(s.valid)
                marker.setVisible(s.valid)
                if s.valid:horizontal.setValue(s.y);marker.setData([s.x],[s.y])
                text.setText('AB'[i])
            a,b=self.states
            if a.enabled and b.enabled and a.valid and b.valid:
                ax,ay=self.read(0);bx,by=self.read(1);dx=bx-ax;dy=by-ay
                xu,yu=self.units(0);other_unit=self.units(1)[1]
                label='Δt' if xu in ('µs','s') else 'Δf'
                second=f'Δ{ "V" if yu=="V" else "f" if yu=="Hz" else "Y"} {dy:.6g} {yu}' if yu==other_unit else 'ΔY: unidades distintas'
                reciprocal=(f' · 1/|Δt| {(1e6 if xu=="µs" else 1)/abs(dx):.6g} Hz' if xu in ('µs','s') and abs(dx)>1e-12 else '')
                level_delta=(f' · ΔNivel {self.levels[1]-self.levels[0]:.5g} {self.owner.spectral.scale.currentText()}' if self.owner.spectral.mode==2 else '')
                self.delta.setText(f'B − A · {label} {dx:.6g} {xu} · {second}{reciprocal}{level_delta}')
            else:self.delta.setText('B − A · Δt — · ΔY —')
            valid=a.enabled and b.enabled and a.valid and b.valid
            if valid:
                self._tile(self.differences[0],label,reading(dx,xu))
                self._tile(self.differences[1],'ΔV' if yu=='V' else 'Δf' if yu=='Hz' else 'ΔY',reading(dy,yu) if yu==other_unit else '—')
                if self.owner.spectral.mode==2:
                    self._tile(self.differences[2],'ΔNivel',reading(self.levels[1]-self.levels[0],self.owner.spectral.scale.currentText()))
                else:
                    self._tile(self.differences[2],'1/|Δt|',reading((1e6 if xu=="µs" else 1)/abs(dx),'Hz') if xu in ('µs','s') and abs(dx)>1e-12 else '—')
            else:
                for tile,title,value in self.differences:value.setText('—')
            self._position_tags()
        finally:self._updating=False

    @staticmethod
    def _tile(field,title,value):
        field[1].setText(title);field[2].setText(value);field[2].setToolTip(value)

    def _update_measurement_tiles(self,i,x,y,xu,yu,valid):
        fields=self.measurements[i]
        self._tile(fields[0],'t' if xu in ('µs','s') else 'f',reading(x,xu) if valid else '—')
        self._tile(fields[1],'V' if yu=='V' else 'f' if yu=='Hz' else yu,reading(y,yu) if valid else '—')
        fields[2][0].setVisible(self.owner.spectral.mode==2)
        self._tile(fields[2],'Nivel',reading(self.levels[i],self.owner.spectral.scale.currentText()) if valid else '—')

    def _position_tags(self):
        for i,state in enumerate(self.states):
            target=self.target(i)
            if not state.enabled or target is None:continue
            view=target.getViewBox();yr=view.viewRange()[1]
            self.items[i][3].setPos(state.x,yr[1]-(yr[1]-yr[0])*8/max(1,view.height()))

    def cancel_move(self):
        if self.active is None:return
        if self.previous:
            for state,(x,y) in zip(self.states,self.previous):state.x=x;state.y=y
        self.active=None;self.refresh()

    def detach(self):
        self.plot.viewport().removeEventFilter(self)
        self.owner.spectral.widget.viewport().removeEventFilter(self)
        self.escape.setEnabled(False);self.spectral_escape.setEnabled(False)

    def eventFilter(self,watched,event):
        kind=event.type()
        if kind==QtCore.QEvent.Type.KeyPress and event.key()==QtCore.Qt.Key.Key_Escape and self.active is not None:
            self.cancel_move();return True
        if kind not in (QtCore.QEvent.Type.MouseMove,QtCore.QEvent.Type.MouseButtonPress):return False
        widget=self.plot if self.temporal() else self.owner.spectral.widget
        if watched is not widget.viewport():return False
        scene=widget.mapToScene(event.position().toPoint())
        if self.active is None and kind==QtCore.QEvent.Type.MouseButtonPress and event.button()==QtCore.Qt.MouseButton.LeftButton:
            for i,state in enumerate(self.states):
                text=self.items[i][3]
                if state.enabled and text.isVisible() and text.sceneBoundingRect().contains(scene):
                    self.arm(i);return True
        chosen=None
        indices=[self.active] if self.active is not None else range(2)
        for i in indices:
            target=self.target(i)
            if target is not None and target.getViewBox().sceneBoundingRect().contains(scene):chosen=target;break
        if chosen is None:return False
        view=chosen.getViewBox();point=view.mapSceneToView(scene)
        click=kind==QtCore.QEvent.Type.MouseButtonPress and event.button()==QtCore.Qt.MouseButton.LeftButton
        if self.active is not None:
            self.place(self.active,point.x(),point.y())
            if click:
                self.active=None;self.refresh()
            return True
        if click:
            candidates=[]
            for i,s in enumerate(self.states):
                if not s.enabled or self.target(i) is not chosen:continue
                px=view.mapViewToScene(QtCore.QPointF(s.x,point.y())).x()
                distance=abs(px-scene.x())
                if self.items[i][3].sceneBoundingRect().contains(scene):distance=0
                if distance<=8:candidates.append((distance,i))
            if candidates:self.arm(min(candidates)[1]);return True
        return False
