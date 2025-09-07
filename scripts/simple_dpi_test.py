#!/usr/bin/env python3
"""
Simple PyQt6 DPI Test
Testing what DPI attributes and methods are available in PyQt6
"""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget


def main():
    app = QApplication(sys.argv)

    print("=== PyQt6 DPI Information ===")

    # Check available Qt attributes
    print("\nAvailable Qt attributes:")
    qt_attrs = [attr for attr in dir(Qt) if "AA_" in attr or "DPI" in attr or "HighDpi" in attr]
    for attr in qt_attrs:
        print(f"  {attr}")

    # Get screen information
    screens = app.screens()
    print(f"\nScreens detected: {len(screens)}")

    for i, screen in enumerate(screens):
        print(f"\nScreen {i}: {screen.name()}")
        print(f"  Device Pixel Ratio: {screen.devicePixelRatio()}")
        print(f"  Logical DPI: {screen.logicalDotsPerInch()}")
        print(f"  Physical DPI: {screen.physicalDotsPerInch()}")
        print(f"  Geometry: {screen.geometry()}")
        print(f"  Available Geometry: {screen.availableGeometry()}")

    # Test window
    window = QMainWindow()
    window.setWindowTitle("Simple DPI Test")

    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)

    # Add some test labels
    layout.addWidget(QLabel("Normal text"))
    layout.addWidget(QLabel("This is a DPI scaling test"))

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
