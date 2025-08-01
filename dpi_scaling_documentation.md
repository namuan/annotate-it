# PyQt6 DPI Scaling Handling Documentation

## Overview

PyQt6 provides comprehensive support for high DPI displays with automatic scaling enabled by default. This document covers the key concepts, APIs, and best practices for handling DPI scaling in multi-monitor environments.

## Key Concepts

### Device Pixel Ratio (DPR)
- **Definition**: The ratio between physical pixels and device-independent pixels
- **Examples**: 
  - 1.0 = Standard DPI display
  - 2.0 = High DPI display (e.g., Retina)
  - 1.5 = Medium DPI display (e.g., 150% scaling)

### Device-Independent Pixels
- PyQt6 applications operate in device-independent coordinate system
- Qt automatically maps these to physical pixels using the device pixel ratio
- Higher-level APIs (Widgets, Quick) handle this automatically

## PyQt6 DPI Scaling Features

### Automatic High DPI Support
```python
# PyQt6 enables high DPI scaling by default - no setup required!
# This is different from PyQt5 where you needed:
# QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
```

### Available Application Attributes
```python
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Optional: Enable high DPI pixmaps (recommended)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# If needed: Disable high DPI scaling
QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True)
```

### Scale Factor Rounding Policies
```python
from PyQt6.QtCore import Qt

# Set rounding policy before creating QApplication
app = QApplication(sys.argv)
app.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

# Available policies:
# - Round: Round to nearest integer
# - Ceil: Always round up
# - Floor: Always round down  
# - RoundPreferFloor: Round, prefer floor for .5 values
# - PassThrough: Use exact fractional values
```

## Screen Information APIs

### Getting Screen Properties
```python
from PyQt6.QtWidgets import QApplication

# Get all screens
screens = QApplication.screens()

# Get primary screen
primary_screen = QApplication.primaryScreen()

# Get current window's screen
window_screen = window.screen()

for screen in screens:
    print(f"Screen: {screen.name()}")
    print(f"Device Pixel Ratio: {screen.devicePixelRatio()}")
    print(f"Logical DPI: {screen.logicalDotsPerInch()}")
    print(f"Physical DPI: {screen.physicalDotsPerInch()}")
    print(f"Geometry: {screen.geometry()}")
    print(f"Available Geometry: {screen.availableGeometry()}")
```

### Key QScreen Properties
- **`devicePixelRatio()`**: Scale factor for the screen
- **`logicalDotsPerInch()`**: DPI in device-independent pixels
- **`physicalDotsPerInch()`**: Actual physical DPI
- **`geometry()`**: Full screen geometry
- **`availableGeometry()`**: Available area (excluding taskbars, etc.)
- **`refreshRate()`**: Screen refresh rate in Hz

## Multi-Monitor DPI Handling

### Coordinate System Considerations
```python
# Screens can have different DPI settings
# Example multi-monitor setup:
# Screen 0: Built-in Retina Display (DPR: 2.0)
# Screen 1: External Monitor (DPR: 1.0)

# When moving windows between screens:
for screen in QApplication.screens():
    geometry = screen.availableGeometry()
    dpr = screen.devicePixelRatio()
    
    if dpr > 1.5:
        print(f"{screen.name()}: High DPI display")
    else:
        print(f"{screen.name()}: Standard DPI display")
```

### Window Positioning Across Screens
```python
def move_window_to_screen(window, target_screen):
    """Move window to specific screen with proper DPI handling"""
    geometry = target_screen.availableGeometry()
    
    # Position window on target screen
    window.move(geometry.x() + 50, geometry.y() + 50)
    
    # Optional: Resize based on screen DPI
    dpr = target_screen.devicePixelRatio()
    if dpr != window.screen().devicePixelRatio():
        # Handle DPI change if needed
        window.update()  # Trigger repaint
```

## Best Practices

### 1. Application Setup
```python
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

def main():
    # Set attributes BEFORE creating QApplication
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # Set rounding policy for consistent scaling
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Your application code here
    return app.exec()
```

### 2. DPI-Aware Image Handling
```python
from PyQt6.QtGui import QPixmap, QIcon

# Use high DPI pixmaps
pixmap = QPixmap("image.png")
pixmap.setDevicePixelRatio(screen.devicePixelRatio())

# For icons, provide multiple resolutions:
# - image.png (standard)
# - image@2x.png (high DPI)
icon = QIcon("image.png")  # Qt automatically selects appropriate version
```

### 3. Font and Size Handling
```python
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QSize

# Use point sizes for fonts (automatically scaled)
font = QFont("Arial", 12)  # 12pt font scales automatically

# For fixed pixel sizes, consider DPI:
def get_scaled_size(base_size, screen):
    dpr = screen.devicePixelRatio()
    return QSize(int(base_size.width() * dpr), int(base_size.height() * dpr))
```

### 4. OpenGL and Low-Level Graphics
```python
# For OpenGL or custom painting, manually handle DPI:
def paintEvent(self, event):
    painter = QPainter(self)
    
    # Get device pixel ratio
    dpr = self.devicePixelRatio()
    
    # Scale drawing operations
    painter.scale(dpr, dpr)
    
    # Your drawing code here
```

## Common Issues and Solutions

### Issue 1: Blurry Text on High DPI
**Solution**: Ensure high DPI pixmaps are enabled
```python
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
```

### Issue 2: Inconsistent Scaling Across Monitors
**Solution**: Use PassThrough rounding policy
```python
app.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
```

### Issue 3: Custom Widgets Not Scaling
**Solution**: Override `paintEvent` and handle DPI manually
```python
def paintEvent(self, event):
    painter = QPainter(self)
    dpr = self.devicePixelRatio()
    painter.scale(dpr, dpr)
    # Custom drawing code
```

### Issue 4: Fixed Pixel Sizes Too Small/Large
**Solution**: Scale sizes based on DPI
```python
def get_dpi_scaled_size(base_size):
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio()
    return int(base_size * dpr)
```

## Testing DPI Scaling

### Environment Variables for Testing
```bash
# Force specific scale factor
export QT_SCALE_FACTOR=2.0

# Set per-screen scale factors
export QT_SCREEN_SCALE_FACTORS="1.5;2.0"

# Force DPI
export QT_FONT_DPI=144
```

### Programmatic Testing
```python
def analyze_dpi_setup():
    """Analyze current DPI configuration"""
    screens = QApplication.screens()
    
    print(f"Total screens: {len(screens)}")
    
    for i, screen in enumerate(screens):
        dpr = screen.devicePixelRatio()
        logical_dpi = screen.logicalDotsPerInch()
        physical_dpi = screen.physicalDotsPerInch()
        
        print(f"Screen {i}: {screen.name()}")
        print(f"  DPR: {dpr:.2f}")
        print(f"  Logical DPI: {logical_dpi:.1f}")
        print(f"  Physical DPI: {physical_dpi:.1f}")
        
        if dpr > 1.5:
            print(f"  → High DPI display")
        elif dpr > 1.0:
            print(f"  → Medium DPI display")
        else:
            print(f"  → Standard DPI display")
```

## Summary

PyQt6 significantly simplifies high DPI support compared to PyQt5:

1. **Automatic scaling** is enabled by default
2. **No manual setup** required for basic applications
3. **Consistent behavior** across platforms
4. **Flexible rounding policies** for fine-tuning
5. **Comprehensive screen APIs** for multi-monitor support

For most applications, simply enabling high DPI pixmaps and setting an appropriate rounding policy is sufficient for excellent high DPI support across all screen configurations.