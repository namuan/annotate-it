import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QPoint
from PyQt6.QtCore import QPointF
from PyQt6.QtCore import QRect
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QCursor
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QKeySequence
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QPen
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QRadialGradient
from PyQt6.QtGui import QShortcut
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QColorDialog
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget


class ConfigManager:
    def __init__(self, app_name="annotate_it"):
        self.app_name = app_name
        self.config_file = self.get_config_dir() / "config.json"

    def get_config_dir(self):
        home = Path.home()
        if sys.platform == "darwin":  # macOS
            config_dir = home / "Library" / "Application Support" / self.app_name
        elif sys.platform == "win32":  # Windows
            config_dir = Path(os.getenv("APPDATA")) / self.app_name
        else:  # Linux and other Unix-like
            config_dir = home / ".config" / self.app_name.lower()

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def load_config(self):
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}

    def save_config(self, config):
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)


class QColorButton(QPushButton):
    def __init__(self, color):
        super().__init__()
        self.setFixedSize(50, 24)
        self.color = color
        self.setStyleSheet(f"background-color: {color.name()}")

    def mousePressEvent(self, e):
        color = QColorDialog.getColor(self.color)
        if color.isValid():
            self.color = color
            self.setStyleSheet(f"background-color: {self.color.name()}")
            self.update()


class TransparentWindow(QWidget):
    default_font_family: str = "HanziPen TC"
    default_font_size: int = 36

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.load_config()
        self.shapes = []
        self.shortcuts = []
        self.init_ui()
        self.drawing = False
        self.lastPoint = QPoint()
        self.currentShape = None
        self.undoStack = []
        self.redoStack = []
        self.font = QFont(self.default_font_family, self.default_font_size)
        self.drawingLayer = QPixmap(self.size())
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        self.cursor_pos = QPoint()
        self.show_halo = False
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.update_timer.setInterval(16)  # ~60 FPS
        QTimer.singleShot(1000, self.toggle_halo)

        # For keeping text
        self.current_text = ""
        self.current_text_pos = None
        self.is_typing = False
        self.show_cursor = True
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.blink_cursor)
        self.cursor_timer.start(500)

    def blink_cursor(self):
        if self.is_typing:
            self.show_cursor = not self.show_cursor
            self.update()

    def load_config(self):
        config = self.config_manager.load_config()
        self.shape = config.get("shape", "arrow")
        self.arrowColor = QColor(config.get("arrowColor", "#00FF00"))
        self.rectColor = QColor(config.get("rectColor", "#FF1493"))
        self.ellipseColor = QColor(config.get("ellipseColor", "#00BFFF"))
        self.textColor = QColor(config.get("textColor", "#AA26FF"))

    def save_config(self):
        config = {
            "shape": self.shape,
            "arrowColor": self.arrowColor.name(),
            "rectColor": self.rectColor.name(),
            "ellipseColor": self.ellipseColor.name(),
            "textColor": self.textColor.name(),
        }
        self.config_manager.save_config(config)

    def closeEvent(self, event):
        self.save_config()
        super().closeEvent(event)

    def init_ui(self):
        self.setWindowTitle("Transparent Drawing")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showMaximized()

        self.setup_shortcuts()

    def setup_shortcuts(self):
        self.shortcuts = [
            QShortcut(QKeySequence("A"), self, lambda: self.set_shape("arrow")),
            QShortcut(QKeySequence("R"), self, lambda: self.set_shape("rectangle")),
            QShortcut(QKeySequence("E"), self, lambda: self.set_shape("ellipse")),
            QShortcut(QKeySequence("T"), self, lambda: self.set_shape("text")),
            QShortcut(QKeySequence("H"), self, self.toggle_halo),
            QShortcut(QKeySequence("C"), self, self.clear_drawings),
            QShortcut(QKeySequence("Q"), self, self.close),
            QShortcut(QKeySequence("Ctrl+Z"), self, self.undo),
            QShortcut(QKeySequence("Ctrl+Y"), self, self.redo),
            QShortcut(QKeySequence("Ctrl+,"), self, self.show_config_dialog),
        ]

    def disable_shortcuts(self):
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)

    def enable_shortcuts(self):
        for shortcut in self.shortcuts:
            shortcut.setEnabled(True)

    def toggle_halo(self):
        self.show_halo = not self.show_halo
        if self.show_halo:
            self.update_timer.start()
        else:
            self.update_timer.stop()
        self.update()
        print(f"Halo effect {'enabled' if self.show_halo else 'disabled'}")

    def show_config_dialog(self):
        dialog = ConfigDialog(self)
        dialog.exec()
        self.redraw_shapes()

    def set_shape(self, shape):
        self.shape = shape
        self.save_config()
        print(f"Current shape: {self.shape}")

    def clear_drawings(self):
        if self.shapes:
            self.undoStack.append(self.shapes.copy())
            self.shapes.clear()
            self.redoStack.clear()
            self.drawingLayer.fill(Qt.GlobalColor.transparent)
            self.update()
            print("Drawings cleared")

    def undo(self):
        if self.shapes:
            self.redoStack.append(self.shapes.copy())
            self.shapes = self.undoStack.pop() if self.undoStack else []
            self.redraw_shapes()
            self.update()
            print("Undo")

    def redo(self):
        if self.redoStack:
            self.undoStack.append(self.shapes.copy())
            self.shapes = self.redoStack.pop()
            self.redraw_shapes()
            self.update()
            print("Redo")

    def update_cursor_pos(self):
        if self.underMouse():
            self.cursor_pos = self.mapFromGlobal(QCursor.pos())
        else:
            self.cursor_pos = QCursor.pos()

    def paintEvent(self, event):
        if self.show_halo:
            self.update_cursor_pos()

        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)

        qp.setBrush(QColor(0, 0, 0, 1))
        qp.drawRect(self.rect())

        qp.drawPixmap(0, 0, self.drawingLayer)

        if self.currentShape:
            if self.currentShape["type"] == "arrow":
                qp.setPen(QPen(self.arrowColor, 4, Qt.PenStyle.SolidLine))
                self.draw_arrow(
                    qp, self.currentShape["start"], self.currentShape["end"]
                )
            elif self.currentShape["type"] == "rectangle":
                qp.setPen(QPen(self.rectColor, 4, Qt.PenStyle.SolidLine))
                qp.drawRect(QRect(self.currentShape["start"], self.currentShape["end"]))
            elif self.currentShape["type"] == "ellipse":
                qp.setPen(QPen(self.ellipseColor, 4, Qt.PenStyle.SolidLine))
                qp.drawEllipse(
                    QRect(self.currentShape["start"], self.currentShape["end"])
                )

        if self.is_typing and self.current_text_pos:
            qp.setPen(QPen(self.textColor))
            qp.setFont(self.font)
            # Draw the current text
            qp.drawText(self.current_text_pos, self.current_text)

            # Draw the cursor
            if self.show_cursor:
                metrics = qp.fontMetrics()
                text_width = metrics.horizontalAdvance(self.current_text)
                cursor_x = self.current_text_pos.x() + text_width
                cursor_y = self.current_text_pos.y()
                qp.drawText(QPoint(cursor_x, cursor_y), "_")

        if self.show_halo:
            self.draw_halo(qp)

    def get_current_shape_color(self):
        if self.shape == "arrow":
            return self.arrowColor
        elif self.shape == "rectangle":
            return self.rectColor
        elif self.shape == "ellipse":
            return self.ellipseColor
        elif self.shape == "text":
            return self.textColor
        else:
            return QColor(128, 128, 128)  # Default to gray if no shape is selected

    def draw_halo(self, qp):
        halo_radius = 20
        cursor_pos_f = QPointF(self.cursor_pos)
        gradient = QRadialGradient(cursor_pos_f, halo_radius)

        shape_color = self.get_current_shape_color()

        darker_color = shape_color.darker(150)

        gradient.setColorAt(
            0, QColor(shape_color.red(), shape_color.green(), shape_color.blue(), 100)
        )
        gradient.setColorAt(
            1, QColor(darker_color.red(), darker_color.green(), darker_color.blue(), 75)
        )

        qp.setBrush(gradient)
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawEllipse(cursor_pos_f, halo_radius, halo_radius)

    def focusOutEvent(self, event):
        if self.is_typing and self.current_text:
            self.undoStack.append(self.shapes.copy())
            self.shapes.append(
                {
                    "type": "text",
                    "position": self.current_text_pos,
                    "text": self.current_text,
                }
            )
            self.redraw_shapes()
            self.redoStack.clear()
            self.current_text = ""
            self.current_text_pos = None
            self.is_typing = False
            self.enable_shortcuts()
            self.update()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if self.is_typing:
            if event.key() == Qt.Key.Key_Return:
                if self.current_text:
                    self.undoStack.append(self.shapes.copy())
                    self.shapes.append(
                        {
                            "type": "text",
                            "position": self.current_text_pos,
                            "text": self.current_text,
                        }
                    )
                    self.redraw_shapes()
                    self.redoStack.clear()
                self.current_text = ""
                self.current_text_pos = None
                self.is_typing = False
                self.enable_shortcuts()
            elif (
                event.key() == Qt.Key.Key_Escape
            ):  # Add escape key to cancel text entry
                self.current_text = ""
                self.current_text_pos = None
                self.is_typing = False
                self.enable_shortcuts()  # Re-enable shortcuts when canceling
            elif event.key() == Qt.Key.Key_Backspace:
                self.current_text = self.current_text[:-1]
            else:
                self.current_text += event.text()
            self.show_cursor = True
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.shape == "text":
                # Save current text before starting new one
                if self.is_typing and self.current_text:
                    self.undoStack.append(self.shapes.copy())
                    self.shapes.append(
                        {
                            "type": "text",
                            "position": self.current_text_pos,
                            "text": self.current_text,
                        }
                    )
                    self.redraw_shapes()
                    self.redoStack.clear()

                self.current_text_pos = event.position().toPoint()
                self.is_typing = True
                self.current_text = ""
                self.show_cursor = True
                self.disable_shortcuts()
                self.update()
            else:
                self.drawing = True
                self.lastPoint = event.position().toPoint()
                self.currentShape = {
                    "type": self.shape,
                    "start": self.lastPoint,
                    "end": self.lastPoint,
                }

    def redraw_shapes(self):
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        qp = QPainter(self.drawingLayer)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        for shape in self.shapes:
            if shape["type"] == "arrow":
                qp.setPen(QPen(self.arrowColor, 4, Qt.PenStyle.SolidLine))
                self.draw_arrow(qp, shape["start"], shape["end"])
            elif shape["type"] == "rectangle":
                qp.setPen(QPen(self.rectColor, 4, Qt.PenStyle.SolidLine))
                qp.drawRect(QRect(shape["start"], shape["end"]))
            elif shape["type"] == "ellipse":
                qp.setPen(QPen(self.ellipseColor, 4, Qt.PenStyle.SolidLine))
                qp.drawEllipse(QRect(shape["start"], shape["end"]))
            elif shape["type"] == "text":
                qp.setPen(QPen(self.textColor))
                qp.setFont(self.font)
                qp.drawText(shape["position"], shape["text"])
        qp.end()

    def mouseMoveEvent(self, event):
        self.cursor_pos = event.position().toPoint()
        if self.drawing:
            self.currentShape["end"] = self.cursor_pos
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            end_point = event.position().toPoint()
            self.currentShape["end"] = end_point
            self.undoStack.append(self.shapes.copy())
            self.shapes.append(self.currentShape)
            self.redraw_shapes()
            self.currentShape = None
            self.redoStack.clear()
            print(f"{self.shape.capitalize()} drawn")
            self.update()

    def draw_arrow(self, qp, start, end):
        qp.drawLine(start, end)

        arrow_size = 10  # Size of arrow head

        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
            return

        # Normalize direction vector
        dx, dy = dx / length, dy / length

        # Calculate the points for the arrow head
        left = QPoint(
            int(end.x() - arrow_size * (dx + dy)), int(end.y() - arrow_size * (dy - dx))
        )
        right = QPoint(
            int(end.x() - arrow_size * (dx - dy)), int(end.y() - arrow_size * (dy + dx))
        )

        # Draw the arrow head
        qp.drawLine(end, left)
        qp.drawLine(end, right)

    def add_text(self, position):
        text, ok = QInputDialog.getText(self, "Enter text", None)
        if ok and text:
            self.undoStack.append(self.shapes.copy())
            self.shapes.append({"type": "text", "position": position, "text": text})
            self.redraw_shapes()
            self.redoStack.clear()
            print("Text added")
            self.update()

    def resizeEvent(self, event):
        self.drawingLayer = QPixmap(self.size())
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        self.redraw_shapes()
        super().resizeEvent(event)


class ConfigDialog(QDialog):
    def __init__(self, parent: TransparentWindow = None):
        super().__init__(parent)
        self.parent: TransparentWindow = parent
        self.setWindowTitle("Configuration")
        self.setFixedSize(500, 300)

        layout = QVBoxLayout()
        grid = QGridLayout()

        shortcuts = [
            ("A", "Arrow drawing mode"),
            ("R", "Rectangle drawing mode"),
            ("E", "Ellipse drawing mode"),
            ("T", "Text input mode"),
            ("H", "Toggle cursor halo effect"),
            ("C", "Clear all drawings"),
            ("Q", "Quit the application"),
            ("Ctrl+Z", "Undo last action"),
            ("Ctrl+Y", "Redo last undone action"),
            ("Cmd+, (Ctrl+, on Windows/Linux)", "Open this configuration dialog"),
        ]

        for i, (key, description) in enumerate(shortcuts):
            grid.addWidget(QLabel(key), i, 0)
            grid.addWidget(QLabel(description), i, 1)

        # Add color buttons
        grid.addWidget(QLabel("Arrow Color"), 0, 2)
        self.arrowColorBtn = QColorButton(self.parent.arrowColor)
        grid.addWidget(self.arrowColorBtn, 0, 3)

        grid.addWidget(QLabel("Rectangle Color"), 1, 2)
        self.rectColorBtn = QColorButton(self.parent.rectColor)
        grid.addWidget(self.rectColorBtn, 1, 3)

        grid.addWidget(QLabel("Ellipse Color"), 2, 2)
        self.ellipseColorBtn = QColorButton(self.parent.ellipseColor)
        grid.addWidget(self.ellipseColorBtn, 2, 3)

        grid.addWidget(QLabel("Text Color"), 3, 2)
        self.textColorBtn = QColorButton(self.parent.textColor)
        grid.addWidget(self.textColorBtn, 3, 3)

        layout.addLayout(grid)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.parent.arrowColor = self.arrowColorBtn.color
        self.parent.rectColor = self.rectColorBtn.color
        self.parent.ellipseColor = self.ellipseColorBtn.color
        self.parent.textColor = self.textColorBtn.color
        self.parent.save_config()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = TransparentWindow()
    ex.show()
    sys.exit(app.exec())
