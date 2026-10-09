import sys
import os
import json # เพิ่มไลบรารี json
import csv
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
                               QFrame, QLineEdit, QGridLayout, QTextEdit, QMessageBox,
                               QScrollArea, QFileDialog)
from PySide6.QtGui import QPixmap, QCursor, QFont
from PySide6.QtCore import Qt, Signal

# ==========================================
# 1. DATABASE CONFIGURATION (JSON LOADER)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "parts_database.json")
MODULE_CODES = {
    "UPPER MODULE": "502010284",
    "LOWER MODULE": "502010217",
}
MODULE_SUMMARY_LABELS = {
    "UPPER MODULE": "502010284 (Upper)",
    "LOWER MODULE": "502010217 (Lower)",
}


def module_parts(module_data):
    if isinstance(module_data, dict):
        return module_data.get("parts", [])
    return module_data


def module_image(module_data):
    if isinstance(module_data, dict) and module_data.get("image_path"):
        return module_data["image_path"]
    parts = module_parts(module_data)
    return parts[0].get("image_path", "") if parts else ""


def image_file(image_path):
    if not image_path:
        return ""
    if os.path.isabs(image_path):
        return image_path
    return os.path.join(BASE_DIR, image_path)


def load_scaled_image(path, max_width, max_height):
    if not path or not os.path.exists(path):
        return QPixmap()
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def part_tooltip(part_info):
    components = part_info.get("components", [])
    if components:
        return "\n".join(str(component["id"]) for component in components)
    return str(part_info["id"])


def consumed_part_quantities(part_info, set_quantity):
    components = part_info.get("components", [])
    if not components:
        return [(f"{part_info['id']} ({part_info['name']})", set_quantity)]
    return [
        (
            f"{component['id']} ({component['name']})",
            set_quantity * component.get("qty_per_set", 1),
        )
        for component in components
    ]

def load_database():
    # ถ้าไม่มีไฟล์ JSON ให้สร้างไฟล์พร้อมข้อมูลตั้งต้น
    if not os.path.exists(JSON_FILE):
        default_db = {
            "UPPER MODULE": [
                {"id": "715010063", "name": "FLAT BELT", "default_qty": 2, "image_path": "images/1000387781.jpg"}
            ]
        }
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(default_db, f, indent=4, ensure_ascii=False)
        return default_db
    
    # ถ้ามีไฟล์อยู่แล้ว ให้โหลดข้อมูลขึ้นมาใช้งาน
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return {}

# โหลดข้อมูลเก็บไว้ในตัวแปร PARTS_DB
PARTS_DB = load_database()

# ... (ส่วนโค้ด QSS และ Widget ต่างๆ ยังคงเหมือนเดิม) ...

# ==========================================
# 2. GLOBAL STYLESHEET (QSS)
# ==========================================
STYLESHEET = """
QMainWindow, QWidget#MainContainer {
    background-color: #4a4f54;
}
QWidget {
    color: #f3f4f6;
}
QLabel {
    font-family: 'Segoe UI';
    color: #f3f4f6;
}
QPushButton {
    font-family: 'Segoe UI';
    font-weight: bold;
    border-radius: 10px;
    padding: 10px 20px;
    background-color: #ffffff;
    border: 1px solid #dfe5ee;
    color: #000000;
}
QPushButton:hover {
    background-color: #edf7ff;
    border: 1px solid #00a8ff;
    color: #000000;
}
QPushButton#SettingsBtn {
    background-color: #e4e7e9;
    border: 1px solid #aeb4ba;
    border-radius: 8px;
    color: #343a40;
    font-size: 20px;
    padding: 0;
}
QPushButton#SettingsBtn:hover {
    background-color: #ffffff;
    border: 1px solid #7b838a;
}
QWidget#ModuleEntryPanel {
    background-color: #d9dde0;
    border: 1px solid #aeb4ba;
    border-radius: 8px;
}
QWidget#ModuleEntryPanel QLabel {
    color: #343a40;
}
QPushButton#QuantityBtn {
    color: #000000;
    padding: 0;
}
QPushButton#PrimaryBtn {
    background-color: #6bce91;
    color: #000000;
    border: none;
}
QPushButton#PrimaryBtn:hover {
    background-color: #82dca4;
}
QPushButton#DangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff9c8f, stop:1 #ff8179);
    color: #000000;
    border: none;
}
QPushButton#DangerBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffb0a5, stop:1 #ff958d);
}
QLineEdit {
    padding: 9px 10px;
    border: 1px solid #dfe5ee;
    border-radius: 8px;
    font-family: 'Segoe UI';
    background-color: #ffffff;
    color: #000000;
}
QLineEdit:focus {
    border: 1px solid #4e9b70;
}
QTextEdit {
    color: #000000;
}
QToolTip {
    color: #000000;
    background-color: #ffffff;
}
QFrame#ExtraParts QLabel {
    color: #000000;
}
"""

# ==========================================
# 3. CUSTOM WIDGETS
# ==========================================
class PartCard(QFrame):
    def __init__(self, part_info, selectable=True):
        super().__init__()
        self.part_info = part_info
        self.selectable = selectable
        self.is_selected = False
        self.current_qty = part_info.get("default_qty", 1)
        tooltip = part_tooltip(part_info)

        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(220, 300)
        self.setToolTip(tooltip)
        self.setAttribute(Qt.WA_Hover, True)
        self.update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        image_frame = QFrame()
        image_frame.setStyleSheet("QFrame { background: #f4f7fb; border: 1px solid #dfeaf5; border-radius: 10px; }")
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(8, 8, 8, 8)
        image_layout.setAlignment(Qt.AlignCenter)

        self.lbl_image = ClickableLabel()
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setCursor(QCursor(Qt.PointingHandCursor))
        self.lbl_image.setToolTip(tooltip)
        path = image_file(part_info.get("image_path", ""))
        pixmap = load_scaled_image(path, 150, 130)
        if not pixmap.isNull():
            self.lbl_image.setFixedSize(pixmap.size())
            image_frame.setFixedSize(pixmap.width() + 18, pixmap.height() + 18)
            self.lbl_image.setPixmap(pixmap)
        else:
            image_frame.setFixedSize(170, 150)
            self.lbl_image.setFixedSize(120, 120)
            self.lbl_image.setText("IMAGE\nNOT FOUND")
            self.lbl_image.setStyleSheet("color: #000000; font-size: 10px; font-weight: bold;")
        self.lbl_image.clicked.connect(self.toggle_selection)
        image_layout.addWidget(self.lbl_image, alignment=Qt.AlignCenter)
        layout.addWidget(image_frame, alignment=Qt.AlignCenter)

        self.lbl_name = ClickableLabel(part_info["name"])
        self.lbl_name.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_name.setAlignment(Qt.AlignCenter)
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setStyleSheet("padding-top: 2px; color: #000000;")
        self.lbl_name.setToolTip(tooltip)
        self.lbl_name.setCursor(QCursor(Qt.PointingHandCursor))
        self.lbl_name.clicked.connect(self.toggle_selection)
        layout.addWidget(self.lbl_name)

        components = part_info.get("components", [])
        if components:
            self.lbl_components = QLabel(f"{len(components)} COMPONENTS / SET")
            self.lbl_components.setAlignment(Qt.AlignCenter)
            self.lbl_components.setStyleSheet("color: #000000; font-size: 9px; font-weight: bold;")
            self.lbl_components.setToolTip(tooltip)
            layout.addWidget(self.lbl_components)

        qty_layout = QHBoxLayout()
        qty_layout.setAlignment(Qt.AlignCenter)
        qty_layout.setSpacing(10)

        self.btn_minus = QPushButton("-")
        self.btn_minus.setObjectName("QuantityBtn")
        self.btn_minus.setFixedSize(30, 30)
        self.btn_minus.setEnabled(selectable)
        self.btn_minus.clicked.connect(self.decrease_qty)

        self.lbl_qty = QLabel(str(self.current_qty))
        self.lbl_qty.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.lbl_qty.setAlignment(Qt.AlignCenter)
        self.lbl_qty.setFixedWidth(40)
        self.lbl_qty.setStyleSheet("color: #000000;")

        self.btn_plus = QPushButton("+")
        self.btn_plus.setObjectName("QuantityBtn")
        self.btn_plus.setFixedSize(30, 30)
        self.btn_plus.setEnabled(selectable)
        self.btn_plus.clicked.connect(self.increase_qty)

        qty_layout.addWidget(self.btn_minus)
        qty_layout.addWidget(self.lbl_qty)
        qty_layout.addWidget(self.btn_plus)
        layout.addLayout(qty_layout)

    def decrease_qty(self):
        if self.current_qty > 1:
            self.current_qty -= 1
            self.lbl_qty.setText(str(self.current_qty))

    def increase_qty(self):
        self.current_qty += 1
        self.lbl_qty.setText(str(self.current_qty))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_selection()
        super().mousePressEvent(event)

    def toggle_selection(self):
        if not self.selectable:
            return
        self.is_selected = not self.is_selected
        self.update_style()

    def set_selectable(self, selectable):
        self.selectable = selectable
        self.btn_minus.setEnabled(selectable)
        self.btn_plus.setEnabled(selectable)

    def enterEvent(self, event):
        self.setStyleSheet("QFrame { background-color: #f8fbff; border: 2px solid #bfe8ff; border-radius: 10px; }")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_style()
        super().leaveEvent(event)

    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("QFrame { background-color: #edf8ff; border: 2px solid #00a8ff; border-radius: 10px; }")
        else:
            self.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #dfe5ee; border-radius: 10px; }")


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class ModuleCard(QFrame):
    def __init__(self, module_name, module_number, image_path, on_click):
        super().__init__()
        tooltip = module_number or module_name
        self.setFixedSize(240, 230)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setToolTip(tooltip)
        self.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #dfe5ee; border-radius: 10px; }"
            "QFrame:hover { background: #f4faf8; border: 2px solid #26836b; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        self.image = ClickableLabel()
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setToolTip(tooltip)
        self.image.setStyleSheet("background: #f1f5f4; border-radius: 9px; color: #000000; font-size: 11px; font-weight: bold;")
        path = image_file(image_path)
        pixmap = load_scaled_image(path, 210, 155)
        if not pixmap.isNull():
            self.image.setFixedSize(pixmap.size())
            self.image.setPixmap(pixmap)
        else:
            self.image.setFixedSize(210, 155)
            self.image.setText("MODULE IMAGE\nNOT FOUND")
        self.image.clicked.connect(on_click)
        layout.addWidget(self.image, alignment=Qt.AlignCenter)

        self.name = ClickableLabel(module_name)
        self.name.setAlignment(Qt.AlignCenter)
        self.name.setWordWrap(True)
        self.name.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.name.setStyleSheet("color: #000000; border: none; background: transparent;")
        self.name.setToolTip(tooltip)
        self.name.clicked.connect(on_click)
        layout.addWidget(self.name)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.image.clicked.emit()
        super().mousePressEvent(event)

# ==========================================
# 4. MAIN APPLICATION WIZARD
# ==========================================
class ATMRepairApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ATM Part Tracker Pro (PySide6)")
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            window_width = max(1, min(1100, available.width() - 40))
            window_height = max(1, min(760, available.height() - 64))
            self.setMinimumSize(min(640, window_width), min(480, window_height))
            self.resize(window_width, window_height)
            self.move(available.center() - self.rect().center())
        else:
            self.setMinimumSize(640, 480)
            self.resize(1100, 760)
        self.setStyleSheet(STYLESHEET)

        self.summary_bad = {}
        self.summary_good = {}
        self.summary_module_numbers = {}
        self.current_module = ""
        self.active_cards = []
        self.temp_extra_parts = {}
        self.temporary_module_numbers = {}
        self.module_settings_mode = False
        self.part_settings_mode = False

        # Central Widget & Stacked Layout
        self.central_widget = QWidget()
        self.central_widget.setObjectName("MainContainer")
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        self.init_page_1()
        self.init_page_2()
        self.init_page_3()

    # --- PAGE 1: MODULE SELECTION ---
    def init_page_1(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 26, 32, 26)
        layout.setAlignment(Qt.AlignCenter)

        header_layout = QHBoxLayout()
        self.btn_module_settings = QPushButton("✎")
        self.btn_module_settings.setObjectName("SettingsBtn")
        self.btn_module_settings.setFixedSize(44, 44)
        self.btn_module_settings.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_module_settings.setToolTip("Manage modules")
        self.btn_module_settings.clicked.connect(self.toggle_module_settings)
        header_layout.addSpacing(44)

        lbl_title = QLabel("SELECT BAD MODULE")
        lbl_title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: #f3f4f6;")
        header_layout.addWidget(lbl_title, stretch=1)
        header_layout.addWidget(self.btn_module_settings)
        layout.addLayout(header_layout)
        layout.addSpacing(28)

        module_scroll = QScrollArea()
        module_scroll.setWidgetResizable(True)
        module_scroll.setFrameShape(QFrame.NoFrame)
        module_scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self.module_content = QWidget()
        self.module_layout = QGridLayout(self.module_content)
        self.module_layout.setAlignment(Qt.AlignCenter)
        self.module_layout.setHorizontalSpacing(18)
        self.module_layout.setVerticalSpacing(18)
        module_scroll.setWidget(self.module_content)
        layout.addWidget(module_scroll, stretch=1)
        layout.addSpacing(18)

        self.one_time_module_widget = QWidget()
        self.one_time_module_widget.setObjectName("ModuleEntryPanel")
        one_time_module_row = QHBoxLayout(self.one_time_module_widget)
        one_time_module_row.setContentsMargins(14, 8, 14, 8)
        one_time_module_row.setSpacing(10)
        one_time_module_row.addStretch()
        one_time_module_row.addWidget(QLabel("ONE-TIME MODULE:"))
        self.entry_one_time_module_number = QLineEdit()
        self.entry_one_time_module_number.setPlaceholderText("Module Number")
        self.entry_one_time_module_number.setFixedWidth(220)
        one_time_module_row.addWidget(self.entry_one_time_module_number)
        btn_use_once = QPushButton("USE ONCE")
        btn_use_once.setCursor(QCursor(Qt.PointingHandCursor))
        btn_use_once.clicked.connect(self.use_one_time_module)
        one_time_module_row.addWidget(btn_use_once)
        one_time_module_row.addStretch()
        layout.addWidget(self.one_time_module_widget)

        self.module_management_widget = QWidget()
        self.module_management_widget.setObjectName("ModuleEntryPanel")
        add_module_row = QHBoxLayout(self.module_management_widget)
        add_module_row.setContentsMargins(14, 8, 14, 8)
        add_module_row.setSpacing(10)
        add_module_row.addStretch()
        self.entry_module_name = QLineEdit()
        self.entry_module_name.setPlaceholderText("Module Name")
        self.entry_module_name.setFixedWidth(220)
        self.entry_module_number = QLineEdit()
        self.entry_module_number.setPlaceholderText("Module Number")
        self.entry_module_number.setFixedWidth(180)
        btn_add_module = QPushButton("ADD MODULE")
        btn_add_module.setCursor(QCursor(Qt.PointingHandCursor))
        btn_add_module.clicked.connect(self.add_module)
        add_module_row.addStretch()
        add_module_row.addWidget(self.entry_module_name)
        add_module_row.addWidget(self.entry_module_number)
        add_module_row.addWidget(btn_add_module)
        add_module_row.addStretch()
        layout.addWidget(self.module_management_widget)
        self.module_management_widget.hide()

        btn_summary = QPushButton("VIEW SUMMARY")
        btn_summary.setFixedSize(200, 50)
        btn_summary.setCursor(QCursor(Qt.PointingHandCursor))
        btn_summary.clicked.connect(lambda: self.switch_page(2))
        layout.addWidget(btn_summary, alignment=Qt.AlignCenter)

        self.stacked_widget.addWidget(page)
        self.refresh_module_cards()

    def refresh_module_cards(self):
        while self.module_layout.count():
            child = self.module_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        module_columns = max(1, min(3, (self.width() - 64 + 18) // 258))
        for index, (module_name, module_data) in enumerate(PARTS_DB.items()):
            module_number = MODULE_CODES.get(module_name, "")
            if isinstance(module_data, dict):
                module_number = module_data.get("module_number", module_number)
            card = ModuleCard(
                module_name,
                module_number,
                module_image(module_data),
                lambda name=module_name: self.select_module(name),
            )
            card_container = QWidget()
            card_layout = QVBoxLayout(card_container)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(6)
            card_layout.addWidget(card)
            if self.module_settings_mode:
                btn_delete = QPushButton("DELETE MODULE")
                btn_delete.setObjectName("DangerBtn")
                btn_delete.setCursor(QCursor(Qt.PointingHandCursor))
                btn_delete.clicked.connect(
                    lambda checked=False, name=module_name: self.delete_module(name)
                )
                card_layout.addWidget(btn_delete)
            self.module_layout.addWidget(
                card_container,
                index // module_columns,
                index % module_columns,
            )

    def toggle_module_settings(self):
        self.module_settings_mode = not self.module_settings_mode
        self.one_time_module_widget.setVisible(not self.module_settings_mode)
        self.module_management_widget.setVisible(self.module_settings_mode)
        self.btn_module_settings.setText("✓" if self.module_settings_mode else "✎")
        self.btn_module_settings.setToolTip(
            "Finish module settings" if self.module_settings_mode else "Manage modules"
        )
        self.refresh_module_cards()

    def use_one_time_module(self):
        module_number = self.entry_one_time_module_number.text().strip()
        if not module_number:
            QMessageBox.warning(self, "Missing module number", "Enter a module number to use once.")
            return

        for module_name, module_data in PARTS_DB.items():
            known_number = MODULE_CODES.get(module_name, "")
            if isinstance(module_data, dict):
                known_number = module_data.get("module_number", known_number)
            if str(known_number).casefold() == module_number.casefold():
                self.entry_one_time_module_number.clear()
                self.select_module(module_name)
                return

        temporary_name = f"ONE-TIME MODULE {module_number}"
        suffix = 2
        while temporary_name in PARTS_DB and temporary_name not in self.temporary_module_numbers:
            temporary_name = f"ONE-TIME MODULE {module_number} ({suffix})"
            suffix += 1
        self.temporary_module_numbers[temporary_name] = module_number
        self.entry_one_time_module_number.clear()
        self.select_module(temporary_name)

    def delete_module(self, module_name):
        reply = QMessageBox.question(
            self,
            "Delete module",
            f"Delete {module_name} and its part list from the module database?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        module_data = PARTS_DB.pop(module_name)
        try:
            with open(JSON_FILE, "w", encoding="utf-8") as database_file:
                json.dump(PARTS_DB, database_file, indent=4, ensure_ascii=False)
        except OSError as error:
            PARTS_DB[module_name] = module_data
            QMessageBox.critical(self, "Delete failed", f"Could not update the module database:\n{error}")
            return

        self.refresh_module_cards()

    def add_module(self):
        if not self.module_settings_mode:
            return
        module_name = self.entry_module_name.text().strip().upper()
        module_number = self.entry_module_number.text().strip()

        if not module_name or not module_number:
            QMessageBox.warning(self, "Missing information", "Enter both a module name and module number.")
            return
        if any(name.casefold() == module_name.casefold() for name in PARTS_DB):
            QMessageBox.warning(self, "Duplicate module", "This module name already exists.")
            return

        existing_numbers = {
            str(MODULE_CODES.get(name, "")).casefold()
            for name in PARTS_DB
        }
        existing_numbers.update(
            str(data.get("module_number", "")).casefold()
            for data in PARTS_DB.values()
            if isinstance(data, dict)
        )
        if module_number.casefold() in existing_numbers:
            QMessageBox.warning(self, "Duplicate module number", "This module number already exists.")
            return

        PARTS_DB[module_name] = {
            "module_number": module_number,
            "image_path": "",
            "parts": [],
        }
        try:
            with open(JSON_FILE, "w", encoding="utf-8") as database_file:
                json.dump(PARTS_DB, database_file, indent=4, ensure_ascii=False)
        except OSError as error:
            del PARTS_DB[module_name]
            QMessageBox.critical(self, "Save failed", f"Could not save the module:\n{error}")
            return

        self.entry_module_name.clear()
        self.entry_module_number.clear()
        self.refresh_module_cards()

    def select_module(self, module_name):
        if self.module_settings_mode:
            return
        self.current_module = module_name
        module_data = PARTS_DB.get(module_name, {})
        module_number = MODULE_CODES.get(module_name, "")
        if isinstance(module_data, dict):
            module_number = module_data.get("module_number", module_number)
        self.summary_module_numbers[module_name] = self.temporary_module_numbers.get(
            module_name,
            module_number,
        )
        self.summary_bad[module_name] = self.summary_bad.get(module_name, 0) + 1
        self.load_parts_for_module()
        self.switch_page(1)

    # --- PAGE 2: PART SELECTION ---
    def init_page_2(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 22)
        
        page2_header = QHBoxLayout()
        page2_header.addSpacing(44)
        self.lbl_page2_title = QLabel()
        self.lbl_page2_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.lbl_page2_title.setStyleSheet("color: #f3f4f6;")
        self.lbl_page2_title.setAlignment(Qt.AlignCenter)
        page2_header.addWidget(self.lbl_page2_title, stretch=1)
        self.btn_part_settings = QPushButton("✎")
        self.btn_part_settings.setObjectName("SettingsBtn")
        self.btn_part_settings.setFixedSize(44, 44)
        self.btn_part_settings.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_part_settings.setToolTip("Manage parts for this module")
        self.btn_part_settings.clicked.connect(self.toggle_part_settings)
        page2_header.addWidget(self.btn_part_settings)
        layout.addLayout(page2_header)
        layout.addSpacing(20)

        # Dynamic, scrollable grid for cards
        parts_scroll = QScrollArea()
        parts_scroll.setWidgetResizable(True)
        parts_scroll.setFrameShape(QFrame.NoFrame)
        parts_scroll.setStyleSheet("QScrollArea { background: transparent; }")
        parts_content = QWidget()
        self.grid_layout = QGridLayout(parts_content)
        self.grid_layout.setAlignment(Qt.AlignCenter)
        self.grid_layout.setHorizontalSpacing(16)
        self.grid_layout.setVerticalSpacing(16)
        parts_scroll.setWidget(parts_content)
        layout.addWidget(parts_scroll, stretch=1)
        layout.addSpacing(12)

        self.part_settings_widget = QWidget()
        self.part_settings_widget.setObjectName("ModuleEntryPanel")
        part_settings_row = QHBoxLayout(self.part_settings_widget)
        part_settings_row.setContentsMargins(14, 8, 14, 8)
        part_settings_row.setSpacing(10)
        part_settings_row.addStretch()
        part_settings_row.addWidget(QLabel("ADD PERMANENT PART:"))
        self.entry_part_id = QLineEdit()
        self.entry_part_id.setPlaceholderText("Part Number")
        self.entry_part_id.setFixedWidth(180)
        self.entry_part_name = QLineEdit()
        self.entry_part_name.setPlaceholderText("Part Name")
        self.entry_part_name.setFixedWidth(210)
        self.entry_part_qty = QLineEdit("1")
        self.entry_part_qty.setPlaceholderText("Default Qty")
        self.entry_part_qty.setFixedWidth(90)
        self.entry_part_qty.setAlignment(Qt.AlignCenter)
        btn_add_part = QPushButton("ADD PART")
        btn_add_part.setObjectName("PrimaryBtn")
        btn_add_part.setCursor(QCursor(Qt.PointingHandCursor))
        btn_add_part.clicked.connect(self.add_part_to_module)
        part_settings_row.addWidget(self.entry_part_id)
        part_settings_row.addWidget(self.entry_part_name)
        part_settings_row.addWidget(self.entry_part_qty)
        part_settings_row.addWidget(btn_add_part)
        part_settings_row.addStretch()
        layout.addWidget(self.part_settings_widget)
        self.part_settings_widget.hide()

        # Extra Parts Section
        self.extra_parts_frame = QFrame()
        self.extra_parts_frame.setObjectName("ExtraParts")
        self.extra_parts_frame.setStyleSheet("background-color: white; border: 1px solid #dcdde1; border-radius: 8px;")
        extra_layout = QHBoxLayout(self.extra_parts_frame)
        lbl_extra = QLabel("ADD EXTRA PARTS:")
        lbl_extra.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.entry_extra_name = QLineEdit()
        self.entry_extra_name.setPlaceholderText("Part Name or S/N")
        self.entry_extra_name.setFixedWidth(250)
        
        self.entry_extra_qty = QLineEdit("1")
        self.entry_extra_qty.setFixedWidth(60)
        self.entry_extra_qty.setAlignment(Qt.AlignCenter)

        btn_add = QPushButton("ADD")
        btn_add.setCursor(QCursor(Qt.PointingHandCursor))
        btn_add.clicked.connect(self.add_extra_part)

        self.lbl_extra_list = QLabel("")
        self.lbl_extra_list.setStyleSheet("color: #000000; font-weight: bold; border: none;")

        extra_layout.addWidget(lbl_extra)
        extra_layout.addWidget(self.entry_extra_name)
        extra_layout.addWidget(QLabel("QTY:"))
        extra_layout.addWidget(self.entry_extra_qty)
        extra_layout.addWidget(btn_add)
        extra_layout.addWidget(self.lbl_extra_list)
        extra_layout.addStretch()
        
        layout.addWidget(self.extra_parts_frame)
        layout.addStretch()

        # Bottom Buttons
        self.part_navigation_widget = QWidget()
        btn_layout = QHBoxLayout(self.part_navigation_widget)
        btn_layout.setAlignment(Qt.AlignCenter)
        
        btn_back = QPushButton("BACK")
        btn_back.setFixedSize(150, 45)
        btn_back.clicked.connect(self.cancel_selection)
        
        btn_confirm = QPushButton("CONFIRM & NEXT")
        btn_confirm.setObjectName("PrimaryBtn")
        btn_confirm.setFixedSize(200, 45)
        btn_confirm.clicked.connect(self.save_parts_and_go_next)

        btn_layout.addWidget(btn_back)
        btn_layout.addWidget(btn_confirm)
        layout.addWidget(self.part_navigation_widget)

        self.stacked_widget.addWidget(page)

    def load_parts_for_module(self, reset_extra_parts=True, preserve_selection=False):
        self.lbl_page2_title.setText(f"REPLACEMENT PARTS : {self.current_module}")
        if reset_extra_parts:
            self.temp_extra_parts.clear()
            self.lbl_extra_list.setText("")
        previous_selection = {
            (str(card.part_info.get("id", "")), str(card.part_info.get("name", ""))): (
                card.is_selected,
                card.current_qty,
            )
            for card in self.active_cards
        } if preserve_selection else {}
        self.active_cards.clear()
        self.empty_parts_label = None
        self.part_delete_buttons = []

        # Clear existing layout
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if self.current_module in self.temporary_module_numbers:
            parts = []
        else:
            parts = module_parts(PARTS_DB.get(self.current_module, []))
        self.btn_part_settings.setEnabled(self.current_module not in self.temporary_module_numbers)
        if not parts:
            self.empty_parts_label = QLabel(
                "No registered parts. Use the pencil button to add one."
                if self.current_module not in self.temporary_module_numbers
                else "No registered parts for this one-time module."
            )
            self.empty_parts_label.setAlignment(Qt.AlignCenter)
            self.empty_parts_label.setStyleSheet("color: #e0e4e7; font-size: 14px;")
            self.grid_layout.addWidget(self.empty_parts_label, 0, 0)
        part_columns = max(1, min(4, (self.width() - 56 + 16) // 236))
        for i, part in enumerate(parts):
            card = PartCard(part, selectable=not self.part_settings_mode)
            card_container = QWidget()
            card_layout = QVBoxLayout(card_container)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(6)
            card_layout.addWidget(card)
            btn_delete = QPushButton("DELETE PART")
            btn_delete.setObjectName("DangerBtn")
            btn_delete.setCursor(QCursor(Qt.PointingHandCursor))
            btn_delete.setVisible(self.part_settings_mode)
            btn_delete.clicked.connect(
                lambda checked=False, part_id=part.get("id", ""), part_name=part.get("name", ""):
                    self.delete_part_from_module(part_id, part_name)
            )
            card_layout.addWidget(btn_delete)
            self.part_delete_buttons.append(btn_delete)
            self.grid_layout.addWidget(card_container, i // part_columns, i % part_columns)
            selection = previous_selection.get(
                (str(part.get("id", "")), str(part.get("name", "")))
            )
            if selection:
                card.is_selected, card.current_qty = selection
                card.lbl_qty.setText(str(card.current_qty))
                card.update_style()
            self.active_cards.append(card)

    def toggle_part_settings(self):
        if self.current_module in self.temporary_module_numbers:
            return
        self.part_settings_mode = not self.part_settings_mode
        self.part_settings_widget.setVisible(self.part_settings_mode)
        self.extra_parts_frame.setVisible(not self.part_settings_mode)
        self.part_navigation_widget.setVisible(not self.part_settings_mode)
        self.btn_part_settings.setText("✓" if self.part_settings_mode else "✎")
        self.btn_part_settings.setToolTip(
            "Finish part settings" if self.part_settings_mode else "Manage parts for this module"
        )
        for card in self.active_cards:
            card.set_selectable(not self.part_settings_mode)
        for button in self.part_delete_buttons:
            button.setVisible(self.part_settings_mode)
        if getattr(self, "empty_parts_label", None):
            self.empty_parts_label.setText(
                "No registered parts. Add one using the form below."
                if self.part_settings_mode
                else "No registered parts. Use the pencil button to add one."
            )

    def add_part_to_module(self):
        if not self.part_settings_mode or self.current_module in self.temporary_module_numbers:
            return

        part_id = self.entry_part_id.text().strip()
        part_name = self.entry_part_name.text().strip().upper()
        quantity_text = self.entry_part_qty.text().strip()
        if not part_id or not part_name or not quantity_text.isdigit() or int(quantity_text) < 1:
            QMessageBox.warning(
                self,
                "Invalid part",
                "Enter a part number, part name, and a quantity greater than zero.",
            )
            return

        original_module_data = PARTS_DB.get(self.current_module, [])
        parts = module_parts(original_module_data)
        if any(str(part.get("id", "")).casefold() == part_id.casefold() for part in parts):
            QMessageBox.warning(self, "Duplicate part", "This part number already exists in this module.")
            return

        parts.append({
            "id": part_id,
            "name": part_name,
            "default_qty": int(quantity_text),
            "image_path": "",
            "components": [],
        })
        if not isinstance(original_module_data, dict):
            PARTS_DB[self.current_module] = {
                "image_path": module_image(original_module_data),
                "parts": parts,
            }
        try:
            with open(JSON_FILE, "w", encoding="utf-8") as database_file:
                json.dump(PARTS_DB, database_file, indent=4, ensure_ascii=False)
        except OSError as error:
            parts.pop()
            PARTS_DB[self.current_module] = original_module_data
            QMessageBox.critical(self, "Save failed", f"Could not save the part:\n{error}")
            return

        self.entry_part_id.clear()
        self.entry_part_name.clear()
        self.entry_part_qty.setText("1")
        self.load_parts_for_module(reset_extra_parts=False, preserve_selection=True)

    def delete_part_from_module(self, part_id, part_name):
        if not self.part_settings_mode:
            return
        reply = QMessageBox.question(
            self,
            "Delete part",
            f"Delete {part_id} ({part_name}) from {self.current_module}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        module_data = PARTS_DB.get(self.current_module, [])
        parts = module_parts(module_data)
        part_index = next(
            (
                index for index, part in enumerate(parts)
                if str(part.get("id", "")) == str(part_id)
                and str(part.get("name", "")) == str(part_name)
            ),
            None,
        )
        if part_index is None:
            return
        removed_part = parts.pop(part_index)
        try:
            with open(JSON_FILE, "w", encoding="utf-8") as database_file:
                json.dump(PARTS_DB, database_file, indent=4, ensure_ascii=False)
        except OSError as error:
            parts.insert(part_index, removed_part)
            QMessageBox.critical(self, "Delete failed", f"Could not update the part database:\n{error}")
            return

        self.load_parts_for_module(reset_extra_parts=False, preserve_selection=True)

    def add_extra_part(self):
        part_name = self.entry_extra_name.text().strip().upper()
        qty_str = self.entry_extra_qty.text().strip()
        
        if part_name and qty_str.isdigit():
            qty = int(qty_str)
            self.temp_extra_parts[part_name] = self.temp_extra_parts.get(part_name, 0) + qty
            
            self.entry_extra_name.clear()
            self.entry_extra_qty.setText("1")
            
            items = [f"{k} (x{v})" for k, v in self.temp_extra_parts.items()]
            self.lbl_extra_list.setText("Added: " + ", ".join(items))

    def save_parts_and_go_next(self):
        for card in self.active_cards:
            if card.is_selected:
                for part_name, quantity in consumed_part_quantities(
                    card.part_info, card.current_qty
                ):
                    self.summary_good[part_name] = (
                        self.summary_good.get(part_name, 0) + quantity
                    )
        
        for name, qty in self.temp_extra_parts.items():
            self.summary_good[name] = self.summary_good.get(name, 0) + qty

        self.switch_page(0)

    def cancel_selection(self):
        if self.summary_bad.get(self.current_module, 0) > 0:
            self.summary_bad[self.current_module] -= 1
            if self.summary_bad[self.current_module] == 0:
                del self.summary_bad[self.current_module]
        self.switch_page(0)

    # --- PAGE 3: SUMMARY ---
    def init_page_3(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        lbl_title = QLabel("WEEKLY INVENTORY SUMMARY")
        lbl_title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(lbl_title, alignment=Qt.AlignCenter)
        layout.addSpacing(20)

        # Text Boxes
        text_layout = QHBoxLayout()
        
        self.txt_bad = QTextEdit()
        self.txt_bad.setReadOnly(True)
        self.txt_bad.setStyleSheet("background-color: #fff5f5; color: #000000; font-family: 'Consolas'; font-size: 14px; border: 1px solid #ffcccc; border-radius: 8px; padding: 10px;")
        
        self.txt_good = QTextEdit()
        self.txt_good.setReadOnly(True)
        self.txt_good.setStyleSheet("background-color: #f5fffa; color: #000000; font-family: 'Consolas'; font-size: 14px; border: 1px solid #ccffeb; border-radius: 8px; padding: 10px;")

        text_layout.addWidget(self.txt_bad)
        text_layout.addWidget(self.txt_good)
        layout.addLayout(text_layout)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        
        btn_back = QPushButton("BACK")
        btn_back.setFixedSize(150, 45)
        btn_back.clicked.connect(lambda: self.switch_page(0))
        
        btn_reset = QPushButton("RESET DATA")
        btn_reset.setObjectName("DangerBtn")
        btn_reset.setFixedSize(150, 45)
        btn_reset.clicked.connect(self.reset_all)

        btn_export = QPushButton("EXPORT CSV")
        btn_export.setObjectName("PrimaryBtn")
        btn_export.setFixedSize(150, 45)
        btn_export.clicked.connect(self.export_summary_csv)

        btn_layout.addWidget(btn_back)
        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_reset)
        layout.addLayout(btn_layout)

        self.stacked_widget.addWidget(page)

    def update_summary_view(self):
        bad_text = "BAD PARTS (DEFECTIVE MODULES)\n" + "="*35 + "\n\n"
        for mod, qty in self.summary_bad.items():
            module_label = MODULE_SUMMARY_LABELS.get(
                mod,
                f"{self.temporary_module_numbers[mod]} (One-time)"
                if mod in self.temporary_module_numbers
                else mod,
            )
            bad_text += f"[{qty}x] {module_label}\n"
        self.txt_bad.setText(bad_text)

        good_text = "GOOD PARTS (CONSUMED INVENTORY)\n" + "="*35 + "\n\n"
        for part, qty in self.summary_good.items():
            good_text += f"[{qty}x] {part}\n"
        self.txt_good.setText(good_text)

    def export_summary_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export inventory summary",
            "inventory_summary.csv",
            "CSV files (*.csv)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["Type", "Module", "Part Number", "Part Name", "Quantity"])
                for module_name, quantity in self.summary_bad.items():
                    module_data = PARTS_DB.get(module_name, {})
                    module_number = MODULE_CODES.get(module_name, "")
                    if isinstance(module_data, dict):
                        module_number = module_data.get("module_number", module_number)
                    module_number = self.summary_module_numbers.get(module_name, module_number)
                    writer.writerow([
                        "Defective Module",
                        module_name,
                        module_number,
                        "",
                        quantity,
                    ])
                for part_label, quantity in self.summary_good.items():
                    if " (" in part_label and part_label.endswith(")"):
                        part_number, part_name = part_label[:-1].split(" (", 1)
                    else:
                        part_number, part_name = "", part_label
                    writer.writerow(["Consumed Part", "", part_number, part_name, quantity])
        except OSError as error:
            QMessageBox.critical(self, "Export failed", f"Could not export the CSV file:\n{error}")
            return

        QMessageBox.information(self, "Export complete", f"CSV exported to:\n{file_path}")

    def switch_page(self, index):
        if index == 2:
            self.update_summary_view()
        self.stacked_widget.setCurrentIndex(index)

    def reset_all(self):
        reply = QMessageBox.question(self, 'Confirm Reset', 'Are you sure you want to clear all data for this week?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.summary_bad.clear()
            self.summary_good.clear()
            self.summary_module_numbers.clear()
            self.temporary_module_numbers.clear()
            self.switch_page(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ATMRepairApp()
    window.show()
    sys.exit(app.exec())