import sys

from PyQt6.QtCore import QPoint
from PyQt6.QtCore import QRect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QKeySequence
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QPen
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QShortcut
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtWidgets import QWidget


class TransparentWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.shapes = []
        self.init_ui()
        self.drawing = False
        self.lastPoint = QPoint()
        self.shape = "arrow"  # Default to arrow
        self.currentShape = None
        self.undoStack = []
        self.redoStack = []
        self.arrowColor = QColor(0, 255, 0)  # Fluorescent green
        self.rectColor = QColor(255, 20, 147)  # Fluorescent pink
        self.ellipseColor = QColor(0, 191, 255)  # Deep sky blue
        self.textColor = QColor(50, 50, 50)  # Dark gray
        self.font = QFont("Fantasque Sans Mono", 18)
        self.drawingLayer = QPixmap(self.size())
        self.drawingLayer.fill(Qt.GlobalColor.transparent)

    def init_ui(self):
        self.setWindowTitle("Transparent Drawing")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showMaximized()

        # Setup shortcuts
        QShortcut(QKeySequence("A"), self, lambda: self.set_shape("arrow"))
        QShortcut(QKeySequence("R"), self, lambda: self.set_shape("rectangle"))
        QShortcut(QKeySequence("E"), self, lambda: self.set_shape("ellipse"))
        QShortcut(QKeySequence("T"), self, lambda: self.set_shape("text"))
        QShortcut(QKeySequence("C"), self, self.clear_drawings)
        QShortcut(QKeySequence("Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)

    def set_shape(self, shape):
        self.shape = shape
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

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the semi-transparent background
        qp.setBrush(QColor(0, 0, 0, 10))  # 40% opacity
        qp.drawRect(self.rect())

        # Draw the shapes layer
        qp.drawPixmap(0, 0, self.drawingLayer)

        # Draw the current shape being drawn
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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.shape == "text":
                self.add_text(event.position().toPoint())
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
        if self.drawing:
            self.currentShape["end"] = event.position().toPoint()
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
        text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = TransparentWindow()
    ex.show()
    sys.exit(app.exec())
