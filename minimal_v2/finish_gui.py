import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui

ROOT=Path('D:/basketball/minimal_v2')
exec(compile(Path('D:/basketball/MinimalLauncherV2.FCMacro').read_text(encoding='utf-8'),'D:/basketball/MinimalLauncherV2.FCMacro','exec'),{})
p=Gui._minimal_v2_player
p.pause()
p.t=4.12
p.apply()
p.view.redraw()
Gui.updateGui()
p.view.saveImage(str(ROOT/'mechanism.png'),1400,1050,'White')
p.reset()
p.close()
p.doc.getObject('Collector').Visibility=True
p.doc.recompute()
p.doc.save()
# Restore a usable dock after saving the engineering layout in its rest pose.
p=Gui._minimal_v2_player_module.launch()
p.pause()
p.t=2.5
p.apply()
p.view.redraw()
Gui.updateGui()
p.reset()
p.play_button.click()
print(json.dumps({'document':p.doc.Name,'file':p.doc.FileName,'dock_visible':p.isVisible(),'timer_active':p.timer.isActive(),'start_ticks':p.ticks},ensure_ascii=False))
