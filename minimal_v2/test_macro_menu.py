import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore,QtWidgets

state={'opened':False,'selected':False,'clicked':False,'error':None}
Gui._v2_native_macro_test=state

def execute_selected_macro():
    try:
        dialog=QtWidgets.QApplication.activeModalWidget()
        if dialog is None:
            state['error']='Macro menu did not open';return
        state['opened']=True
        state['dialog_title']=dialog.windowTitle()
        views=dialog.findChildren(QtWidgets.QAbstractItemView)
        for view in views:
            model=view.model()
            for row in range(model.rowCount()):
                index=model.index(row,0)
                value=str(model.data(index,QtCore.Qt.DisplayRole))
                if value.lower()=='minimallauncherv2.fcmacro':
                    view.setCurrentIndex(index)
                    view.selectionModel().select(index,QtCore.QItemSelectionModel.ClearAndSelect|QtCore.QItemSelectionModel.Rows)
                    state['selected']=True
                    break
            if state['selected']:break
        if not state['selected']:
            state['error']='Macro entry not found';dialog.reject();return
        buttons=dialog.findChildren(QtWidgets.QPushButton)
        button=next((b for b in buttons if b.text().replace('&','').strip().lower() in ('执行','execute')),None)
        if button is None or not button.isEnabled():
            state['error']='Execute button not enabled';dialog.reject();return
        state['clicked']=True
        button.click()
    except Exception as exc:
        state['error']=repr(exc)
        dialog=QtWidgets.QApplication.activeModalWidget()
        if dialog:dialog.reject()

def fallback_close():
    if not state['clicked']:
        modal=QtWidgets.QApplication.activeModalWidget()
        if modal:modal.reject()

QtCore.QTimer.singleShot(350,execute_selected_macro)
QtCore.QTimer.singleShot(4000,fallback_close)
Gui.runCommand('Std_DlgMacroExecute')
print('native macro dialog test:',state)
