import sys
import os
import json
import subprocess
import threading
from datetime import datetime

from PyQt5.QtCore import Qt, QUrl, QTimer, QPropertyAnimation, QRect, pyqtProperty, QSize, QDateTime, QEvent
from PyQt5.QtGui import QIcon, QFont, QColor, QPainter, QPalette, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QToolBar, QLineEdit,
    QAction, QVBoxLayout, QWidget, QStatusBar, QPushButton, QMenu,
    QMessageBox, QInputDialog, QListWidget, QDialog, QHBoxLayout,
    QLabel, QProgressBar, QFormLayout, QComboBox, QFileDialog,
    QCheckBox, QDialogButtonBox, QGroupBox, QTabWidget as QTabDialog,
    QFrame, QSizePolicy, QHeaderView, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QListWidgetItem, QScrollArea, QSpinBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebEngineWidgets import QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QStandardPaths
from PyQt5.QtNetwork import QNetworkReply

ABOUT_TEXT = """2.3 version
                SNAKE all """

MPDEFENDER = os.path.join(
    os.environ.get("ProgramData", "C:\\ProgramData"),
    "Microsoft", "Windows Defender", "Platform"
)


def find_defender():
    if not os.path.isdir(MPDEFENDER):
        return None
    dirs = [d for d in os.listdir(MPDEFENDER) if d.startswith("4.")]
    if not dirs:
        return None
    latest = sorted(dirs)[-1]
    exe = os.path.join(MPDEFENDER, latest, "MpCmdRun.exe")
    return exe if os.path.exists(exe) else None


def scan_file(filepath):
    exe = find_defender()
    if not exe:
        return "unknown"
    try:
        r = subprocess.run(
            [exe, "-Scan", "-ScanType", "3", "-File", filepath],
            capture_output=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW
        )
        if r.returncode == 0:
            return "clean"
        elif r.returncode == 2:
            return "threat"
        else:
            return "error"
    except Exception:
        return "error"


CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SEARCH_ENGINES = {
    "Google": "https://www.google.com/search?q={}",
    "Yandex": "https://yandex.ru/search/?text={}",
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
    "Bing": "https://www.bing.com/search?q={}",
}

SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "settings.json"
)

DEFAULT_SETTINGS = {
    "home_url": "https://www.google.com",
    "search_engine": "Google",
    "download_dir": "",
    "js_enabled": True,
    "user_agent": CHROME_UA,
    "open_tabs": [],
    "night_mode": False,
    "permissions": {},
    "default_zoom": 100,
    "auto_images": True,
    "show_bookmarks_bar": True,
    "confirm_close": True,
    "tab_position": "top",
    "new_tab_page": "home",
    "block_popups": True,
    "cookie_policy": "allow",
    "font_size": 16,
    "smooth_scroll": True,
    "spell_check": False,
    "show_home_button": True,
    "show_nav_buttons": True,
    "double_click_close": False,
    "minimum_font_size": 0,
    "caret_browsing": False,
    "dns_prefetch": True,
    "local_storage": True,
    "webgl": True,
    "download_sound": False,
    "session_restore": True,
    "show_status_bar": True,
    "mouse_wheel_tabs": True,
    "open_in_new_tab": True,
    "show_full_url": True,
}

NEWTAB_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "newtab.html"
).replace("\\", "/")

NEWTAB_URL = f"file:///{NEWTAB_FILE}"

DOWNLOADS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "downloads.json"
)

BOOKMARKS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bookmarks.json"
)

HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "history.json"
)

MAX_HISTORY = 5000


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
                return {**DEFAULT_SETTINGS, **s}
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def load_downloads():
    if os.path.exists(DOWNLOADS_FILE):
        try:
            with open(DOWNLOADS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def load_bookmarks():
    if os.path.exists(BOOKMARKS_FILE):
        try:
            with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_bookmarks(bookmarks):
    with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, indent=2, ensure_ascii=False)


def save_downloads(entries):
    data = [
        {
            "path": e.path,
            "name": e.name,
            "received": e.received,
            "total": e.total,
            "status": e.status,
            "scan_status": e.scan_status,
        }
        for e in entries
        if e.status in ("complete", "cancelled", "interrupted", "paused")
    ]
    with open(DOWNLOADS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(entries):
    entries = entries[-MAX_HISTORY:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def configure_profile(profile, settings=None):
    if settings is None:
        settings = load_settings()
    profile.setHttpUserAgent(settings.get("user_agent", CHROME_UA))
    s = profile.settings()
    s.setAttribute(QWebEngineSettings.JavascriptEnabled, settings.get("js_enabled", True))
    s.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, not settings.get("block_popups", True))
    s.setAttribute(QWebEngineSettings.LocalStorageEnabled, settings.get("local_storage", True))
    s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
    s.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
    s.setAttribute(QWebEngineSettings.WebGLEnabled, settings.get("webgl", True))
    s.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
    s.setAttribute(QWebEngineSettings.AutoLoadImages, settings.get("auto_images", True))
    s.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
    s.setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, False)
    s.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, settings.get("smooth_scroll", True))
    s.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, settings.get("dns_prefetch", True))
    s.setFontSize(QWebEngineSettings.DefaultFontSize, settings.get("font_size", 16))
    s.setFontSize(QWebEngineSettings.MinimumFontSize, settings.get("minimum_font_size", 0))
    profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
    policy = settings.get("cookie_policy", "allow")
    if policy == "allow":
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
    else:
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
    profile.setSpellCheckEnabled(settings.get("spell_check", False))


class AnimatedProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 18)
        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self):
        self._offset = (self._offset + 0.02) % 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h // 2

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#3c3c3c"))
        p.drawRoundedRect(0, 0, w, h, r, r)

        colors = ["#4a9eff", "#6cb4ff", "#4a9eff"]
        bar_w = w - 4
        bar_h = h - 4
        seg_count = 3
        seg_w = bar_w / seg_count

        for i in range(seg_count):
            pos = (self._offset + i / seg_count) % 1.0
            x = 2 + pos * (bar_w - seg_w)
            alpha = int(255 * (1 - abs(pos - 0.5) * 2))
            alpha = max(60, min(255, alpha))
            color = QColor(colors[i % len(colors)])
            color.setAlpha(alpha)
            p.setBrush(color)
            p.drawRoundedRect(int(x), 2, int(seg_w - 2), bar_h, bar_h // 2, bar_h // 2)

        p.end()

    def setValue(self, value):
        pass


class DownloadEntry:
    def __init__(self, download, path, on_threat=None):
        self.download = download
        self.path = path
        self.name = os.path.basename(path)
        self.received = 0
        self.total = 0
        self.speed = 0
        self.status = "downloading"
        self.scan_status = None
        self._on_threat = on_threat
        self.start_time = QDateTime.currentDateTime()
        self._prev_received = 0
        self._prev_time = self.start_time

    def update_progress(self, received, total):
        now = QDateTime.currentDateTime()
        dt = self._prev_time.msecsTo(now) / 1000.0
        if dt > 0.5:
            self.speed = (received - self._prev_received) / dt if dt > 0 else 0
            self._prev_received = received
            self._prev_time = now
        self.received = received
        self.total = total
        if total > 0 and received >= total:
            self.status = "complete"
            self.start_scan()

    def start_scan(self):
        self.scan_status = "scanning"
        t = threading.Thread(target=self._do_scan, daemon=True)
        t.start()

    def _do_scan(self):
        result = scan_file(self.path)
        self.scan_status = result
        if result == "threat" and self._on_threat:
            QTimer.singleShot(0, self._on_threat)

    def cancel(self):
        if self.download:
            self.download.cancel()
        self.status = "cancelled"

    def pause(self):
        if self.download:
            self.download.pause()
        self.status = "paused"

    def resume(self):
        if self.download:
            self.download.resume()
        self.status = "downloading"

    def size_str(self):
        def fmt(sz):
            for unit in ["B", "KB", "MB", "GB"]:
                if sz < 1024:
                    return f"{sz:.1f} {unit}"
                sz /= 1024
            return f"{sz:.1f} TB"
        if self.total > 0:
            return f"{fmt(self.received)} / {fmt(self.total)}"
        return fmt(self.received)

    def speed_str(self):
        for unit in ["B/s", "KB/s", "MB/s"]:
            if self.speed < 1024:
                return f"{self.speed:.1f} {unit}"
            self.speed /= 1024
        return f"{self.speed:.1f} GB/s"

    def percent(self):
        return int(self.received / self.total * 100) if self.total > 0 else 0

    def scan_label(self):
        labels = {
            "clean": "🛡 Чисто",
            "threat": "⚠ Угроза!",
            "scanning": "🔍 Сканирование...",
            "unknown": "🛡 Не проверен",
            "error": "❌ Ошибка сканирования",
        }
        return labels.get(self.scan_status, "")


class DownloadManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Менеджер загрузок")
        self.setMinimumSize(680, 400)
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; color: #fff; }
            QLabel { color: #ccc; }
            QPushButton {
                background: #3c3c3c; color: #fff; border: none;
                border-radius: 4px; padding: 6px 14px;
            }
            QPushButton:hover { background: #505050; }
            QPushButton#danger { background: #5a2c2c; color: #ff6b6b; }
            QPushButton#danger:hover { background: #7a3c3c; }
            QTableWidget { background: #1e1e1e; color: #fff; border: 1px solid #3c3c3c;
                gridline-color: #2b2b2b; }
            QHeaderView::section { background: #3c3c3c; color: #aaa; padding: 6px;
                border: none; }
        """)
        self.entries = []
        self.setup_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_table)
        self._timer.start(1000)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Загрузки")
        header.setStyleSheet("font-size: 18px; color: #fff; padding: 4px 0;")
        layout.addWidget(header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Файл", "Размер", "Скорость", "Прогресс", "Статус", "Антивирус"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        clear_btn = QPushButton("Очистить завершённые")
        clear_btn.clicked.connect(self.clear_finished)
        btn_layout.addWidget(clear_btn)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def add_entry(self, entry):
        if entry not in self.entries:
            self.entries.append(entry)
        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        for entry in self.entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QTableWidgetItem(entry.name)
            name_item.setToolTip(entry.path)
            self.table.setItem(row, 0, name_item)

            self.table.setItem(row, 1, QTableWidgetItem(entry.size_str()))

            self.table.setItem(row, 2, QTableWidgetItem(
                entry.speed_str() if entry.status == "downloading" else "—"
            ))

            prog = QProgressBar()
            prog.setMinimumHeight(18)
            prog.setValue(entry.percent())
            prog.setStyleSheet("""
                QProgressBar { background: #3c3c3c; border: none; border-radius: 3px;
                    text-align: center; color: #fff; font-size: 11px; }
                QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4a9eff, stop:1 #6cb4ff); border-radius: 3px; }
            """)
            self.table.setCellWidget(row, 3, prog)

            status_map = {
                "downloading": "⬇ Загружается",
                "complete": "✅ Завершено",
                "cancelled": "❌ Отменено",
                "paused": "⏸ На паузе",
                "interrupted": "⚠ Прервано",
            }
            self.table.setItem(row, 4, QTableWidgetItem(
                status_map.get(entry.status, entry.status)
            ))

            scan_item = QTableWidgetItem(entry.scan_label() if entry.scan_status else "")
            scan_item.setTextAlignment(Qt.AlignCenter)
            if entry.scan_status == "threat":
                scan_item.setForeground(QColor("#ff6b6b"))
                scan_item.setToolTip("Windows Defender обнаружил угрозу")
            elif entry.scan_status == "clean":
                scan_item.setForeground(QColor("#6bff6b"))
            elif entry.scan_status == "scanning":
                scan_item.setForeground(QColor("#ffcc00"))
            self.table.setItem(row, 5, scan_item)

            self.table.setRowHeight(row, 36)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        if row < 0 or row >= len(self.entries):
            return
        entry = self.entries[row]

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background: #2b2b2b; color: #fff; border: 1px solid #3c3c3c; }
            QMenu::item:selected { background: #4a9eff; }
        """)

        if entry.status == "complete":
            menu.addAction("📂 Открыть файл", lambda: self.open_file(entry))
            menu.addAction("📁 Открыть папку", lambda: self.open_folder(entry))
            menu.addSeparator()
            menu.addAction("🗑 Удалить из списка", lambda: self.remove_entry(row))
        elif entry.status == "downloading":
            menu.addAction("⏸ Пауза", lambda: entry.pause())
            menu.addAction("✕ Отменить", lambda: entry.cancel())
        elif entry.status == "paused":
            menu.addAction("▶ Возобновить", lambda: entry.resume())
            menu.addAction("✕ Отменить", lambda: entry.cancel())
        else:
            menu.addAction("🗑 Удалить из списка", lambda: self.remove_entry(row))

        menu.exec_(self.table.mapToGlobal(pos))

    def open_file(self, entry):
        if os.path.exists(entry.path):
            os.startfile(entry.path)

    def open_folder(self, entry):
        folder = os.path.dirname(entry.path)
        if os.path.exists(folder):
            os.startfile(folder)

    def remove_entry(self, row):
        if 0 <= row < len(self.entries):
            self.entries.pop(row)
            self.refresh_table()

    def clear_finished(self):
        self.entries = [e for e in self.entries if e.status not in ("complete", "cancelled", "interrupted")]
        self.refresh_table()


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = dict(settings)
        self.setWindowTitle("Настройки")
        self.setMinimumSize(500, 400)
        self.resize(520, 440)
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; color: #fff; }
            QGroupBox { color: #fff; border: 1px solid #3c3c3c;
                border-radius: 4px; margin-top: 8px; padding-top: 16px; }
            QGroupBox::title { color: #4a9eff; }
            QLabel { color: #ccc; }
            QLineEdit, QComboBox {
                background: #1e1e1e; color: #fff; border: 1px solid #3c3c3c;
                border-radius: 3px; padding: 4px 8px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; border: none; }
            QComboBox QAbstractItemView {
                background: #1e1e1e; color: #fff; selection-background-color: #4a9eff;
            }
            QCheckBox { color: #ccc; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px;
                border: 1px solid #3c3c3c; background: #1e1e1e; }
            QCheckBox::indicator:checked { background: #4a9eff; }
            QPushButton {
                background: #3c3c3c; color: #fff; border: none;
                border-radius: 4px; padding: 6px 16px;
            }
            QPushButton:hover { background: #505050; }
            QPushButton#danger { background: #5a2c2c; color: #ff6b6b; }
            QPushButton#danger:hover { background: #7a3c3c; }
        """)

        tabs = QTabDialog()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3c3c3c; background: #2b2b2b; }
            QTabBar::tab { background: #3c3c3c; color: #aaa; padding: 6px 14px;
                border: none; }
            QTabBar::tab:selected { background: #1e1e1e; color: #fff; }
        """)

        tabs.addTab(self._general_tab(), "Основные")
        tabs.addTab(self._ui_tab(), "Интерфейс")
        tabs.addTab(self._advanced_tab(), "Дополнительно")
        tabs.addTab(self._permissions_tab(), "Разрешения")
        tabs.addTab(self._privacy_tab(), "Приватность")
        tabs.addTab(self._about_tab(), "О программе")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("QPushButton { min-width: 80px; }")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _general_tab(self):
        w = QWidget()
        w.setStyleSheet("background: #2b2b2b; color: #ccc;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(w)
        scroll.setStyleSheet("QScrollArea { border: none; background: #2b2b2b; } QScrollArea > QWidget > QWidget { background: #2b2b2b; } QScrollBar:vertical { background: #2b2b2b; width: 10px; } QScrollBar::handle:vertical { background: #3c3c3c; border-radius: 4px; min-height: 20px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }")
        layout = QFormLayout(w)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self.home_input = QLineEdit(self.settings["home_url"])
        layout.addRow("Домашняя страница:", self.home_input)

        self.search_combo = QComboBox()
        self.search_combo.addItems(list(SEARCH_ENGINES.keys()))
        self.search_combo.setCurrentText(self.settings["search_engine"])
        layout.addRow("Поисковая система:", self.search_combo)

        dl_group = QGroupBox("Загрузки")
        dl_layout = QHBoxLayout(dl_group)
        self.dl_input = QLineEdit(self.settings.get("download_dir", ""))
        self.dl_input.setPlaceholderText("Папка по умолчанию")
        dl_browse = QPushButton("...")
        dl_browse.setFixedWidth(30)
        dl_browse.clicked.connect(self._browse_dl)
        dl_layout.addWidget(self.dl_input)
        dl_layout.addWidget(dl_browse)
        layout.addRow(dl_group)

        self.js_check = QCheckBox("Включить JavaScript")
        self.js_check.setChecked(self.settings.get("js_enabled", True))
        layout.addRow("", self.js_check)

        self.images_check = QCheckBox("Загружать изображения")
        self.images_check.setChecked(self.settings.get("auto_images", True))
        layout.addRow("", self.images_check)

        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(25, 300)
        self.zoom_spin.setSuffix("%")
        self.zoom_spin.setValue(self.settings.get("default_zoom", 100))
        self.zoom_spin.setStyleSheet("background: #1e1e1e; color: #fff; border: 1px solid #3c3c3c; border-radius: 3px; padding: 4px;")
        layout.addRow("Масштаб:", self.zoom_spin)

        self.tab_pos = QComboBox()
        self.tab_pos.addItems(["Сверху", "Снизу"])
        self.tab_pos.setCurrentText("Сверху" if self.settings.get("tab_position", "top") == "top" else "Снизу")
        layout.addRow("Позиция вкладок:", self.tab_pos)

        self.show_bm = QCheckBox("Показывать панель закладок")
        self.show_bm.setChecked(self.settings.get("show_bookmarks_bar", True))
        layout.addRow("", self.show_bm)

        self.confirm_close_check = QCheckBox("Подтверждать закрытие нескольких вкладок")
        self.confirm_close_check.setChecked(self.settings.get("confirm_close", True))
        layout.addRow("", self.confirm_close_check)

        layout.addRow(QLabel("── Внешний вид ──"))

        self.new_tab_combo = QComboBox()
        self.new_tab_combo.addItems(["Домашняя страница", "Пустая страница", "Поисковая система"])
        nt = self.settings.get("new_tab_page", "home")
        self.new_tab_combo.setCurrentText({"home": "Домашняя страница", "blank": "Пустая страница", "search": "Поисковая система"}.get(nt, "Домашняя страница"))
        layout.addRow("Новая вкладка:", self.new_tab_combo)

        self.popup_check = QCheckBox("Блокировать всплывающие окна")
        self.popup_check.setChecked(self.settings.get("block_popups", True))
        layout.addRow("", self.popup_check)

        self.cookie_combo = QComboBox()
        self.cookie_combo.addItems(["Все cookies", "Только текущего сайта", "Заблокировать все"])
        cp = self.settings.get("cookie_policy", "allow")
        self.cookie_combo.setCurrentText({"allow": "Все cookies", "third-party": "Только текущего сайта", "block": "Заблокировать все"}.get(cp, "Все cookies"))
        layout.addRow("Cookies:", self.cookie_combo)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 72)
        self.font_spin.setSuffix("px")
        self.font_spin.setValue(self.settings.get("font_size", 16))
        self.font_spin.setStyleSheet("background: #1e1e1e; color: #fff; border: 1px solid #3c3c3c; border-radius: 3px; padding: 4px;")
        layout.addRow("Размер шрифта:", self.font_spin)

        self.smooth_check = QCheckBox("Плавная прокрутка")
        self.smooth_check.setChecked(self.settings.get("smooth_scroll", True))
        layout.addRow("", self.smooth_check)

        self.spell_check = QCheckBox("Проверка орфографии")
        self.spell_check.setChecked(self.settings.get("spell_check", False))
        layout.addRow("", self.spell_check)

        return scroll

    def _ui_tab(self):
        w = QWidget()
        w.setStyleSheet("background: #2b2b2b; color: #ccc;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(w)
        scroll.setStyleSheet("QScrollArea { border: none; background: #2b2b2b; } QScrollArea > QWidget > QWidget { background: #2b2b2b; } QScrollBar:vertical { background: #2b2b2b; width: 10px; } QScrollBar::handle:vertical { background: #3c3c3c; border-radius: 4px; min-height: 20px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }")
        layout = QFormLayout(w)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self.show_nav = QCheckBox("Показывать кнопки навигации (◀ ▶ ⟳ 🏠)")
        self.show_nav.setChecked(self.settings.get("show_nav_buttons", True))
        layout.addRow("", self.show_nav)

        self.show_home = QCheckBox("Показывать кнопку «Домой»")
        self.show_home.setChecked(self.settings.get("show_home_button", True))
        layout.addRow("", self.show_home)

        self.dbl_close = QCheckBox("Закрывать вкладку двойным кликом")
        self.dbl_close.setChecked(self.settings.get("double_click_close", False))
        layout.addRow("", self.dbl_close)

        self.session_check = QCheckBox("Восстанавливать вкладки при запуске")
        self.session_check.setChecked(self.settings.get("session_restore", True))
        layout.addRow("", self.session_check)

        self.status_bar_check = QCheckBox("Показывать строку состояния")
        self.status_bar_check.setChecked(self.settings.get("show_status_bar", True))
        layout.addRow("", self.status_bar_check)

        self.wheel_tabs_check = QCheckBox("Переключать вкладки колёсиком мыши")
        self.wheel_tabs_check.setChecked(self.settings.get("mouse_wheel_tabs", True))
        layout.addRow("", self.wheel_tabs_check)

        self.newtab_links_check = QCheckBox("Открывать ссылки в новой вкладке")
        self.newtab_links_check.setChecked(self.settings.get("open_in_new_tab", True))
        layout.addRow("", self.newtab_links_check)

        self.full_url_check = QCheckBox("Показывать полный URL в адресной строке")
        self.full_url_check.setChecked(self.settings.get("show_full_url", True))
        layout.addRow("", self.full_url_check)

        return scroll

    def _advanced_tab(self):
        w = QWidget()
        w.setStyleSheet("background: #2b2b2b; color: #ccc;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(w)
        scroll.setStyleSheet("QScrollArea { border: none; background: #2b2b2b; } QScrollArea > QWidget > QWidget { background: #2b2b2b; } QScrollBar:vertical { background: #2b2b2b; width: 10px; } QScrollBar::handle:vertical { background: #3c3c3c; border-radius: 4px; min-height: 20px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }")
        layout = QFormLayout(w)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self.min_font = QSpinBox()
        self.min_font.setRange(0, 48)
        self.min_font.setSuffix("px")
        self.min_font.setValue(self.settings.get("minimum_font_size", 0))
        self.min_font.setStyleSheet("background: #1e1e1e; color: #fff; border: 1px solid #3c3c3c; border-radius: 3px; padding: 4px;")
        self.min_font.setSpecialValueText("Нет")
        layout.addRow("Мин. размер шрифта:", self.min_font)

        self.caret_check = QCheckBox("Навигация с курсором (Caret Browsing)")
        self.caret_check.setChecked(self.settings.get("caret_browsing", False))
        layout.addRow("", self.caret_check)

        self.dns_check = QCheckBox("DNS prefetch")
        self.dns_check.setChecked(self.settings.get("dns_prefetch", True))
        layout.addRow("", self.dns_check)

        self.local_storage_check = QCheckBox("Локальное хранилище (LocalStorage)")
        self.local_storage_check.setChecked(self.settings.get("local_storage", True))
        layout.addRow("", self.local_storage_check)

        self.webgl_check = QCheckBox("WebGL")
        self.webgl_check.setChecked(self.settings.get("webgl", True))
        layout.addRow("", self.webgl_check)

        self.dl_sound_check = QCheckBox("Звук уведомления о завершении загрузки")
        self.dl_sound_check.setChecked(self.settings.get("download_sound", False))
        layout.addRow("", self.dl_sound_check)

        return scroll

    def _permissions_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        self.perm_list = QTableWidget()
        self.perm_list.setColumnCount(3)
        self.perm_list.setHorizontalHeaderLabels(["Сайт", "Разрешение", "Статус"])
        self.perm_list.horizontalHeader().setStretchLastSection(True)
        self.perm_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.perm_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.perm_list.verticalHeader().setVisible(False)
        self.perm_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.perm_list.setStyleSheet("""
            QTableWidget { background: #1e1e1e; color: #fff; border: 1px solid #3c3c3c;
                gridline-color: #3c3c3c; }
            QHeaderView::section { background: #2b2b2b; color: #aaa; border: none;
                padding: 4px; }
        """)
        self._refresh_perm_table()

        btn_layout = QHBoxLayout()
        del_btn = QPushButton("Удалить выбранное")
        del_btn.clicked.connect(self._delete_selected_perm)
        clear_all = QPushButton("Очистить все")
        clear_all.setObjectName("danger")
        clear_all.clicked.connect(self._clear_all_perms)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(clear_all)
        btn_layout.addStretch()

        layout.addWidget(QLabel("Сохранённые разрешения для сайтов:"))
        layout.addWidget(self.perm_list)
        layout.addLayout(btn_layout)
        return w

    def _refresh_perm_table(self):
        self.perm_list.setRowCount(0)
        perms = self.settings.get("permissions", {})
        FEATURE_LABELS = {
            "notifications": "Уведомления",
            "microphone": "Микрофон",
            "camera": "Камера",
            "geolocation": "Геолокация",
        }
        STATUS_LABELS = {"grant": "Разрешено", "deny": "Запрещено", "ask": "Спрашивать"}
        for domain, features in perms.items():
            for feat, status in features.items():
                row = self.perm_list.rowCount()
                self.perm_list.insertRow(row)
                self.perm_list.setItem(row, 0, QTableWidgetItem(domain))
                self.perm_list.setItem(row, 1, QTableWidgetItem(FEATURE_LABELS.get(feat, feat)))
                self.perm_list.setItem(row, 2, QTableWidgetItem(STATUS_LABELS.get(status, status)))

    def _delete_selected_perm(self):
        rows = set()
        for item in self.perm_list.selectedItems():
            rows.add(item.row())
        perms = self.settings.setdefault("permissions", {})
        for row in sorted(rows, reverse=True):
            domain = self.perm_list.item(row, 0).text()
            feat_key = self.perm_list.item(row, 1).text()
            # reverse lookup
            FEATURE_KEYS = {"Уведомления": "notifications", "Микрофон": "microphone",
                           "Камера": "camera", "Геолокация": "geolocation"}
            feat = FEATURE_KEYS.get(feat_key, feat_key)
            if domain in perms and feat in perms[domain]:
                del perms[domain][feat]
                if not perms[domain]:
                    del perms[domain]
            self.perm_list.removeRow(row)
        self.settings["permissions"] = perms

    def _clear_all_perms(self):
        self.settings["permissions"] = {}
        self._refresh_perm_table()

    def _privacy_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        clear_cache = QPushButton("Очистить кэш")
        clear_cache.clicked.connect(self._clear_cache)
        clear_cache.setObjectName("danger")

        clear_cookies = QPushButton("Очистить cookies")
        clear_cookies.clicked.connect(self._clear_cookies)
        clear_cookies.setObjectName("danger")

        clear_history = QPushButton("Очистить историю")
        clear_history.clicked.connect(self._clear_history)
        clear_history.setObjectName("danger")

        layout.addWidget(QLabel("Данные браузера:"))
        layout.addWidget(clear_cache)
        layout.addWidget(clear_cookies)
        layout.addWidget(clear_history)
        layout.addStretch()
        return w

    def _clear_history(self):
        save_history([])
        QMessageBox.information(self, "Очищено", "История удалена")

    def _about_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        for line in ABOUT_TEXT.strip().split("\n"):
            layout.addWidget(QLabel(line))
        layout.addStretch()
        return w

    def _browse_dl(self):
        path = QFileDialog.getExistingDirectory(self, "Папка для загрузок")
        if path:
            self.dl_input.setText(path)

    def _clear_cache(self):
        profile = QWebEngineProfile.defaultProfile()
        profile.clearHttpCache()
        QMessageBox.information(self, "Очищено", "Кэш очищен")

    def _clear_cookies(self):
        profile = QWebEngineProfile.defaultProfile()
        profile.cookieStore().deleteAllCookies()
        QMessageBox.information(self, "Очищено", "Cookies удалены")

    def _save(self):
        self.settings["home_url"] = self.home_input.text().strip()
        self.settings["search_engine"] = self.search_combo.currentText()
        self.settings["download_dir"] = self.dl_input.text().strip()
        self.settings["js_enabled"] = self.js_check.isChecked()
        self.settings["auto_images"] = self.images_check.isChecked()
        self.settings["default_zoom"] = self.zoom_spin.value()
        self.settings["tab_position"] = "top" if self.tab_pos.currentText() == "Сверху" else "bottom"
        self.settings["show_bookmarks_bar"] = self.show_bm.isChecked()
        self.settings["confirm_close"] = self.confirm_close_check.isChecked()
        nt_map = {"Домашняя страница": "home", "Пустая страница": "blank", "Поисковая система": "search"}
        self.settings["new_tab_page"] = nt_map.get(self.new_tab_combo.currentText(), "home")
        self.settings["block_popups"] = self.popup_check.isChecked()
        cp_map = {"Все cookies": "allow", "Только текущего сайта": "third-party", "Заблокировать все": "block"}
        self.settings["cookie_policy"] = cp_map.get(self.cookie_combo.currentText(), "allow")
        self.settings["font_size"] = self.font_spin.value()
        self.settings["smooth_scroll"] = self.smooth_check.isChecked()
        self.settings["spell_check"] = self.spell_check.isChecked()
        self.settings["show_nav_buttons"] = self.show_nav.isChecked()
        self.settings["show_home_button"] = self.show_home.isChecked()
        self.settings["double_click_close"] = self.dbl_close.isChecked()
        self.settings["session_restore"] = self.session_check.isChecked()
        self.settings["minimum_font_size"] = self.min_font.value()
        self.settings["caret_browsing"] = self.caret_check.isChecked()
        self.settings["dns_prefetch"] = self.dns_check.isChecked()
        self.settings["local_storage"] = self.local_storage_check.isChecked()
        self.settings["webgl"] = self.webgl_check.isChecked()
        self.settings["download_sound"] = self.dl_sound_check.isChecked()
        self.settings["show_status_bar"] = self.status_bar_check.isChecked()
        self.settings["mouse_wheel_tabs"] = self.wheel_tabs_check.isChecked()
        self.settings["open_in_new_tab"] = self.newtab_links_check.isChecked()
        self.settings["show_full_url"] = self.full_url_check.isChecked()
        save_settings(self.settings)
        configure_profile(QWebEngineProfile.defaultProfile(), self.settings)
        self.accept()


class HistoryDialog(QDialog):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.history = history
        self.setWindowTitle("История")
        self.setMinimumSize(640, 420)
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; color: #fff; }
            QLabel { color: #ccc; }
            QLineEdit {
                background: #1e1e1e; color: #fff; border: 1px solid #3c3c3c;
                border-radius: 3px; padding: 6px 10px;
            }
            QLineEdit:focus { border-color: #4a9eff; }
            QPushButton {
                background: #3c3c3c; color: #fff; border: none;
                border-radius: 4px; padding: 6px 14px;
            }
            QPushButton:hover { background: #505050; }
            QPushButton#danger { background: #5a2c2c; color: #ff6b6b; }
            QPushButton#danger:hover { background: #7a3c3c; }
            QListWidget {
                background: #1e1e1e; color: #fff; border: 1px solid #3c3c3c;
                outline: none;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #2b2b2b; }
            QListWidget::item:hover { background: #3c3c3c; }
            QListWidget::item:selected { background: #4a9eff; }
        """)
        layout = QVBoxLayout(self)

        header = QLabel("История посещений")
        header.setStyleSheet("font-size: 18px; color: #fff; padding: 4px 0;")
        layout.addWidget(header)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по истории...")
        self.search_input.textChanged.connect(self._filter)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_item)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.list)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        clear_btn = QPushButton("Очистить историю")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(clear_btn)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._filter()

    def _filter(self):
        query = self.search_input.text().lower()
        self.list.clear()
        for item in reversed(self.history):
            if query in item["title"].lower() or query in item["url"].lower():
                ts = datetime.fromtimestamp(item["time"]).strftime("%d.%m.%Y %H:%M")
                display = f"{item['title']}\n{item['url']}  —  {ts}"
                li = QListWidgetItem(display)
                li.setData(Qt.UserRole, item["url"])
                self.list.addItem(li)

    def _open_item(self, item):
        url = item.data(Qt.UserRole)
        if url:
            p = self.parent()
            while p and not isinstance(p, Browser):
                p = p.parent()
            if p:
                if p.settings.get("open_in_new_tab", True):
                    p.new_tab(url)
                else:
                    p._navigate_to(url)
            self.accept()

    def _context_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        url = item.data(Qt.UserRole)
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background: #2b2b2b; color: #fff; border: 1px solid #3c3c3c; }
            QMenu::item:selected { background: #4a9eff; }
        """)
        menu.addAction("📂 Открыть", lambda: self._open_item(item))
        menu.addAction("➕ Открыть в новой вкладке", lambda: self._open_new_tab(url))
        menu.addAction("📋 Копировать URL", lambda: QApplication.clipboard().setText(url))
        menu.addSeparator()
        menu.addAction("🗑 Удалить", lambda: self._delete_item(item))
        menu.exec_(self.list.mapToGlobal(pos))

    def _open_new_tab(self, url):
        p = self.parent()
        while p and not isinstance(p, Browser):
            p = p.parent()
        if p:
            p.new_tab(url)

    def _delete_item(self, item):
        url = item.data(Qt.UserRole)
        row = self.list.row(item)
        self.list.takeItem(row)
        self.history[:] = [h for h in self.history if h["url"] != url]
        save_history(self.history)

    def _clear_all(self):
        reply = QMessageBox.question(
            self, "Очистить историю",
            "Удалить всю историю посещений?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history.clear()
            save_history([])
            self.list.clear()
            self.search_input.clear()


class BrowserTab(QWidget):
    def __init__(self, browser_window, parent=None):
        super().__init__(parent)
        self.browser_window = browser_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QWebEngineView()
        self.browser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.browser.customContextMenuRequested.connect(self.show_context_menu)
        self.browser.urlChanged.connect(lambda url: self.browser_window.update_url.emit(url))

        layout.addWidget(self.browser)

    def show_context_menu(self, pos):
        page = self.browser.page()
        selected = page.selectedText()

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background: #2b2b2b; color: #fff; border: 1px solid #3c3c3c; }
            QMenu::item:selected { background: #4a9eff; }
        """)
        back = menu.addAction("◀ Назад")
        forward = menu.addAction("▶ Вперёд")
        reload = menu.addAction("⟳ Обновить")
        menu.addSeparator()
        copy_url = menu.addAction("📋 Копировать URL")
        open_new = menu.addAction("➕ Открыть в новой вкладке")
        if selected:
            menu.addSeparator()
            search = menu.addAction(f"🔍 Найти «{selected[:30]}»")

        action = menu.exec_(self.browser.mapToGlobal(pos))

        if action == back:
            self.browser.back()
        elif action == forward:
            self.browser.forward()
        elif action == reload:
            self.browser.reload()
        elif action == copy_url:
            QApplication.clipboard().setText(self.browser.url().toString())
        elif action == open_new:
            self.browser_window.new_tab(self.browser.url().toString())
        elif selected and action == search:
            engine = self.browser_window.settings.get("search_engine", "Google")
            template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["Google"])
            url = QUrl(template.format(selected.replace(" ", "+")))
            self.browser.setUrl(url)
            self.browser.forward()

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.setWindowTitle("Browzer")
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appicon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(100, 100, 1200, 800)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.tab_context_menu)
        self.tabs.tabBar().setMouseTracking(True)
        self.tabs.tabBar().installEventFilter(self)

        central = QWidget()
        self.central_layout = QVBoxLayout(central)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)
        self.setCentralWidget(central)

        self.update_url = UrlSignal()
        self.update_url.connect(self.update_address_bar)

        self.home_url = self.settings["home_url"]

        self.download_entries = []
        self.download_dialog = None

        QWebEngineProfile.defaultProfile().downloadRequested.connect(
            self.on_download_requested
        )

        self._fullscreen = False
        self._night_mode = self.settings.get("night_mode", False)
        self._zoom = {}
        self._bookmarks = load_bookmarks()
        self._history = load_history()

        self.setup_toolbar()
        self.setup_bookmarks_bar()
        self.setup_download_bar()
        self.setup_statusbar()
        self.apply_styles()
        self._apply_ui_settings()

        self.icon_timer = QTimer(self)
        self.icon_timer.timeout.connect(self._poll_icon)
        self.icon_timer.start(1000)

        if self._night_mode:
            self.night_btn.setChecked(True)
            self.night_btn.setText("☀️")

        self._restore_tabs()
        if self.tabs.count() == 0:
            self.new_tab()
        self._restore_downloads()

    def setup_toolbar(self):
        toolbar = QWidget()
        toolbar.setFixedHeight(48)
        toolbar.setStyleSheet("background: #2b2b2b;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._add_nav_buttons(layout)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Введите URL или поисковый запрос...")
        self.url_bar.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px; border-radius: 4px;
                background: #1e1e1e; color: #fff; font-size: 14px;
                border: 1px solid #3c3c3c; min-height: 36px; font-size: 15px;
                padding-left: 30px;
            }
            QLineEdit:focus { border-color: #4a9eff; }
        """)
        self.url_bar.returnPressed.connect(self.navigate)
        self.url_icon = self.url_bar.addAction(QIcon(), QLineEdit.LeadingPosition)
        self.url_icon.setVisible(False)
        layout.addWidget(self.url_bar, 1)

        layout.addStretch()

        self._add_extra_buttons(layout)

        self.central_layout.addWidget(toolbar)

    def _make_btn(self, text, tip, callback):
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setFixedHeight(36)
        btn.setStyleSheet("""
            QPushButton { color: #fff; background: #3c3c3c; border: none;
                border-radius: 4px; padding: 4px 10px; font-size: 15px; }
            QPushButton:hover { background: #505050; }
        """)
        btn.clicked.connect(callback)
        return btn

    def _add_nav_buttons(self, layout):
        self._nav_btns = []
        self._nav_btns.append(self._make_btn("◀", "Назад", lambda: self.current_browser().back()))
        self._nav_btns.append(self._make_btn("▶", "Вперёд", lambda: self.current_browser().forward()))
        self._nav_btns.append(self._make_btn("⟳", "Обновить", lambda: self.current_browser().reload()))
        self._home_btn = self._make_btn("🏠", "Домой", self.go_home)
        self._nav_btns.append(self._home_btn)
        for btn in self._nav_btns:
            layout.addWidget(btn)

    def _add_extra_buttons(self, layout):
        layout.addWidget(self._make_btn("+", "Новая вкладка", lambda: self.new_tab()))
        layout.addWidget(self._make_btn("🕐", "История (Ctrl+H)", self.show_history))
        layout.addWidget(self._make_btn("⬇", "Менеджер загрузок", self.show_downloads))
        self.night_btn = self._make_btn("🌙", "Ночной режим", self.toggle_night_mode)
        self.night_btn.setCheckable(True)
        layout.addWidget(self.night_btn)
        layout.addWidget(self._make_btn("⚙", "Настройки", self.show_settings))

    def setup_bookmarks_bar(self):
        self.bookmark_toolbar = QToolBar("Закладки")
        self.bookmark_toolbar.setMovable(False)
        self.bookmark_toolbar.setObjectName("bookmark_bar")
        self.bookmark_toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.bookmark_toolbar.setIconSize(QSize(1, 1))
        self.bookmark_toolbar.setAcceptDrops(True)
        self.bookmark_toolbar.installEventFilter(self)

        self.bm_star = QAction("☆", self)
        self.bm_star.setToolTip("Добавить / удалить закладку")
        self.bm_star.triggered.connect(self.toggle_bookmark)
        self.bookmark_toolbar.addAction(self.bm_star)

        self.bookmark_toolbar.addSeparator()
        self._refresh_bookmarks_bar()
        self.central_layout.addWidget(self.bookmark_toolbar)
        self.central_layout.addWidget(self.tabs, 1)

    def setup_download_bar(self):
        self.download_bar = QWidget()
        self.download_bar.setVisible(False)
        self.download_bar.setStyleSheet("background: #1e1e1e; border-top: 1px solid #3c3c3c;")
        dl_layout = QVBoxLayout(self.download_bar)
        dl_layout.setContentsMargins(8, 4, 8, 4)
        dl_layout.setSpacing(2)
        self.download_bar_layout = dl_layout
        self.central_layout.addWidget(self.download_bar)
        self._dl_bar_entries = []

    def _refresh_bookmarks_bar(self):
        for a in self.bookmark_toolbar.actions()[2:]:
            self.bookmark_toolbar.removeAction(a)
        for bm in self._bookmarks:
            a = QAction(bm["title"], self)
            a.setToolTip(bm["url"])
            a.setData(bm["url"])
            if self.settings.get("open_in_new_tab", True):
                a.triggered.connect(lambda checked, u=bm["url"]: self.new_tab(u))
            else:
                a.triggered.connect(lambda checked, u=bm["url"]: self._navigate_to(u))
            self.bookmark_toolbar.addAction(a)

    def _update_bookmark_star(self, url):
        is_bm = any(bm["url"] == url for bm in self._bookmarks)
        self.bm_star.setText("★" if is_bm else "☆")
        self.bm_star.setToolTip("Удалить закладку" if is_bm else "Добавить закладку")

    def toggle_bookmark(self):
        tab = self.current_browser()
        if not tab:
            return
        url = tab.url().toString()
        if not url or url == "about:blank":
            return
        for i, bm in enumerate(self._bookmarks):
            if bm["url"] == url:
                self._bookmarks.pop(i)
                save_bookmarks(self._bookmarks)
                self._refresh_bookmarks_bar()
                self._update_bookmark_star(url)
                self.status.showMessage("Закладка удалена")
                return
        title = tab.page().title() or url
        self._bookmarks.append({"title": title, "url": url})
        save_bookmarks(self._bookmarks)
        self._refresh_bookmarks_bar()
        self._update_bookmark_star(url)
        self.status.showMessage("Закладка добавлена")

    def setup_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Готово")
        self.status.setStyleSheet("QStatusBar { background: #2b2b2b; color: #aaa; font-size: 12px; }")

        self.animated_progress = AnimatedProgress()
        self.animated_progress.setVisible(False)
        self.status.addPermanentWidget(self.animated_progress)

        self.tab_count_label = QLabel()
        self.tab_count_label.setStyleSheet("color: #666; font-size: 11px; padding: 0 6px;")
        self.status.addPermanentWidget(self.tab_count_label)
        self._update_tab_count()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background: #2b2b2b; }
            QToolBar {
                background: #2b2b2b; border: none;
                padding: 0px; spacing: 0px;
            }
            QToolBar#bookmark_bar QToolButton {
                color: #ccc; background: transparent; border: none;
                border-radius: 2px; padding: 2px 6px; font-size: 12px;
            }
            QToolBar#bookmark_bar QToolButton:hover {
                background: #3c3c3c; color: #fff;
            }
            QTabWidget::pane { border: none; background: #fff; }
            QTabBar::tab {
                background: #3c3c3c; color: #aaa;
                padding: 8px 16px; border: none;
                min-width: 60px; max-width: 200px;
            }
            QTabBar::tab:selected { background: #1e1e1e; color: #fff; }
            QTabBar::tab:hover { color: #fff; }
            QStatusBar { background: #2b2b2b; color: #aaa; font-size: 12px; }
        """)

    def _apply_ui_settings(self):
        self._update_tab_position()
        self._update_bookmarks_visibility()
        self._default_zoom = self.settings.get("default_zoom", 100)
        show_nav = self.settings.get("show_nav_buttons", True)
        for btn in getattr(self, '_nav_btns', []):
            btn.setVisible(show_nav)
        show_home = self.settings.get("show_home_button", True)
        if hasattr(self, '_home_btn'):
            self._home_btn.setVisible(show_home)
        self.status.setVisible(self.settings.get("show_status_bar", True))
        if not self.settings.get("session_restore", True):
            self.settings["open_tabs"] = []
        self._refresh_bookmarks_bar()

    def _update_tab_position(self):
        pos = self.settings.get("tab_position", "top")
        self.tabs.setTabPosition(QTabWidget.North if pos == "top" else QTabWidget.South)

    def _update_bookmarks_visibility(self):
        visible = self.settings.get("show_bookmarks_bar", True)
        self.bookmark_toolbar.setVisible(visible)

    def closeEvent(self, event):
        if self.settings.get("confirm_close", True) and self.tabs.count() > 1:
            reply = QMessageBox.question(
                self, "Подтверждение",
                f"Закрыть {self.tabs.count()} вкладок?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        self._save_tabs()
        save_settings(self.settings)
        save_history(self._history)
        save_downloads(self.download_entries)
        event.accept()

    def _save_tabs(self):
        if not self.settings.get("session_restore", True):
            return
        urls = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab and tab.browser:
                url = tab.browser.url().toString()
                if url and url != "about:blank":
                    pinned = getattr(tab, '_pinned', False)
                    urls.append({"url": url, "pinned": pinned})
        self.settings["open_tabs"] = urls
        save_settings(self.settings)

    def _restore_tabs(self):
        if not self.settings.get("session_restore", True):
            return
        for entry in self.settings.get("open_tabs", []):
            if isinstance(entry, dict):
                self.new_tab(entry["url"])
                if entry.get("pinned"):
                    idx = self.tabs.count() - 1
                    self._pin_tab(idx)
            else:
                self.new_tab(entry)

    def _restore_downloads(self):
        for item in load_downloads():
            if not os.path.exists(item["path"]):
                continue
            entry = DownloadEntry(None, item["path"])
            entry.name = item["name"]
            entry.received = item["received"]
            entry.total = item["total"]
            entry.status = item["status"]
            entry.scan_status = item.get("scan_status", "clean" if item["status"] == "complete" else None)
            self.download_entries.append(entry)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_T:
                self.new_tab()
            elif event.key() == Qt.Key_W:
                self.close_tab(self.tabs.currentIndex())
            elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
                self.zoom_in()
            elif event.key() == Qt.Key_Minus:
                self.zoom_out()
            elif event.key() == Qt.Key_0:
                self.zoom_reset()
            elif event.key() == Qt.Key_F:
                self.find_on_page()
            elif event.key() == Qt.Key_D:
                self.toggle_bookmark()
            elif event.key() == Qt.Key_H:
                self.show_history()
            elif event.key() == Qt.Key_L:
                self.url_bar.setFocus()
                self.url_bar.selectAll()
            elif event.key() == Qt.Key_P:
                self.print_page()
            elif event.key() == Qt.Key_S:
                self.save_page()
            elif event.key() == Qt.Key_Tab:
                idx = (self.tabs.currentIndex() + 1) % self.tabs.count()
                self.tabs.setCurrentIndex(idx)
        elif event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_Escape and self._fullscreen:
            self.toggle_fullscreen()
        elif event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_N:
            self.toggle_night_mode()
        super().keyPressEvent(event)

    def toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

    def toggle_night_mode(self):
        self._night_mode = not self._night_mode
        self.settings["night_mode"] = self._night_mode
        js = """
        (function() {
            var el = document.getElementById('__browzer_night');
            if (el) { el.remove(); return; }
            var css = 'html{filter:invert(0.9)hue-rotate(180deg)}img,video,canvas,svg{filter:invert(1)hue-rotate(180deg)}';
            var s = document.createElement('style');
            s.id = '__browzer_night';
            s.textContent = css;
            document.head.appendChild(s);
        })();
        """
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab and tab.browser:
                tab.browser.page().runJavaScript(js)
        self.night_btn.setText("☀️" if self._night_mode else "🌙")
        self.status.showMessage("Ночной режим: вкл" if self._night_mode else "Ночной режим: выкл")

    def zoom_in(self):
        tab = self.current_browser()
        if tab:
            z = self._zoom.get(tab, 1.0) + 0.1
            self._zoom[tab] = z
            tab.setZoomFactor(z)
            self.status.showMessage(f"Масштаб: {int(z * 100)}%")

    def zoom_out(self):
        tab = self.current_browser()
        if tab:
            z = max(0.3, self._zoom.get(tab, 1.0) - 0.1)
            self._zoom[tab] = z
            tab.setZoomFactor(z)
            self.status.showMessage(f"Масштаб: {int(z * 100)}%")

    def zoom_reset(self):
        tab = self.current_browser()
        if tab:
            self._zoom[tab] = 1.0
            tab.setZoomFactor(1.0)
            self.status.showMessage("Масштаб: 100%")

    def find_on_page(self):
        tab = self.current_browser()
        if not tab:
            return
        text, ok = QInputDialog.getText(self, "Поиск на странице", "Найти:")
        if ok and text:
            tab.findText(text)

    def tab_context_menu(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx < 0:
            return
        tab = self.tabs.widget(idx)
        pinned = getattr(tab, '_pinned', False) if tab else False
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background: #2b2b2b; color: #fff; border: 1px solid #3c3c3c; }
            QMenu::item:selected { background: #4a9eff; }
        """)
        menu.addAction("✕ Закрыть вкладку", lambda: self.close_tab(idx))
        menu.addAction("✕ Закрыть другие", lambda: self._close_other_tabs(idx))
        menu.addAction("✕ Закрыть справа", lambda: self._close_tabs_right(idx))
        menu.addSeparator()
        menu.addAction("🔄 Обновить", lambda: self.tabs.widget(idx).browser.reload())
        menu.addAction("📋 Дублировать", lambda: self._duplicate_tab(idx))
        menu.addSeparator()
        if pinned:
            menu.addAction("📌 Открепить вкладку", lambda: self._pin_tab(idx))
        else:
            menu.addAction("📌 Закрепить вкладку", lambda: self._pin_tab(idx))
        menu.exec_(self.tabs.mapToGlobal(pos))

    def _close_other_tabs(self, keep):
        for i in range(self.tabs.count() - 1, -1, -1):
            tab = self.tabs.widget(i)
            if i != keep and not (tab and getattr(tab, '_pinned', False)):
                self.tabs.removeTab(i)
        self._update_tab_count()

    def _close_tabs_right(self, idx):
        for i in range(self.tabs.count() - 1, idx, -1):
            tab = self.tabs.widget(i)
            if not (tab and getattr(tab, '_pinned', False)):
                self.tabs.removeTab(i)
        self._update_tab_count()

    def _duplicate_tab(self, idx):
        tab = self.tabs.widget(idx)
        if tab and tab.browser:
            self.new_tab(tab.browser.url().toString())

    def _pin_tab(self, idx):
        tab = self.tabs.widget(idx)
        if not tab:
            return
        pinned = not getattr(tab, '_pinned', False)
        tab._pinned = pinned
        if pinned:
            self.tabs.setTabText(idx, "")
            self.tabs.setTabToolTip(idx, tab.browser.url().toString())
        else:
            title = getattr(tab, '_last_title', "Новая вкладка")
            self.tabs.setTabText(idx, title[:30])
            self.tabs.setTabToolTip(idx, "")

    def current_browser(self):
        tab = self.tabs.currentWidget()
        return tab.browser if tab else None

    def new_tab(self, url=None):
        tab = BrowserTab(self)
        idx = self.tabs.addTab(tab, "Новая вкладка")
        self.tabs.setCurrentIndex(idx)
        self._update_tab_count()

        page = tab.browser.page()
        page.titleChanged.connect(lambda title, t=tab, i=idx: self.on_title_changed(t, i))
        page.iconChanged.connect(lambda icon, i=idx: self.on_icon_changed(icon, i))
        page.loadProgress.connect(self.on_load_progress)
        page.loadStarted.connect(lambda: self.on_load_started(tab))
        page.loadFinished.connect(lambda ok: self.on_load_finished(tab, ok))
        page.renderProcessTerminated.connect(lambda status, code, t=tab: self.on_render_crashed(t))
        page.featurePermissionRequested.connect(lambda url, feat, p=page: self.on_permission_requested(p, url, feat))

        default_url = self.home_url
        if not url:
            ntp = self.settings.get("new_tab_page", "home")
            if ntp == "blank":
                default_url = "about:blank"
            elif ntp == "search":
                engine = self.settings.get("search_engine", "Google")
                template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["Google"])
                default_url = template.format("")
            else:
                default_url = self.home_url
        tab.browser.setZoomFactor(self._default_zoom / 100.0)
        tab.browser.setUrl(QUrl(url if url else default_url))

        if not url:
            self.url_bar.setFocus()
            self.url_bar.selectAll()

    def on_render_crashed(self, tab):
        url = getattr(tab, '_last_url', '')
        if url and url != "about:blank" and not getattr(tab, '_reloading', False):
            tab._reloading = True
            self.status.showMessage(f"Рендер упал, перезагружаем: {url}")
            QTimer.singleShot(500, lambda t=tab, u=url: self._reload_after_crash(t, u))

    def _reload_after_crash(self, tab, url):
        if not getattr(tab, '_reloading', False):
            return
        idx = self.tabs.indexOf(tab)
        if idx < 0:
            return
        title = getattr(tab, '_last_title', "Новая вкладка")
        new_tab = BrowserTab(self)
        self.tabs.insertTab(idx + 1, new_tab, title)
        self.tabs.removeTab(idx)
        self.tabs.setCurrentIndex(idx if idx < self.tabs.count() else self.tabs.count() - 1)
        new_tab.browser.setUrl(QUrl(url))

    def on_permission_requested(self, page, url, feature):
        domain = url.host()
        perms = self.settings.get("permissions", {})
        feature_name = {
            QWebEnginePage.Notifications: "notifications",
            QWebEnginePage.Geolocation: "geolocation",
            QWebEnginePage.MediaAudioCapture: "microphone",
            QWebEnginePage.MediaVideoCapture: "camera",
            QWebEnginePage.MediaAudioVideoCapture: "media",
        }.get(feature, str(feature))
        saved = perms.get(domain, {}).get(feature_name, "ask")
        if saved == "grant":
            page.setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)
            return
        if saved == "deny":
            page.setFeaturePermission(url, feature, QWebEnginePage.PermissionDeniedByUser)
            return
        self._ask_permission(page, url, feature, domain, feature_name)

    def _ask_permission(self, page, url, feature, domain, feature_name):
        labels = {"notifications": "уведомления", "geolocation": "геолокацию",
                  "microphone": "микрофон", "camera": "камеру", "media": "камеру и микрофон"}
        label = labels.get(feature_name, feature_name)
        msg = QMessageBox(self)
        msg.setWindowTitle("Разрешение")
        msg.setText(f"Сайт {domain} запрашивает доступ к {label}")
        msg.setIcon(QMessageBox.Question)
        yes = msg.addButton("Разрешить", QMessageBox.YesRole)
        no = msg.addButton("Запретить", QMessageBox.NoRole)
        always = msg.addButton("Всегда разрешать", QMessageBox.AcceptRole)
        never = msg.addButton("Всегда запрещать", QMessageBox.DestructiveRole)
        msg.exec_()
        if msg.clickedButton() == yes:
            page.setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)
        elif msg.clickedButton() == no:
            page.setFeaturePermission(url, feature, QWebEnginePage.PermissionDeniedByUser)
        elif msg.clickedButton() == always:
            perms = self.settings.setdefault("permissions", {})
            perms.setdefault(domain, {})[feature_name] = "grant"
            save_settings(self.settings)
            page.setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)
        elif msg.clickedButton() == never:
            perms = self.settings.setdefault("permissions", {})
            perms.setdefault(domain, {})[feature_name] = "deny"
            save_settings(self.settings)
            page.setFeaturePermission(url, feature, QWebEnginePage.PermissionDeniedByUser)

    def close_tab(self, idx):
        tab = self.tabs.widget(idx)
        if tab and getattr(tab, '_pinned', False):
            return
        if self.tabs.count() > 1:
            self.tabs.removeTab(idx)
            self._update_tab_count()
        else:
            self.close()

    def on_tab_changed(self, idx):
        tab = self.tabs.widget(idx)
        if tab and tab.browser:
            url = tab.browser.url().toString()
            self.url_bar.setText(url)
            self._update_bookmark_star(url)
            icon = getattr(tab, '_icon', QIcon())
            self._update_url_icon(icon)

    def on_icon_changed(self, icon, idx):
        self.tabs.setTabIcon(idx, icon)
        tab = self.tabs.widget(idx)
        if tab:
            tab._icon = icon
        if idx == self.tabs.currentIndex():
            self._update_url_icon(icon)

    def _update_url_icon(self, icon):
        if icon and not icon.isNull():
            self.url_icon.setIcon(icon)
            self.url_icon.setVisible(True)
        else:
            self.url_icon.setVisible(False)

    def on_title_changed(self, tab, idx):
        title = tab.browser.page().title() or "Новая вкладка"
        tab._last_title = title
        if not getattr(tab, '_pinned', False):
            self.tabs.setTabText(idx, title[:30])

    def eventFilter(self, obj, event):
        if obj == self.tabs.tabBar():
            if event.type() == event.MouseButtonRelease and event.button() == Qt.MiddleButton:
                idx = self.tabs.tabBar().tabAt(event.pos())
                if idx >= 0:
                    self.close_tab(idx)
                    return True
            elif event.type() == event.MouseButtonDblClick:
                idx = self.tabs.tabBar().tabAt(event.pos())
                if idx >= 0:
                    if self.settings.get("double_click_close", False):
                        self.close_tab(idx)
                        return True
                else:
                    self.new_tab()
                    return True
            elif event.type() == event.Wheel and self.settings.get("mouse_wheel_tabs", True):
                idx = self.tabs.currentIndex()
                d = event.angleDelta().y()
                if d > 0:
                    self.tabs.setCurrentIndex((idx - 1) % self.tabs.count())
                else:
                    self.tabs.setCurrentIndex((idx + 1) % self.tabs.count())
                return True
        return super().eventFilter(obj, event)

    def navigate(self):
        text = self.url_bar.text().strip()
        if not text:
            return

        url = QUrl(text)
        if url.scheme() == "":
            if "." in text and not text.startswith("."):
                url = QUrl("https://" + text)
            else:
                engine = self.settings.get("search_engine", "Google")
                template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["Google"])
                url = QUrl(template.format(text.replace(" ", "+")))

        self.current_browser().setUrl(url)

    def _poll_icon(self):
        tab = self.tabs.currentWidget()
        if tab:
            icon = tab.browser.page().icon()
            if icon and not icon.isNull():
                tab._icon = icon
                self._update_url_icon(icon)

    def update_address_bar(self, url):
        self.url_bar.setText(url.toString())
        tab = self.tabs.currentWidget()
        if tab:
            tab._last_url = url.toString()
            icon = getattr(tab, '_icon', QIcon())
            self._update_url_icon(icon)

    def go_home(self):
        self.current_browser().setUrl(QUrl(self.home_url))

    def on_load_started(self, tab):
        self.status.showMessage("Загрузка...")
        self.animated_progress.setVisible(True)
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            cur = self.tabs.tabText(idx)
            if not cur.startswith("⟳ "):
                self.tabs.setTabText(idx, "⟳ " + cur)

    def on_load_progress(self, progress):
        pass

    def on_load_finished(self, tab, ok):
        self.animated_progress.setVisible(False)
        self.status.showMessage("Готово" if ok else "Ошибка загрузки")
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            cur = self.tabs.tabText(idx)
            self.tabs.setTabText(idx, cur.replace("⟳ ", ""))
        bw = tab.browser
        if ok:
            url = bw.url().toString()
            title = bw.page().title() or url
            if url and url != "about:blank":
                self._add_history(url, title)
        if bw == self.current_browser():
            self._update_bookmark_star(bw.url().toString())
            self.update_address_bar(bw.url())

    def _add_history(self, url, title):
        if self._history and self._history[-1]["url"] == url:
            self._history[-1]["time"] = QDateTime.currentDateTime().toSecsSinceEpoch()
            return
        self._history.append({
            "url": url,
            "title": title,
            "time": QDateTime.currentDateTime().toSecsSinceEpoch(),
        })

    def on_download_requested(self, download):
        dl_dir = self.settings.get("download_dir", "")
        if not dl_dir or not os.path.isdir(dl_dir):
            dl_dir = QStandardPaths.writableLocation(
                QStandardPaths.DownloadLocation
            )
        path = os.path.join(dl_dir, os.path.basename(download.path()))
        if os.path.exists(path):
            base, ext = os.path.splitext(path)
            n = 1
            while os.path.exists(f"{base} ({n}){ext}"):
                n += 1
            path = f"{base} ({n}){ext}"
        download.setPath(path)
        download.accept()
        entry = DownloadEntry(download, path, on_threat=lambda: self._warn_threat(entry))
        entry.download.downloadProgress.connect(
            lambda r, t, e=entry: e.update_progress(r, t)
        )
        entry.download.finished.connect(lambda e=entry: setattr(e, 'status', 'complete'))
        entry.download.finished.connect(lambda: self._check_dl_bar())
        self.download_entries.append(entry)
        self._add_dl_bar_entry(entry)
        if self.download_dialog is not None:
            self.download_dialog.add_entry(entry)
        self.status.showMessage(f"Скачивание: {os.path.basename(path)}")

    def _add_dl_bar_entry(self, entry):
        row = QWidget()
        row.setFixedHeight(36)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 0, 4, 0)
        row_layout.setSpacing(8)

        name = QLabel(entry.name)
        name.setStyleSheet("color: #fff; font-size: 12px;")
        name.setMaximumWidth(250)

        progress = QProgressBar()
        progress.setFixedHeight(18)
        progress.setMinimumWidth(220)
        progress.setTextVisible(True)
        progress.setStyleSheet("""
            QProgressBar { background: #2b2b2b; border: none; border-radius: 3px;
                text-align: center; color: #fff; font-size: 11px; }
            QProgressBar::chunk { background: #4a9eff; border-radius: 3px; }
        """)
        progress.setValue(0)
        progress.setFormat("0%")

        cancel = QPushButton("✕")
        cancel.setFixedSize(24, 24)
        cancel.setStyleSheet("QPushButton { color: #ff6b6b; background: transparent; border: none; } QPushButton:hover { color: #ff4444; }")
        cancel.clicked.connect(entry.cancel)

        row_layout.addWidget(name)
        row_layout.addWidget(progress)
        row_layout.addStretch()
        row_layout.addWidget(cancel)

        entry._bar_row = row
        entry._bar_progress = progress
        self.download_bar_layout.addWidget(row)
        self.download_bar.setVisible(True)

        # update progress periodically
        timer = QTimer(self)
        timer.timeout.connect(lambda e=entry, p=progress: self._update_dl_bar(e, p))
        timer.start(500)
        entry._bar_timer = timer

    def _update_dl_bar(self, entry, progress):
        if entry.status in ("complete", "cancelled"):
            progress.setValue(100 if entry.status == "complete" else 0)
            if hasattr(entry, '_bar_timer'):
                entry._bar_timer.stop()
            self._check_dl_bar()
            return
        if entry.total > 0:
            pct = int(entry.received / entry.total * 100)
            progress.setValue(pct)
            progress.setFormat(f"{pct}%  {entry.size_str()}  {entry.speed_str()}")
        else:
            progress.setFormat(f"{entry.size_str()}")

    def _check_dl_bar(self):
        entries = [e for e in self.download_entries if hasattr(e, '_bar_row')]
        if all(e.status in ("complete", "cancelled") for e in entries):
            self.download_bar.setVisible(False)
            for e in entries:
                if hasattr(e, '_bar_timer'):
                    e._bar_timer.stop()
                if e._bar_row:
                    e._bar_row.deleteLater()
                    e._bar_row = None

    def _warn_threat(self, entry):
        QMessageBox.warning(
            self, "Угроза обнаружена",
            f"Windows Defender обнаружил угрозу в файле:\n{entry.name}\n\n"
            "Рекомендуется удалить этот файл."
        )

    def _update_tab_count(self):
        self.tab_count_label.setText(f"{self.tabs.count()} вкл")

    def show_downloads(self):
        if self.download_dialog is None:
            self.download_dialog = DownloadManagerDialog(self)
            for entry in self.download_entries:
                self.download_dialog.add_entry(entry)
        self.download_dialog.show()
        self.download_dialog.raise_()
        self.download_dialog.activateWindow()

    def show_history(self):
        dialog = HistoryDialog(self._history, self)
        dialog.exec_()

    def eventFilter(self, obj, event):
        if obj is self.bookmark_toolbar:
            if event.type() == QEvent.DragEnter:
                if event.mimeData().hasUrls() or event.mimeData().hasText():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Drop:
                url = None
                if event.mimeData().hasUrls():
                    url = event.mimeData().urls()[0].toString()
                elif event.mimeData().hasText():
                    url = event.mimeData().text().strip()
                if url and url.startswith("http"):
                    title = url.rsplit("/", 1)[-1].replace("_", " ").replace("-", " ").title() or url
                    for bm in self._bookmarks:
                        if bm["url"] == url:
                            QMessageBox.information(self, "Закладка", "Этот сайт уже в закладках")
                            return True
                    self._bookmarks.append({"title": title, "url": url})
                    save_bookmarks(self._bookmarks)
                    self._refresh_bookmarks_bar()
                    self.status.showMessage(f"Закладка добавлена: {title}")
                event.acceptProposedAction()
                return True
        return super().eventFilter(obj, event)

    def print_page(self):
        bw = self.current_browser()
        if bw:
            bw.page().printToPdf(lambda path: self._on_printed(path) if path else None)

    def _on_printed(self, path):
        self.status.showMessage(f"PDF сохранён: {os.path.basename(path)}")
        QMessageBox.information(self, "Печать", f"PDF сохранён:\n{path}")

    def save_page(self):
        bw = self.current_browser()
        if not bw:
            return
        url = bw.url().toString()
        title = bw.page().title() or "page"
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:50]
        suggested = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.DownloadLocation),
            f"{safe}.html"
        )
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить страницу", suggested, "HTML (*.html)")
        if path:
            bw.page().save(path, QWebEnginePage.CompleteHtmlSaveFormat)
            self.status.showMessage(f"Страница сохранена: {os.path.basename(path)}")

    def show_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_() == QDialog.Accepted:
            self.settings = load_settings()
            self.home_url = self.settings["home_url"]
            configure_profile(QWebEngineProfile.defaultProfile(), self.settings)
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if tab and tab.browser:
                    page = tab.browser.page()
                    page.profile().setHttpUserAgent(self.settings.get("user_agent", CHROME_UA))
            self._apply_ui_settings()
            zoom = self.settings.get("default_zoom", 100) / 100.0
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if tab and tab.browser:
                    tab.browser.setZoomFactor(zoom)
            if self.current_browser():
                self.current_browser().setZoomFactor(zoom)


class UrlSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, value):
        for cb in self._callbacks:
            cb(value)


if __name__ == "__main__":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
    app = QApplication(sys.argv)
    app.setApplicationName("Browzer")
    app.setApplicationDisplayName("Browzer")

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appicon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    configure_profile(QWebEngineProfile.defaultProfile())
    window = Browser()
    window.show()
    sys.exit(app.exec_())
