#!/usr/bin/env python3
"""
Test script for PyQt6 multi-monitor coordinate system differences
Demonstrates how coordinates work across different monitor arrangements
"""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class CoordinateSystemTest(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.analyze_coordinate_systems()

    def initUI(self):
        self.setWindowTitle("PyQt6 Multi-Monitor Coordinate System Analysis")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Multi-Monitor Coordinate System Analysis")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        # Text area for detailed analysis
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        layout.addWidget(self.analysis_text)

        # Buttons for testing
        refresh_btn = QPushButton("Refresh Analysis")
        refresh_btn.clicked.connect(self.analyze_coordinate_systems)
        layout.addWidget(refresh_btn)

        test_positioning_btn = QPushButton("Test Window Positioning")
        test_positioning_btn.clicked.connect(self.test_window_positioning)
        layout.addWidget(test_positioning_btn)

        self.setLayout(layout)

    def analyze_coordinate_systems(self):
        """Analyze coordinate systems across all available screens"""
        app = QApplication.instance()
        screens = app.screens()
        primary_screen = app.primaryScreen()

        analysis = "=== MULTI-MONITOR COORDINATE SYSTEM ANALYSIS ===\n\n"

        # Basic screen information
        analysis += f"Total screens detected: {len(screens)}\n"
        analysis += f"Primary screen: {primary_screen.name() if primary_screen else 'None'}\n\n"

        # Virtual desktop information
        if screens:
            virtual_geometry = screens[0].virtualGeometry()
            analysis += f"Virtual Desktop Geometry: {virtual_geometry}\n"
            analysis += f"Virtual Desktop Size: {virtual_geometry.width()}x{virtual_geometry.height()}\n\n"

        # Detailed analysis for each screen
        analysis += "=== INDIVIDUAL SCREEN COORDINATE ANALYSIS ===\n\n"

        for i, screen in enumerate(screens):
            is_primary = screen == primary_screen
            analysis += f"Screen {i + 1} {'(PRIMARY)' if is_primary else ''}:\n"
            analysis += f"  Name: {screen.name()}\n"

            # Geometry analysis
            geometry = screen.geometry()
            available_geometry = screen.availableGeometry()

            analysis += f"  Full Geometry: {geometry}\n"
            analysis += f"    - Position: ({geometry.x()}, {geometry.y()})\n"
            analysis += f"    - Size: {geometry.width()}x{geometry.height()}\n"

            analysis += f"  Available Geometry: {available_geometry}\n"
            analysis += f"    - Position: ({available_geometry.x()}, {available_geometry.y()})\n"
            analysis += f"    - Size: {available_geometry.width()}x{available_geometry.height()}\n"

            # Coordinate system analysis
            analysis += "  Coordinate System Analysis:\n"
            if geometry.x() < 0:
                analysis += "    - NEGATIVE X coordinate: Screen is positioned LEFT of primary\n"
            elif geometry.x() > 0:
                analysis += "    - POSITIVE X coordinate: Screen is positioned RIGHT of primary\n"
            else:
                analysis += "    - ZERO X coordinate: Screen aligns with primary horizontally\n"

            if geometry.y() < 0:
                analysis += "    - NEGATIVE Y coordinate: Screen is positioned ABOVE primary\n"
            elif geometry.y() > 0:
                analysis += "    - POSITIVE Y coordinate: Screen is positioned BELOW primary\n"
            else:
                analysis += "    - ZERO Y coordinate: Screen aligns with primary vertically\n"

            # Corner coordinates
            analysis += "  Corner Coordinates:\n"
            analysis += f"    - Top-Left: ({geometry.x()}, {geometry.y()})\n"
            analysis += f"    - Top-Right: ({geometry.x() + geometry.width() - 1}, {geometry.y()})\n"
            analysis += f"    - Bottom-Left: ({geometry.x()}, {geometry.y() + geometry.height() - 1})\n"
            analysis += (
                f"    - Bottom-Right: ({geometry.x() + geometry.width() - 1}, {geometry.y() + geometry.height() - 1})\n"
            )

            # Virtual siblings
            virtual_siblings = screen.virtualSiblings()
            analysis += f"  Virtual Siblings: {len(virtual_siblings)} screens\n"

            analysis += "\n"

        # Coordinate system implications
        analysis += "=== COORDINATE SYSTEM IMPLICATIONS ===\n\n"

        analysis += "Key Points About Multi-Monitor Coordinates:\n"
        analysis += "1. PRIMARY SCREEN: Always has (0,0) at its top-left corner\n"
        analysis += "2. SECONDARY SCREENS: Can have negative or positive coordinates\n"
        analysis += "3. NEGATIVE COORDINATES: Indicate screens positioned left/above primary\n"
        analysis += "4. COORDINATE ORIGIN: Always (0,0) at primary screen's top-left\n"
        analysis += "5. VIRTUAL DESKTOP: Bounding box containing all screens\n\n"

        # Practical implications
        analysis += "Practical Implications for Window Positioning:\n"
        analysis += "• Use screen.geometry() to get absolute screen coordinates\n"
        analysis += "• Use screen.availableGeometry() to respect system UI elements\n"
        analysis += "• Always validate coordinates before positioning windows\n"
        analysis += "• Consider negative coordinates when calculating positions\n"
        analysis += "• Use screen.topLeft() for relative positioning\n\n"

        # Current window position
        current_screen = self.screen()
        if current_screen:
            window_pos = self.pos()
            analysis += "Current Window Information:\n"
            analysis += f"  Screen: {current_screen.name()}\n"
            analysis += f"  Window Position: ({window_pos.x()}, {window_pos.y()})\n"
            analysis += f"  Screen Geometry: {current_screen.geometry()}\n"

        self.analysis_text.setPlainText(analysis)

    def test_window_positioning(self):
        """Test window positioning across different screens"""
        app = QApplication.instance()
        screens = app.screens()

        if len(screens) < 2:
            self.analysis_text.append("\n=== POSITIONING TEST ===\n")
            self.analysis_text.append("Only one screen detected. Cannot test multi-screen positioning.\n")
            return

        self.analysis_text.append("\n=== POSITIONING TEST ===\n")

        # Test positioning on each screen
        for i, screen in enumerate(screens):
            geometry = screen.availableGeometry()

            # Calculate center position
            center_x = geometry.x() + geometry.width() // 2 - self.width() // 2
            center_y = geometry.y() + geometry.height() // 2 - self.height() // 2

            self.analysis_text.append(f"Screen {i + 1} ({screen.name()}):")
            self.analysis_text.append(f"  Available Geometry: {geometry}")
            self.analysis_text.append(f"  Calculated Center Position: ({center_x}, {center_y})")

            # Validate coordinates
            if (
                center_x >= geometry.x()
                and center_x + self.width() <= geometry.x() + geometry.width()
                and center_y >= geometry.y()
                and center_y + self.height() <= geometry.y() + geometry.height()
            ):
                self.analysis_text.append("  ✓ Valid positioning coordinates")
            else:
                self.analysis_text.append("  ✗ Invalid positioning coordinates")

            self.analysis_text.append("")

        # Move to next screen for demonstration
        current_screen_index = 0
        for i, screen in enumerate(screens):
            if screen == self.screen():
                current_screen_index = i
                break

        next_screen_index = (current_screen_index + 1) % len(screens)
        target_screen = screens[next_screen_index]
        target_geometry = target_screen.availableGeometry()

        # Move window to center of target screen
        new_x = target_geometry.x() + (target_geometry.width() - self.width()) // 2
        new_y = target_geometry.y() + (target_geometry.height() - self.height()) // 2

        self.move(new_x, new_y)

        self.analysis_text.append(f"Window moved to Screen {next_screen_index + 1} ({target_screen.name()})")
        self.analysis_text.append(f"New position: ({new_x}, {new_y})")

        # Update analysis after move
        self.analyze_coordinate_systems()


def demonstrate_coordinate_calculations():
    """Demonstrate coordinate calculations without GUI"""
    app = QApplication.instance()
    screens = app.screens()

    print("=== COORDINATE CALCULATION DEMONSTRATION ===")
    print(f"Total screens: {len(screens)}")
    print()

    for i, screen in enumerate(screens):
        geometry = screen.geometry()
        available = screen.availableGeometry()

        print(f"Screen {i}: {screen.name()}")
        print(f"  Full geometry: {geometry}")
        print(f"  Available geometry: {available}")
        print("  Coordinate analysis:")

        if geometry.x() < 0:
            print(f"    - X={geometry.x()}: Screen is {abs(geometry.x())} pixels LEFT of primary")
        elif geometry.x() > 0:
            print(f"    - X={geometry.x()}: Screen is {geometry.x()} pixels RIGHT of primary")
        else:
            print(f"    - X={geometry.x()}: Screen horizontally aligned with primary")

        if geometry.y() < 0:
            print(f"    - Y={geometry.y()}: Screen is {abs(geometry.y())} pixels ABOVE primary")
        elif geometry.y() > 0:
            print(f"    - Y={geometry.y()}: Screen is {geometry.y()} pixels BELOW primary")
        else:
            print(f"    - Y={geometry.y()}: Screen vertically aligned with primary")

        print()


def main():
    app = QApplication(sys.argv)

    # Demonstrate coordinate calculations in console
    demonstrate_coordinate_calculations()

    # Create and show the GUI test window
    window = CoordinateSystemTest()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
