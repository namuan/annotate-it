import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QPoint
from PyQt6.QtCore import QPointF
from PyQt6.QtCore import QRect
from PyQt6.QtCore import QRectF
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QCursor
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QKeySequence
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QPainterPath
from PyQt6.QtGui import QPen
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QRadialGradient
from PyQt6.QtGui import QShortcut
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QColorDialog
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from monitor_selection_dialog import MonitorSelectionDialog


class ConfigManager:
    """Manages loading and saving of application configuration."""

    def __init__(self, app_name="annotate_it"):
        self.app_name = app_name
        self.config_file = self.get_config_dir() / "config.json"

    def get_config_dir(self):
        """Determine the configuration directory based on the platform."""
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
        """Load configuration from file if it exists, otherwise return empty dict."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error loading config: {e}")
                return {}
        return {}

    def save_config(self, config):
        """Save configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
        except OSError as e:
            print(f"Error saving config: {e}")


class QColorButton(QPushButton):
    """A button that displays a color and allows selection via color dialog."""

    def __init__(self, color):
        super().__init__()
        self.setFixedSize(50, 24)
        self.color = color
        self.setStyleSheet(f"background-color: {color.name()}")

    def mousePressEvent(self, e):
        """Open color dialog on mouse press."""
        color = QColorDialog.getColor(self.color)
        if color.isValid():
            self.color = color
            self.setStyleSheet(f"background-color: {self.color.name()}")
            self.update()


class TransparentWindow(QWidget):
    """Main transparent window for drawing annotations on screen."""

    default_font_family: str = "HanziPen TC"
    default_font_size: int = 36

    def __init__(self, target_screen=None):
        super().__init__()
        self.target_screen = target_screen
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
        self.show_mouse_mask = False
        self.mouse_mask_radius = 100
        self.mouse_mask_alpha = 128
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
        """Toggle cursor visibility for text input."""
        if self.is_typing:
            self.show_cursor = not self.show_cursor
            self.update()

    def load_config(self):
        """Load colors and shape from config."""
        config = self.config_manager.load_config()
        self.shape = config.get("shape", "arrow")
        self.arrowColor = QColor(config.get("arrowColor", "#00FF00"))
        self.rectColor = QColor(config.get("rectColor", "#FF1493"))
        self.ellipseColor = QColor(config.get("ellipseColor", "#00BFFF"))
        self.textColor = QColor(config.get("textColor", "#AA26FF"))
        self.lineColor = QColor(config.get("lineColor", "#FFFF00"))

    def save_config(self):
        """Save current colors and shape to config."""
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
        """Save config on close."""
        self.save_config()
        super().closeEvent(event)

    def init_ui(self):
        """Initialize UI settings and shortcuts."""
        self.setWindowTitle("Transparent Drawing")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Position window on target screen or maximize on primary screen
        if self.target_screen:
            screen_geometry = self.target_screen.geometry()
            self.setGeometry(screen_geometry)
        else:
            self.showMaximized()

        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        self.shortcuts = [
            QShortcut(QKeySequence("L"), self, lambda: self.set_shape("line")),
            QShortcut(QKeySequence("A"), self, lambda: self.set_shape("arrow")),
            QShortcut(QKeySequence("R"), self, lambda: self.set_shape("rectangle")),
            QShortcut(QKeySequence("E"), self, lambda: self.set_shape("ellipse")),
            QShortcut(QKeySequence("T"), self, lambda: self.set_shape("text")),
            QShortcut(QKeySequence("H"), self, self.toggle_halo),
            QShortcut(QKeySequence("M"), self, self.toggle_mouse_mask),
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
        """Export current drawing to clipboard as image."""
        if self.show_halo:
            self.toggle_halo()
            self.update()
            QTimer.singleShot(50, self._actual_capture)
        else:
            self._actual_capture()

    def _actual_capture(self):
        """Perform the actual screen capture."""
        screen = QApplication.primaryScreen()
        if screen:
            window_rect = self.frameGeometry()
            screen_grab = screen.grabWindow(
                0,
                window_rect.x(),
                window_rect.y(),
                window_rect.width(),
                window_rect.height(),
            )

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
        """Cycle through opacity levels."""
        self.current_opacity_index = (self.current_opacity_index + 1) % len(
            self.opacity_levels
        )
        self.current_opacity = self.opacity_levels[self.current_opacity_index]
        print(f"Opacity set to {int(self.current_opacity / 255 * 100)}%")

    def disable_shortcuts(self):
        """Disable all shortcuts."""
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)

    def enable_shortcuts(self):
        """Enable all shortcuts."""
        for shortcut in self.shortcuts:
            shortcut.setEnabled(True)

    def toggle_filled_shapes(self):
        """Toggle filled shapes mode."""
        self.filled_shapes = not self.filled_shapes
        print(f"Filled shapes {'enabled' if self.filled_shapes else 'disabled'}")

    def toggle_halo(self):
        """Toggle halo effect around cursor."""
        self.show_halo = not self.show_halo
        self._manage_update_timer()
        self.update()
        print(f"Halo effect {'enabled' if self.show_halo else 'disabled'}")

    def toggle_mouse_mask(self):
        """Toggle mouse mask effect."""
        self.show_mouse_mask = not self.show_mouse_mask
        self._manage_update_timer()
        self.update()
        print(f"Mouse mask {'enabled' if self.show_mouse_mask else 'disabled'}")

    def _manage_update_timer(self):
        """Start or stop update timer based on active effects."""
        if self.show_flashlight or self.show_halo or self.show_mouse_mask:
            self.update_timer.start()
        else:
            self.update_timer.stop()

    def show_config_dialog(self):
        """Show configuration dialog."""
        dialog = ConfigDialog(self)
        dialog.exec()
        self.redraw_shapes()

    def set_shape(self, shape):
        """Set current drawing shape."""
        self.shape = shape
        self.save_config()
        print(f"Current shape: {self.shape}")

    def clear_drawings(self):
        """Clear all drawings."""
        if self.shapes:
            self.undoStack.append(self.shapes.copy())
            self.shapes.clear()
            self.redoStack.clear()
            self.drawingLayer.fill(Qt.GlobalColor.transparent)
            self.update()
            print("Drawings cleared")

    def undo(self):
        """Undo last action."""
        if self.shapes:
            self.redoStack.append(self.shapes.copy())
            self.shapes = self.undoStack.pop() if self.undoStack else []
            self.redraw_shapes()
            self.update()
            print("Undo")

    def redo(self):
        """Redo last undone action."""
        if self.redoStack:
            self.undoStack.append(self.shapes.copy())
            self.shapes = self.redoStack.pop()
            self.redraw_shapes()
            self.update()
            print("Redo")

    def update_cursor_pos(self):
        """Update cursor position relative to window."""
        self.cursor_pos = self.mapFromGlobal(QCursor.pos())

    def get_color_with_opacity(self, color, opacity):
        """Return color with specified opacity."""
        return QColor(color.red(), color.green(), color.blue(), opacity)

    def paintEvent(self, event):
        """Handle painting of the window."""
        if self.show_halo or self.show_flashlight or self.show_mouse_mask:
            self.update_cursor_pos()

        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)

        qp.setBrush(QColor(0, 0, 0, 1))
        qp.drawRect(self.rect())

        qp.drawPixmap(0, 0, self.drawingLayer)

        if self.currentShape:
            self._draw_current_shape(qp)

        if self.is_typing and self.current_text_pos:
            self._draw_current_text(qp)

        if self.show_halo:
            self.draw_halo(qp)
        if self.show_flashlight:
            self.draw_flashlight(qp)
        if self.show_mouse_mask:
            self.draw_mouse_mask(qp)

    def _draw_current_shape(self, qp):
        """Draw the current shape being created."""
        opacity = self.currentShape.get("opacity", self.current_opacity)
        shape_type = self.currentShape["type"]
        start = self.currentShape["start"]
        end = self.currentShape["end"]

        if shape_type == "arrow":
            qp.setPen(
                QPen(
                    self.get_color_with_opacity(self.arrowColor, opacity),
                    4,
                    Qt.PenStyle.SolidLine,
                )
            )
            self.draw_arrow(qp, start, end)
        elif shape_type == "rectangle":
            color = self.get_color_with_opacity(self.rectColor, opacity)
            qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            qp.setBrush(color if self.filled_shapes else Qt.BrushStyle.NoBrush)
            qp.drawRect(QRect(start, end))
        elif shape_type == "ellipse":
            color = self.get_color_with_opacity(self.ellipseColor, opacity)
            qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            qp.setBrush(color if self.filled_shapes else Qt.BrushStyle.NoBrush)
            qp.drawEllipse(QRect(start, end))
        elif shape_type == "line":
            qp.setPen(
                QPen(
                    self.get_color_with_opacity(self.lineColor, opacity),
                    4,
                    Qt.PenStyle.SolidLine,
                )
            )
            qp.drawLine(start, end)

    def _draw_current_text(self, qp):
        """Draw the current text being typed."""
        qp.setPen(QPen(self.textColor))
        qp.setFont(self.font)
        qp.drawText(self.current_text_pos, self.current_text)

        if self.show_cursor:
            metrics = qp.fontMetrics()
            text_width = metrics.horizontalAdvance(self.current_text)
            cursor_x = self.current_text_pos.x() + text_width
            cursor_y = self.current_text_pos.y()
            qp.drawText(QPoint(cursor_x, cursor_y), "_")

    def get_current_shape_color(self):
        """Get color for current shape."""
        shape_colors = {
            "line": self.lineColor,
            "arrow": self.arrowColor,
            "rectangle": self.rectColor,
            "ellipse": self.ellipseColor,
            "text": self.textColor,
        }
        return shape_colors.get(self.shape, QColor(128, 128, 128))

    def draw_flashlight(self, qp):
        """Draw flashlight effect around cursor."""
        flashlight_radius = 80
        cursor_pos_f = QPointF(self.cursor_pos)
        gradient = QRadialGradient(cursor_pos_f, flashlight_radius)
        gradient.setColorAt(0, QColor(255, 255, 0, 120))
        gradient.setColorAt(0.5, QColor(255, 255, 0, 60))
        gradient.setColorAt(1, QColor(255, 255, 0, 0))
        qp.setBrush(gradient)
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawEllipse(cursor_pos_f, flashlight_radius, flashlight_radius)

    def toggle_flashlight(self):
        """Toggle flashlight effect."""
        self.show_flashlight = not self.show_flashlight
        self._manage_update_timer()
        self.update()
        print(f"Flashlight {'enabled' if self.show_flashlight else 'disabled'}")

    def draw_halo(self, qp):
        """Draw halo effect around cursor."""
        halo_radius = 20
        cursor_pos_f = QPointF(self.cursor_pos)
        gradient = QRadialGradient(cursor_pos_f, halo_radius)
        shape_color = self.get_current_shape_color()
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
            1, QColor(shape_color.red(), shape_color.green(), shape_color.blue(), 75)
        )
        qp.setBrush(gradient)
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawEllipse(cursor_pos_f, halo_radius, halo_radius)

    def draw_mouse_mask(self, qp):
        """Draw mouse mask effect."""
        outer_path = QPainterPath()
        outer_path.addRect(QRectF(self.rect()))

        inner_path = QPainterPath()
        center = QPointF(self.cursor_pos)
        radius = self.mouse_mask_radius
        inner_path.addEllipse(center, radius, radius)
        mask_path = outer_path.subtracted(inner_path)
        qp.fillPath(mask_path, QColor(0, 0, 0, self.mouse_mask_alpha))

    def focusOutEvent(self, event):
        """Handle focus loss during text input."""
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
            self.current_text = ""
            self.current_text_pos = None
            self.is_typing = False
            self.enable_shortcuts()
            self.update()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        """Handle key presses for text input."""
        if self.is_typing:
            if event.key() == Qt.Key.Key_Return:
                if self.current_text:
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
                self.current_text = ""
                self.current_text_pos = None
                self.is_typing = False
                self.enable_shortcuts()
            elif event.key() == Qt.Key.Key_Escape:
                self.current_text = ""
                self.current_text_pos = None
                self.is_typing = False
                self.enable_shortcuts()
            elif event.key() == Qt.Key.Key_Backspace:
                self.current_text = self.current_text[:-1]
            else:
                self.current_text += event.text()
            self.show_cursor = True
            self.update()

    def mousePressEvent(self, event):
        """Handle mouse press for starting drawings or text."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.shape == "text":
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
        """Redraw all shapes on the drawing layer."""
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        qp = QPainter(self.drawingLayer)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        for shape in self.shapes:
            self._draw_shape(qp, shape)
        qp.end()

    def _draw_shape(self, qp, shape):
        """Draw a single shape on the painter."""
        opacity = shape.get("opacity", 128)
        shape_type = shape["type"]

        if shape_type == "arrow":
            qp.setPen(
                QPen(
                    self.get_color_with_opacity(self.arrowColor, opacity),
                    4,
                    Qt.PenStyle.SolidLine,
                )
            )
            self.draw_arrow(qp, shape["start"], shape["end"])
        elif shape_type == "rectangle":
            color = self.get_color_with_opacity(self.rectColor, opacity)
            qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            qp.setBrush(color if shape.get("filled", False) else Qt.BrushStyle.NoBrush)
            qp.drawRect(QRect(shape["start"], shape["end"]))
        elif shape_type == "ellipse":
            color = self.get_color_with_opacity(self.ellipseColor, opacity)
            qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            qp.setBrush(color if shape.get("filled", False) else Qt.BrushStyle.NoBrush)
            qp.drawEllipse(QRect(shape["start"], shape["end"]))
        elif shape_type == "line":
            qp.setPen(
                QPen(
                    self.get_color_with_opacity(self.lineColor, opacity),
                    4,
                    Qt.PenStyle.SolidLine,
                )
            )
            qp.drawLine(shape["start"], shape["end"])
        elif shape_type == "text":
            qp.setPen(QPen(self.textColor))
            qp.setFont(self.font)
            qp.drawText(shape["position"], shape["text"])

    def mouseMoveEvent(self, event):
        """Handle mouse movement for updating cursor and drawing."""
        self.cursor_pos = event.position().toPoint()
        if self.drawing:
            self.currentShape["end"] = self.cursor_pos
        self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release for completing drawings."""
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
        """Draw an arrow from start to end."""
        qp.drawLine(start, end)

        arrow_size = 10
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
            return

        dx, dy = dx / length, dy / length

        left = QPoint(
            int(end.x() - arrow_size * (dx + dy)),
            int(end.y() - arrow_size * (dy - dx)),
        )
        right = QPoint(
            int(end.x() - arrow_size * (dx - dy)),
            int(end.y() - arrow_size * (dy + dx)),
        )

        qp.drawLine(end, left)
        qp.drawLine(end, right)

    def resizeEvent(self, event):
        """Handle window resize by updating drawing layer."""
        self.drawingLayer = QPixmap(self.size())
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        self.redraw_shapes()
        super().resizeEvent(event)


class ConfigDialog(QDialog):
    """Dialog for configuring shortcuts and colors."""

    def __init__(self, parent: TransparentWindow):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

    def init_ui(self):
        """Initialize UI for config dialog."""
        self.setWindowTitle("Keyboard Shortcuts")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(8)
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
            ("M", "Toggle Mouse Mask"),
        ]

        for i, (key, description) in enumerate(shortcuts):
            key_label = QLabel(f"<b>{key}</b>")
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            grid.addWidget(key_label, i, 0)
            grid.addWidget(desc_label, i, 1)

        color_layout = QGridLayout()
        color_layout.setSpacing(8)
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
        layout.addSpacing(20)
        layout.addLayout(color_layout)
        layout.addStretch()
        self.setLayout(layout)

    def closeEvent(self, event):
        """Update parent colors on close."""
        self.parent.arrowColor = self.arrow_color.color
        self.parent.rectColor = self.rect_color.color
        self.parent.ellipseColor = self.ellipse_color.color
        self.parent.textColor = self.text_color.color
        self.parent.lineColor = self.line_color.color
        self.parent.save_config()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Show monitor selection dialog if multiple monitors are available
    screens = app.screens()
    target_screen = None
    
    if len(screens) > 1:
        dialog = MonitorSelectionDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            target_screen = dialog.get_selected_screen()
        else:
            # User cancelled, exit application
            sys.exit(0)
    
    # Create and show the main window
    ex = TransparentWindow(target_screen)
    ex.show()
    sys.exit(app.exec())
