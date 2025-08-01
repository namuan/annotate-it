# Monitor Selection UI Mockups

This document provides mockups and design specifications for the monitor selection interface in different scenarios.

## Scenario 1: Single Monitor Setup

### Behavior
- When only one monitor is detected, the monitor selection dialog is **skipped entirely**
- The application launches directly on the primary (only) monitor
- No user interaction required for monitor selection

### User Experience
```
Application Start → Direct Launch on Primary Monitor
```

### Implementation
- Check `len(app.screens()) == 1`
- If true, skip dialog and use primary screen
- Seamless experience for single-monitor users

---

## Scenario 2: Multiple Monitor Setup

### Behavior
- Monitor selection dialog appears before main application
- Shows visual representation of all monitors with relative positioning
- User can click to select target monitor
- Application launches on selected monitor

### User Experience
```
Application Start → Monitor Selection Dialog → Launch on Selected Monitor
```

### Dialog Layout Mockup

```
┌─────────────────────────────────────────────────────────────┐
│                Select Monitor for Annotations               │
├─────────────────────────────────────────────────────────────┤
│  Click on a monitor below to select it for the annotation  │
│  overlay. The layout shows the relative positions of your  │
│  monitors.                                                  │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │   Monitor 1     │    │   Monitor 2     │                │
│  │   (Primary)     │    │                 │                │
│  │                 │    │                 │                │
│  │ Resolution:     │    │ Resolution:     │                │
│  │ 1800x1169       │    │ 1920x1080       │                │
│  │ Position:       │    │ Position:       │                │
│  │ (0, 0)          │    │ (1800, -98)     │                │
│  │ DPI: 110        │    │ DPI: 96         │                │
│  │ Scale: 2.0x     │    │ Scale: 1.0x     │                │
│  │ Refresh: 60Hz   │    │ Refresh: 60Hz   │                │
│  │ Name: Built-in  │    │ Name: Display   │                │
│  │ Retina Display  │    │                 │                │
│  └─────────────────┘    └─────────────────┘                │
│                                                             │
│                                    [Use Monitor 2] [Cancel]│
└─────────────────────────────────────────────────────────────┘
```

### Visual Design Elements

#### Monitor Representation
- **Size**: Scaled proportionally to actual resolution
- **Minimum Size**: 150x110 pixels for readability
- **Border**: 2-3px solid border
- **Colors**:
  - Primary Monitor: Light blue background (#E3F2FD), blue border (#1976D2)
  - Secondary Monitors: Light gray background (#F5F5F5), gray border (#757575)
  - Selected Monitor: Green background (#4CAF50), dark green border (#2E7D32)

#### Information Display
- **Monitor Number**: Bold, larger font (8pt)
- **Details**: Regular font (7pt)
- **Information Shown**:
  - Resolution (width x height)
  - Position coordinates (x, y)
  - DPI (logical and physical)
  - Scale factor
  - Refresh rate
  - Display name (truncated if too long)

#### Layout Positioning
- Monitors positioned relative to their actual screen coordinates
- Scaled to fit within dialog bounds
- Maintains aspect ratio and relative positioning
- Centered in dialog with margins

---

## Scenario 3: Complex Multi-Monitor Arrangements

### Vertical Stack
```
┌─────────────┐
│  Monitor 1  │
│  (Primary)  │
│ 1920x1080   │
│ (0, -1080)  │
└─────────────┘
┌─────────────┐
│  Monitor 2  │
│ 1920x1080   │
│ (0, 0)      │
└─────────────┘
```

### L-Shape Arrangement
```
┌─────────────┐ ┌─────────────┐
│  Monitor 1  │ │  Monitor 3  │
│  (Primary)  │ │ 1024x768    │
│ 1920x1080   │ │ (1920, 0)   │
│ (0, 0)      │ └─────────────┘
└─────────────┘
┌─────────────┐
│  Monitor 2  │
│ 1920x1080   │
│ (0, 1080)   │
└─────────────┘
```

### Mixed DPI Setup
```
┌─────────────────┐    ┌─────────────┐
│   Monitor 1     │    │  Monitor 2  │
│   (Primary)     │    │ 1920x1080   │
│ Retina Display  │    │ DPI: 96     │
│ 2880x1800       │    │ Scale: 1.0x │
│ DPI: 220        │    │ (2880, 0)   │
│ Scale: 2.0x     │    └─────────────┘
│ (0, 0)          │
└─────────────────┘
```

---

## User Interaction Flow

### Selection Process
1. **Visual Feedback**: Hover effects on monitor widgets
2. **Click Selection**: Single click to select monitor
3. **Immediate Feedback**: Selected monitor highlighted in green
4. **Button Update**: OK button text updates to "Use Monitor X"
5. **Confirmation**: Click OK to proceed or Cancel to exit

### Default Selection
- Primary monitor is selected by default
- Provides sensible default for quick selection
- User can change selection before confirming

### Error Handling
- If user cancels dialog, application exits gracefully
- No monitor selection means no application launch
- Prevents confusion about which monitor will be used

---

## Technical Implementation Notes

### Scaling Algorithm
```python
# Calculate bounding box of all monitors
min_x = min(screen.geometry().x() for screen in screens)
min_y = min(screen.geometry().y() for screen in screens)
max_x = max(screen.geometry().x() + screen.geometry().width() for screen in screens)
max_y = max(screen.geometry().y() + screen.geometry().height() for screen in screens)

# Calculate scale to fit in dialog
available_width = 700
available_height = 350
scale_x = available_width / (max_x - min_x)
scale_y = available_height / (max_y - min_y)
scale_factor = min(scale_x, scale_y, 0.2)  # Cap at 0.2 for readability
```

### Information Gathering
```python
# Comprehensive monitor information
geometry = screen.geometry()
resolution = f"{geometry.width()}x{geometry.height()}"
position = f"({geometry.x()}, {geometry.y()})"
logical_dpi = screen.logicalDotsPerInch()
physical_dpi = screen.physicalDotsPerInch()
device_pixel_ratio = screen.devicePixelRatio()
refresh_rate = screen.refreshRate()
screen_name = screen.name()
```

### Responsive Design
- Dialog resizes based on number and arrangement of monitors
- Minimum widget sizes ensure readability
- Text truncation for long display names
- Scalable layout accommodates various configurations

---

## Accessibility Considerations

### Keyboard Navigation
- Tab navigation between monitor widgets
- Enter key to select highlighted monitor
- Escape key to cancel dialog

### Visual Accessibility
- High contrast colors for selection states
- Clear visual hierarchy with font weights
- Sufficient color contrast ratios
- Readable font sizes even at small scales

### Screen Reader Support
- Descriptive labels for each monitor widget
- Accessible button text
- Proper dialog structure and navigation

---

## Future Enhancements

### Possible Additions
1. **Remember Last Selection**: Save user's preferred monitor
2. **Quick Launch Shortcut**: Bypass dialog with keyboard shortcut
3. **Monitor Profiles**: Save different configurations
4. **Real-time Preview**: Show annotation window preview on hover
5. **Advanced Info**: Color gamut, HDR support, etc.

### Performance Optimizations
1. **Lazy Loading**: Only create widgets for visible monitors
2. **Caching**: Cache monitor information to avoid repeated queries
3. **Efficient Rendering**: Optimize paint events for smooth interaction