#!/usr/bin/env python3
"""
Magnifier Coordinate System Test

This script tests the coordinate transformation behavior of the magnifier
functionality across multiple monitors to identify issues with the zoom
window on secondary displays.

Hypothesis: The magnifier's coordinate system calculations are incorrect
when the application window is positioned on a secondary monitor, causing
the zoom window to show content from the wrong screen region.
"""

import logging
import sys
from pathlib import Path

# Add the parent directory to the path to import main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import QPoint, QTimer
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class MagnifierCoordinateTest(QWidget):
    """Test widget to analyze magnifier coordinate behavior across monitors."""

    def __init__(self):
        super().__init__()
        self.current_screen_index = 0
        self.screens = QApplication.screens()
        self.init_ui()
        self.setup_timer()

        # Logging setup
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Magnifier Coordinate System Test")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        # Screen info section
        screen_layout = QHBoxLayout()
        self.screen_label = QLabel("Current Screen: N/A")
        self.screen_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        screen_layout.addWidget(self.screen_label)

        self.move_button = QPushButton("Move to Next Screen")
        self.move_button.clicked.connect(self.move_to_next_screen)
        screen_layout.addWidget(self.move_button)

        layout.addLayout(screen_layout)

        # Coordinate info section
        coord_layout = QVBoxLayout()

        self.global_cursor_label = QLabel("Global Cursor: (0, 0)")
        self.window_cursor_label = QLabel("Window-Relative Cursor: (0, 0)")
        self.window_geometry_label = QLabel("Window Geometry: (0, 0, 0, 0)")
        self.screen_geometry_label = QLabel("Screen Geometry: (0, 0, 0, 0)")
        self.dpi_info_label = QLabel("DPI Info: N/A")

        for label in [
            self.global_cursor_label,
            self.window_cursor_label,
            self.window_geometry_label,
            self.screen_geometry_label,
            self.dpi_info_label,
        ]:
            label.setFont(QFont("Courier", 10))
            coord_layout.addWidget(label)

        layout.addLayout(coord_layout)

        # Analysis output
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Courier", 9))
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        # Test buttons
        button_layout = QHBoxLayout()

        self.analyze_button = QPushButton("Analyze Current Position")
        self.analyze_button.clicked.connect(self.analyze_coordinates)
        button_layout.addWidget(self.analyze_button)

        self.clear_button = QPushButton("Clear Output")
        self.clear_button.clicked.connect(self.output_text.clear)
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initial screen detection
        self.update_screen_info()

    def setup_timer(self):
        """Setup timer for real-time coordinate updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_coordinates)
        self.update_timer.start(100)  # Update every 100ms

    def update_coordinates(self):
        """Update coordinate displays in real-time."""
        # Global cursor position
        global_pos = QCursor.pos()
        self.global_cursor_label.setText(f"Global Cursor: ({global_pos.x()}, {global_pos.y()})")

        # Window-relative cursor position
        window_pos = self.mapFromGlobal(global_pos)
        self.window_cursor_label.setText(f"Window-Relative Cursor: ({window_pos.x()}, {window_pos.y()})")

        # Window geometry
        geom = self.frameGeometry()
        self.window_geometry_label.setText(
            f"Window Geometry: ({geom.x()}, {geom.y()}, {geom.width()}, {geom.height()})"
        )

        # Current screen info
        current_screen = self.screen()
        if current_screen:
            screen_geom = current_screen.geometry()
            self.screen_geometry_label.setText(
                f"Screen Geometry: ({screen_geom.x()}, {screen_geom.y()}, {screen_geom.width()}, {screen_geom.height()})"
            )

            dpr = current_screen.devicePixelRatio()
            logical_dpi = current_screen.logicalDotsPerInch()
            self.dpi_info_label.setText(f"DPI Info: Ratio={dpr:.2f}, Logical DPI={logical_dpi:.1f}")

    def update_screen_info(self):
        """Update screen information display."""
        if self.screens:
            current_screen = self.screen()
            screen_name = current_screen.name() if current_screen else "Unknown"
            screen_index = self.screens.index(current_screen) if current_screen in self.screens else -1
            self.screen_label.setText(f"Current Screen: {screen_index + 1}/{len(self.screens)} - {screen_name}")

    def move_to_next_screen(self):
        """Move window to the next available screen."""
        if len(self.screens) <= 1:
            self.output_text.append("Only one screen available - cannot test multi-monitor behavior")
            return

        # Move to next screen
        self.current_screen_index = (self.current_screen_index + 1) % len(self.screens)
        target_screen = self.screens[self.current_screen_index]

        # Get the geometry of the target screen
        screen_geometry = target_screen.availableGeometry()

        # Move window to the center of the target screen
        window_size = self.size()
        x = screen_geometry.x() + (screen_geometry.width() - window_size.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - window_size.height()) // 2

        self.move(x, y)

        # Log the move
        self.output_text.append(f"\n=== MOVED TO SCREEN {self.current_screen_index + 1} ===")
        self.output_text.append(f"Target Screen: {target_screen.name()}")
        self.output_text.append(f"Screen Geometry: {screen_geometry}")
        self.output_text.append(f"Window moved to: ({x}, {y})")

        # Update screen info
        QTimer.singleShot(100, self.update_screen_info)  # Delay to allow window move to complete

    def analyze_coordinates(self):
        """Perform detailed coordinate analysis for magnifier behavior."""
        self.output_text.append("\n=== COORDINATE ANALYSIS ===")

        # Current state
        global_cursor = QCursor.pos()
        window_cursor = self.mapFromGlobal(global_cursor)
        window_geom = self.frameGeometry()
        current_screen = self.screen()

        if not current_screen:
            self.output_text.append("ERROR: Cannot determine current screen")
            return

        screen_geom = current_screen.geometry()
        dpr = current_screen.devicePixelRatio()

        self.output_text.append(f"Screen: {current_screen.name()}")
        self.output_text.append(f"Screen Geometry: {screen_geom}")
        self.output_text.append(f"Window Geometry: {window_geom}")
        self.output_text.append(f"Device Pixel Ratio: {dpr}")
        self.output_text.append(f"Global Cursor: {global_cursor}")
        self.output_text.append(f"Window-Relative Cursor: {window_cursor}")

        # Simulate magnifier coordinate calculations
        self.output_text.append("\n--- MAGNIFIER COORDINATE SIMULATION ---")

        # This simulates the logic from the main application
        center = window_cursor  # This is what the magnifier uses as center
        radius = 120  # Default magnifier radius
        factor = 2.0  # Magnification factor

        # Calculate what the magnifier would capture
        center_px = QPoint(int(round(center.x() * dpr)), int(round(center.y() * dpr)))
        src_size_px = max(1, int(round((2 * radius * dpr) / max(0.01, factor))))

        # The key issue: where does the screen capture come from?
        # The current implementation uses CGWindowListCreateImage with CGRectInfinite
        # which captures the entire virtual desktop, then crops based on window geometry

        self.output_text.append(f"Magnifier center (window coords): {center}")
        self.output_text.append(f"Magnifier center (pixel coords): {center_px}")
        self.output_text.append(f"Source capture size: {src_size_px}x{src_size_px} pixels")

        # Calculate the actual screen region that would be captured
        # This is the potential bug area
        capture_x = window_geom.x() + center.x()
        capture_y = window_geom.y() + center.y()

        self.output_text.append("\n--- POTENTIAL ISSUE ANALYSIS ---")
        self.output_text.append(f"Expected capture center (global): ({capture_x}, {capture_y})")

        # Check if this falls within the current screen
        if (
            screen_geom.x() <= capture_x <= screen_geom.x() + screen_geom.width()
            and screen_geom.y() <= capture_y <= screen_geom.y() + screen_geom.height()
        ):
            self.output_text.append("✅ Capture center is within current screen bounds")
        else:
            self.output_text.append("❌ ISSUE: Capture center is OUTSIDE current screen bounds!")

            # Find which screen it would actually capture from
            for i, screen in enumerate(self.screens):
                sg = screen.geometry()
                if sg.x() <= capture_x <= sg.x() + sg.width() and sg.y() <= capture_y <= sg.y() + sg.height():
                    self.output_text.append(f"   Would capture from Screen {i + 1}: {screen.name()}")
                    break
            else:
                self.output_text.append("   Capture point doesn't fall on any screen!")

        # Additional analysis for coordinate system issues
        self.output_text.append("\n--- COORDINATE SYSTEM ANALYSIS ---")

        # Check for negative coordinates (common in multi-monitor setups)
        if screen_geom.x() < 0 or screen_geom.y() < 0:
            self.output_text.append(f"⚠️  Screen has negative coordinates: ({screen_geom.x()}, {screen_geom.y()})")
            self.output_text.append("   This can cause coordinate transformation issues")

        # Check for DPI scaling differences
        primary_screen = QApplication.primaryScreen()
        if primary_screen and primary_screen != current_screen:
            primary_dpr = primary_screen.devicePixelRatio()
            if abs(primary_dpr - dpr) > 0.1:
                self.output_text.append("⚠️  DPI scaling difference detected:")
                self.output_text.append(f"   Primary screen DPR: {primary_dpr}")
                self.output_text.append(f"   Current screen DPR: {dpr}")
                self.output_text.append("   This can cause scaling issues in screen capture")


def main():
    """Main function to run the coordinate test."""
    app = QApplication(sys.argv)

    # Check if we have multiple monitors
    screens = app.screens()
    print(f"Detected {len(screens)} screen(s)")

    if len(screens) < 2:
        print("WARNING: Only one screen detected. Multi-monitor testing not possible.")
        print("Connect a second monitor to fully test the magnifier coordinate issue.")

    test_widget = MagnifierCoordinateTest()
    test_widget.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
