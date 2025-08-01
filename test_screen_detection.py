#!/usr/bin/env python3
"""
Test script for PyQt6 multi-monitor screen detection APIs
Based on research of QScreen class and QApplication.screens() method
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QScreen
from PyQt6.QtCore import Qt


class ScreenDetectionTest(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.detect_screens()
    
    def initUI(self):
        self.setWindowTitle('PyQt6 Multi-Monitor Screen Detection Test')
        self.setGeometry(300, 300, 600, 400)
        
        layout = QVBoxLayout()
        
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Button to refresh screen info
        refresh_btn = QPushButton('Refresh Screen Info')
        refresh_btn.clicked.connect(self.detect_screens)
        layout.addWidget(refresh_btn)
        
        # Button to move to next screen
        move_btn = QPushButton('Move to Next Screen')
        move_btn.clicked.connect(self.move_to_next_screen)
        layout.addWidget(move_btn)
        
        self.setLayout(layout)
        self.current_screen_index = 0
    
    def detect_screens(self):
        """Detect and display information about all available screens"""
        app = QApplication.instance()
        screens = app.screens()
        primary_screen = app.primaryScreen()
        
        info_text = f"Screen Detection Results:\n\n"
        info_text += f"Total screens detected: {len(screens)}\n\n"
        
        for i, screen in enumerate(screens):
            is_primary = screen == primary_screen
            info_text += f"Screen {i + 1}{'(Primary)' if is_primary else ''}:\n"
            info_text += f"  Name: {screen.name()}\n"
            info_text += f"  Manufacturer: {screen.manufacturer()}\n"
            info_text += f"  Model: {screen.model()}\n"
            
            # Geometry information
            geometry = screen.geometry()
            info_text += f"  Geometry: {geometry.width()}x{geometry.height()} at ({geometry.x()}, {geometry.y()})\n"
            
            # Available geometry (excluding taskbars, etc.)
            available_geometry = screen.availableGeometry()
            info_text += f"  Available Geometry: {available_geometry.width()}x{available_geometry.height()} at ({available_geometry.x()}, {available_geometry.y()})\n"
            
            # DPI information
            info_text += f"  Device Pixel Ratio: {screen.devicePixelRatio()}\n"
            info_text += f"  Logical DPI: {screen.logicalDotsPerInch():.1f}\n"
            info_text += f"  Physical DPI: {screen.physicalDotsPerInch():.1f}\n"
            
            # Color depth
            info_text += f"  Color Depth: {screen.depth()} bits\n"
            
            # Virtual siblings (for multi-monitor setups)
            virtual_siblings = screen.virtualSiblings()
            info_text += f"  Virtual Siblings: {len(virtual_siblings)} screens\n"
            
            info_text += "\n"
        
        # Current window screen info
        current_screen = self.screen()
        if current_screen:
            info_text += f"Current window is on screen: {current_screen.name()}\n"
        
        self.info_label.setText(info_text)
    
    def move_to_next_screen(self):
        """Move window to the next available screen"""
        app = QApplication.instance()
        screens = app.screens()
        
        if len(screens) <= 1:
            return
        
        # Move to next screen
        self.current_screen_index = (self.current_screen_index + 1) % len(screens)
        target_screen = screens[self.current_screen_index]
        
        # Get the geometry of the target screen
        screen_geometry = target_screen.availableGeometry()
        
        # Move window to the center of the target screen
        window_size = self.size()
        x = screen_geometry.x() + (screen_geometry.width() - window_size.width()) // 2
        y = screen_geometry.y() + (screen_geometry.height() - window_size.height()) // 2
        
        self.move(x, y)
        
        # Update screen info
        self.detect_screens()


def main():
    app = QApplication(sys.argv)
    
    # Test basic screen detection without creating a window
    print("=== Basic Screen Detection Test ===")
    screens = app.screens()
    primary_screen = app.primaryScreen()
    
    print(f"Total screens: {len(screens)}")
    print(f"Primary screen: {primary_screen.name() if primary_screen else 'None'}")
    
    for i, screen in enumerate(screens):
        print(f"\nScreen {i}:")
        print(f"  Name: {screen.name()}")
        print(f"  Geometry: {screen.geometry()}")
        print(f"  Available Geometry: {screen.availableGeometry()}")
        print(f"  Device Pixel Ratio: {screen.devicePixelRatio()}")
    
    # Create and show the test window
    window = ScreenDetectionTest()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()