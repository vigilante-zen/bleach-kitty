"""Render the actual theme with dummy login data; never authenticates."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtQml import QQmlPropertyMap

class Dummy(QObject):
    loginFailed = Signal()
    canReboot = Property(bool, lambda self: True, constant=True)
    canPowerOff = Property(bool, lambda self: True, constant=True)
    @Slot(str, str, int)
    def login(self, *_): self.loginFailed.emit()
    @Slot()
    def reboot(self): pass
    @Slot()
    def powerOff(self): pass

app = QGuiApplication([])
view = QQuickView()
user = QQmlPropertyMap(); user.insert('lastUser', 'zen')
keyboard = QQmlPropertyMap(); keyboard.insert('capsLock', False)
# Use a ListModel wrapper so lastIndex matches the greeter API.
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
class Sessions(QAbstractListModel):
    lastIndex = Property(int, lambda self: 0, constant=True)
    def rowCount(self, parent=QModelIndex()): return 1
    def roleNames(self): return {Qt.UserRole + 1: b'name'}
    def data(self, index, role): return 'Plasma (Wayland)' if role == Qt.UserRole + 1 else None
sessions = Sessions(); dummy = Dummy()
for key, value in [('userModel', user), ('keyboard', keyboard), ('sessionModel', sessions), ('sddm', dummy)]:
    view.rootContext().setContextProperty(key, value)
base = Path(__file__).resolve().parent
view.setSource(QUrl.fromLocalFile(str(base / 'theme/Main.qml')))
if view.status() == QQuickView.Error:
    print([e.toString() for e in view.errors()]); raise SystemExit(1)
view.setResizeMode(QQuickView.SizeRootObjectToView)
view.resize(1280, 720); view.show()
def capture():
    if not view.grabWindow().save(str(base / 'preview.png')): raise RuntimeError('Capture failed')
    app.quit()
QTimer.singleShot(1800, capture)
app.exec()
