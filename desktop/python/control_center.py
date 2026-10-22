#!/usr/bin/env python3
"""Bankai: a native desktop control center for the Bleach setup."""
from datetime import datetime
import argparse
import json
import os
import shutil
from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, QFileSystemWatcher, QLockFile, QObject, QProcess, QSize, Qt, QTimer, QUrl, Slot
from PySide6.QtGui import QActionGroup, QColor, QDesktopServices, QFont, QIcon, QImageReader, QKeySequence, QShortcut, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QColorDialog, QFormLayout, QInputDialog, QLineEdit, QListWidgetItem, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton, QSpinBox, QStackedWidget,
    QScrollArea, QSystemTrayIcon, QTextEdit, QToolButton, QVBoxLayout, QWidget,
)
from snapshot_manager import SnapshotStore, format_size, reject_symlinks

HOME = Path.home()
DATA = HOME / '.local/share/bleach-desktop'
BIN = HOME / '.local/bin'
WALLPAPERS = HOME / 'Pictures/Bleach-TYBW/Wallpapers'
SNAPSHOTS = HOME / 'Backups/Bleach-Desktop'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared') if (Path(__file__).resolve().parents[1] / 'shared/appearance_settings.py').is_file() else str(DATA))
import appearance_settings
PRESETS = {p['id']: (p['title'], p['subtitle'], p['accent'], p['image']) for p in appearance_settings.catalog()}

def appearance():
    try: return appearance_settings.load(HOME)
    except (OSError, ValueError): return appearance_settings.defaults()

def wallpaper(name):
    return WALLPAPERS / (name + '-manga.png' if appearance()['edition'] == 'manga' else PRESETS[name][3])

ICONS = Path(__file__).resolve().parent / 'icons'


def hollow_icon(accent):
    """Render the vector mask at native tray and high-DPI sizes."""
    source = (ICONS / 'bleach-tray.svg').read_text().replace('#d72f43', accent)
    renderer = QSvgRenderer(QByteArray(source.encode()))
    if not renderer.isValid():
        return QIcon()
    icon = QIcon()
    for size in (16, 22, 24, 32, 48, 64, 128):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


STYLE = '''
QWidget { background: #090c12; color: #e8edf5; font-family: "Noto Sans"; font-size: 13px; }
QFrame#sidebar { background: #101620; border-right: 1px solid #253044; }
QFrame#sidebar QLabel { background: transparent; }
QLabel#brand { font-size: 29px; font-weight: 800; letter-spacing: 5px; }
QLabel#eyebrow { color: #e96b75; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#heading { font-size: 26px; font-weight: 700; }
QLabel#muted { color: #9baabd; }
QLabel#notice { background: #131e2b; color: #b8ccdf; padding: 12px; border-radius: 8px; }
QListWidget { border: 0; background: transparent; outline: none; }
QListWidget::item { padding: 13px 10px; margin: 3px 0; border-radius: 7px; color: #acb9ca; }
QListWidget::item:selected { background: #243044; color: white; border-left: 3px solid #e63946; }
QPushButton { background: #192332; border: 1px solid #2b3a50; padding: 10px 16px; border-radius: 7px; }
QPushButton:hover { background: #253348; border-color: #617d9e; }
QPushButton:disabled { color: #657080; background: #141a24; border-color: #202936; }
QPushButton#primary { background: #b52a3a; border-color: #db4f60; color: white; font-weight: 700; }
QPushButton#primary:hover { background: #d23648; }
QPushButton#primary:disabled { background: #512430; color: #96858c; border-color: #512430; }
QToolButton { border: 1px solid #29364a; border-radius: 9px; padding: 8px; background: #111925; }
QToolButton:hover { background: #1a2638; border-color: #8294aa; }
QToolButton:checked { border: 2px solid #e8edf5; background: #1a2638; }
QComboBox { background: #151f2d; border: 1px solid #32435c; border-radius: 6px; padding: 10px; }
QComboBox QAbstractItemView { background: #151f2d; selection-background-color: #334861; }
QTextEdit { background: #0d131d; border: 1px solid #263348; border-radius: 7px; font-family: monospace; font-size: 11px; }
QMessageBox QLabel { min-width: 360px; }
'''


def label(text, style=None):
    widget = QLabel(text)
    if style:
        widget.setObjectName(style)
    widget.setWordWrap(True)
    return widget


def saved_preset():
    try:
        name = (DATA / 'current').read_text().strip()
        return name if name in PRESETS else 'tybw'
    except OSError:
        return 'tybw'


class Artwork(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)
        self.name = 'tybw'
        self.pixmap = QPixmap()
        self.scaled_preview = QPixmap()
        self.preview_size = QSize()

    def select(self, name):
        self.name = name
        reader = QImageReader(str(wallpaper(name)))
        if reader.size().isValid():
            reader.setScaledSize(reader.size().scaled(1600, 1000, Qt.AspectRatioMode.KeepAspectRatio))
        self.pixmap = QPixmap.fromImage(reader.read())
        self.preview_size = QSize()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(self.rect().toRectF(), 12, 12)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor('#111925'))
        if not self.pixmap.isNull():
            if self.preview_size != self.size():
                self.scaled_preview = self.pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.SmoothTransformation)
                self.preview_size = self.size()
            scaled = self.scaled_preview
            painter.drawPixmap((self.width() - scaled.width()) // 2,
                               (self.height() - scaled.height()) // 2, scaled)
        gradient = QLinearGradient(0, self.height() * 0.25, 0, self.height())
        gradient.setColorAt(0, QColor(9, 12, 18, 0))
        gradient.setColorAt(1, QColor(9, 12, 18, 245))
        painter.fillRect(self.rect(), gradient)
        title, subtitle, accent, _ = PRESETS[self.name]
        accent = appearance()["accent"] or accent
        painter.setPen(QColor(accent))
        font = QFont('Noto Sans', 10)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        painter.setFont(font)
        painter.drawText(24, self.height() - 77, 'SOUL SOCIETY / ' + title.upper())
        painter.setPen(QColor('#ffffff'))
        painter.setFont(QFont('Noto Sans', 25, QFont.Weight.Bold))
        painter.drawText(22, self.height() - 37, title)
        painter.setFont(QFont('Noto Sans', 10))
        painter.setPen(QColor('#bcc9da'))
        painter.drawText(24, self.height() - 15, subtitle)


class ControlCenter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Bankai · Soul Society Control Center')
        self.setWindowIcon(QIcon(str(HOME / '.local/share/icons/hicolor/scalable/apps/bleach-bankai.svg')))
        self.setMinimumSize(850, 590)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1140, int(screen.width() * .93)), min(820, int(screen.height() * .93)))
        self.selected = saved_preset()
        self.process = None
        self.process_callback = None
        self.action_buttons = []
        self.cards = {}
        self.output = ''
        self.store = SnapshotStore(SNAPSHOTS, HOME / '.local/state/bleach-desktop')
        self.snapshot_rows = {}
        self.tray = None
        self.tray_actions = []
        self.preset_actions = {}
        self.custom_rows = []
        self.quitting = False
        body = QWidget()
        self.setCentralWidget(body)
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(210)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(23, 30, 23, 23)
        side.addWidget(label('SOUL SOCIETY', 'eyebrow'))
        side.addWidget(label('BANKAI', 'brand'))
        side.addWidget(label('Your command center', 'muted'))
        side.addSpacing(28)
        self.navigation = QListWidget()
        self.navigation.addItems(['Appearance', 'Backups & restore', 'Terminal & tools'])
        side.addWidget(self.navigation)
        self.saved = label('', 'muted')
        side.addWidget(self.saved)
        side.addSpacing(10)
        side.addWidget(label('THOUSAND-YEAR\nBLOOD WAR', 'eyebrow'))
        layout.addWidget(sidebar)
        content = QWidget()
        right = QVBoxLayout(content)
        right.setContentsMargins(26, 25, 26, 18)
        right.setSpacing(13)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.appearance_page())
        self.pages.addWidget(self.backups_page())
        self.pages.addWidget(self.tools_page())
        right.addWidget(self.pages, 1)
        self.message = label('Choose a character to preview. Click Apply when you are ready.', 'notice')
        right.addWidget(self.message)
        self.details_button = QPushButton('Show activity')
        self.details_button.setMaximumWidth(140)
        self.details_button.clicked.connect(self.toggle_output)
        right.addWidget(self.details_button)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.log.hide()
        right.addWidget(self.log)
        layout.addWidget(content, 1)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        for index in range(self.navigation.count()):
            shortcut = QShortcut(QKeySequence(f'Ctrl+{index + 1}'), self)
            shortcut.activated.connect(lambda row=index: self.navigation.setCurrentRow(row))
            self.navigation.item(index).setToolTip(f'Ctrl+{index + 1}')
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.operation_timeout)
        self.select_preset(self.selected)
        self.refresh_state()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        columns = max(1, min(4, (self.width() - 290) // 160))
        if not hasattr(self, 'preset_grid') or columns == self.preset_columns:
            return
        self.preset_columns = columns
        for card in self.cards.values():
            self.preset_grid.removeWidget(card)
        for index, card in enumerate(self.cards.values()):
            self.preset_grid.addWidget(card, index // columns, index % columns)

    def show_window(self, backups=False):
        if backups:
            self.navigation.setCurrentRow(1)
            self.refresh_snapshots()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def setup_tray(self, show=True):
        icon = QIcon(str(Path(__file__).resolve().parent / 'icons/bleach-tray.svg'))
        self.tray = QSystemTrayIcon(icon if not icon.isNull() else self.windowIcon(), self)
        self.tray_menu = QMenu(self)
        self.tray_status = self.tray_menu.addAction('Bankai')
        self.tray_status.setEnabled(False)
        self.tray_menu.addAction('Open control center', lambda: self.show_window())
        presets = self.tray_menu.addMenu('Switch character')
        self.preset_action_group = QActionGroup(self)
        self.preset_action_group.setExclusive(True)
        for name, (title, _, _, _) in PRESETS.items():
            action = presets.addAction(title)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, n=name: self.apply_from_tray(n))
            self.preset_action_group.addAction(action)
            self.preset_actions[name] = action
            self.tray_actions.append(action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(QIcon(str(ICONS / 'bleach-terminal.svg')), 'Soul Society Terminal', lambda: self.launch_terminal())
        self.tray_menu.addAction(QIcon(str(ICONS / 'bleach-monitor.svg')), 'Reiatsu Monitor', lambda: self.launch_terminal('bankai-monitor', 'Reiatsu Monitor'))
        self.tray_actions.append(self.tray_menu.addAction(QIcon(str(ICONS / 'bleach-backups.svg')), 'Create snapshot', lambda: self.run_task(
            [str(BIN / 'bankai-desktop-backup')], 'Creating a snapshot…', 'Snapshot saved.')))
        self.tray_menu.addAction(QIcon(str(ICONS / 'bleach-backups.svg')), 'Backups && restore', lambda: self.show_window(backups=True))
        self.tray_menu.addSeparator()
        self.tray_menu.addAction('Quit Bankai', self.quit_app)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray_refresh = QTimer(self)
        self.tray_refresh.setInterval(30000)
        self.tray_refresh.timeout.connect(self.refresh_tray)
        self.tray_refresh.start()
        self.tray_icon_preset = None
        self.tray_watch = QFileSystemWatcher(self)
        self.tray_watch.addPath(str(DATA))
        self.tray_debounce = QTimer(self)
        self.tray_debounce.setSingleShot(True)
        self.tray_debounce.setInterval(150)
        self.tray_debounce.timeout.connect(self.refresh_external_state)
        self.tray_watch.directoryChanged.connect(lambda path: self.tray_debounce.start())
        self.tray_watch.fileChanged.connect(lambda path: self.tray_debounce.start())
        self.refresh_tray()
        if show:
            self.tray.show()

    def refresh_tray(self):
        if self.tray is None:
            return
        name = saved_preset()
        current_file = DATA / 'current'
        if current_file.exists() and str(current_file) not in self.tray_watch.files():
            self.tray_watch.addPath(str(current_file))
        if self.tray_icon_preset != name:
            try:
                icon = hollow_icon(PRESETS[name][2])
                if not icon.isNull():
                    self.tray.setIcon(icon)
                    self.tray_icon_preset = name
            except OSError:
                pass  # Keep the last usable icon if the asset is unavailable.
        title = PRESETS[name][0]
        pending = (HOME / '.local/state/bleach-desktop/pending').exists()
        text = 'Bankai · ' + title + (' · refresh queued' if pending else '')
        self.tray.setToolTip(text)
        self.tray_status.setText(text)
        for key, action in self.preset_actions.items():
            action.setChecked(key == name)
            action.setEnabled(self.process is None)

    def refresh_external_state(self):
        self.refresh_tray()
        self.refresh_custom_presets()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    def apply_from_tray(self, name):
        if self.process is None:
            self.select_preset(name)
            self.apply_preset()

    def quit_app(self):
        if self.process is not None:
            self.show_window()
            self.message.setText('Let the current action finish before quitting Bankai.')
            return
        self.quitting = True
        if self.tray is not None:
            self.tray.hide()
        QApplication.instance().quit()

    def button(self, text, callback, primary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName('primary')
        button.clicked.connect(callback)
        self.action_buttons.append(button)
        return button

    def appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(13)
        header = QHBoxLayout()
        header.addWidget(label('Make it yours', 'heading')); header.addStretch()
        header.addWidget(self.button('Appearance options', self.appearance_options))
        layout.addLayout(header)
        layout.addWidget(label('Eighteen characters and forms, color or manga wallpapers, and matching login scenes.', 'muted'))
        self.art = Artwork()
        layout.addWidget(self.art, 1)
        cards = QGridLayout()
        self.preset_grid = cards
        self.preset_columns = 4
        self.card_group = QButtonGroup(self)
        self.card_group.setExclusive(True)
        for index, (name, (title, subtitle, accent, image)) in enumerate(PRESETS.items()):
            card = QToolButton()
            card.setCheckable(True)
            card.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            card.setText(title)
            card.setToolTip(subtitle)
            reader = QImageReader(str(WALLPAPERS / image))
            if reader.size().isValid():
                reader.setScaledSize(reader.size().scaled(276, 130, Qt.AspectRatioMode.KeepAspectRatio))
            thumb = QPixmap.fromImage(reader.read())
            card.setIcon(QIcon(thumb))
            card.setIconSize(QSize(138, 65))
            card.setMinimumHeight(96)
            card.clicked.connect(lambda checked=False, n=name: self.select_preset(n))
            self.card_group.addButton(card)
            self.cards[name] = card
            cards.addWidget(card, index // 4, index % 4)
        layout.addLayout(cards)
        self.preview_note = label('', 'muted')
        layout.addWidget(self.preview_note)
        actions = QHBoxLayout()
        actions.addWidget(self.button('Apply preset', self.apply_preset, primary=True))
        actions.addWidget(self.button('Open wallpaper', self.open_wallpaper))
        actions.addStretch()
        layout.addLayout(actions)
        saved_row = QHBoxLayout()
        self.custom_combo = QComboBox()
        self.custom_combo.setMinimumWidth(190)
        self.custom_combo.currentIndexChanged.connect(self.preview_custom_preset)
        saved_row.addWidget(self.custom_combo, 1)
        saved_row.addWidget(self.button('Save current choices', self.save_custom_preset))
        self.custom_apply_button = self.button('Apply saved', self.apply_custom_preset, primary=True)
        self.custom_delete_button = self.button('Delete', self.delete_custom_preset)
        saved_row.addWidget(self.custom_apply_button)
        saved_row.addWidget(self.custom_delete_button)
        layout.addLayout(saved_row)
        self.refresh_custom_presets()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        self.appearance_scroll = scroll
        return scroll

    def backups_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(label('Keep a way back', 'heading'))
        layout.addWidget(label('Save the desktop and terminal together. Restore checks file integrity and saves your current settings first.', 'muted'))
        snapshot_button = self.button('Create snapshot', lambda: self.run_task(
            [str(BIN / 'bankai-desktop-backup')], 'Creating a snapshot…', 'Snapshot saved.'), primary=True)
        snapshot_button.setIcon(QIcon(str(ICONS / 'bleach-backups.svg')))
        layout.addWidget(snapshot_button)
        layout.addSpacing(8)
        layout.addWidget(label('SAVED SNAPSHOTS', 'eyebrow'))
        self.snapshots = QComboBox()
        self.snapshots.currentIndexChanged.connect(self.snapshot_changed)
        layout.addWidget(self.snapshots)
        self.snapshot_details = label('', 'muted')
        layout.addWidget(self.snapshot_details)
        self.storage_summary = label('', 'notice')
        layout.addWidget(self.storage_summary)
        row = QHBoxLayout()
        self.verify_button = self.button('Verify', self.verify_snapshot)
        self.restore_button = self.button('Restore…', self.restore_snapshot)
        row.addWidget(self.verify_button)
        row.addWidget(self.restore_button)
        self.protect_button = self.button('Protect snapshot', self.toggle_protection)
        row.addWidget(self.protect_button)
        row.addWidget(self.button('Refresh', self.refresh_snapshots))
        layout.addLayout(row)
        layout.addSpacing(8)
        layout.addWidget(label('CLEAN UP OLDER COPIES', 'eyebrow'))
        cleanup = QHBoxLayout()
        cleanup.addWidget(label('Keep newest'))
        self.keep_count = QSpinBox()
        self.keep_count.setRange(1, 100)
        self.keep_count.setValue(5)
        cleanup.addWidget(self.keep_count)
        cleanup.addWidget(label('plus all protected snapshots'))
        cleanup.addStretch()
        self.cleanup_button = self.button('Preview cleanup…', self.preview_cleanup)
        cleanup.addWidget(self.cleanup_button)
        layout.addLayout(cleanup)
        layout.addStretch()
        layout.addWidget(label('After restoring, log out and back in. The system login screen has a separate restore command in the setup guide.', 'notice'))
        return page

    def tools_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(13)
        layout.addWidget(label('At your command', 'heading'))
        layout.addWidget(label('Portraits, favorites, greetings and system monitoring.', 'muted'))
        layout.addWidget(self.button('Terminal settings', lambda: self.launch_terminal('bankai-settings', 'Bankai settings'), True))
        terminal_button = self.button('Open Soul Society Terminal', lambda: self.launch_terminal())
        terminal_button.setIcon(QIcon(str(ICONS / 'bleach-terminal.svg')))
        layout.addWidget(terminal_button)
        monitor_button = self.button('Reiatsu Monitor', lambda: self.launch_terminal('bankai-monitor', 'Reiatsu Monitor'))
        monitor_button.setIcon(QIcon(str(ICONS / 'bleach-monitor.svg')))
        layout.addWidget(monitor_button)
        layout.addWidget(self.button('Check setup', lambda: self.run_task(
            [str(BIN / 'bankai-doctor')], 'Checking your setup…', 'Setup check complete. See activity for results.')))
        layout.addWidget(self.button('Browse artwork', self.browse_artwork))
        layout.addWidget(self.button('Login screen setup', self.login_setup))
        layout.addWidget(self.button('Setup & restore guide', lambda: self.open_file(DATA / 'README.md')))
        self.start_at_login = QCheckBox('Start Bankai in the tray at login')
        self.start_at_login.setChecked((HOME / '.config/autostart/bleach-bankai.desktop').exists())
        self.start_at_login.toggled.connect(self.set_autostart)
        layout.addWidget(self.start_at_login)
        layout.addStretch()
        return page

    def select_preset(self, name):
        self.selected = name
        self.cards[name].setChecked(True)
        self.art.select(name)
        title = PRESETS[name][0]
        self.preview_note.setText(f'Previewing {title}. Applying saves a snapshot first.')

    def refresh_state(self):
        name = saved_preset()
        pending = (HOME / '.local/state/bleach-desktop/pending').exists()
        self.saved.setText('SAVED PRESET\n' + PRESETS[name][0] + ('\nRefresh queued for login' if pending else ''))
        self.refresh_snapshots()
        self.refresh_tray()

    def refresh_snapshots(self):
        try:
            rows = self.store.scan()
        except (OSError, ValueError, TypeError) as error:
            if isinstance(error, BlockingIOError):
                self.storage_summary.setText('Another Bankai operation is updating snapshots. Refreshing shortly…')
                self.cleanup_button.setEnabled(False)
                QTimer.singleShot(1000, self.refresh_snapshots)
                return
            rows = None
            self.snapshot_rows = {}
            self.storage_summary.setText('Could not read snapshot storage: ' + str(error))
            self.cleanup_button.setEnabled(False)

        selected = self.snapshots.currentData()
        self.snapshots.blockSignals(True)
        self.snapshots.clear()
        if rows is not None:
            self.snapshot_rows = {row['name']: row for row in rows}
            self.storage_summary.setText(f'{len(rows)} snapshots · {format_size(sum(r["bytes"] for r in rows))} stored · '
                                         f'{sum(r["protected"] for r in rows)} protected')
            self.cleanup_button.setEnabled(self.process is None)
            for row in rows:
                name = row['name']
                try:
                    stamp = datetime.strptime(name, '%Y%m%d-%H%M%S-%f')
                    title = stamp.strftime('%b %d, %Y  ·  %I:%M:%S %p') + '  ·  ' + str(stamp.microsecond).zfill(6)
                except ValueError:
                    title = name
                title += ' · ' + (format_size(row['bytes']) if row['eligible'] else 'needs review')
                if row['protected']:
                    title += ' · ' + ('Baseline' if row['baseline'] else '★ Protected')
                self.snapshots.addItem(title, name)
        index = self.snapshots.findData(selected)
        if index >= 0:
            self.snapshots.setCurrentIndex(index)
        self.snapshots.blockSignals(False)
        self.snapshot_changed()

    def snapshot_changed(self, index=None):
        name = self.snapshots.currentData()
        available = bool(name)
        for button in (self.verify_button, self.restore_button, self.protect_button):
            button.setEnabled(available and self.process is None)
        if not name:
            self.snapshot_details.setText('No snapshots yet. Create one to save your setup.')
            return
        row = self.snapshot_rows.get(name, {})
        self.protect_button.setText('Remove protection' if row.get('protected') else 'Protect snapshot')
        self.protect_button.setEnabled(available and not row.get('baseline', False) and self.process is None)
        try:
            manifest = json.loads((SNAPSHOTS / name / 'manifest.json').read_text())
            files = manifest['files']
            if not isinstance(files, list):
                raise ValueError('Invalid file list')
            self.snapshot_details.setText(f'{len(files)} saved files · Integrity will be checked before restore.')
        except (OSError, ValueError, TypeError, KeyError):
            self.snapshot_details.setText('This snapshot could not be read. Verify it for details.')

    def toggle_protection(self):
        name = self.snapshots.currentData()
        row = self.snapshot_rows.get(name)
        if not row:
            return
        try:
            enabled = not row['protected']
            self.store.protect(name, enabled)
            self.refresh_snapshots()
            self.message.setText('Snapshot protected from cleanup.' if enabled else 'Snapshot protection removed.')
        except (OSError, ValueError, TypeError) as error:
            message = ('Another snapshot operation is running. Try again shortly.'
                       if isinstance(error, BlockingIOError) else str(error))
            self.message.setText('Could not update protection: ' + message)

    def preview_cleanup(self):
        try:
            plan = self.store.plan(self.keep_count.value())
            if not plan['candidates']:
                self.message.setText('No older snapshots to remove. Recent and protected copies are kept.')
                return
            if self.confirm_cleanup(plan):
                self.run_task([sys.executable, str(DATA / 'snapshot_manager.py'), 'cleanup', '--plan', json.dumps(plan)],
                              'Removing the reviewed snapshots…', 'Older snapshots removed.')
        except (OSError, ValueError, TypeError) as error:
            message = ('Another snapshot operation is running. Try again shortly.'
                       if isinstance(error, BlockingIOError) else str(error))
            self.message.setText('Cleanup could not be prepared: ' + message)

    def confirm_cleanup(self, plan):
        dialog = QMessageBox(self)
        dialog.setWindowTitle('Review snapshot cleanup')
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setText(f'Permanently remove {len(plan["candidates"])} older snapshots ({format_size(plan["bytes"])})?')
        names = '\n'.join(row['name'] + ' · ' + format_size(row['bytes']) for row in plan['candidates'])
        dialog.setInformativeText(f'The newest {plan["keep"]} usable snapshots, the original baseline, and all protected copies are kept.\n\n'
                                  + (names if len(plan['candidates']) <= 8 else 'Expand details to see every snapshot in this plan.'))
        dialog.setDetailedText(names)
        cancel = dialog.addButton(QMessageBox.StandardButton.Cancel)
        remove = dialog.addButton('Delete reviewed snapshots', QMessageBox.ButtonRole.DestructiveRole)
        dialog.setDefaultButton(cancel)
        dialog.exec()
        return dialog.clickedButton() == remove

    def set_autostart(self, enabled):
        path = HOME / '.config/autostart/bleach-bankai.desktop'
        try:
            if enabled:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('[Desktop Entry]\nType=Application\nName=Bankai tray menu\n'
                                f'Exec={BIN / "bankai-python"} tray\nOnlyShowIn=KDE;\nNoDisplay=true\nX-KDE-autostart-phase=2\n')
            else:
                path.unlink(missing_ok=True)
            self.message.setText('Bankai will start in the tray at login.' if enabled else 'Bankai login startup disabled.')
        except OSError as error:
            self.start_at_login.blockSignals(True)
            self.start_at_login.setChecked(not enabled)
            self.start_at_login.blockSignals(False)
            self.message.setText('Could not change login startup: ' + str(error))

    def apply_preset(self):
        name = self.selected
        self.run_task([str(BIN / 'bankai-desktop'), name], 'Applying ' + PRESETS[name][0] + '…',
                      'Preset saved. Open a new terminal for the matching greeting.')

    def refresh_custom_presets(self):
        selected = self.custom_combo.currentData()
        try: self.custom_rows = appearance_settings.custom_presets(HOME)
        except (OSError, ValueError, TypeError) as error:
            self.custom_rows = []
            if hasattr(self, 'message'): self.message.setText('Could not read saved presets: ' + str(error))
        self.custom_combo.blockSignals(True)
        self.custom_combo.clear()
        for row in self.custom_rows: self.custom_combo.addItem(row['name'], row['id'])
        selected_index = self.custom_combo.findData(selected)
        if selected_index >= 0: self.custom_combo.setCurrentIndex(selected_index)
        self.custom_combo.blockSignals(False)
        available = bool(self.custom_rows)
        self.custom_apply_button.setEnabled(available)
        self.custom_delete_button.setEnabled(available)

    def save_custom_preset(self):
        name, accepted = QInputDialog.getText(self, 'Save custom preset', 'Preset name (1–40 characters):')
        if not accepted: return
        try:
            appearance_settings.save_custom_preset(HOME, name, self.selected, appearance())
            self.refresh_custom_presets()
            self.custom_combo.setCurrentIndex(self.custom_combo.count() - 1)
            self.message.setText('Saved current wallpaper, accent, and login-scene choices.')
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.information(self, 'Save custom preset', str(error))

    def preview_custom_preset(self, index):
        if index < 0 or index >= len(self.custom_rows): return
        row = self.custom_rows[index]
        self.select_preset(row['preset'])
        self.message.setText(f"Previewing saved combination ‘{row['name']}’. Apply when ready.")

    def apply_custom_preset(self):
        identifier = self.custom_combo.currentData()
        row = next((row for row in self.custom_rows if row['id'] == identifier), None)
        if not row: return
        self.run_task([str(BIN / 'bankai-desktop'), 'apply-custom', identifier],
                      'Applying ' + row['name'] + '…', 'Custom preset applied.')

    def delete_custom_preset(self):
        identifier = self.custom_combo.currentData()
        if not identifier: return
        try:
            appearance_settings.delete_custom_preset(HOME, identifier)
            self.refresh_custom_presets()
            self.message.setText('Saved preset deleted.')
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.information(self, 'Delete custom preset', str(error))

    def verify_snapshot(self):
        name = self.snapshots.currentData()
        if name:
            self.run_task([str(BIN / 'bankai-desktop-backup'), 'verify', name],
                          'Verifying snapshot…', 'Snapshot integrity verified.')

    def restore_snapshot(self):
        name = self.snapshots.currentData()
        if not name:
            return
        if self.confirm_restore():
            self.run_task([str(BIN / 'bankai-desktop-backup'), 'restore', name],
                          'Checking and restoring snapshot…', 'Snapshot restored. Log out and back in to reload KDE.')

    def confirm_restore(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle('Restore this snapshot?')
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setText('Restore the desktop and terminal from ' + self.snapshots.currentText() + '?')
        dialog.setInformativeText('Your current settings will be saved first. Log out and back in afterward.\n\n'
                                  'The system login screen is managed separately.')
        cancel = dialog.addButton(QMessageBox.StandardButton.Cancel)
        restore = dialog.addButton('Restore snapshot', QMessageBox.ButtonRole.AcceptRole)
        dialog.setDefaultButton(cancel)
        dialog.exec()
        return dialog.clickedButton() == restore

    def run_task(self, command, progress, success):
        if self.process is not None:
            return
        self.output = ''
        self.log.clear()
        self.message.setText(progress)
        for button in self.action_buttons:
            button.setEnabled(False)
        self.snapshots.setEnabled(False)
        self.keep_count.setEnabled(False)
        for action in self.tray_actions:
            action.setEnabled(False)
        for card in self.cards.values():
            card.setEnabled(False)
        process = QProcess(self)
        self.process = process
        self.process_callback = success
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self.read_output)
        process.finished.connect(self.task_finished)
        process.errorOccurred.connect(self.task_error)
        process.start(command[0], command[1:])
        self.timeout.start(120000)

    def read_output(self):
        if self.process is not None:
            text = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
            self.output = (self.output + text)[-65536:]
            self.log.setPlainText(self.output)
            bar = self.log.verticalScrollBar()
            bar.setValue(bar.maximum())

    def task_finished(self, code, status):
        if self.process is None:
            return
        self.read_output()
        process = self.process
        self.process = None
        self.timeout.stop()
        success = code == 0 and status == QProcess.ExitStatus.NormalExit
        if success:
            pending = (HOME / '.local/state/bleach-desktop/pending').exists()
            self.message.setText(self.process_callback + (' Desktop refresh is queued for your next KDE login.'
                if pending and process.program().endswith('/bankai-desktop') else ''))
        else:
            self.message.setText('The action did not finish successfully. Your activity log has the details.')
            self.log.show()
            self.details_button.setText('Hide activity')
        for button in self.action_buttons:
            button.setEnabled(True)
        self.snapshots.setEnabled(True)
        self.keep_count.setEnabled(True)
        for action in self.tray_actions:
            action.setEnabled(True)
        for card in self.cards.values():
            card.setEnabled(True)
        self.refresh_state()
        if self.tray is not None and self.tray.isVisible() and not self.isVisible():
            self.tray.showMessage('Bankai', self.message.text(), QSystemTrayIcon.MessageIcon.Information if success else QSystemTrayIcon.MessageIcon.Warning)
        process.deleteLater()

    def task_error(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.process is not None:
            self.output = self.process.errorString()
            self.log.setPlainText(self.output)
            self.task_finished(-1, QProcess.ExitStatus.CrashExit)

    def operation_timeout(self):
        if self.process is not None:
            # Do not kill a restore midway through replacing files.
            self.message.setText('This is taking longer than expected. The action is still running; see activity for progress.')
            self.log.show()
            self.details_button.setText('Hide activity')

    def launch_terminal(self, function=None, title=None):
        args = ['--class', 'bleach-monitor' if function == 'bankai-monitor' else 'bleach-terminal']
        if title:
            args += ['--title', title]
        if function:
            args += ['/usr/bin/fish', '-c', function]
        success, _ = QProcess.startDetached('/usr/bin/kitty', args)
        self.message.setText('Opened ' + (title or 'Soul Society Terminal') + '.' if success else 'Could not start Kitty.')

    def open_file(self, path):
        if not path.exists():
            self.message.setText('This file could not be found: ' + path.name)
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self.message.setText('Could not open ' + path.name + '.')

    def open_wallpaper(self):
        self.open_file(wallpaper(self.selected))

    def browse_artwork(self):
        gallery = HOME / '.config/fastfetch/previews/manga-roster.html'
        self.open_file(gallery if gallery.exists() else WALLPAPERS)

    def appearance_options(self):
        try: options = appearance_settings.load(HOME)
        except (OSError, ValueError, TypeError) as error:
            answer = QMessageBox.question(self, 'Appearance options',
                'Saved appearance settings could not be loaded. Restore defaults and preserve a backup of this file?\n\n' + str(error),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                try: result = appearance_settings.repair(HOME)
                except (OSError, ValueError, TypeError) as repair_error:
                    QMessageBox.information(self, 'Appearance options', str(repair_error))
                else: self.message.setText(result['message'])
            return
        dialog = QDialog(self); dialog.setWindowTitle('Appearance options')
        layout = QVBoxLayout(dialog); form = QFormLayout(); layout.addLayout(form)
        edition = QComboBox(); edition.addItem('Color', 'color'); edition.addItem('Manga', 'manga')
        edition.setCurrentIndex(max(0, edition.findData(options['edition'])))
        form.addRow('Desktop and lock screen', edition)
        accent = QLineEdit(options['accent']); accent.setPlaceholderText('Use character accent')
        form.addRow('Accent override (#RRGGBB)', accent)
        choose = QPushButton('Choose accent color')
        def choose_color():
            color = QColorDialog.getColor(QColor(accent.text() or PRESETS[self.selected][2]), dialog)
            if color.isValid(): accent.setText(color.name())
        choose.clicked.connect(choose_color); layout.addWidget(choose)
        login = QComboBox(); login.addItem('Follow background character', 'follow')
        for name, row in PRESETS.items(): login.addItem(row[0] + ' (fixed manga scene)', name)
        login.setCurrentIndex(max(0, login.findData(options['login'])))
        form.addRow('Login scene', login)
        shuffle = QCheckBox('Choose a different background when Bankai starts at login')
        shuffle.setChecked(options['shuffle_login']); layout.addWidget(shuffle)
        layout.addWidget(label('Shuffle pool (choose at least one):', 'muted'))
        pool = QListWidget(); pool.setMaximumHeight(190)
        for name, row in PRESETS.items():
            item = QListWidgetItem(row[0]); item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in options['pool'] else Qt.CheckState.Unchecked)
            pool.addItem(item)
        layout.addWidget(pool)
        layout.addWidget(label('Save options, then Apply a background for wallpaper and accent changes. Login choice syncs after one-time system setup. Enable only one Bankai edition at login for shuffle.', 'muted'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons); buttons.rejected.connect(dialog.reject)
        def save():
            value = dict(edition=edition.currentData(), accent=accent.text().strip(), login=login.currentData(),
                         shuffle_login=shuffle.isChecked(), pool=[pool.item(i).data(Qt.ItemDataRole.UserRole) for i in range(pool.count()) if pool.item(i).checkState() == Qt.CheckState.Checked])
            try: appearance_settings.save(HOME, value, expected=options)
            except (OSError, ValueError) as error:
                QMessageBox.information(dialog, 'Appearance options', str(error)); return
            self.select_preset(self.selected)
            self.message.setText('Appearance saved. Apply a background to update wallpaper and accents.')
            dialog.accept()
        buttons.accepted.connect(save); dialog.exec()

    def login_setup(self):
        installer = DATA / 'install-login.py'
        theme = DATA / 'login-theme'
        if not installer.is_file() or not (theme / 'Main.qml').is_file():
            QMessageBox.information(self, 'Login screen', 'Update this Bankai edition with its installer to add the manga login theme.')
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle('Manga login screen')
        install = 'sudo python3 ~/.local/share/bleach-desktop/install-login.py install'
        restore = 'sudo python3 ~/.local/share/bleach-desktop/install-login.py restore'
        dialog.setText('Manga login scene follows your desktop character')
        dialog.setInformativeText('Preview without logging out. To activate or update, run:\n' + install +
                                  '\n\nTo restore the previous theme:\n' + restore +
                                  '\n\nOne-time administrator setup enables automatic matching for your account. Changes appear at the next login screen.')
        dialog.setStandardButtons(QMessageBox.StandardButton.Close)
        preview = dialog.addButton('Preview', QMessageBox.ButtonRole.ActionRole)
        preview.clicked.connect(lambda: self.preview_login(theme))
        copy = dialog.addButton('Copy install command', QMessageBox.ButtonRole.ActionRole)
        copy.clicked.connect(lambda: QApplication.clipboard().setText(install))
        undo = dialog.addButton('Copy restore command', QMessageBox.ButtonRole.ActionRole)
        undo.clicked.connect(lambda: QApplication.clipboard().setText(restore))
        dialog.exec()

    def preview_login(self, theme):
        if not shutil.which('sddm-greeter-qt6'):
            QMessageBox.information(self, 'Login preview', 'Install SDDM with Qt 6 to preview this theme.')
            return
        success, _ = QProcess.startDetached(sys.executable, [str(DATA / 'preview-login.py')])
        if not success:
            QMessageBox.information(self, 'Login preview', 'Could not start sddm-greeter-qt6. Install SDDM with Qt 6 to preview this theme.')

    def toggle_output(self):
        self.log.setVisible(not self.log.isVisible())
        self.details_button.setText('Hide activity' if self.log.isVisible() else 'Show activity')

    def closeEvent(self, event):
        if self.process is not None:
            self.message.setText('Let the current action finish before closing Bankai.')
            event.ignore()
        elif self.tray is not None and self.tray.isVisible() and not self.quitting:
            self.hide()
            event.ignore()
        else:
            event.accept()


class InstanceCoordinator(QObject):
    """Route a second launch to the existing window without a second tray icon."""
    def __init__(self, state):
        super().__init__()
        reject_symlinks(state)
        state.mkdir(parents=True, exist_ok=True)
        self.state_path = state
        self.socket_path = state / 'bankai-control.sock'
        self.lock_path = state / 'bankai-control.lock'
        reject_symlinks(state)
        reject_symlinks(self.socket_path)
        reject_symlinks(self.lock_path)
        self.socket_name = str(self.socket_path)
        self.lock = QLockFile(str(self.lock_path))
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.callback = None
        self.server.newConnection.connect(self.accept_connection)

    def forward(self, message):
        socket = QLocalSocket()
        socket.connectToServer(self.socket_name)
        if not socket.waitForConnected(400):
            return False
        socket.write((message + '\n').encode())
        socket.waitForBytesWritten(400)
        socket.disconnectFromServer()
        return True

    def start(self):
        reject_symlinks(self.state_path)
        reject_symlinks(self.socket_path)
        reject_symlinks(self.lock_path)
        if not self.lock.tryLock(0):
            return False
        QLocalServer.removeServer(self.socket_name)
        if not self.server.listen(self.socket_name):
            self.lock.unlock()
            raise OSError(self.server.errorString())
        return True

    def accept_connection(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.setProperty('message', b'')
            socket.readyRead.connect(self.read_pending_message)
            socket.disconnected.connect(socket.deleteLater)
            self.read_message(socket)

    @Slot()
    def read_pending_message(self):
        socket = self.sender()
        if isinstance(socket, QLocalSocket):
            self.read_message(socket)

    def read_message(self, socket):
        data = bytes(socket.property('message') or b'') + bytes(socket.readAll())
        if len(data) > 128:
            socket.abort()
            return
        if b'\n' in data:
            message = data.split(b'\n', 1)[0].decode('ascii', errors='ignore')
            if message in ('open', 'backups', 'tray') and self.callback is not None:
                self.callback(message)
            socket.disconnectFromServer()
        else:
            socket.setProperty('message', data)

    def close(self):
        self.server.close()
        self.lock.unlock()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tray', action='store_true', help='Start in the system tray')
    parser.add_argument('--backups', action='store_true', help='Open backup management')
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    app.setApplicationName('Bankai')
    app.setDesktopFileName('bleach-bankai')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    coordinator = InstanceCoordinator(HOME / '.local/state/bleach-desktop')
    message = 'backups' if args.backups else ('tray' if args.tray else 'open')
    if coordinator.forward(message):
        return 0
    try:
        started = coordinator.start()
    except OSError as error:
        QMessageBox.warning(None, 'Bankai could not start', str(error))
        return 1
    if not started:
        QMessageBox.information(None, 'Bankai is already starting', 'Open Bankai from its tray icon in a moment.')
        return 0
    try:
        window = ControlCenter()
        coordinator.callback = lambda request: window.show_window(backups=request == 'backups') if request != 'tray' else None
        available = QSystemTrayIcon.isSystemTrayAvailable()
        if available:
            window.setup_tray()
            app.setQuitOnLastWindowClosed(False)
        elif args.tray:
            # Plasma's tray can appear after login autostart. Qt registers the
            # visible icon when the tray service becomes available.
            window.setup_tray()
            app.setQuitOnLastWindowClosed(False)
            def check_tray():
                if not QSystemTrayIcon.isSystemTrayAvailable():
                    window.tray.hide()
                    app.setQuitOnLastWindowClosed(True)
                    window.show_window()
                    window.message.setText('The system tray is unavailable, so Bankai opened its window instead.')
            QTimer.singleShot(10000, check_tray)
        if args.tray and appearance()['shuffle_login']:
            window.run_task([str(BIN / 'bankai-desktop'), 'shuffle-login'], 'Choosing a login background…', 'Login background selected.')
        if not args.tray:
            window.show_window(backups=args.backups)
        return app.exec()
    finally:
        coordinator.close()


if __name__ == '__main__':
    sys.exit(main())
