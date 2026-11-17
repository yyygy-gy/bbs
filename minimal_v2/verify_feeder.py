import json
import math
from pathlib import Path
import FreeCAD as App
import Part

root=Path('D:/basketball/minimal_v2')
cfg=json.loads((root/'design.json').read_text(encoding='utf-8'))
doc=App.getDocument(cfg['document_name'])
T=App.Placement(App.Vector(*cfg['wheel_origin_mm']),App.Rotation(App.Vector(0,1,0),-cfg['launch_angle_deg']))
fixed=[]
for group in ('Frame','Drive','Feeder','Guards'):
    fixed.extend(obj for obj in doc.getObject(group).Group if obj.Name not in ('Pusher','FeedCrank','FeedLink','FeedServoHorn'))
slider0=cfg['stage_s_mm']-cfg['ball_diameter_mm']/2-4
r=cfg['pusher_stroke_mm']/2
L=180.0
pivot=slider0+r+L
original=doc.getObject('Pusher').Shape
fail=[]
for step in range(19):
    fraction=step/18
    theta=math.pi*(1-fraction)
    end=App.Vector(pivot+r*math.cos(theta),r*math.sin(theta),-152)
    s=pivot+r*math.cos(theta)-math.sqrt(L*L-r*r*math.sin(theta)**2)
    move=App.Placement(T.Rotation.multVec(App.Vector(s-slider0,0,0)),App.Rotation())
    paddle=original.copy();paddle.Placement=move.multiply(paddle.Placement)
    crank=Part.makeCylinder(6,r,App.Vector(pivot,0,-152),end-App.Vector(pivot,0,-152))
    link=Part.makeCylinder(4,L,end,App.Vector(s,0,-152)-end)
    crank.Placement=T.multiply(crank.Placement)
    link.Placement=T.multiply(link.Placement)
    for name,shape in (('Pusher',paddle),('Crank',crank),('Link',link)):
        for obj in fixed:
            if name=='Pusher' and obj.Name.startswith('SliderRail'):
                # Sliding holes have modeled radial clearance of 0.2 mm;
                # do not exclude these from the actual intersection check.
                pass
            if not shape.BoundBox.intersect(obj.Shape.BoundBox):continue
            v=shape.common(obj.Shape).Volume
            if v>1:
                fail.append({'step':step,'moving':name,'fixed':obj.Name,'overlap_mm3':round(v,3)})
report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
report['feeder_pose_samples']=19
report['feeder_motion_collisions']=fail
(root/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pose_samples':19,'feeder_collisions':fail},ensure_ascii=False))
