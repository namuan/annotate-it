#!/usr/bin/env python3
"""
Monitor Selection Dialog for Annotate-It

Provides a visual interface that displays all available monitors with their
relative positions and allows users to select which monitor to use for the
annotation window.
"""

import sys

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QPen
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget


class MonitorWidget(QFrame):
    """Widget representing a single monitor in the layout."""

    clicked = pyqtSignal(int)  # Emits monitor index when clicked

    def __init__(self, monitor_index, screen, is_primary=False, scale_factor=0.1):
        super().__init__()
        self.monitor_index = monitor_index
        self.screen = screen
        self.is_primary = is_primary
        self.scale_factor = scale_factor
        self.is_selected = False

        # Calculate scaled size for display
        geometry = screen.geometry()
        self.scaled_width = int(geometry.width() * scale_factor)
        self.scaled_height = int(geometry.height() * scale_factor)

        # Ensure minimum size for readability
        min_width = 150
        min_height = 110
        self.scaled_width = max(self.scaled_width, min_width)
        self.scaled_height = max(self.scaled_height, min_height)

        self.setFixedSize(self.scaled_width, self.scaled_height)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Set initial style
        self.update_style()

    def update_style(self):
        """Update the visual style based on selection state."""
        if self.is_selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #4CAF50;
                    border: 3px solid #2E7D32;
                    border-radius: 5px;
                }
            """)
        elif self.is_primary:
            self.setStyleSheet("""
                QFrame {
                    background-color: #E3F2FD;
                    border: 2px solid #1976D2;
                    border-radius: 5px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #F5F5F5;
                    border: 2px solid #757575;
                    border-radius: 5px;
                }
            """)

    def set_selected(self, selected):
        """Set the selection state of this monitor."""
        self.is_selected = selected
        self.update_style()

    def mousePressEvent(self, event):
        """Handle mouse click to select this monitor."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.monitor_index)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Custom paint event to draw monitor information."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Set font for text
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)

        # Draw monitor number
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        number_text = f"Monitor {self.monitor_index + 1}"
        if self.is_primary:
            number_text += " (Primary)"

        painter.drawText(5, 15, number_text)

        # Set regular font for details
        font.setBold(False)
        font.setPointSize(7)
        painter.setFont(font)

        # Draw resolution
        geometry = self.screen.geometry()
        resolution_text = f"Resolution: {geometry.width()}x{geometry.height()}"
        painter.drawText(5, 30, resolution_text)

        # Draw position
        position_text = f"Position: ({geometry.x()}, {geometry.y()})"
        painter.drawText(5, 43, position_text)

        # Draw DPI info
        logical_dpi = self.screen.logicalDotsPerInch()
        physical_dpi = self.screen.physicalDotsPerInch()
        dpi_text = f"DPI: {logical_dpi:.0f} (Physical: {physical_dpi:.0f})"
        painter.drawText(5, 56, dpi_text)

        # Draw device pixel ratio
        dpr = self.screen.devicePixelRatio()
        dpr_text = f"Scale Factor: {dpr:.1f}x"
        painter.drawText(5, 69, dpr_text)

        # Draw refresh rate
        refresh_rate = self.screen.refreshRate()
        refresh_text = f"Refresh: {refresh_rate:.0f}Hz"
        painter.drawText(5, 82, refresh_text)

        # Draw screen name if available
        screen_name = self.screen.name()
        if screen_name and len(screen_name) > 0:
            # Truncate long names
            if len(screen_name) > 20:
                screen_name = screen_name[:17] + "..."
            name_text = f"Name: {screen_name}"
            painter.drawText(5, 95, name_text)


class MonitorSelectionDialog(QDialog):
    """Dialog for selecting which monitor to use for annotations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_monitor_index = 0
        self.monitor_widgets = []
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Select Monitor for Annotations")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Title and instructions
        title_label = QLabel("Select Monitor for Annotation Window")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        instruction_label = QLabel(
            "Click on a monitor below to select it for the annotation overlay. "
            "The layout shows the relative positions of your monitors."
        )
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)

        # Monitor layout area
        self.monitor_layout_widget = QWidget()
        self.monitor_layout_widget.setMinimumHeight(400)
        layout.addWidget(self.monitor_layout_widget)

        # Buttons
        button_layout = QHBoxLayout()

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # Create monitor layout after buttons are created
        self.create_monitor_layout()

    def create_monitor_layout(self):
        """Create the visual layout of monitors with responsive design."""
        app = QApplication.instance()
        screens = app.screens()
        primary_screen = app.primaryScreen()

        if not screens:
            return

        # Analyze monitor configuration
        config_info = self.analyze_monitor_configuration(screens)

        # Adjust dialog size based on configuration
        self.adjust_dialog_size(config_info)

        # Calculate responsive layout parameters
        layout_params = self.calculate_responsive_layout(screens, config_info)

        # Create monitor widgets with responsive sizing
        self.create_monitor_widgets(screens, primary_screen, layout_params)

    def analyze_monitor_configuration(self, screens):
        """Analyze the monitor configuration to determine layout strategy."""
        if len(screens) <= 1:
            return {"type": "single", "complexity": "simple"}

        # Calculate bounding box
        min_x = min(screen.geometry().x() for screen in screens)
        min_y = min(screen.geometry().y() for screen in screens)
        max_x = max(
            screen.geometry().x() + screen.geometry().width() for screen in screens
        )
        max_y = max(
            screen.geometry().y() + screen.geometry().height() for screen in screens
        )

        total_width = max_x - min_x
        total_height = max_y - min_y
        aspect_ratio = total_width / total_height if total_height > 0 else 1.0

        # Determine configuration type
        config_type = (
            "horizontal"
            if aspect_ratio > 2.0
            else "vertical"
            if aspect_ratio < 0.5
            else "mixed"
        )

        # Determine complexity
        complexity = (
            "simple"
            if len(screens) <= 2
            else "moderate"
            if len(screens) <= 4
            else "complex"
        )

        return {
            "type": config_type,
            "complexity": complexity,
            "count": len(screens),
            "total_width": total_width,
            "total_height": total_height,
            "aspect_ratio": aspect_ratio,
            "bounds": (min_x, min_y, max_x, max_y),
        }

    def adjust_dialog_size(self, config_info):
        """Adjust dialog size based on monitor configuration."""
        base_width = 800
        base_height = 600

        # Adjust based on configuration type
        if config_info["type"] == "horizontal":
            # Wide layout for horizontal arrangements
            width = min(1200, base_width + config_info["count"] * 100)
            height = base_height
        elif config_info["type"] == "vertical":
            # Tall layout for vertical arrangements
            width = base_width
            height = min(900, base_height + config_info["count"] * 80)
        else:
            # Balanced layout for mixed arrangements
            width = min(1000, base_width + config_info["count"] * 50)
            height = min(800, base_height + config_info["count"] * 40)

        # Adjust for complexity
        if config_info["complexity"] == "complex":
            width = min(width * 1.2, 1400)
            height = min(height * 1.2, 1000)

        self.resize(int(width), int(height))

    def calculate_responsive_layout(self, screens, config_info):
        """Calculate responsive layout parameters."""
        # Get available space (accounting for margins and other UI elements)
        dialog_size = self.size()
        available_width = dialog_size.width() - 100  # Margins
        available_height = dialog_size.height() - 250  # Title, buttons, margins

        # Ensure minimum available space
        available_width = max(available_width, 400)
        available_height = max(available_height, 300)

        total_width = config_info["total_width"]
        total_height = config_info["total_height"]

        # Calculate scale factors
        scale_x = available_width / total_width if total_width > 0 else 0.1
        scale_y = available_height / total_height if total_height > 0 else 0.1

        # Choose appropriate scale factor based on configuration
        if config_info["type"] == "horizontal":
            # Prioritize width for horizontal layouts
            scale_factor = min(scale_x, scale_y * 1.2, 0.25)
        elif config_info["type"] == "vertical":
            # Prioritize height for vertical layouts
            scale_factor = min(scale_x * 1.2, scale_y, 0.25)
        else:
            # Balanced scaling for mixed layouts
            scale_factor = min(scale_x, scale_y, 0.2)

        # Adjust minimum scale based on complexity
        min_scale = 0.05 if config_info["complexity"] == "complex" else 0.08
        scale_factor = max(scale_factor, min_scale)

        return {
            "scale_factor": scale_factor,
            "available_width": available_width,
            "available_height": available_height,
            "margin_x": 50,
            "margin_y": 50,
        }

    def create_monitor_widgets(self, screens, primary_screen, layout_params):
        """Create monitor widgets with responsive positioning."""
        min_x, min_y, max_x, max_y = self.analyze_monitor_configuration(screens)[
            "bounds"
        ]
        scale_factor = layout_params["scale_factor"]
        margin_x = layout_params["margin_x"]
        margin_y = layout_params["margin_y"]

        # Create monitor widgets and position them
        for i, screen in enumerate(screens):
            is_primary = screen == primary_screen
            monitor_widget = MonitorWidget(i, screen, is_primary, scale_factor)
            monitor_widget.clicked.connect(self.on_monitor_selected)

            # Calculate position relative to the layout
            geometry = screen.geometry()
            rel_x = geometry.x() - min_x
            rel_y = geometry.y() - min_y

            scaled_x = int(rel_x * scale_factor)
            scaled_y = int(rel_y * scale_factor)

            # Position the widget with responsive margins
            monitor_widget.setParent(self.monitor_layout_widget)
            monitor_widget.move(scaled_x + margin_x, scaled_y + margin_y)
            monitor_widget.show()

            self.monitor_widgets.append(monitor_widget)

        # Update layout widget size to accommodate all monitors
        self.update_layout_widget_size(layout_params)

        # Select primary monitor by default
        primary_index = 0
        for i, screen in enumerate(screens):
            if screen == primary_screen:
                primary_index = i
                break

        self.on_monitor_selected(primary_index)

    def update_layout_widget_size(self, layout_params):
        """Update the layout widget size to fit all monitor widgets."""
        if not self.monitor_widgets:
            return

        # Calculate required size based on monitor widget positions and sizes
        max_x = 0
        max_y = 0

        for widget in self.monitor_widgets:
            widget_rect = widget.geometry()
            max_x = max(max_x, widget_rect.x() + widget_rect.width())
            max_y = max(max_y, widget_rect.y() + widget_rect.height())

        # Add some padding
        required_width = max_x + layout_params["margin_x"]
        required_height = max_y + layout_params["margin_y"]

        # Ensure minimum size
        required_width = max(required_width, layout_params["available_width"])
        required_height = max(required_height, layout_params["available_height"])

        self.monitor_layout_widget.setMinimumSize(required_width, required_height)

    def on_monitor_selected(self, monitor_index):
        """Handle monitor selection."""
        self.selected_monitor_index = monitor_index

        # Update visual selection
        for i, widget in enumerate(self.monitor_widgets):
            widget.set_selected(i == monitor_index)

        # Update OK button text
        self.ok_button.setText(f"Use Monitor {monitor_index + 1}")