import json
import math
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part

ROOT = Path('D:/basketball/minimal_v2')
cfg = json.loads((ROOT / 'design.json').read_text(encoding='utf-8'))
doc = App.listDocuments().get(cfg['document_name'])
if doc is None:
    doc = App.newDocument(cfg['document_name'])
else:
    for obj in list(doc.Objects):
        doc.removeObject(obj.Name)
doc.Label = '七号球极简发球机 V2 · 双轮夹持'
App.setActiveDocument(doc.Name)
Gui.setActiveDocument(doc.Name)

# Stop every older demo so its callbacks cannot change this scene.
from PySide import QtWidgets
for window in list(QtWidgets.QApplication.topLevelWidgets()):
    if isinstance(window, QtWidgets.QDialog) and any(s in window.windowTitle() for s in ('供球', '发球机完整', '极简单球')):
        for timer in window.findChildren(__import__('PySide').QtCore.QTimer):
            timer.stop()
        window.close()

angle = math.radians(cfg['launch_angle_deg'])
rot = App.Rotation(App.Vector(0, 1, 0), -cfg['launch_angle_deg'])
origin = App.Vector(*cfg['wheel_origin_mm'])
transform = App.Placement(origin, rot)
R = cfg['ball_diameter_mm'] / 2
rw = cfg['wheel_radius_mm']
half_pitch = rw + cfg['wheel_gap_mm'] / 2
groups = {}
for name, label in [('Frame', '01 底架与搬运'), ('Drive', '02 对转发球轮与支承'),
                    ('Feeder', '03 单球托位与推球'), ('Guards', '04 轮罩与电控'),
                    ('Collector', '05 可拆集球网架'), ('Reference', '06 参考与球路')]:
    group = doc.addObject('App::DocumentObjectGroup', name)
    group.Label = label
    groups[name] = group

rigid = []
def world(local):
    return transform.multVec(App.Vector(*local))

def show(name, label, shape, color, group, local=True, transparency=0, collision=False):
    obj = doc.addObject('Part::Feature', name)
    obj.Label = label
    if local:
        shape = shape.copy()
        shape.Placement = transform.multiply(shape.Placement)
    obj.Shape = shape
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.LineColor = (0.13, 0.15, 0.17)
    obj.ViewObject.Transparency = transparency
    groups[group].addObject(obj)
    if collision:
        rigid.append(obj)
    return obj

def box(x, y, z, pos):
    return Part.makeBox(x, y, z, App.Vector(*pos))

def tube(a, b, outer, inner=0):
    pa, pb = App.Vector(*a), App.Vector(*b)
    v = pb - pa
    shape = Part.makeCylinder(outer, v.Length, pa, v)
    if inner:
        shape = shape.cut(Part.makeCylinder(inner, v.Length, pa, v))
    return shape

def square_tube(a, b, size=20, wall=1.2):
    pa, pb = App.Vector(*a), App.Vector(*b)
    length = (pb-pa).Length
    s = Part.makeBox(size, size, length, App.Vector(-size/2, -size/2, 0))
    hole = Part.makeBox(size-2*wall, size-2*wall, length+2, App.Vector(-size/2+wall, -size/2+wall, -1))
    s = s.cut(hole)
    s.Placement = App.Placement(pa, App.Rotation(App.Vector(0, 0, 1), pb-pa))
    return s

steel, dark, rubber, orange = (.53,.57,.60), (.19,.23,.27), (.07,.08,.09), (1.0,.36,.04)
green, blue = (.15,.42,.31), (.17,.40,.63)

params = doc.addObject('App::FeaturePython', 'DesignParameters')
params.Label = '设计参数 · mm / rpm / kg'
for prop, val in [('BallDiameter',cfg['ball_diameter_mm']),('WheelRadius',rw),
                  ('WheelGap',cfg['wheel_gap_mm']),('PusherStroke',cfg['pusher_stroke_mm']),
                  ('RailClearWidth',cfg['rail_inner_width_mm'])]:
    params.addProperty('App::PropertyLength', prop, 'Design'); setattr(params,prop,val)
params.addProperty('App::PropertyAngle', 'LaunchAngle', 'Design'); params.LaunchAngle = cfg['launch_angle_deg']
params.addProperty('App::PropertyInteger', 'BallCapacity', 'Design'); params.BallCapacity = 1
params.addProperty('App::PropertyInteger', 'WheelRPM', 'Design'); params.WheelRPM = cfg['wheel_rpm']
params.addProperty('App::PropertyString', 'Status', 'Design'); params.Status = '布置及净空检查；轮胎抓球能力、射程、温升待实物验证'

# Welded light steel frame; no solid 45 mm base block and no decorative body.
for i, (a,b) in enumerate([
    ((-310,-270,75),(255,-270,75)),((-310,270,75),(255,270,75)),
    ((-310,-270,75),(-310,270,75)),((255,-270,75),(255,270,75)),
    ((-310,-270,75),tuple(world((-320,-240,-182)))),((-310,270,75),tuple(world((-320,240,-182)))),
    ((255,-270,75),tuple(world((100,-240,-182)))),((255,270,75),tuple(world((100,240,-182))))]):
    show('FrameTube%02d'%i,'20×20×1.2 钢方管',square_tube(a,b),dark,'Frame',False,collision=True)
for i,y in enumerate((-240,240)):
    show('HeadSideBeam%d'%i,'发球头纵梁',square_tube((-350,y,-182),(100,y,-182)),dark,'Frame',collision=True)
for i,s in enumerate((0,60)):
    show('HeadCrossBeam%d'%i,'轴承座横梁 · 与支架相接',square_tube((s,-240,-182),(s,240,-182)),dark,'Frame',collision=True)
for i,s in enumerate((-350,-140)):
    show('SlideSupportBeam%d'%i,'推球滑杆端支承',square_tube((s,-240,-182),(s,240,-182),16,1),dark,'Frame',collision=True)

for i,y in enumerate((-267,267)):
    wheel = Part.makeCylinder(37.5,25,App.Vector(-290,y-12.5,37.5),App.Vector(0,1,0))
    show('TransportWheel%d'%i,'搬运轮 Ø75 · 工作时前脚着地',wheel,rubber,'Frame',False,collision=True)
for i,y in enumerate((-250,250)):
    foot=box(55,55,12,(195,y-27.5,0)).fuse(Part.makeCylinder(10,70,App.Vector(222.5,y,12)))
    show('Foot%d'%i,'前固定脚 · 承受发球反力',foot,rubber,'Frame',False,collision=True)

# Two bottom cheek brackets in local coordinates support bearing units.
for i,y in enumerate((-half_pitch,half_pitch)):
    bracket = box(160,90,3,(-80,y-45,-172))
    # The complete motor/bearing/guard cassette shifts laterally on the head
    # beams; the guard stays concentric rather than rubbing an adjusted tire.
    for bx in (0,60):
        for by in (-25,25):
            slot=box(7,20,5,(bx-3.5,y+by-10,-173))
            for sy in (-10,10):
                slot=slot.fuse(Part.makeCylinder(3.5,5,App.Vector(bx,y+by+sy,-173)))
            bracket=bracket.cut(slot)
    bracket = bracket.fuse(box(160,3,120,(-80,y-45,-169)))
    # Each flange bearing has an actual cantilever shelf joined to the wall.
    # Slotted bolt positions allow lateral gap adjustment before tightening.
    for shelf_z in (-124,-64):
        shelf=box(90,86,3,(-45,y-45,shelf_z-3))
        shelf=shelf.cut(Part.makeCylinder(11,5,App.Vector(0,y,shelf_z-4)))
        for sx in (-24,24):
            slot=box(7,16,5,(sx-3.5,y-8,shelf_z-4))
            for sy in (-8,8):
                slot=slot.fuse(Part.makeCylinder(3.5,5,App.Vector(sx,y+sy,shelf_z-4)))
            shelf=shelf.cut(slot)
        bracket=bracket.fuse(shelf)
    motor_shelf=box(110,86,3,(-55,y-45,-153))
    motor_shelf=motor_shelf.cut(Part.makeCylinder(20,5,App.Vector(0,y,-154)))
    bracket=bracket.fuse(motor_shelf)
    show('DriveBracket%d'%i,'3 mm 整组滑移支架 · 调隙后锁紧',bracket,steel,'Drive',collision=True)
    shaft=Part.makeCylinder(10,173,App.Vector(0,y,-138))
    show('WheelShaft%d'%i,'Ø20 独立轮轴 · 键连接',shaft,steel,'Drive',collision=True)
    for j,z in enumerate((-118,-58)):
        block=box(66,62,12,(-33,y-31,z-6))
        block=block.cut(Part.makeCylinder(10.2,16,App.Vector(0,y,z-8)))
        show('Bearing%d_%d'%(i,j),'Ø20 带座轴承 · 双支点',block,dark,'Drive',collision=True)
    hub=Part.makeCylinder(58,20,App.Vector(0,y,-10)).cut(Part.makeCylinder(10,22,App.Vector(0,y,-11)))
    hub=hub.fuse(Part.makeCylinder(18,70,App.Vector(0,y,-35)).cut(Part.makeCylinder(10,72,App.Vector(0,y,-36))))
    tire=Part.makeCylinder(rw,70,App.Vector(0,y,-35)).cut(Part.makeCylinder(58,72,App.Vector(0,y,-36)))
    hubobj=show('RotorHub%d'%i,'钢轮芯 · 转动惯量计入计算',hub,steel,'Drive')
    tireobj=show('Tire%d'%i,'弹性轮面 Ø140×70 · 可调轮隙',tire,rubber,'Drive')
    for obj in (hubobj,tireobj):
        obj.addProperty('App::PropertyString','ComplianceNote','Design')
        obj.ComplianceNote='球与弹性轮面允许压缩接触；刚性轮芯须保持净空'
    rigid.append(hubobj)
    motor=Part.makeCylinder(37,115,App.Vector(0,y,-269))
    motor=motor.fuse(Part.makeCylinder(44,3,App.Vector(0,y,-156)))
    motor=motor.fuse(Part.makeCylinder(8,14,App.Vector(0,y,-154)))
    show('Motor%d'%i,'24V 150–200W · 目标负载转速1400rpm，待询型',motor,blue,'Drive',collision=True)
    coupling=Part.makeCylinder(17,26,App.Vector(0,y,-151))
    coupling=coupling.cut(Part.makeCylinder(8,13,App.Vector(0,y,-152)))
    coupling=coupling.cut(Part.makeCylinder(10,15,App.Vector(0,y,-139)))
    show('Coupling%d'%i,'柔性联轴器 · 不让电机轴承承受夹球力',coupling,steel,'Drive',collision=True)
    # Outer guard is cut back around the explicit 260 mm ball corridor.
    outer=Part.makeCylinder(rw+7,80,App.Vector(0,y,-40))
    inner=Part.makeCylinder(rw+5,84,App.Vector(0,y,-42))
    guard=outer.cut(inner)
    for z in (-42,40):
        guard=guard.fuse(Part.makeCylinder(rw+7,2,App.Vector(0,y,z)))
    guard=guard.cut(box(360,260,450,(-180,-130,-140)))
    guard=guard.cut(Part.makeCylinder(12,90,App.Vector(0,y,-44)))
    show('WheelGuard%d'%i,'1 mm 钢轮罩 · 留出中央球路',guard,dark,'Guards',collision=True)
    # A radial line on the steel hub makes opposing wheel rotation visible.
    mark=box(3,36,2,(-1.5,y+20,11))
    show('RotationMark%d'%i,'轮转向标记',mark,(1.0,.66,.10),'Reference')

# Minimum ball guide: two slender rails, each actually tangent to the sphere.
# At y=+-85 the bottom of a 245 mm sphere is z=-88.2. Use the largest ball
# to place the rails lower; a supported ball has a 2 mm margin to the floor.
rail_y=85.0
rail_radius=4.0
rail_h=-math.sqrt((R+rail_radius)**2-rail_y**2)
for i,y in enumerate((-rail_y,rail_y)):
    rail=tube((-350,y,rail_h),(cfg['outlet_s_mm'],y,rail_h),rail_radius)
    show('BallSupportRail%d'%i,'Ø8 托球导轨 · 双轨支撑',rail,steel,'Feeder')
    rigid.append(doc.getObject('BallSupportRail%d'%i))
for i,y in enumerate((-137,133)):
    # Low guide strips cannot cover the vertical drop mouth.
    guide=box(495,4,80,(-350,y,-100))
    guide=guide.cut(box(170,12,100,(-85,y-4,-105)))
    show('SideGuide%d'%i,'侧导向 · 净宽266 mm',guide,steel,'Feeder',collision=True)

# Slider-crank feeder under the ball track. Its only job is to overcome the
# uphill component of gravity and bring the ball to the wheel entry tangent.
slider_start=cfg['stage_s_mm']-R-4
for i,y in enumerate((-105,105)):
    show('SliderRail%d'%i,'推球滑杆 Ø8',tube((slider_start-20,y,-165),(-140,y,-165),4),steel,'Feeder',collision=True)
paddle=box(4,210,32,(slider_start,-105,-16))
for y in (-103,97):
    paddle=paddle.fuse(box(4,6,150,(slider_start,y,-166)))
paddle=paddle.fuse(box(14,220,12,(slider_start-5,-110,-172)))
paddle=paddle.fuse(box(12,18,22,(slider_start-4,-9,-166)))
for y in (-105,105):
    paddle=paddle.cut(Part.makeCylinder(4.2,24,App.Vector(slider_start-8,y,-165),App.Vector(1,0,0)))
show('Pusher','单片推球片 · 行程180 mm',paddle,(.90,.56,.12),'Feeder')
crank_r=cfg['pusher_stroke_mm']/2
link_l=180.0
crank_pivot=slider_start+crank_r+link_l
show('FeedServo','20 kg·cm 级舵机 · 推球所需扭矩另核算',box(60,35,42,(crank_pivot-30,-17.5,-225)),blue,'Feeder',collision=True)
crank_end=App.Vector(crank_pivot-crank_r,0,-152)
show('FeedCrank','曲柄 r90 mm',tube((crank_pivot,0,-152),tuple(crank_end),6),orange,'Feeder')
show('FeedLink','连杆 180 mm',tube(tuple(crank_end),(slider_start,0,-152),4),steel,'Feeder')
show('FeedServoHorn','舵机输出连接柱',Part.makeCylinder(6,31,App.Vector(crank_pivot,0,-183)),steel,'Feeder')

# No long launch tray. The ball is free once it leaves the two wheels and
# short tangent support rails. Electrical enclosure is below the ball route.
electrical=box(175,120,40,(-230,-60,-253))
show('ControlSupply','24V 电源+双路调速 · 插电式',electrical,blue,'Guards',collision=True)
sensor=box(24,12,25,(cfg['stage_s_mm']-12,140,-60))
show('BallSensor','单球到位光电检测',sensor,green,'Guards',collision=True)

# Return collector. Transparent textile surfaces do not pretend to be solids.
stage_world=world((cfg['stage_s_mm'],0,0))
bx=stage_world.x
mouth_z=stage_world.z+R+55
top_z=cfg['collector_top_z_mm']
top=[(bx-900,-800,top_z),(bx+900,-800,top_z),(bx+900,800,top_z),(bx-900,800,top_z)]
bottom=[(bx-140,-140,mouth_z),(bx+140,-140,mouth_z),(bx+140,140,mouth_z),(bx-140,140,mouth_z)]
for i in range(4):
    j=(i+1)%4
    pts=[App.Vector(*p) for p in (top[i],top[j],bottom[j],bottom[i],top[i])]
    panel=Part.Face(Part.Wire(Part.makePolygon(pts).Edges))
    if i==1:
        # A low central aperture keeps the returning soft net out of the
        # complete launch envelope. The ball never shoots through a net face.
        panel=panel.cut(box(950,340,850,(bx-140,-170,0)))
    show('NetPanel%d'%i,'PE 软网 · 直落单球托位',panel,green,'Collector',False,88)
    # Segment top rim for transportation: maximum individual length 900 mm.
    a,b=App.Vector(*top[i]),App.Vector(*top[j]); mid=(a+b)*.5
    for k,(p,q) in enumerate(((a,mid),(mid,b))):
        show('NetRim%d_%d'%(i,k),'可拆边杆 · 单节≤900mm',tube(tuple(p),tuple(q),8,7.2),steel,'Collector',False)
    foot=App.Vector(-310 if i in (0,3) else 255,-270 if i in (0,1) else 270,85)
    tip=App.Vector(*top[i]); v=tip-foot
    # Nested tube display: three overlapping stages; this is a deployed
    # layout, not a proven folding/stiffness design.
    for k,(t0,t1,r) in enumerate(((0,.37,12),(.33,.70,10),(.66,1.0,8))):
        a,b=foot+v*t0,foot+v*t1
        show('NetPole%d_%d'%(i,k),'伸缩钢管 · 展开布置，锁止待样机',tube(tuple(a),tuple(b),r,r-.8),steel,'Collector',False)

ball=show('BallReference','单颗七号球 Ø245',Part.makeSphere(R,world((cfg['stage_s_mm'],0,0))),orange,'Reference',False,10)
ball.addProperty('App::PropertyString','OperatingRule','Design'); ball.OperatingRule='仅一颗球循环，不含第二球储存或分球机构'

# Nominal path, hidden by default. This is a kinematic route, not a solution
# of tire/ball contact dynamics.
pts=[world((cfg['stage_s_mm'],0,0)),world((-50,0,0)),world((0,0,0)),world((cfg['outlet_s_mm'],0,0))]
route=show('BallPath','参考中心路径 · 默认隐藏',Part.makePolygon(pts),(1.0,.65,.08),'Reference',False)
route.ViewObject.Visibility=False

doc.recompute()
invalid=[o.Name for o in doc.Objects if hasattr(o,'Shape') and not o.Shape.isNull() and not o.Shape.isValid()]
if invalid:
    raise RuntimeError('Invalid geometry: '+str(invalid))

# Exact solid intersections along the ball path. Rubber tire interference is
# intentional (nominal 6.5 mm/side). Contact rails are checked with a 0.4 mm
# shrink allowance to disregard tangency tolerances.
obstacles=rigid
failures=[]
positions=[]
for s in range(-205,226,10): positions.append(('feed',world((s,0,0))))
for dz in range(0,1451,50): positions.append(('drop',stage_world+App.Vector(0,0,dz)))
for kind,p in positions:
    sphere=Part.makeSphere(R-.4,p)
    bb=sphere.BoundBox
    for obj in obstacles:
        if not bb.intersect(obj.Shape.BoundBox):
            continue
        vol=sphere.common(obj.Shape).Volume
        if vol>1.0:
            failures.append({'phase':kind,'at_mm':[round(p.x,2),round(p.y,2),round(p.z,2)],'part':obj.Name,'overlap_mm3':round(vol,2)})

# Energy and geometry numbers are useful even before motor procurement.
mass=cfg['ball_mass_kg']; speed=cfg['target_ball_speed_m_s']; omega=cfg['wheel_rpm']*2*math.pi/60
rotor_inertia=0.0
rotor_mass=0.0
for i in range(2):
    # Steel disc + sleeve and PU tire. Shapes include their production bores.
    hub=doc.getObject('RotorHub%d'%i)
    tire=doc.getObject('Tire%d'%i)
    for obj,rho in ((hub,7.85e-6),(tire,1.10e-6)):
        m=obj.Shape.Volume*rho
        rotor_mass+=m
        # Analytic inertia about the wheel shaft, mm -> m.
    disc_m=math.pi*(58**2-10**2)*20*7.85e-6
    sleeve_extra=math.pi*(18**2-10**2)*50*7.85e-6
    tread_m=math.pi*(rw**2-58**2)*70*1.10e-6
    rotor_inertia+=.5*disc_m*((.058)**2+.010**2)+.5*sleeve_extra*(.018**2+.010**2)+.5*tread_m*((rw/1000)**2+.058**2)
trans_energy=.5*mass*speed**2
spin_energy=(1/3)*mass*.1225**2*(1/.1225)**2 # 1 m/s top/bottom surface mismatch budget
bank=.5*rotor_inertia*omega**2
entry_half=math.sqrt((rw+R)**2-half_pitch**2)
feed_force=mass*9.81*math.sin(angle)+2.0
max_feed_torque=feed_force*(crank_r/1000)*1.2
collector_names={o.Name for o in groups['Collector'].Group}
clear_solids=[o for o in doc.Objects if o.TypeId!='App::DocumentObjectGroup' and hasattr(o,'Shape') and not o.Shape.isNull() and o.Name not in collector_names and o.Name not in ('BallPath','BallReference')]
bb=App.BoundBox()
for obj in clear_solids: bb.add(obj.Shape.BoundBox)
report={
 'ball_diameter_mm':2*R,'ball_operating_range_mm':[cfg['ball_min_mm'],cfg['ball_max_mm']],
 'wheel_gap_mm':cfg['wheel_gap_mm'],'nominal_radial_compression_per_side_mm':(2*R-cfg['wheel_gap_mm'])/2,
 'wheel_surface_speed_m_s':round(omega*rw/1000,3),'target_ball_speed_m_s':speed,
 'target_ball_translation_energy_J':round(trans_energy,3),
 'total_rotor_mass_kg':round(rotor_mass,3),'total_rotor_inertia_kg_m2':round(rotor_inertia,6),
 'stored_rotor_energy_J':round(bank,3),
 'rotor_speed_drop_ideal_pct':round((1-math.sqrt(max(0,1-trans_energy/bank)))*100,2),
 'rigid_nominal_ball_contact_travel_mm':round(2*entry_half,2),
 'required_average_accelerating_force_N':round(trans_energy/(2*entry_half/1000),1),
 'friction_mu_assumed':.65,
 'required_average_normal_force_per_wheel_N':round(trans_energy/(2*entry_half/1000)/(2*.65),1),
 'feeder_design_force_N':round(feed_force,2),'estimated_feeder_peak_torque_Nm':round(max_feed_torque,3),
 'main_unit_envelope_mm':[round(bb.XLength,1),round(bb.YLength,1),round(bb.ZLength,1)],
 'invalid_geometry':invalid,'nominal_path_samples':len(positions),'rigid_path_collisions':failures,
 'limits':'No tire contact dynamics, transient motor model, strength/stability proof, or prototype launch test. Contact force and speed must be measured; 232 mm gap is adjustable starting point.'
}
(ROOT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()
Gui.activeDocument().activeView().redraw()
Gui.updateGui()
Gui.activeDocument().activeView().saveImage(str(ROOT/'assembly.png'),1400,1100,'White')
doc.recompute()
doc.saveAs('D:/basketball/七号球极简发球机_V2.FCStd')
print(json.dumps(report,ensure_ascii=False))
