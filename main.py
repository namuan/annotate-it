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
        self.show_flashlight = False
        self.filled_shapes = False
        self.opacity_levels = [255, 128, 64]
        self.current_opacity_index = 1
        self.current_opacity = self.opacity_levels[self.current_opacity_index]
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
        self.lineColor = QColor(config.get("lineColor", "#FFFF00"))

    def save_config(self):
        config = {
            "shape": self.shape,
            "arrowColor": self.arrowColor.name(),
            "rectColor": self.rectColor.name(),
            "ellipseColor": self.ellipseColor.name(),
            "textColor": self.textColor.name(),
            "lineColor": self.lineColor.name(),
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
            QShortcut(QKeySequence("L"), self, lambda: self.set_shape("line")),
            QShortcut(QKeySequence("A"), self, lambda: self.set_shape("arrow")),
            QShortcut(QKeySequence("R"), self, lambda: self.set_shape("rectangle")),
            QShortcut(QKeySequence("E"), self, lambda: self.set_shape("ellipse")),
            QShortcut(QKeySequence("T"), self, lambda: self.set_shape("text")),
            QShortcut(QKeySequence("H"), self, self.toggle_halo),
            QShortcut(QKeySequence("F"), self, self.toggle_filled_shapes),
            QShortcut(QKeySequence("O"), self, self.cycle_opacity),
            QShortcut(QKeySequence("C"), self, self.clear_drawings),
            QShortcut(QKeySequence("X"), self, self.export_to_image),
            QShortcut(QKeySequence("Q"), self, self.close),
            QShortcut(QKeySequence("Ctrl+Z"), self, self.undo),
            QShortcut(QKeySequence("Ctrl+Y"), self, self.redo),
            QShortcut(QKeySequence("Ctrl+,"), self, self.show_config_dialog),
            QShortcut(QKeySequence("Shift+F"), self, self.toggle_flashlight),
        ]

    def export_to_image(self):
        if self.show_halo:
            self.toggle_halo()
            self.update()
            QTimer.singleShot(50, lambda: self.actual_capture())
        else:
            self.actual_capture()

    def actual_capture(self):
        screen = QApplication.primaryScreen()
        if screen:
            # Capture only the area covered by the window
            window_rect = self.frameGeometry()
            screen_grab = screen.grabWindow(
                0,
                window_rect.x(),
                window_rect.y(),
                window_rect.width(),
                window_rect.height(),
            )

            # Crop the image to match the window's content
            pixmap = QPixmap(self.size())
            painter = QPainter(pixmap)
            painter.drawPixmap(0, 0, screen_grab)
            painter.end()
            pixmap = pixmap.copy(QRect(window_rect.topLeft(), window_rect.size()))

            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            print("Image copied to clipboard")
        else:
            print("Screen capture failed")

    def cycle_opacity(self):
        self.current_opacity_index = (self.current_opacity_index + 1) % len(
            self.opacity_levels
        )
        self.current_opacity = self.opacity_levels[self.current_opacity_index]
        print(f"Opacity set to {int(self.current_opacity / 255 * 100)}%")

    def disable_shortcuts(self):
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)

    def enable_shortcuts(self):
        for shortcut in self.shortcuts:
            shortcut.setEnabled(True)

    def toggle_filled_shapes(self):
        self.filled_shapes = not self.filled_shapes
        print(f"Filled shapes {'enabled' if self.filled_shapes else 'disabled'}")

    def toggle_halo(self):
        self.show_halo = not self.show_halo
        if self.show_flashlight or self.show_halo:
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

    def get_color_with_opacity(self, color, opacity):
        return QColor(color.red(), color.green(), color.blue(), opacity)

    def paintEvent(self, event):
        if self.show_halo or self.show_flashlight:
            self.update_cursor_pos()

        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)

        qp.setBrush(QColor(0, 0, 0, 1))
        qp.drawRect(self.rect())

        qp.drawPixmap(0, 0, self.drawingLayer)

        if self.currentShape:
            opacity = self.currentShape.get("opacity", self.current_opacity)
            if self.currentShape["type"] == "arrow":
                qp.setPen(
                    QPen(
                        self.get_color_with_opacity(self.arrowColor, opacity),
                        4,
                        Qt.PenStyle.SolidLine,
                    )
                )
                self.draw_arrow(
                    qp, self.currentShape["start"], self.currentShape["end"]
                )
            elif self.currentShape["type"] == "rectangle":
                color = self.get_color_with_opacity(self.rectColor, opacity)
                qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
                if self.filled_shapes:
                    qp.setBrush(color)
                else:
                    qp.setBrush(Qt.BrushStyle.NoBrush)
                qp.drawRect(QRect(self.currentShape["start"], self.currentShape["end"]))
            elif self.currentShape["type"] == "ellipse":
                color = self.get_color_with_opacity(self.ellipseColor, opacity)
                qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
                if self.filled_shapes:
                    qp.setBrush(color)
                else:
                    qp.setBrush(Qt.BrushStyle.NoBrush)
                qp.drawEllipse(
                    QRect(self.currentShape["start"], self.currentShape["end"])
                )
            elif self.currentShape["type"] == "line":
                qp.setPen(
                    QPen(
                        self.get_color_with_opacity(self.lineColor, opacity),
                        4,
                        Qt.PenStyle.SolidLine,
                    )
                )
                qp.drawLine(self.currentShape["start"], self.currentShape["end"])

        if self.is_typing and self.current_text_pos:
            qp.setPen(QPen(self.textColor))
            qp.setFont(self.font)
            qp.drawText(self.current_text_pos, self.current_text)

            if self.show_cursor:
                metrics = qp.fontMetrics()
                text_width = metrics.horizontalAdvance(self.current_text)
                cursor_x = self.current_text_pos.x() + text_width
                cursor_y = self.current_text_pos.y()
                qp.drawText(QPoint(cursor_x, cursor_y), "_")

        if self.show_halo:
            self.draw_halo(qp)
        if self.show_flashlight:
            self.draw_flashlight(qp)

    def get_current_shape_color(self):
        if self.shape == "line":
            return self.lineColor
        elif self.shape == "arrow":
            return self.arrowColor
        elif self.shape == "rectangle":
            return self.rectColor
        elif self.shape == "ellipse":
            return self.ellipseColor
        elif self.shape == "text":
            return self.textColor
        else:
            return QColor(128, 128, 128)  # Default to gray if no shape is selected

    def draw_flashlight(self, qp):
        flashlight_radius = 80  # Large radius for visibility
        cursor_pos_f = QPointF(self.cursor_pos)
        gradient = QRadialGradient(cursor_pos_f, flashlight_radius)
        gradient.setColorAt(0, QColor(255, 255, 0, 120))
        gradient.setColorAt(0.5, QColor(255, 255, 0, 60))
        gradient.setColorAt(1, QColor(255, 255, 0, 0))
        qp.setBrush(gradient)
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawEllipse(cursor_pos_f, flashlight_radius, flashlight_radius)

    def toggle_flashlight(self):
        self.show_flashlight = not self.show_flashlight
        if self.show_flashlight or self.show_halo:
            self.update_timer.start()
        else:
            self.update_timer.stop()
        self.update()
        print(f"Flashlight mode {'enabled' if self.show_flashlight else 'disabled'}")

    def draw_halo(self, qp):
        halo_radius = 20
        cursor_pos_f = QPointF(self.cursor_pos)
        gradient = QRadialGradient(cursor_pos_f, halo_radius)
        shape_color = self.get_current_shape_color()
        darker_color = shape_color.darker(150)
        gradient.setColorAt(
            0,
            QColor(
                shape_color.red(),
                shape_color.green(),
                shape_color.blue(),
                self.current_opacity,
            ),
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
                            "opacity": self.current_opacity,
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
                    "filled": self.filled_shapes,
                    "opacity": self.current_opacity,
                }

    def redraw_shapes(self):
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        qp = QPainter(self.drawingLayer)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        for shape in self.shapes:
            opacity = shape.get("opacity", 128)
            if shape["type"] == "arrow":
                qp.setPen(
                    QPen(
                        self.get_color_with_opacity(self.arrowColor, opacity),
                        4,
                        Qt.PenStyle.SolidLine,
                    )
                )
                self.draw_arrow(qp, shape["start"], shape["end"])
            elif shape["type"] == "rectangle":
                color = self.get_color_with_opacity(self.rectColor, opacity)
                qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
                if shape.get("filled", False):
                    qp.setBrush(color)
                else:
                    qp.setBrush(Qt.BrushStyle.NoBrush)
                qp.drawRect(QRect(shape["start"], shape["end"]))
            elif shape["type"] == "ellipse":
                color = self.get_color_with_opacity(self.ellipseColor, opacity)
                qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
                if shape.get("filled", False):
                    qp.setBrush(color)
                else:
                    qp.setBrush(Qt.BrushStyle.NoBrush)
                qp.drawEllipse(QRect(shape["start"], shape["end"]))
            elif shape["type"] == "line":
                qp.setPen(
                    QPen(
                        self.get_color_with_opacity(self.lineColor, opacity),
                        4,
                        Qt.PenStyle.SolidLine,
                    )
                )
                qp.drawLine(shape["start"], shape["end"])
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
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        # Set a minimum size for the dialog to prevent text cutoff
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

    def init_ui(self):
        self.setWindowTitle("Keyboard Shortcuts")
        layout = QVBoxLayout()
        layout.setSpacing(10)  # Add spacing between elements

        # Create grid layout for shortcuts
        grid = QGridLayout()
        grid.setSpacing(8)  # Add spacing between grid items
        shortcuts = [
            ("L", "Line Tool"),
            ("A", "Arrow Tool"),
            ("R", "Rectangle Tool"),
            ("E", "Ellipse Tool"),
            ("T", "Text Tool"),
            ("H", "Toggle Halo Effect"),
            ("F", "Toggle Filled Shapes"),
            ("O", "Cycle Opacity (100% → 50% → 25%)"),
            ("C", "Clear All Drawings"),
            ("X", "Export to Image"),
            ("Q", "Quit Application"),
            ("Ctrl+Z", "Undo"),
            ("Ctrl+Y", "Redo"),
            ("Ctrl+,", "Show This Dialog"),
        ]

        # Add shortcuts to grid
        for i, (key, description) in enumerate(shortcuts):
            key_label = QLabel(f"<b>{key}</b>")
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)  # Enable word wrap for long descriptions
            grid.addWidget(key_label, i, 0)
            grid.addWidget(desc_label, i, 1)

        # Add color selection buttons
        color_layout = QGridLayout()
        color_layout.setSpacing(8)  # Add spacing between color items
        self.arrow_color = QColorButton(self.parent.arrowColor)
        self.rect_color = QColorButton(self.parent.rectColor)
        self.ellipse_color = QColorButton(self.parent.ellipseColor)
        self.text_color = QColorButton(self.parent.textColor)
        self.line_color = QColorButton(self.parent.lineColor)

        color_layout.addWidget(QLabel("Arrow Color:"), 0, 0)
        color_layout.addWidget(self.arrow_color, 0, 1)
        color_layout.addWidget(QLabel("Rectangle Color:"), 1, 0)
        color_layout.addWidget(self.rect_color, 1, 1)
        color_layout.addWidget(QLabel("Ellipse Color:"), 2, 0)
        color_layout.addWidget(self.ellipse_color, 2, 1)
        color_layout.addWidget(QLabel("Text Color:"), 3, 0)
        color_layout.addWidget(self.text_color, 3, 1)
        color_layout.addWidget(QLabel("Line Color:"), 4, 0)
        color_layout.addWidget(self.line_color, 4, 1)

        layout.addLayout(grid)
        layout.addSpacing(20)  # Add space between shortcuts and color section
        layout.addLayout(color_layout)
        layout.addStretch()  # Add stretch to push everything up
        self.setLayout(layout)

    def closeEvent(self, event):
        self.parent.arrowColor = self.arrow_color.color
        self.parent.rectColor = self.rect_color.color
        self.parent.ellipseColor = self.ellipse_color.color
        self.parent.textColor = self.text_color.color
        self.parent.lineColor = self.line_color.color
        self.parent.save_config()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = TransparentWindow()
    ex.show()
    sys.exit(app.exec())
