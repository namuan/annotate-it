# PyQt6 Multi-Monitor Screen Properties Documentation

This document provides comprehensive information about PyQt6's multi-monitor APIs and available screen properties.

## Overview

PyQt6 provides robust support for multi-monitor setups through the `QScreen` class and `QApplication.screens()` method. These APIs allow applications to detect, enumerate, and work with multiple displays.

## Key Classes and Methods

### QApplication.screens()
- **Returns**: List of `QScreen` objects representing all available screens
- **Usage**: `app.screens()` where `app` is a `QApplication` instance
- **Note**: Screens are indexed starting from 0

### QApplication.primaryScreen()
- **Returns**: `QScreen` object representing the primary screen
- **Usage**: `app.primaryScreen()`
- **Note**: The primary screen is typically where the main desktop and taskbar are located

### QScreen Class
Represents a single screen/monitor in the system.

## Available Screen Properties

### Basic Identification

#### name()
- **Type**: `str`
- **Description**: User-presentable string representing the screen
- **Example**: "Built-in Retina Display", "VGA1", "HDMI1"
- **Note**: Not guaranteed to match native APIs; should not be used for unique identification

#### manufacturer()
- **Type**: `str`
- **Description**: Manufacturer of the screen
- **Example**: "Apple", "Dell", "Samsung"

#### model()
- **Type**: `str`
- **Description**: Model of the screen
- **Example**: "Studio Display", "U2720Q"

### Geometry Properties

#### geometry()
- **Type**: `QRect`
- **Description**: Screen's geometry in pixels
- **Example**: `QRect(0, 0, 1280, 1024)` for primary screen, `QRect(1280, 0, 1280, 1024)` for secondary
- **Note**: In multi-monitor setups, coordinates can be negative or start from non-zero values

#### availableGeometry()
- **Type**: `QRect`
- **Description**: Available geometry excluding window manager reserved areas (taskbars, system menus)
- **Example**: `QRect(0, 44, 1800, 1125)` (44px reserved for macOS menu bar)
- **Note**: On X11, returns true available geometry only with one monitor and `_NET_WORKAREA` atom set

#### size()
- **Type**: `QSize`
- **Description**: Screen's size in pixels
- **Usage**: `screen.size().width()`, `screen.size().height()`

#### availableSize()
- **Type**: `QSize`
- **Description**: Available size excluding window manager reserved areas

### Virtual Desktop Properties

#### virtualGeometry()
- **Type**: `QRect`
- **Description**: Geometry of the virtual desktop to which this screen belongs
- **Note**: Union of all virtual siblings' geometries

#### availableVirtualGeometry()
- **Type**: `QRect`
- **Description**: Available geometry of the virtual desktop
- **Note**: Union of virtual siblings' individual available geometries

#### virtualSize()
- **Type**: `QSize`
- **Description**: Size of the virtual desktop

#### availableVirtualSize()
- **Type**: `QSize`
- **Description**: Available size of the virtual desktop

#### virtualSiblings()
- **Type**: `List[QScreen]`
- **Description**: List of screens that are part of the same virtual desktop
- **Usage**: For detecting screens that work together as one extended desktop

### DPI and Scaling Properties

#### devicePixelRatio()
- **Type**: `float`
- **Description**: Ratio between physical pixels and device-independent pixels
- **Common Values**:
  - `1.0` for normal displays
  - `2.0` for "retina" displays
  - Higher values possible for high-DPI displays
- **Note**: Use for converting between logical and physical pixels

#### logicalDotsPerInch()
- **Type**: `float`
- **Description**: Logical DPI (average of X and Y)
- **Usage**: Converting font point sizes to pixel sizes
- **Note**: May be user-configurable in desktop environment settings

#### logicalDotsPerInchX()
- **Type**: `float`
- **Description**: Logical DPI in horizontal direction

#### logicalDotsPerInchY()
- **Type**: `float`
- **Description**: Logical DPI in vertical direction

#### physicalDotsPerInch()
- **Type**: `float`
- **Description**: Physical DPI based on actual pixel sizes
- **Usage**: Print preview and cases requiring exact physical dimensions
- **Note**: Multiply by `devicePixelRatio()` for device-dependent density

#### physicalDotsPerInchX()
- **Type**: `float`
- **Description**: Physical DPI in horizontal direction

#### physicalDotsPerInchY()
- **Type**: `float`
- **Description**: Physical DPI in vertical direction

#### physicalSize()
- **Type**: `QSizeF`
- **Description**: Physical size of the screen in millimeters

### Display Properties

#### depth()
- **Type**: `int`
- **Description**: Color depth of the screen in bits
- **Common Values**: 24, 32

#### refreshRate()
- **Type**: `float`
- **Description**: Approximate vertical refresh rate in Hz
- **Example**: 60.0, 120.0, 144.0

### Orientation Properties

#### orientation()
- **Type**: `Qt.ScreenOrientation`
- **Description**: Current orientation of the screen
- **Values**: `Qt.PrimaryOrientation`, `Qt.PortraitOrientation`, `Qt.LandscapeOrientation`, etc.

#### nativeOrientation()
- **Type**: `Qt.ScreenOrientation`
- **Description**: Native orientation where device logo appears right-way up
- **Note**: Hardware property that doesn't change

#### primaryOrientation()
- **Type**: `Qt.ScreenOrientation`
- **Description**: Primary orientation of the screen

## Practical Usage Examples

### Detecting Multiple Monitors
```python
app = QApplication(sys.argv)
screens = app.screens()
print(f"Found {len(screens)} monitors")
```

### Moving Window to Specific Screen
```python
# Move to second screen (index 1)
if len(screens) > 1:
    target_screen = screens[1]
    screen_geometry = target_screen.availableGeometry()
    widget.move(screen_geometry.x(), screen_geometry.y())
```

### Getting Screen Information
```python
for i, screen in enumerate(screens):
    print(f"Screen {i}: {screen.name()}")
    print(f"  Resolution: {screen.size().width()}x{screen.size().height()}")
    print(f"  DPI: {screen.logicalDotsPerInch():.1f}")
    print(f"  Device Pixel Ratio: {screen.devicePixelRatio()}")
```

### Handling DPI Scaling
```python
# Convert logical pixels to physical pixels
logical_size = 100  # pixels
physical_size = logical_size * screen.devicePixelRatio()
```

## Important Notes

1. **Screen Indexing**: Screens are indexed starting from 0
2. **Coordinate Systems**: In multi-monitor setups, coordinates can be negative or start from non-zero values
3. **DPI Scaling**: Always consider `devicePixelRatio()` when working with high-DPI displays
4. **Platform Differences**: Some properties may behave differently across platforms (Windows, macOS, Linux)
5. **Dynamic Changes**: Screen configuration can change at runtime (monitors added/removed, resolution changed)
6. **Virtual Desktops**: macOS virtual desktops are treated as separate screens by PyQt6

## Signals for Dynamic Updates

The following signals can be used to detect changes in screen configuration:

- `QGuiApplication.screenAdded(QScreen)`
- `QGuiApplication.screenRemoved(QScreen)`
- `QGuiApplication.primaryScreenChanged(QScreen)`
- `QScreen.geometryChanged(QRect)`
- `QScreen.availableGeometryChanged(QRect)`
- `QScreen.physicalSizeChanged(QSizeF)`
- `QScreen.logicalDotsPerInchChanged(qreal)`
- `QScreen.physicalDotsPerInchChanged(qreal)`

## Best Practices

1. **Always check screen count** before accessing specific screen indices
2. **Use availableGeometry()** instead of geometry() for window positioning to respect system UI elements
3. **Handle DPI scaling** properly for high-DPI displays
4. **Listen to screen change signals** for robust multi-monitor support
5. **Test on different platforms** as behavior may vary
6. **Consider virtual siblings** when working with extended desktop setups
