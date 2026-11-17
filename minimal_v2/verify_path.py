import json
import math
from pathlib import Path
import FreeCAD as App
import Part

root=Path('D:/basketball/minimal_v2')
cfg=json.loads((root/'design.json').read_text(encoding='utf-8'))
doc=App.getDocument(cfg['document_name'])
transform=App.Placement(App.Vector(*cfg['wheel_origin_mm']),App.Rotation(App.Vector(0,1,0),-cfg['launch_angle_deg']))
def W(s,h=0):return transform.multVec(App.Vector(s,0,h))
nominal_r=cfg['ball_diameter_mm']/2
rail_h=-math.sqrt((nominal_r+4)**2-85**2)
fixed=[]
for group_name in ('Frame','Drive','Feeder','Guards','Collector'):
    for obj in doc.getObject(group_name).Group:
        if obj.Name.startswith(('Tire','Pusher','FeedCrank','FeedLink','RotationMark','NetPanel')):
            continue
        fixed.append(obj)
net=[o for o in doc.getObject('Collector').Group if o.Name.startswith('NetPanel')]
fail=[]
counts={}
for diameter in (cfg['ball_min_mm'],cfg['ball_diameter_mm'],cfg['ball_max_mm']):
    radius=diameter/2
    h=math.sqrt((radius+4)**2-85**2)+rail_h
    stage_s=cfg['stage_s_mm']+radius-nominal_r
    rest=W(stage_s,h)
    positions=[]
    for dz in range(0,1601,50):positions.append(('drop',rest+App.Vector(0,0,dz)))
    for i in range(39):
        s=stage_s+(cfg['outlet_s_mm']+20-stage_s)*i/38
        positions.append(('feed',W(s,h)))
    exit_pos=W(cfg['outlet_s_mm'],h)
    direction=transform.Rotation.multVec(App.Vector(1,0,0))
    for i in range(31):
        t=i*.02
        positions.append(('flight',exit_pos+direction*(cfg['target_ball_speed_m_s']*1000*t)+App.Vector(0,0,-4905*t*t)))
    counts[diameter]=len(positions)
    for phase,pos in positions:
        sphere=Part.makeSphere(radius-.4,pos)
        for obj in fixed+net:
            if not sphere.BoundBox.intersect(obj.Shape.BoundBox):continue
            common=sphere.common(obj.Shape)
            metric=common.Area if obj in net else common.Volume
            if metric>1:
                fail.append({'diameter':diameter,'phase':phase,'part':obj.Name,'intersection':round(metric,3),'point':[round(v,2) for v in (pos.x,pos.y,pos.z)]})

# The wheels must be able to turn without cutting through a rigid guide or
# bracket. This is separate from the deliberate tire/ball compliance.
wheel_clashes=[]
for i in (0,1):
    wheel=doc.getObject('Tire%d'%i)
    for obj in fixed:
        if obj.Name.startswith(('RotorHub','WheelShaft','Motor','Coupling')):continue
        if not wheel.Shape.BoundBox.intersect(obj.Shape.BoundBox):continue
        volume=wheel.Shape.common(obj.Shape).Volume
        if volume>1:wheel_clashes.append({'wheel':wheel.Name,'part':obj.Name,'overlap_mm3':round(volume,3)})

report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
report['diameter_path_samples']=counts
report['all_diameter_path_collisions']=fail
report['wheel_to_rigid_part_collisions']=wheel_clashes
report['net_launch_aperture_mm']={'width':340,'top_z':850}
report['support_height_adjustment_mm']={str(d):round(math.sqrt((d/2+4)**2-85**2)+rail_h,3) for d in counts}
report['minimum_ball_reaches_pinch']=cfg['stage_s_mm']+cfg['pusher_stroke_mm']+cfg['ball_min_mm']/2-nominal_r > -math.sqrt((cfg['wheel_radius_mm']+cfg['ball_min_mm']/2)**2-(cfg['wheel_radius_mm']+cfg['wheel_gap_mm']/2)**2)
pitch=cfg['wheel_radius_mm']+cfg['wheel_gap_mm']/2
sum_r=cfg['wheel_radius_mm']+nominal_r
half_contact=math.sqrt(sum_r**2-pitch**2)
# Conditional quasistatic tire law N=k*indentation and sliding coefficient mu.
# Normal forces have zero net work over symmetric entry/exit. This is only a
# first sizing bound: real rubber hysteresis, slip and spin must be measured.
integral_mm2=2*pitch*(sum_r*math.asinh(half_contact/pitch)-half_contact)
required_energy=report['target_ball_translation_energy_J']+cfg['ball_mass_kg']*9.81*(2*half_contact/1000)*math.sin(math.radians(cfg['launch_angle_deg']))
stiffness=required_energy*1000/(2*.65*integral_mm2)
report['conditional_contact_sizing']={
    'model':'Symmetric linear effective wheel/ball stiffness, sliding friction mu=0.65, no hysteresis; sizing estimate only',
    'self_feed_friction_coefficient_lower_bound':round(half_contact/pitch,3),
    'effective_stiffness_required_per_side_N_per_mm':round(stiffness,2),
    'predicted_peak_radial_force_each_N':round(stiffness*(nominal_r-cfg['wheel_gap_mm']/2),1),
    'shaft_diameter_mm':20,
    'shaft_bending_stress_at_400N_MPa':round(32*400*58/(math.pi*20**3),2),
    'required_motor_running_torque_each_Nm':[round(w/(cfg['wheel_rpm']*2*math.pi/60),3) for w in (150,200)]
}
(root/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'samples':counts,'ball_path_failures':fail,'wheel_clashes':wheel_clashes},ensure_ascii=False))
