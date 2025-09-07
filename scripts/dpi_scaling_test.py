#!/usr/bin/env python3
"""
PyQt6 DPI Scaling Handling Test

This script demonstrates various aspects of DPI scaling in PyQt6:
- High DPI scaling attributes
- Device pixel ratio detection
- Scale factor rounding policies
- Multi-monitor DPI handling
- Best practices for DPI-aware applications
"""

import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DPIScalingTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 DPI Scaling Test")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # DPI Information Group
        dpi_group = self.create_dpi_info_group()
        layout.addWidget(dpi_group)

        # Scaling Controls Group
        controls_group = self.create_scaling_controls_group()
        layout.addWidget(controls_group)

        # Visual Test Group
        visual_group = self.create_visual_test_group()
        layout.addWidget(visual_group)

        # Output area
        self.output_text = QTextEdit()
        self.output_text.setMaximumHeight(200)
        layout.addWidget(QLabel("DPI Analysis Output:"))
        layout.addWidget(self.output_text)

        # Update DPI info initially
        self.update_dpi_info()

        # Timer for periodic updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dpi_info)
        self.timer.start(2000)  # Update every 2 seconds

    def create_dpi_info_group(self):
        """Create group showing current DPI information"""
        group = QGroupBox("Current DPI Information")
        layout = QGridLayout(group)

        # Labels for DPI info
        self.screen_name_label = QLabel()
        self.device_pixel_ratio_label = QLabel()
        self.logical_dpi_label = QLabel()
        self.physical_dpi_label = QLabel()
        self.scale_factor_label = QLabel()

        layout.addWidget(QLabel("Screen:"), 0, 0)
        layout.addWidget(self.screen_name_label, 0, 1)
        layout.addWidget(QLabel("Device Pixel Ratio:"), 1, 0)
        layout.addWidget(self.device_pixel_ratio_label, 1, 1)
        layout.addWidget(QLabel("Logical DPI:"), 2, 0)
        layout.addWidget(self.logical_dpi_label, 2, 1)
        layout.addWidget(QLabel("Physical DPI:"), 3, 0)
        layout.addWidget(self.physical_dpi_label, 3, 1)
        layout.addWidget(QLabel("Effective Scale:"), 4, 0)
        layout.addWidget(self.scale_factor_label, 4, 1)

        return group

    def create_scaling_controls_group(self):
        """Create group with scaling controls and options"""
        group = QGroupBox("DPI Scaling Controls")
        layout = QVBoxLayout(group)

        # Rounding policy selection
        policy_layout = QHBoxLayout()
        policy_layout.addWidget(QLabel("Scale Factor Rounding Policy:"))

        self.policy_combo = QComboBox()
        self.policy_combo.addItems(["Round", "Ceil", "Floor", "RoundPreferFloor", "PassThrough"])
        self.policy_combo.currentTextChanged.connect(self.change_rounding_policy)
        policy_layout.addWidget(self.policy_combo)
        layout.addLayout(policy_layout)

        # Test buttons
        button_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh DPI Info")
        refresh_btn.clicked.connect(self.update_dpi_info)
        button_layout.addWidget(refresh_btn)

        move_btn = QPushButton("Move to Next Screen")
        move_btn.clicked.connect(self.move_to_next_screen)
        button_layout.addWidget(move_btn)

        test_btn = QPushButton("Test DPI Scaling")
        test_btn.clicked.connect(self.test_dpi_scaling)
        button_layout.addWidget(test_btn)

        layout.addLayout(button_layout)

        return group

    def create_visual_test_group(self):
        """Create group with visual elements for DPI testing"""
        group = QGroupBox("Visual DPI Test Elements")
        layout = QGridLayout(group)

        # Different sized elements to test scaling
        small_label = QLabel("Small Text (8pt)")
        small_label.setFont(QFont("Arial", 8))
        layout.addWidget(small_label, 0, 0)

        medium_label = QLabel("Medium Text (12pt)")
        medium_label.setFont(QFont("Arial", 12))
        layout.addWidget(medium_label, 0, 1)

        large_label = QLabel("Large Text (16pt)")
        large_label.setFont(QFont("Arial", 16))
        layout.addWidget(large_label, 0, 2)

        # Buttons of different sizes
        small_btn = QPushButton("Small")
        small_btn.setFixedSize(60, 25)
        layout.addWidget(small_btn, 1, 0)

        medium_btn = QPushButton("Medium")
        medium_btn.setFixedSize(100, 35)
        layout.addWidget(medium_btn, 1, 1)

        large_btn = QPushButton("Large")
        large_btn.setFixedSize(140, 45)
        layout.addWidget(large_btn, 1, 2)

        return group

    def update_dpi_info(self):
        """Update DPI information display"""
        screen = self.screen()
        if screen:
            self.screen_name_label.setText(screen.name())
            self.device_pixel_ratio_label.setText(f"{screen.devicePixelRatio():.2f}")
            self.logical_dpi_label.setText(f"{screen.logicalDotsPerInch():.1f}")
            self.physical_dpi_label.setText(f"{screen.physicalDotsPerInch():.1f}")

            # Calculate effective scale factor
            effective_scale = screen.devicePixelRatio()
            self.scale_factor_label.setText(f"{effective_scale:.2f}x")

    def change_rounding_policy(self, policy_text):
        """Change the high DPI scale factor rounding policy"""
        policy_map = {
            "Round": Qt.HighDpiScaleFactorRoundingPolicy.Round,
            "Ceil": Qt.HighDpiScaleFactorRoundingPolicy.Ceil,
            "Floor": Qt.HighDpiScaleFactorRoundingPolicy.Floor,
            "RoundPreferFloor": Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor,
            "PassThrough": Qt.HighDpiScaleFactorRoundingPolicy.PassThrough,
        }

        if policy_text in policy_map:
            QApplication.setHighDpiScaleFactorRoundingPolicy(policy_map[policy_text])
            self.output_text.append(f"Changed rounding policy to: {policy_text}")

    def move_to_next_screen(self):
        """Move window to the next available screen"""
        screens = QApplication.screens()
        if len(screens) > 1:
            current_screen = self.screen()
            current_index = screens.index(current_screen)
            next_index = (current_index + 1) % len(screens)
            next_screen = screens[next_index]

            # Move window to next screen
            geometry = next_screen.availableGeometry()
            self.move(geometry.x() + 50, geometry.y() + 50)

            self.output_text.append(f"Moved to screen: {next_screen.name()}")
        else:
            self.output_text.append("Only one screen available")

    def test_dpi_scaling(self):
        """Perform comprehensive DPI scaling test"""
        self.output_text.clear()
        self.output_text.append("=== DPI SCALING ANALYSIS ===")

        # Application-level DPI info
        app = QApplication.instance()
        self.output_text.append("High DPI scaling: Enabled by default in PyQt6")
        self.output_text.append(f"Use high DPI pixmaps: {app.testAttribute(Qt.AA_UseHighDpiPixmaps)}")

        # Screen analysis
        screens = QApplication.screens()
        self.output_text.append(f"\nTotal screens: {len(screens)}")

        for i, screen in enumerate(screens):
            self.output_text.append(f"\nScreen {i}: {screen.name()}")
            self.output_text.append(f"  Geometry: {screen.geometry().width()}x{screen.geometry().height()}")
            self.output_text.append(
                f"  Available: {screen.availableGeometry().width()}x{screen.availableGeometry().height()}"
            )
            self.output_text.append(f"  Device Pixel Ratio: {screen.devicePixelRatio():.2f}")
            self.output_text.append(f"  Logical DPI: {screen.logicalDotsPerInch():.1f}")
            self.output_text.append(f"  Physical DPI: {screen.physicalDotsPerInch():.1f}")
            self.output_text.append(f"  Refresh Rate: {screen.refreshRate():.1f} Hz")

            # DPI scaling analysis
            dpr = screen.devicePixelRatio()
            if dpr > 1.5:
                self.output_text.append(f"  → High DPI display detected (scale: {dpr:.1f}x)")
            elif dpr > 1.0:
                self.output_text.append(f"  → Medium DPI display (scale: {dpr:.1f}x)")
            else:
                self.output_text.append("  → Standard DPI display")


def demonstrate_dpi_attributes():
    """Demonstrate DPI-related application attributes"""
    print("=== DPI SCALING ATTRIBUTES DEMONSTRATION ===")

    # These attributes should be set BEFORE creating QApplication
    print("\nDPI attributes in PyQt6:")
    print("- High DPI scaling is ENABLED BY DEFAULT (no need to set AA_EnableHighDpiScaling)")
    print("- Qt.AA_UseHighDpiPixmaps: Use high DPI versions of pixmaps")
    print("- Qt.AA_DisableHighDpiScaling: Disable high DPI scaling (if needed)")

    print("\nRounding policies for scale factors:")
    policies = [
        "Round: Round to nearest integer",
        "Ceil: Always round up",
        "Floor: Always round down",
        "RoundPreferFloor: Round, but prefer floor for .5 values",
        "PassThrough: Use exact fractional values",
    ]
    for policy in policies:
        print(f"- {policy}")


def main():
    # In PyQt6, high DPI scaling is enabled by default
    # Set DPI attributes BEFORE creating QApplication
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Set high DPI scale factor rounding policy
    app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # Demonstrate DPI attributes
    demonstrate_dpi_attributes()

    # Create and show the test window
    window = DPIScalingTest()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
