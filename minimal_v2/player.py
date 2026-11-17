"""FreeCAD GUI kinematic demonstration of the V2 contact layout.

Uses the saved model's real paddle, crank, rods and wheel centres. Animation
is explanatory slow motion; it does not claim to solve compliant tire contact.
"""
import json
import math
import time
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtWidgets

ROOT = Path('D:/basketball/minimal_v2')
CFG = json.loads((ROOT/'design.json').read_text(encoding='utf-8'))

class Player(QtWidgets.QDockWidget):
    def __init__(self):
        super().__init__('V2 单球发球演示', Gui.getMainWindow())
        self.setObjectName('MinimalV2Player')
        # FreeCAD changes the internal document name when an FCStd is reopened.
        required=('Pusher','FeedCrank','FeedLink','RotorHub0','RotorHub1','Tire0','Tire1','RotationMark0','RotationMark1','Collector','BallReference')
        def compatible(candidate):
            return candidate is not None and all(candidate.getObject(n) is not None for n in required)
        candidates=[App.ActiveDocument]+list(App.listDocuments().values())
        self.doc=next((candidate for candidate in candidates if compatible(candidate)),None)
        if self.doc is None:
            self.doc=App.openDocument('D:/basketball/七号球极简发球机_V2.FCStd')
        if not compatible(self.doc):
            raise RuntimeError('V2模型缺少运动部件，请打开七号球极简发球机_V2.FCStd')
        App.setActiveDocument(self.doc.Name)
        Gui.setActiveDocument(self.doc.Name)
        self.view=Gui.getDocument(self.doc.Name).activeView()
        self.T=App.Placement(App.Vector(*CFG['wheel_origin_mm']),App.Rotation(App.Vector(0,1,0),-CFG['launch_angle_deg']))
        self.R=CFG['ball_diameter_mm']/2
        self.stage=CFG['stage_s_mm']
        self.pitch=CFG['wheel_radius_mm']+CFG['wheel_gap_mm']/2
        self.saved={name:self.doc.getObject(name).Placement for name in
                    ('Pusher','FeedCrank','FeedLink','RotorHub0','RotorHub1','Tire0','Tire1','RotationMark0','RotationMark1')}
        self.ball=self.doc.getObject('AnimatedBall')
        if self.ball is None:
            self.ball=self.doc.addObject('Part::Feature','AnimatedBall')
            self.ball.Shape=Part.makeSphere(self.R)
            self.ball.Label='演示球 · 运动示意'
            self.ball.ViewObject.ShapeColor=(1.0,.36,.04)
        self.ball.ViewObject.Visibility=True
        self.doc.getObject('BallReference').Visibility=False
        widget=QtWidgets.QWidget()
        layout=QtWidgets.QVBoxLayout(widget)
        self.caption=QtWidgets.QLabel()
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        note=QtWidgets.QLabel('运动示意：夹持加速阶段放慢\n实际轮隙、抓球力和速度须实球测试')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.slider=QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0,1000)
        layout.addWidget(self.slider)
        row=QtWidgets.QHBoxLayout()
        self.play_button=QtWidgets.QPushButton('播放')
        self.pause_button=QtWidgets.QPushButton('暂停')
        self.reset_button=QtWidgets.QPushButton('复位')
        for button in (self.play_button,self.pause_button,self.reset_button): row.addWidget(button)
        layout.addLayout(row)
        self.loop=QtWidgets.QCheckBox('循环演示')
        self.loop.setChecked(True)
        layout.addWidget(self.loop)
        zoom=QtWidgets.QHBoxLayout()
        b1=QtWidgets.QPushButton('机构近景'); b2=QtWidgets.QPushButton('整机')
        zoom.addWidget(b1);zoom.addWidget(b2);layout.addLayout(zoom)
        layout.addStretch()
        self.setWidget(widget)
        self.timer=QtCore.QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)
        self.play_button.clicked.connect(lambda checked=False:self.play())
        self.pause_button.clicked.connect(lambda checked=False:self.pause())
        self.reset_button.clicked.connect(lambda checked=False:self.reset())
        self.slider.sliderPressed.connect(self.pause)
        self.slider.valueChanged.connect(self.scrub)
        b1.clicked.connect(lambda checked=False:self.zoom(False))
        b2.clicked.connect(lambda checked=False:self.zoom(True))
        self.t=0.0
        self.duration=8.5
        self.ticks=0
        self.started=0
        self.origin_t=0
        self.cycles=0
        self.contact_s=-math.sqrt((CFG['wheel_radius_mm']+self.R)**2-self.pitch**2)
        r=CFG['pusher_stroke_mm']/2; L=180.0
        slider0=self.stage-self.R-4
        pivot=slider0+r+L
        lo,hi=0.0,1.0
        for _ in range(50):
            f=(lo+hi)/2; a=math.pi*(1-f)
            ds=pivot+r*math.cos(a)-math.sqrt(L*L-r*r*math.sin(a)**2)-slider0
            if self.stage+ds<self.contact_s:lo=f
            else:hi=f
        self.grip_time=2.8+1.6*(lo+hi)/2
        self.leave_time=self.grip_time+.55
        self.flight_time=self.leave_time+.35
        self.saved_guard_transparency={}
        for i in (0,1):
            guard=self.doc.getObject('WheelGuard%d'%i)
            self.saved_guard_transparency[guard.Name]=guard.ViewObject.Transparency
            guard.ViewObject.Transparency=70
        self.reset()

    def W(self,s,y=0,h=0):
        return self.T.multVec(App.Vector(s,y,h))

    def zoom(self,whole):
        self.doc.getObject('Collector').Visibility=whole
        self.ball.Visibility=False
        self.view.viewAxonometric()
        self.view.fitAll()
        self.ball.Visibility=True
        self.view.fitAll()
        self.view.redraw()

    def apply(self):
        t=self.t
        # Incoming motion is vertical through the actual 280 mm mesh mouth.
        rest=self.W(self.stage)
        if t<1.8:
            u=t/1.8
            pos=rest+App.Vector(0,0,500*(1-u*u))
            stage='① 单球落入托位'
        elif t<2.8:
            pos=rest;stage='② 轮组升速；推球片待命'
        elif t<self.grip_time:
            stage='③ 推球片将球送到轮组夹口'
        elif t<self.leave_time:
            u=(t-self.grip_time)/(self.leave_time-self.grip_time)
            entry=self.contact_s; end=-self.contact_s
            pos=self.W(entry+(end-entry)*(.75*u+.25*u*u))
            stage='④ 两轮接触处同向前送，夹持加速'
        elif t<self.flight_time:
            u=(t-self.leave_time)/(self.flight_time-self.leave_time)
            start=math.sqrt((CFG['wheel_radius_mm']+self.R)**2-self.pitch**2)
            pos=self.W(start+(CFG['outlet_s_mm']-start)*u)
            stage='⑤ 球脱离轮组，越过短导轨末端'
        else:
            physical=(t-self.flight_time)*.11
            direction=self.T.Rotation.multVec(App.Vector(1,0,0))
            pos=self.W(CFG['outlet_s_mm'])+direction*(CFG['target_ball_speed_m_s']*1000*physical)+App.Vector(0,0,-4905*physical*physical)
            stage='⑥ 篮球射出；推球片返回'

        # Exact slider-crank geometry: r82.5 + L180, with slider at y=0.
        r=CFG['pusher_stroke_mm']/2; L=180.0
        slider0=self.stage-self.R-4
        pivot=slider0+r+L
        if t<2.8: fraction=0.0
        elif t<4.4: fraction=(t-2.8)/1.6
        elif t<5.4: fraction=1.0
        elif t<6.6: fraction=1-(t-5.4)/1.2
        else: fraction=0.0
        theta=math.pi*(1-fraction)
        end=App.Vector(pivot+r*math.cos(theta),r*math.sin(theta),-152)
        slider_s=pivot+r*math.cos(theta)-math.sqrt(L*L-r*r*math.sin(theta)**2)
        delta=slider_s-slider0
        move=App.Placement(self.T.Rotation.multVec(App.Vector(delta,0,0)),App.Rotation())
        self.doc.getObject('Pusher').Placement=move.multiply(self.saved['Pusher'])
        if 2.8<=t<self.grip_time: pos=self.W(self.stage+delta)
        crank=Part.makeCylinder(6,(end-App.Vector(pivot,0,-152)).Length,App.Vector(pivot,0,-152),end-App.Vector(pivot,0,-152))
        rodend=App.Vector(slider_s,0,-152)
        link=Part.makeCylinder(4,(rodend-end).Length,end,rodend-end)
        for name,shape in (('FeedCrank',crank),('FeedLink',link)):
            shape.Placement=self.T.multiply(shape.Placement)
            obj=self.doc.getObject(name);obj.Placement=App.Placement();obj.Shape=shape
        self.ball.Placement.Base=pos

        rotation=max(0,t-1.8)*430
        axis=self.T.Rotation.multVec(App.Vector(0,0,1))
        for i in (0,1):
            centre=self.W(0,(-1 if i==0 else 1)*self.pitch)
            sign=-1 if i==0 else 1
            turn=App.Placement(App.Vector(),App.Rotation(axis,sign*rotation),centre)
            for prefix in ('RotorHub','Tire','RotationMark'):
                name=prefix+str(i)
                self.doc.getObject(name).Placement=turn.multiply(self.saved[name])
        self.caption.setText(stage)
        self.slider.blockSignals(True)
        self.slider.setValue(int(t/self.duration*1000))
        self.slider.blockSignals(False)
        self.view.redraw()

    def play(self):
        if self.t>=self.duration:self.t=0
        self.origin_t=self.t; self.started=time.perf_counter()
        self.timer.start()

    def pause(self): self.timer.stop()

    def reset(self):
        self.timer.stop();self.t=0;self.apply()

    def scrub(self,value):
        self.timer.stop();self.t=value/1000*self.duration;self.apply()

    def tick(self):
        try:
            if App.getDocument(self.doc.Name) is None:
                self.timer.stop();return
            self.ticks+=1
            self.t=min(self.duration,self.origin_t+time.perf_counter()-self.started)
            self.apply()
            if self.t>=self.duration:
                self.cycles+=1
                if self.loop.isChecked():
                    self.origin_t=0;self.t=0;self.started=time.perf_counter()
                else:self.timer.stop()
        except Exception as exc:
            self.timer.stop();self.caption.setText('演示停止：'+str(exc))

    def closeEvent(self,event):
        self.timer.stop()
        try:
            self.reset()
            self.ball.Visibility=False
            self.doc.getObject('BallReference').Visibility=True
            for name,placement in self.saved.items():
                self.doc.getObject(name).Placement=placement
            for name,transparency in self.saved_guard_transparency.items():
                self.doc.getObject(name).ViewObject.Transparency=transparency
        except (ReferenceError,RuntimeError):
            pass
        event.accept()

def launch(autoplay=True):
    main=Gui.getMainWindow()
    # Drop all old instances, including those created before the current module
    # was registered, so one player owns the animation actors at a time.
    for previous in list(main.findChildren(QtWidgets.QDockWidget)):
        if previous.objectName()!='MinimalV2Player':continue
        for timer in previous.findChildren(QtCore.QTimer):timer.stop()
        if previous.isVisible():
            try:previous.close()
            except (ReferenceError,RuntimeError):previous.hide()
        main.removeDockWidget(previous)
        previous.setObjectName('RetiredMinimalV2Player')
        previous.hide()
    player=Player()
    Gui._minimal_v2_player=player
    main.addDockWidget(QtCore.Qt.RightDockWidgetArea,player)
    player.setFloating(True)
    player.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.WindowStaysOnTopHint)
    player.resize(370,260)
    player.setMinimumWidth(340)
    rect=main.frameGeometry()
    screen=QtWidgets.QApplication.primaryScreen().availableGeometry()
    px=min(max(screen.left()+20,rect.right()-400),screen.right()-390)
    py=min(max(screen.top()+30,rect.top()+180),screen.bottom()-300)
    player.move(px,py)
    player.show();player.raise_();player.zoom(False)
    main.statusBar().showMessage('V2单球发球动画：自动循环演示中；右上控制窗可暂停/复位',15000)
    if autoplay:player.play()
    return player
