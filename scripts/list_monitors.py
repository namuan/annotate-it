#!/usr/bin/env python3
"""
Simple Monitor Listing Script for PyQt6

This script provides a simple way to list all connected monitors
and their key properties for multi-monitor development and testing.
"""

import sys

from PyQt6.QtWidgets import QApplication


def list_all_monitors():
    """List all connected monitors with their properties"""
    print("=== PyQt6 Monitor Detection ===")
    print()

    # Get all screens
    screens = QApplication.screens()
    primary_screen = QApplication.primaryScreen()

    print(f"Total monitors detected: {len(screens)}")
    print(f"Primary monitor: {primary_screen.name()}")
    print()

    for i, screen in enumerate(screens):
        is_primary = screen == primary_screen
        print(f"Monitor {i + 1}{' (PRIMARY)' if is_primary else ''}:")
        print(f"  Name: {screen.name()}")
        print(f"  Manufacturer: {screen.manufacturer()}")
        print(f"  Model: {screen.model()}")
        print(f"  Serial Number: {screen.serialNumber()}")

        # Geometry information
        geometry = screen.geometry()
        available = screen.availableGeometry()
        print(f"  Full Geometry: {geometry.width()}x{geometry.height()} at ({geometry.x()}, {geometry.y()})")
        print(f"  Available Area: {available.width()}x{available.height()} at ({available.x()}, {available.y()})")

        # DPI and scaling information
        dpr = screen.devicePixelRatio()
        logical_dpi = screen.logicalDotsPerInch()
        physical_dpi = screen.physicalDotsPerInch()
        print(f"  Device Pixel Ratio: {dpr:.2f}")
        print(f"  Logical DPI: {logical_dpi:.1f}")
        print(f"  Physical DPI: {physical_dpi:.1f}")

        # Display characteristics
        print(f"  Refresh Rate: {screen.refreshRate():.1f} Hz")
        print(f"  Color Depth: {screen.depth()} bits")
        print(f"  Orientation: {screen.orientation().name}")
        print(f"  Native Orientation: {screen.nativeOrientation().name}")

        # DPI classification
        if dpr >= 2.0:
            dpi_class = "High DPI (2x or higher)"
        elif dpr >= 1.5:
            dpi_class = "Medium-High DPI (1.5x)"
        elif dpr > 1.0:
            dpi_class = "Medium DPI (>1x)"
        else:
            dpi_class = "Standard DPI (1x)"
        print(f"  DPI Classification: {dpi_class}")

        # Coordinate system analysis
        if geometry.x() < 0:
            x_pos = f"{abs(geometry.x())} pixels LEFT of primary"
        elif geometry.x() > 0:
            x_pos = f"{geometry.x()} pixels RIGHT of primary"
        else:
            x_pos = "horizontally aligned with primary"

        if geometry.y() < 0:
            y_pos = f"{abs(geometry.y())} pixels ABOVE primary"
        elif geometry.y() > 0:
            y_pos = f"{geometry.y()} pixels BELOW primary"
        else:
            y_pos = "vertically aligned with primary"

        print(f"  Position: {x_pos}, {y_pos}")
        print()


def get_monitor_summary():
    """Get a brief summary of monitor configuration"""
    screens = QApplication.screens()

    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    dpi_ratios = []

    for screen in screens:
        geometry = screen.geometry()

        # Calculate virtual desktop bounds
        min_x = min(min_x, geometry.x())
        max_x = max(max_x, geometry.x() + geometry.width())
        min_y = min(min_y, geometry.y())
        max_y = max(max_y, geometry.y() + geometry.height())

        dpi_ratios.append(screen.devicePixelRatio())

    virtual_width = max_x - min_x
    virtual_height = max_y - min_y

    print("=== Monitor Configuration Summary ===")
    print(f"Number of monitors: {len(screens)}")
    print(f"Virtual desktop size: {virtual_width}x{virtual_height}")
    print(f"Virtual desktop bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"DPI ratios: {', '.join(f'{dpr:.1f}x' for dpr in dpi_ratios)}")

    # Check for mixed DPI setup
    unique_dprs = set(dpi_ratios)
    if len(unique_dprs) > 1:
        print("⚠️  Mixed DPI setup detected - ensure proper scaling handling")
    else:
        print("✅ Uniform DPI setup")

    # Check for negative coordinates
    if min_x < 0 or min_y < 0:
        print("⚠️  Negative coordinates detected - handle coordinate system carefully")
    else:
        print("✅ All coordinates positive")

    print()


def main():
    """Main function to run monitor detection"""
    # Create QApplication (required for screen detection)
    QApplication(sys.argv)

    try:
        # List all monitors in detail
        list_all_monitors()

        # Show configuration summary
        get_monitor_summary()

        print("Monitor detection completed successfully!")

    except Exception as e:
        print(f"Error during monitor detection: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
