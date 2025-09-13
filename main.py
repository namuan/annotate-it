import json
import logging
import os
import platform
import sys
from pathlib import Path

# Third-party Qt imports
from PyQt6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QImage,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# Optional macOS frameworks imported defensively
try:
    import objc  # type: ignore[import]
    import Quartz  # type: ignore[import]
except Exception:
    Quartz = None  # type: ignore[attr-defined]
    objc = None  # type: ignore[attr-defined]

# Platform flags computed after all imports
IS_MAC = platform.system() == "Darwin"
MAC_NATIVE_CAPTURE_AVAILABLE = bool(Quartz) if IS_MAC else False


class ConfigManager:
    """Manages loading and saving of application configuration."""

    def __init__(self, app_name="annotate_it"):
        self.app_name = app_name
        self.config_file = self.get_config_dir() / "config.json"

    def get_config_dir(self):
        """Determine the configuration directory based on the platform."""
        home = Path.home()
        if sys.platform == "darwin":  # macOS
            config_dir = home / "Library" / "Application Support" / self.app_name
        elif sys.platform == "win32":  # Windows
            config_dir = Path(os.getenv("APPDATA")) / self.app_name
        else:  # Linux and other Unix-like
            config_dir = home / ".config" / self.app_name.lower()

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def load_config(self):
        """Load configuration from file if it exists, otherwise return empty dict."""
        if self.config_file.exists():
            try:
                with self.config_file.open() as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error loading config: {e}")
                return {}
        return {}

    def save_config(self, config):
        """Save configuration to file."""
        try:
            with self.config_file.open("w") as f:
                json.dump(config, f, indent=2)
        except OSError as e:
            print(f"Error saving config: {e}")


class QColorButton(QPushButton):
    """A button that displays a color and allows selection via color dialog."""

    def __init__(self, color):
        super().__init__()
        self.setFixedSize(50, 24)
        self.color = color
        self.setStyleSheet(f"background-color: {color.name()}")

    def mousePressEvent(self, e):
        """Open color dialog on mouse press."""
        color = QColorDialog.getColor(self.color)
        if color.isValid():
            self.color = color
            self.setStyleSheet(f"background-color: {self.color.name()}")
            self.update()


class FloatingMenu(QWidget):
    """Floating menu widget that displays annotation tools and effects."""

    def __init__(self, parent=None):
        """Initialize the floating menu.

        Args:
            parent: Parent widget (TransparentWindow instance)
        """
        super().__init__()
        self.parent_window = parent
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing FloatingMenu")

        # Menu state
        self.is_visible = False
        self.auto_hide_enabled = True  # Auto-hide after tool/effect selection

        # Animation setup
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)  # 300ms animation
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Auto-hide timer
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_menu)
        self.auto_hide_delay = 1500  # 1.5 seconds delay

        # Initialize UI
        self.init_ui()
        self.logger.info("FloatingMenu initialized successfully")

    def init_ui(self):
        """Initialize the user interface for the floating menu."""
        self.logger.debug("Setting up FloatingMenu UI")

        # Set window properties
        self.setWindowTitle("AnnotateIt Floating Menu")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Create layout and buttons
        self.setup_layout()
        self.create_tool_buttons()

        # Set initial size and position
        self.resize(400, 60)
        self.position_menu()

        # Initially hidden
        self.hide()

        self.logger.debug("FloatingMenu UI setup complete")

    def setup_layout(self):
        """Set up the layout for the floating menu."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)

        # Store button references for state management
        self.tool_buttons = {}

        self.logger.debug("Layout setup complete")

    def create_tool_buttons(self):
        """Create buttons for drawing tools and visual effects."""
        self.logger.debug("Creating tool and effect buttons")

        # Define drawing tools with their properties
        tools = [
            {"name": "line", "text": "L", "tooltip": "Line Tool (L)", "shortcut": "L", "type": "tool"},
            {"name": "arrow", "text": "A", "tooltip": "Arrow Tool (A)", "shortcut": "A", "type": "tool"},
            {"name": "rectangle", "text": "R", "tooltip": "Rectangle Tool (R)", "shortcut": "R", "type": "tool"},
            {"name": "ellipse", "text": "E", "tooltip": "Ellipse Tool (E)", "shortcut": "E", "type": "tool"},
            {"name": "text", "text": "T", "tooltip": "Text Tool (T)", "shortcut": "T", "type": "tool"},
        ]

        # Define visual effects with their properties
        effects = [
            {"name": "halo", "text": "H", "tooltip": "Halo Effect (H)", "shortcut": "H", "type": "effect"},
            {
                "name": "flashlight",
                "text": "F",
                "tooltip": "Flashlight Effect (Shift+F)",
                "shortcut": "Shift+F",
                "type": "effect",
            },
            {"name": "mouse_mask", "text": "M", "tooltip": "Mouse Mask Effect (M)", "shortcut": "M", "type": "effect"},
            {"name": "magnifier", "text": "Z", "tooltip": "Magnifier Effect (Z)", "shortcut": "Z", "type": "effect"},
            {
                "name": "passthrough",
                "text": "P",
                "tooltip": "Passthrough Mode (Ctrl+\\)",
                "shortcut": "Ctrl+\\",
                "type": "effect",
            },
        ]

        # Store effect buttons separately for state management
        self.effect_buttons = {}

        # Create tool buttons
        for tool in tools:
            button = self.create_tool_button(tool)
            self.tool_buttons[tool["name"]] = button
            self.main_layout.addWidget(button)

        # Add separator
        self.add_separator()

        # Create effect buttons
        for effect in effects:
            button = self.create_effect_button(effect)
            self.effect_buttons[effect["name"]] = button
            self.main_layout.addWidget(button)

        # Add another separator
        self.add_separator()

        # Define utility functions with their properties
        utilities = [
            {"name": "fill_toggle", "text": "F", "tooltip": "Toggle Fill (F)", "shortcut": "F", "type": "utility"},
            {"name": "opacity", "text": "O", "tooltip": "Cycle Opacity (O)", "shortcut": "O", "type": "utility"},
            {"name": "clear", "text": "C", "tooltip": "Clear All (C)", "shortcut": "C", "type": "utility"},
            {"name": "export", "text": "X", "tooltip": "Export to Clipboard (X)", "shortcut": "X", "type": "utility"},
            {
                "name": "config",
                "text": "⚙",
                "tooltip": "Configuration (Ctrl+,)",
                "shortcut": "Ctrl+,",
                "type": "utility",
            },
        ]

        # Store utility buttons separately for state management
        self.utility_buttons = {}

        # Create utility buttons
        for utility in utilities:
            button = self.create_utility_button(utility)
            self.utility_buttons[utility["name"]] = button
            self.main_layout.addWidget(button)

        self.logger.debug("Tool, effect, and utility buttons created successfully")

    def create_tool_button(self, tool_config):
        """Create a single tool button.

        Args:
            tool_config: Dictionary containing tool configuration

        Returns:
            QToolButton: Configured tool button
        """
        button = QToolButton()
        button.setText(tool_config["text"])
        button.setToolTip(tool_config["tooltip"])
        button.setFixedSize(40, 40)

        # Set button style
        button.setStyleSheet("""
            QToolButton {
                background-color: rgba(255, 255, 255, 30);
                border: 2px solid rgba(255, 255, 255, 100);
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 50);
                border-color: rgba(255, 255, 255, 150);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 70);
            }
            QToolButton:checked {
                background-color: rgba(0, 150, 255, 100);
                border-color: rgba(0, 150, 255, 200);
            }
        """)

        # Make button checkable for active state indication
        button.setCheckable(True)

        # Connect button click to tool selection
        tool_name = tool_config["name"]
        button.clicked.connect(lambda checked, name=tool_name: self.select_tool(name))

        return button

    def add_separator(self):
        """Add a visual separator between tool and effect buttons."""
        separator = QLabel("|")
        separator.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 150);
                font-size: 16px;
                font-weight: bold;
                padding: 0 5px;
            }
        """)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(separator)

    def create_effect_button(self, effect_config):
        """Create a single effect button.

        Args:
            effect_config: Dictionary containing effect configuration

        Returns:
            QToolButton: Configured effect button
        """
        button = QToolButton()
        button.setText(effect_config["text"])
        button.setToolTip(effect_config["tooltip"])
        button.setFixedSize(40, 40)

        # Set button style (different color scheme for effects)
        button.setStyleSheet("""
            QToolButton {
                background-color: rgba(255, 255, 255, 30);
                border: 2px solid rgba(255, 255, 255, 100);
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 50);
                border-color: rgba(255, 255, 255, 150);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 70);
            }
            QToolButton:checked {
                background-color: rgba(255, 165, 0, 100);
                border-color: rgba(255, 165, 0, 200);
            }
        """)

        # Make button checkable for active state indication
        button.setCheckable(True)

        # Connect button click to effect toggle
        effect_name = effect_config["name"]
        button.clicked.connect(lambda checked, name=effect_name: self.toggle_effect(name))

        return button

    def toggle_effect(self, effect_name):
        """Handle effect toggle from button click.

        Args:
            effect_name: Name of the effect to toggle
        """
        self.logger.info("Effect toggled from floating menu: %s", effect_name)

        # Map effect names to parent window methods
        effect_methods = {
            "halo": "toggle_halo",
            "flashlight": "toggle_flashlight",
            "mouse_mask": "toggle_mouse_mask",
            "magnifier": "toggle_magnifier",
            "passthrough": "toggle_passthrough_mode",
        }

        # Call the appropriate method on parent window
        if self.parent_window and effect_name in effect_methods:
            method_name = effect_methods[effect_name]
            if hasattr(self.parent_window, method_name):
                getattr(self.parent_window, method_name)()

                # Update button state based on parent window state
                self.update_effect_state(effect_name)

        # Trigger auto-hide after effect toggle
        self._trigger_auto_hide()

    def update_effect_state(self, effect_name):
        """Update effect button state based on parent window state.

        Args:
            effect_name: Name of the effect to update
        """
        if not self.parent_window or effect_name not in self.effect_buttons:
            return

        # Map effect names to parent window state attributes
        state_attributes = {
            "halo": "show_halo",
            "flashlight": "show_flashlight",
            "mouse_mask": "show_mouse_mask",
            "magnifier": "show_magnifier",
            "passthrough": "passthrough_mode",
        }

        if effect_name in state_attributes:
            attr_name = state_attributes[effect_name]
            if hasattr(self.parent_window, attr_name):
                is_active = getattr(self.parent_window, attr_name)
                self.effect_buttons[effect_name].setChecked(is_active)

    def update_all_effect_states(self):
        """Update all effect button states based on parent window state."""
        for effect_name in self.effect_buttons:
            self.update_effect_state(effect_name)

    def create_utility_button(self, utility_config):
        """Create a single utility button.

        Args:
            utility_config: Dictionary containing utility configuration

        Returns:
            QToolButton: Configured utility button
        """
        button = QToolButton()
        button.setText(utility_config["text"])
        button.setToolTip(utility_config["tooltip"])
        button.setFixedSize(40, 40)

        # Set button style (different color scheme for utilities)
        button.setStyleSheet("""
            QToolButton {
                background-color: rgba(255, 255, 255, 30);
                border: 2px solid rgba(255, 255, 255, 100);
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 50);
                border-color: rgba(255, 255, 255, 150);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 70);
            }
            QToolButton:checked {
                background-color: rgba(128, 255, 128, 100);
                border-color: rgba(128, 255, 128, 200);
            }
        """)

        # Some utility buttons are checkable (like fill toggle)
        if utility_config["name"] == "fill_toggle":
            button.setCheckable(True)

        # Connect button click to utility action
        utility_name = utility_config["name"]
        button.clicked.connect(lambda checked, name=utility_name: self.execute_utility(name))

        return button

    def execute_utility(self, utility_name):
        """Handle utility action from button click.

        Args:
            utility_name: Name of the utility to execute
        """
        self.logger.info("Utility executed from floating menu: %s", utility_name)

        # Map utility names to parent window methods
        utility_methods = {
            "fill_toggle": "toggle_filled_shapes",
            "opacity": "cycle_opacity",
            "clear": "clear_drawings",
            "export": "export_to_image",
            "config": "show_config_dialog",
        }

        # Call the appropriate method on parent window
        if self.parent_window and utility_name in utility_methods:
            method_name = utility_methods[utility_name]
            if hasattr(self.parent_window, method_name):
                getattr(self.parent_window, method_name)()

                # Update button state for toggleable utilities
                if utility_name == "fill_toggle":
                    self.update_utility_state(utility_name)

        # Trigger auto-hide after utility execution (except for config)
        if utility_name != "config":
            self._trigger_auto_hide()

    def update_utility_state(self, utility_name):
        """Update utility button state based on parent window state.

        Args:
            utility_name: Name of the utility to update
        """
        if not self.parent_window or utility_name not in self.utility_buttons:
            return

        # Only fill_toggle has a persistent state
        if utility_name == "fill_toggle" and hasattr(self.parent_window, "filled_shapes"):
            is_active = self.parent_window.filled_shapes
            self.utility_buttons[utility_name].setChecked(is_active)

    def update_all_utility_states(self):
        """Update all utility button states based on parent window state."""
        for utility_name in self.utility_buttons:
            self.update_utility_state(utility_name)

    def _trigger_auto_hide(self):
        """Trigger auto-hide timer if enabled and menu is visible."""
        if self.auto_hide_enabled and self.is_visible:
            self.auto_hide_timer.start(self.auto_hide_delay)
            self.logger.debug("Auto-hide timer started")

    def select_tool(self, tool_name):
        """Handle tool selection from button click.

        Args:
            tool_name: Name of the selected tool
        """
        self.logger.info("Tool selected from floating menu: %s", tool_name)

        # Update button states
        for name, button in self.tool_buttons.items():
            button.setChecked(name == tool_name)

        # Notify parent window of tool change
        if self.parent_window:
            self.parent_window.set_shape(tool_name)

        # Trigger auto-hide after tool selection
        self._trigger_auto_hide()

    def update_active_tool(self, tool_name):
        """Update the active tool indicator.

        Args:
            tool_name: Name of the currently active tool
        """
        self.logger.debug("Updating active tool indicator: %s", tool_name)

        for name, button in self.tool_buttons.items():
            button.setChecked(name == tool_name)

    def position_menu(self):
        """Position the menu at the top center of the screen."""
        if self.parent_window and self.parent_window.target_screen:
            screen = self.parent_window.target_screen
        else:
            screen = QApplication.primaryScreen()

        if screen:
            screen_geometry = screen.geometry()
            menu_width = self.width()

            # Position at top center
            x = screen_geometry.x() + (screen_geometry.width() - menu_width) // 2
            y = screen_geometry.y() + 20  # 20px from top

            self.move(x, y)
            self.logger.debug("Positioned FloatingMenu at (%s, %s)", x, y)

    def toggle_visibility(self):
        """Toggle the visibility of the floating menu."""
        if self.is_visible:
            self.hide_menu()
        else:
            self.show_menu()

    def show_menu(self):
        """Show the floating menu with smooth fade-in animation."""
        if self.is_visible:
            return

        # Cancel any pending auto-hide
        self.auto_hide_timer.stop()

        self.position_menu()  # Ensure correct position
        self.setWindowOpacity(0.0)  # Start invisible
        self.show()

        # Animate fade-in
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

        self.is_visible = True
        self.logger.info("FloatingMenu shown with animation")

    def hide_menu(self):
        """Hide the floating menu with smooth fade-out animation."""
        if not self.is_visible:
            return

        # Animate fade-out
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)

        # Connect to hide the widget when animation finishes
        self.fade_animation.finished.connect(self._on_hide_animation_finished)
        self.fade_animation.start()

        self.is_visible = False
        self.logger.info("FloatingMenu hidden with animation")

    def _on_hide_animation_finished(self):
        """Called when hide animation finishes to actually hide the widget."""
        self.hide()
        # Disconnect to avoid multiple connections
        self.fade_animation.finished.disconnect(self._on_hide_animation_finished)

    def paintEvent(self, event):
        """Custom paint event for semi-transparent background with rounded corners."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent background
        background_color = QColor(0, 0, 0, 180)  # Black with 70% opacity
        painter.setBrush(background_color)
        painter.setPen(Qt.PenStyle.NoPen)

        # Draw rounded rectangle
        rect = self.rect()
        painter.drawRoundedRect(rect, 15, 15)

        super().paintEvent(event)


class TransparentWindow(QWidget):
    """Main transparent window for drawing annotations on screen."""

    default_font_family: str = "HanziPen TC"
    default_font_size: int = 36

    def __init__(self, target_screen=None):
        super().__init__()
        self.target_screen = target_screen
        self.config_manager = ConfigManager()
        self.load_config()
        self.shapes = []
        self.shortcuts = []
        self.init_ui()
        self.drawing = False
        self.lastPoint = QPoint()
        self.currentShape = None
        self.undoStack = []
        self.redoStack = []
        self.font = QFont(self.default_font_family, self.default_font_size)
        self.drawingLayer = QPixmap(self.size())
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        self.cursor_pos = QPoint()
        self.show_halo = False
        self.show_flashlight = False
        self.filled_shapes = False
        self.opacity_levels = [255, 128, 64]
        self.current_opacity_index = 1
        self.current_opacity = self.opacity_levels[self.current_opacity_index]
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.show_mouse_mask = False
        self.mouse_mask_radius = 100
        self.mouse_mask_alpha = 128
        # Magnifier (macOS native) state
        self.show_magnifier = False
        self.magnifier_radii = [120, 240, 480]  # Current size, 2x bigger, 4x bigger
        self.current_magnifier_index = 0
        self.magnifier_radius = self.magnifier_radii[self.current_magnifier_index]
        self.magnifier_factor = 2.0  # Keep zoom factor constant at 2x
        self._below_snapshot = None  # QPixmap of the content below this window
        self.update_timer.setInterval(16)  # ~60 FPS
        QTimer.singleShot(1000, self.toggle_halo)

        # For keeping text
        self.current_text = ""
        self.current_text_pos = None
        self.is_typing = False
        self.show_cursor = True
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.blink_cursor)
        self.cursor_timer.start(500)

        # Initialize floating menu (conditionally based on config)
        self.floating_menu = None
        if self.floating_menu_enabled:
            self.floating_menu = FloatingMenu(self)
        self.logger = logging.getLogger(__name__)
        self.logger.info("TransparentWindow initialized with floating menu: %s", self.floating_menu_enabled)

        # Apply passthrough mode if it was loaded from config
        if self.passthrough_mode:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            # Also apply to floating menu if it exists
            if self.floating_menu:
                self.floating_menu.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.logger.info("Passthrough mode restored from config: %s", self.passthrough_mode)

    def blink_cursor(self):
        """Toggle cursor visibility for text input."""
        if self.is_typing:
            self.show_cursor = not self.show_cursor
            self.update()

    def load_config(self):
        """Load colors, shape, and settings from config."""
        config = self.config_manager.load_config()
        self.shape = config.get("shape", "arrow")
        self.arrowColor = QColor(config.get("arrowColor", "#00FF00"))
        self.rectColor = QColor(config.get("rectColor", "#FF1493"))
        self.ellipseColor = QColor(config.get("ellipseColor", "#00BFFF"))
        self.textColor = QColor(config.get("textColor", "#AA26FF"))
        self.lineColor = QColor(config.get("lineColor", "#FFFF00"))
        self.floating_menu_enabled = config.get("floating_menu_enabled", True)
        # Always start in Draw mode (don't persist passthrough mode)
        self.passthrough_mode = False

    def save_config(self):
        """Save current colors, shape, and settings to config."""
        config = {
            "shape": self.shape,
            "arrowColor": self.arrowColor.name(),
            "rectColor": self.rectColor.name(),
            "ellipseColor": self.ellipseColor.name(),
            "textColor": self.textColor.name(),
            "lineColor": self.lineColor.name(),
            "floating_menu_enabled": self.floating_menu_enabled,
        }
        self.config_manager.save_config(config)

    def closeEvent(self, event):
        """Save config on close."""
        self.save_config()
        super().closeEvent(event)

    def init_ui(self):
        """Initialize UI settings and shortcuts."""
        self.setWindowTitle("Transparent Drawing")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Position window on target screen or maximize on primary screen
        if self.target_screen:
            screen_geometry = self.target_screen.geometry()
            self.setGeometry(screen_geometry)
        else:
            self.showMaximized()

        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        self.shortcuts = [
            QShortcut(QKeySequence("L"), self, lambda: self.set_shape("line")),
            QShortcut(QKeySequence("A"), self, lambda: self.set_shape("arrow")),
            QShortcut(QKeySequence("R"), self, lambda: self.set_shape("rectangle")),
            QShortcut(QKeySequence("E"), self, lambda: self.set_shape("ellipse")),
            QShortcut(QKeySequence("T"), self, lambda: self.set_shape("text")),
            QShortcut(QKeySequence("H"), self, self.toggle_halo),
            QShortcut(QKeySequence("M"), self, self.toggle_mouse_mask),
            QShortcut(QKeySequence("F"), self, self.toggle_filled_shapes),
            QShortcut(QKeySequence("O"), self, self.cycle_opacity),
            QShortcut(QKeySequence("C"), self, self.clear_drawings),
            QShortcut(QKeySequence("X"), self, self.export_to_image),
            QShortcut(QKeySequence("Q"), self, self.close),
            QShortcut(QKeySequence("Ctrl+Z"), self, self.undo),
            QShortcut(QKeySequence("Ctrl+Y"), self, self.redo),
            QShortcut(QKeySequence("Ctrl+,"), self, self.show_config_dialog),
            QShortcut(QKeySequence("Shift+F"), self, self.toggle_flashlight),
            QShortcut(QKeySequence("Z"), self, self.toggle_magnifier),
            QShortcut(QKeySequence("Shift+Z"), self, self.cycle_magnifier_size),
            QShortcut(QKeySequence("Tab"), self, self.toggle_floating_menu),
            QShortcut(QKeySequence("Ctrl+\\"), self, self.toggle_passthrough_mode),
        ]

    def export_to_image(self):
        """Export current drawing to clipboard as image."""
        if self.show_halo:
            self.toggle_halo()
            self.update()
            QTimer.singleShot(50, self._actual_capture)
        else:
            self._actual_capture()

    def _actual_capture(self):
        """Perform the actual screen capture."""
        screen = QApplication.primaryScreen()
        if screen:
            window_rect = self.frameGeometry()
            screen_grab = screen.grabWindow(
                0,
                window_rect.x(),
                window_rect.y(),
                window_rect.width(),
                window_rect.height(),
            )

            pixmap = QPixmap(self.size())
            painter = QPainter(pixmap)
            painter.drawPixmap(0, 0, screen_grab)
            painter.end()
            pixmap = pixmap.copy(QRect(window_rect.topLeft(), window_rect.size()))

            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            print("Image copied to clipboard")
        else:
            print("Screen capture failed")

    def cycle_opacity(self):
        """Cycle through opacity levels."""
        self.current_opacity_index = (self.current_opacity_index + 1) % len(self.opacity_levels)
        self.current_opacity = self.opacity_levels[self.current_opacity_index]
        print(f"Opacity set to {int(self.current_opacity / 255 * 100)}%")

    def disable_shortcuts(self):
        """Disable all shortcuts."""
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)

    def enable_shortcuts(self):
        """Enable all shortcuts."""
        for shortcut in self.shortcuts:
            shortcut.setEnabled(True)

    def toggle_filled_shapes(self):
        """Toggle filled shapes mode."""
        self.filled_shapes = not self.filled_shapes
        print(f"Filled shapes {'enabled' if self.filled_shapes else 'disabled'}")

        # Update floating menu state
        if self.floating_menu:
            self.floating_menu.update_utility_state("fill_toggle")

    def toggle_halo(self):
        """Toggle halo effect around cursor."""
        self.show_halo = not self.show_halo
        self._manage_update_timer()
        self.update()
        print(f"Halo effect {'enabled' if self.show_halo else 'disabled'}")

        # Update floating menu state
        if self.floating_menu:
            self.floating_menu.update_effect_state("halo")

    def toggle_mouse_mask(self):
        """Toggle mouse mask effect."""
        self.show_mouse_mask = not self.show_mouse_mask
        self._manage_update_timer()
        self.update()
        print(f"Mouse mask {'enabled' if self.show_mouse_mask else 'disabled'}")

        # Update floating menu state
        if self.floating_menu:
            self.floating_menu.update_effect_state("mouse_mask")

    def toggle_passthrough_mode(self):
        """Toggle passthrough mode to allow mouse events to pass through to underlying applications."""
        old_mode = self.passthrough_mode
        self.passthrough_mode = not self.passthrough_mode

        self.logger.info("Passthrough mode transition: %s -> %s", old_mode, self.passthrough_mode)

        # Apply or restore passthrough mode
        if self.passthrough_mode:
            self._apply_passthrough_mode()
        else:
            self._restore_draw_mode()

        mode_text = "Pass-through" if self.passthrough_mode else "Draw"
        print(f"Mode switched to: {mode_text}")
        self.logger.info("Mode switched to: %s", mode_text)

        # Update floating menu state
        if self.floating_menu:
            self.floating_menu.update_effect_state("passthrough")

        # Update visual feedback if needed
        self.update()

    def _apply_passthrough_mode(self):
        """Apply passthrough mode using window opacity and mouse interaction."""
        try:
            # Make the window almost invisible and disable mouse interaction
            self.setWindowOpacity(0.01)  # Almost invisible but still present
            self.setMouseTracking(False)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

            # Also apply to floating menu
            if self.floating_menu:
                self.floating_menu.setWindowOpacity(0.01)
                self.floating_menu.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

            self.logger.info("Passthrough mode applied")

        except Exception as e:
            self.logger.warning("Passthrough mode application failed: %s", e)

    def _restore_draw_mode(self):
        """Restore draw mode from passthrough mode."""
        try:
            # Restore full opacity
            self.setWindowOpacity(1.0)

            # Re-enable mouse interaction
            self.setMouseTracking(True)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

            # Ensure window is active and focused
            self.raise_()
            self.activateWindow()
            self.setFocus()

            # Also restore floating menu
            if self.floating_menu:
                self.floating_menu.setWindowOpacity(1.0)
                self.floating_menu.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
                if self.floating_menu.is_visible:
                    self.floating_menu.raise_()

            self.logger.info("Draw mode restored")

        except Exception as e:
            self.logger.warning("Draw mode restoration failed: %s", e)

    def _manage_update_timer(self):
        """Start or stop update timer based on active effects."""
        if self.show_flashlight or self.show_halo or self.show_mouse_mask or self.show_magnifier:
            self.update_timer.start()
        else:
            self.update_timer.stop()

    def show_config_dialog(self):
        """Show configuration dialog."""
        dialog = ConfigDialog(self)
        dialog.exec()
        self.redraw_shapes()

    def set_shape(self, shape):
        """Set current drawing shape."""
        self.shape = shape
        self.save_config()
        print(f"Current shape: {self.shape}")

        # Update floating menu active tool indicator
        if self.floating_menu:
            self.floating_menu.update_active_tool(shape)

    def toggle_floating_menu(self):
        """Toggle the visibility of the floating menu."""
        if self.floating_menu:
            self.floating_menu.toggle_visibility()
            self.logger.info("Floating menu toggled")
        else:
            self.logger.info("Floating menu is disabled in configuration")

    def toggle_floating_menu_enabled(self):
        """Toggle the floating menu enabled/disabled setting."""
        self.floating_menu_enabled = not self.floating_menu_enabled

        if self.floating_menu_enabled:
            # Create floating menu if it doesn't exist
            if not self.floating_menu:
                self.floating_menu = FloatingMenu(self)
                # Apply current passthrough mode to the new floating menu
                if self.passthrough_mode:
                    self.floating_menu.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self.logger.info("Floating menu enabled and created")
        else:
            # Hide and destroy floating menu if it exists
            if self.floating_menu:
                self.floating_menu.hide_menu()
                self.floating_menu = None
                self.logger.info("Floating menu disabled and destroyed")

        self.save_config()
        print(f"Floating menu {'enabled' if self.floating_menu_enabled else 'disabled'}")

    def clear_drawings(self):
        """Clear all drawings."""
        if self.shapes:
            self.undoStack.append(self.shapes.copy())
            self.shapes.clear()
            self.redoStack.clear()
            self.drawingLayer.fill(Qt.GlobalColor.transparent)
            self.update()
            print("Drawings cleared")

    def undo(self):
        """Undo last action."""
        if self.shapes:
            self.redoStack.append(self.shapes.copy())
            self.shapes = self.undoStack.pop() if self.undoStack else []
            self.redraw_shapes()
            self.update()
            print("Undo")

    def redo(self):
        """Redo last undone action."""
        if self.redoStack:
            self.undoStack.append(self.shapes.copy())
            self.shapes = self.redoStack.pop()
            self.redraw_shapes()
            self.update()
            print("Redo")

    def update_cursor_pos(self):
        """Update cursor position relative to window."""
        self.cursor_pos = self.mapFromGlobal(QCursor.pos())

    def get_color_with_opacity(self, color, opacity):
        """Return color with specified opacity."""
        return QColor(color.red(), color.green(), color.blue(), opacity)

    def paintEvent(self, event):
        """Handle painting of the window."""
        if self.show_halo or self.show_flashlight or self.show_mouse_mask or self.show_magnifier:
            self.update_cursor_pos()

        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)

        qp.setBrush(QColor(0, 0, 0, 1))
        qp.drawRect(self.rect())

        qp.drawPixmap(0, 0, self.drawingLayer)

        if self.currentShape:
            self._draw_current_shape(qp)

        if self.is_typing and self.current_text_pos:
            self._draw_current_text(qp)

        if self.show_halo:
            self.draw_halo(qp)
        if self.show_flashlight:
            self.draw_flashlight(qp)
        if self.show_mouse_mask:
            self.draw_mouse_mask(qp)
        if self.show_magnifier:
            self.draw_magnifier(qp)

        # Draw passthrough mode visual indicator
        if self.passthrough_mode:
            self.draw_passthrough_indicator(qp)

    def _draw_current_shape(self, qp):
        """Draw the current shape being created."""
        opacity = self.currentShape.get("opacity", self.current_opacity)
        shape_type = self.currentShape["type"]
        start = self.currentShape["start"]
        end = self.currentShape["end"]

        if shape_type == "arrow":
            qp.setPen(
                QPen(
                    self.get_color_with_opacity(self.arrowColor, opacity),
                    4,
                    Qt.PenStyle.SolidLine,
                )
            )
            self.draw_arrow(qp, start, end)
        elif shape_type == "rectangle":
            color = self.get_color_with_opacity(self.rectColor, opacity)
            qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            qp.setBrush(color if self.filled_shapes else Qt.BrushStyle.NoBrush)
            qp.drawRect(QRect(start, end))
        elif shape_type == "ellipse":
            color = self.get_color_with_opacity(self.ellipseColor, opacity)
            qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            qp.setBrush(color if self.filled_shapes else Qt.BrushStyle.NoBrush)
            qp.drawEllipse(QRect(start, end))
        elif shape_type == "line":
            qp.setPen(
                QPen(
                    self.get_color_with_opacity(self.lineColor, opacity),
                    4,
                    Qt.PenStyle.SolidLine,
                )
            )
            qp.drawLine(start, end)

    def _draw_current_text(self, qp):
        """Draw the current text being typed."""
        qp.setPen(QPen(self.textColor))
        qp.setFont(self.font)
        qp.drawText(self.current_text_pos, self.current_text)

        if self.show_cursor:
            metrics = qp.fontMetrics()
            text_width = metrics.horizontalAdvance(self.current_text)
            cursor_x = self.current_text_pos.x() + text_width
            cursor_y = self.current_text_pos.y()
            qp.drawText(QPoint(cursor_x, cursor_y), "_")

    def get_current_shape_color(self):
        """Get color for current shape."""
        shape_colors = {
            "line": self.lineColor,
            "arrow": self.arrowColor,
            "rectangle": self.rectColor,
            "ellipse": self.ellipseColor,
            "text": self.textColor,
        }
        return shape_colors.get(self.shape, QColor(128, 128, 128))

    def draw_flashlight(self, qp):
        """Draw flashlight effect around cursor."""
        flashlight_radius = 80
        cursor_pos_f = QPointF(self.cursor_pos)
        gradient = QRadialGradient(cursor_pos_f, flashlight_radius)
        gradient.setColorAt(0, QColor(255, 255, 0, 120))
        gradient.setColorAt(0.5, QColor(255, 255, 0, 60))
        gradient.setColorAt(1, QColor(255, 255, 0, 0))
        qp.setBrush(gradient)
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawEllipse(cursor_pos_f, flashlight_radius, flashlight_radius)

    def toggle_flashlight(self):
        """Toggle flashlight effect."""
        self.show_flashlight = not self.show_flashlight
        self._manage_update_timer()
        self.update()
        print(f"Flashlight {'enabled' if self.show_flashlight else 'disabled'}")

        # Update floating menu state
        if self.floating_menu:
            self.floating_menu.update_effect_state("flashlight")

    def draw_halo(self, qp):
        """Draw halo effect around cursor."""
        halo_radius = 20
        cursor_pos_f = QPointF(self.cursor_pos)
        gradient = QRadialGradient(cursor_pos_f, halo_radius)
        shape_color = self.get_current_shape_color()
        gradient.setColorAt(
            0,
            QColor(
                shape_color.red(),
                shape_color.green(),
                shape_color.blue(),
                self.current_opacity,
            ),
        )
        gradient.setColorAt(1, QColor(shape_color.red(), shape_color.green(), shape_color.blue(), 75))
        qp.setBrush(gradient)
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawEllipse(cursor_pos_f, halo_radius, halo_radius)

    def draw_mouse_mask(self, qp):
        """Draw mouse mask effect."""
        outer_path = QPainterPath()
        outer_path.addRect(QRectF(self.rect()))

        inner_path = QPainterPath()
        center = QPointF(self.cursor_pos)
        radius = self.mouse_mask_radius
        inner_path.addEllipse(center, radius, radius)
        mask_path = outer_path.subtracted(inner_path)
        qp.fillPath(mask_path, QColor(0, 0, 0, self.mouse_mask_alpha))

    def draw_passthrough_indicator(self, qp):
        """Draw visual indicator for passthrough mode."""
        # Draw a subtle blue tint overlay to indicate passthrough mode
        qp.setBrush(QColor(0, 150, 255, 15))  # Light blue with very low opacity
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawRect(self.rect())

        # Draw a small indicator in the top-right corner
        indicator_size = 20
        margin = 10
        indicator_rect = QRect(self.width() - indicator_size - margin, margin, indicator_size, indicator_size)

        # Draw the indicator circle
        qp.setBrush(QColor(0, 150, 255, 120))  # More opaque blue for the indicator
        qp.setPen(QPen(QColor(255, 255, 255, 180), 2))  # White border
        qp.drawEllipse(indicator_rect)

        # Draw "P" text in the indicator
        qp.setPen(QColor(255, 255, 255, 220))  # White text
        qp.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        qp.drawText(indicator_rect, Qt.AlignmentFlag.AlignCenter, "P")

    def toggle_magnifier(self):
        """Toggle macOS-native magnifier (captures below this window)."""
        if not IS_MAC or not MAC_NATIVE_CAPTURE_AVAILABLE:
            # Avoid spamming logs repeatedly; show once per toggle attempt.
            if not getattr(self, "_magnifier_warned", False):
                print("Magnifier is only available on macOS with PyObjC/Quartz installed.")
                self._magnifier_warned = True
            return
        # Determine desired state first
        desired = not self.show_magnifier
        # When enabling, proactively request Screen Recording permission on macOS 10.15+
        if desired:
            self._macos_request_screen_capture_access()
        self.show_magnifier = desired
        if not self.show_magnifier:
            self._below_snapshot = None
        self._manage_update_timer()
        self.update()
        print(f"Magnifier {'enabled' if self.show_magnifier else 'disabled'}")

        # Update floating menu state
        if self.floating_menu:
            self.floating_menu.update_effect_state("magnifier")

    def cycle_magnifier_size(self):
        """Cycle through different magnifier window sizes (current, 2x bigger, 4x bigger)."""
        if not IS_MAC or not MAC_NATIVE_CAPTURE_AVAILABLE:
            if not getattr(self, "_magnifier_warned", False):
                print("Magnifier is only available on macOS with PyObjC/Quartz installed.")
                self._magnifier_warned = True
            return

        # If magnifier is not currently shown, enable it first
        if not self.show_magnifier:
            self.toggle_magnifier()
            return

        # Cycle to next magnifier window size
        self.current_magnifier_index = (self.current_magnifier_index + 1) % len(self.magnifier_radii)
        self.magnifier_radius = self.magnifier_radii[self.current_magnifier_index]

        # Update display
        self.update()

        # Print current window size
        size_multiplier = self.current_magnifier_index + 1
        if size_multiplier == 1:
            print("Magnifier: Current window size")
        else:
            print(f"Magnifier: {size_multiplier}x bigger window size")

    def _macos_request_screen_capture_access(self) -> bool:
        """Check/request macOS Screen Recording permission. Returns True if available."""
        if not IS_MAC or not MAC_NATIVE_CAPTURE_AVAILABLE:
            return False
        try:
            preflight_ok = True
            if hasattr(Quartz, "CGPreflightScreenCaptureAccess"):
                preflight_ok = bool(Quartz.CGPreflightScreenCaptureAccess())
            if preflight_ok:
                return True
            # Request will show the system permission dialog (only the first time)
            if hasattr(Quartz, "CGRequestScreenCaptureAccess"):
                granted = bool(Quartz.CGRequestScreenCaptureAccess())
            else:
                granted = False
            if not granted:
                if not getattr(self, "_screen_perm_prompted", False):
                    QMessageBox.information(
                        self,
                        "Screen Recording Permission Required",
                        (
                            "To display the magnifier content, enable Screen Recording for this app:\n\n"
                            "System Settings → Privacy & Security → Screen Recording → enable for Annotate It.\n\n"
                            "After enabling, completely quit and reopen the app for changes to take effect."
                        ),
                    )
                    self._screen_perm_prompted = True
                return False
            return True
        except Exception as e:
            logging.debug("Error getting window number: %s", e)

    def _get_cg_window_id(self):
        """Get the CGWindowID (windowNumber) for this widget's NSWindow (macOS)."""
        try:
            # First attempt: from QWidget.winId() (NSView*)
            wid = int(self.winId())
            nsview = objc.objc_object(c_void_p=wid)
            nswindow = nsview.window()
            if nswindow is not None:
                return int(nswindow.windowNumber())
        except Exception as e:
            logging.debug("Error getting window number: %s", e)
        try:
            # Second attempt: from windowHandle().winId() (NSView*)
            wh = self.windowHandle()
            if wh is not None:
                wid2 = int(wh.winId())
                nsview2 = objc.objc_object(c_void_p=wid2)
                nswindow2 = nsview2.window()
                if nswindow2 is not None:
                    return int(nswindow2.windowNumber())
        except Exception as e:
            logging.debug("Error getting window number: %s", e)
        # Warn once to help user diagnose missing ID (and likely permissions)
        if not getattr(self, "_magnifier_id_warned", False):
            print("Magnifier: unable to obtain NSWindow.windowNumber; lens will show hint only.")
            self._magnifier_id_warned = True
        return None

    def _update_below_snapshot(self):
        """Refresh the snapshot of content below this window (macOS)."""
        if not (IS_MAC and MAC_NATIVE_CAPTURE_AVAILABLE and self.show_magnifier):
            self._below_snapshot = None
            return
        try:
            window_id = self._get_cg_window_id()
            if not window_id:
                self._below_snapshot = None
                return

            # Get the current screen to handle multi-monitor coordinate systems properly
            current_screen = self.target_screen if self.target_screen else self.screen()
            if not current_screen:
                self.logger.debug("Cannot determine current screen for magnifier")
                self._below_snapshot = None
                return

            # Capture only the current screen instead of the entire virtual desktop
            # This fixes the coordinate system issue in multi-monitor setups
            screen_geom = current_screen.geometry()
            screen_rect = Quartz.CGRectMake(
                float(screen_geom.x()), float(screen_geom.y()), float(screen_geom.width()), float(screen_geom.height())
            )

            cgimg = Quartz.CGWindowListCreateImage(
                screen_rect,  # Capture only the current screen, not CGRectInfinite
                Quartz.kCGWindowListOptionOnScreenBelowWindow,
                window_id,
                Quartz.kCGWindowImageDefault,
            )
            if not cgimg:
                self._below_snapshot = None
                return
            width = Quartz.CGImageGetWidth(cgimg)
            height = Quartz.CGImageGetHeight(cgimg)
            bytes_per_row = Quartz.CGImageGetBytesPerRow(cgimg)
            data_provider = Quartz.CGImageGetDataProvider(cgimg)
            data = Quartz.CGDataProviderCopyData(data_provider)
            buf = bytes(data)
            qimg = QImage(
                buf,
                width,
                height,
                bytes_per_row,
                QImage.Format.Format_ARGB32_Premultiplied,
            )
            qimg = qimg.copy()  # Detach from buffer
            full = QPixmap.fromImage(qimg)

            # Account for HiDPI: crop using pixel coordinates relative to the current screen
            dpr = float(current_screen.devicePixelRatio())
            self._below_dpr = dpr

            geom = self.frameGeometry()  # logical coords in global coordinate system

            # Convert window coordinates to screen-relative coordinates
            # This is the key fix for multi-monitor support
            screen_relative_x = geom.x() - screen_geom.x()
            screen_relative_y = geom.y() - screen_geom.y()

            # Convert to pixel coordinates for the captured image
            x_px = int(max(0, min(round(screen_relative_x * dpr), full.width() - 1)))
            y_px = int(max(0, min(round(screen_relative_y * dpr), full.height() - 1)))
            w_px = int(max(1, min(round(geom.width() * dpr), full.width() - x_px)))
            h_px = int(max(1, min(round(geom.height() * dpr), full.height() - y_px)))

            self._below_snapshot = full.copy(QRect(x_px, y_px, w_px, h_px))

            self.logger.debug(
                "Magnifier snapshot updated: screen=%s, window_geom=(%d,%d,%d,%d), "
                "screen_geom=(%d,%d,%d,%d), screen_relative=(%d,%d), pixel_crop=(%d,%d,%d,%d)",
                current_screen.name(),
                geom.x(),
                geom.y(),
                geom.width(),
                geom.height(),
                screen_geom.x(),
                screen_geom.y(),
                screen_geom.width(),
                screen_geom.height(),
                screen_relative_x,
                screen_relative_y,
                x_px,
                y_px,
                w_px,
                h_px,
            )

        except Exception as e:
            # If anything fails, disable snapshot for this frame; lens will show hint.
            self.logger.debug("Magnifier snapshot failed: %s", e)
            self._below_snapshot = None

    def draw_magnifier(self, qp):
        """Draw a circular magnifier showing content below this window, in real time."""
        # Update background snapshot (below this window)
        self._update_below_snapshot()

        center = self.cursor_pos  # logical coords
        radius = self.magnifier_radius
        factor = self.magnifier_factor

        # Always draw the lens outline so user can see the magnifier is active
        qp.save()
        path = QPainterPath()
        path.addEllipse(QPointF(center), radius, radius)
        qp.setClipPath(path)

        if self._below_snapshot is not None:
            # HiDPI-aware source selection
            dpr = getattr(self, "_below_dpr", 1.0)
            center_px = QPoint(int(round(center.x() * dpr)), int(round(center.y() * dpr)))
            src_size_px = max(1, int(round((2 * radius * dpr) / max(0.01, factor))))
            src_rect = QRect(
                center_px.x() - src_size_px // 2,
                center_px.y() - src_size_px // 2,
                src_size_px,
                src_size_px,
            )
            src_rect = src_rect.intersected(QRect(0, 0, self._below_snapshot.width(), self._below_snapshot.height()))
            if not src_rect.isEmpty():
                dst_rect = QRect(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)
                qp.drawPixmap(dst_rect, self._below_snapshot, src_rect)
                # Optionally overlay annotations magnified as well
                logical_src_w = max(1, int(round(src_rect.width() / max(0.01, dpr * factor))))
                logical_src_h = max(1, int(round(src_rect.height() / max(0.01, dpr * factor))))
                ann_src = QRect(
                    center.x() - logical_src_w // 2,
                    center.y() - logical_src_h // 2,
                    logical_src_w,
                    logical_src_h,
                )
                qp.drawPixmap(dst_rect, self.drawingLayer, ann_src)
        else:
            # Snapshot unavailable: fill lens with a subtle hint background and text
            qp.fillRect(
                QRect(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius),
                QColor(0, 0, 0, 120),
            )
            qp.setClipping(False)
            qp.setPen(QPen(QColor(255, 255, 255, 230)))
            qp.setFont(QFont(self.default_font_family, 12))
            hint = "Enable Screen Recording in Settings"
            qp.drawText(
                QRect(center.x() - radius, center.y() - 10, 2 * radius, 20),
                Qt.AlignmentFlag.AlignCenter,
                hint,
            )
            qp.setClipPath(path)  # restore clip for outline

        # Draw lens outline on top with thin double border
        qp.setClipping(False)
        qp.setBrush(Qt.BrushStyle.NoBrush)

        # Outer border (dark)
        outer_pen = QPen(QColor(0, 0, 0, 180))
        outer_pen.setWidth(2)
        qp.setPen(outer_pen)
        qp.drawEllipse(QPointF(center), radius, radius)

        # Inner border (light)
        inner_pen = QPen(QColor(255, 255, 255, 200))
        inner_pen.setWidth(1)
        qp.setPen(inner_pen)
        qp.drawEllipse(QPointF(center), radius - 1, radius - 1)

        qp.restore()

    def focusOutEvent(self, event):
        """Handle focus loss during text input."""
        if self.is_typing and self.current_text:
            self.undoStack.append(self.shapes.copy())
            self.shapes.append({
                "type": "text",
                "position": self.current_text_pos,
                "text": self.current_text,
                "opacity": self.current_opacity,
            })
            self.redraw_shapes()
            self.redoStack.clear()
            self.current_text = ""
            self.current_text_pos = None
            self.is_typing = False
            self.enable_shortcuts()
            self.update()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        """Handle key presses for text input."""
        if self.is_typing:
            if event.key() == Qt.Key.Key_Return:
                if self.current_text:
                    self.undoStack.append(self.shapes.copy())
                    self.shapes.append({
                        "type": "text",
                        "position": self.current_text_pos,
                        "text": self.current_text,
                        "opacity": self.current_opacity,
                    })
                    self.redraw_shapes()
                    self.redoStack.clear()
                self.current_text = ""
                self.current_text_pos = None
                self.is_typing = False
                self.enable_shortcuts()
            elif event.key() == Qt.Key.Key_Escape:
                self.current_text = ""
                self.current_text_pos = None
                self.is_typing = False
                self.enable_shortcuts()
            elif event.key() == Qt.Key.Key_Backspace:
                self.current_text = self.current_text[:-1]
            else:
                self.current_text += event.text()
            self.show_cursor = True
            self.update()

    def mousePressEvent(self, event):
        """Handle mouse press for starting drawings or text."""
        self.logger.debug(
            "Mouse press event received - Button: %s, Position: (%d, %d), Passthrough mode: %s",
            event.button(),
            event.position().x(),
            event.position().y(),
            self.passthrough_mode,
        )
        if self.passthrough_mode:
            self.logger.debug("Mouse press ignored due to passthrough mode")
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self.shape == "text":
                if self.is_typing and self.current_text:
                    self.undoStack.append(self.shapes.copy())
                    self.shapes.append({
                        "type": "text",
                        "position": self.current_text_pos,
                        "text": self.current_text,
                        "opacity": self.current_opacity,
                    })
                    self.redraw_shapes()
                    self.redoStack.clear()

                self.current_text_pos = event.position().toPoint()
                self.is_typing = True
                self.current_text = ""
                self.show_cursor = True
                self.disable_shortcuts()
                self.update()
            else:
                self.drawing = True
                self.lastPoint = event.position().toPoint()
                self.currentShape = {
                    "type": self.shape,
                    "start": self.lastPoint,
                    "end": self.lastPoint,
                    "filled": self.filled_shapes,
                    "opacity": self.current_opacity,
                }

    def redraw_shapes(self):
        """Redraw all shapes on the drawing layer."""
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        qp = QPainter(self.drawingLayer)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        for shape in self.shapes:
            self._draw_shape(qp, shape)
        qp.end()

    def _draw_shape(self, qp, shape):
        """Draw a single shape on the painter."""
        opacity = shape.get("opacity", 128)
        shape_type = shape["type"]

        if shape_type == "arrow":
            qp.setPen(
                QPen(
                    self.get_color_with_opacity(self.arrowColor, opacity),
                    4,
                    Qt.PenStyle.SolidLine,
                )
            )
            self.draw_arrow(qp, shape["start"], shape["end"])
        elif shape_type == "rectangle":
            color = self.get_color_with_opacity(self.rectColor, opacity)
            qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            qp.setBrush(color if shape.get("filled", False) else Qt.BrushStyle.NoBrush)
            qp.drawRect(QRect(shape["start"], shape["end"]))
        elif shape_type == "ellipse":
            color = self.get_color_with_opacity(self.ellipseColor, opacity)
            qp.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            qp.setBrush(color if shape.get("filled", False) else Qt.BrushStyle.NoBrush)
            qp.drawEllipse(QRect(shape["start"], shape["end"]))
        elif shape_type == "line":
            qp.setPen(
                QPen(
                    self.get_color_with_opacity(self.lineColor, opacity),
                    4,
                    Qt.PenStyle.SolidLine,
                )
            )
            qp.drawLine(shape["start"], shape["end"])
        elif shape_type == "text":
            qp.setPen(QPen(self.textColor))
            qp.setFont(self.font)
            qp.drawText(shape["position"], shape["text"])

    def mouseMoveEvent(self, event):
        """Handle mouse movement for updating cursor and drawing."""
        self.cursor_pos = event.position().toPoint()

        # Log mouse move events only when drawing or in debug mode
        if self.drawing or self.passthrough_mode:
            self.logger.debug(
                "Mouse move event - Position: (%d, %d), Drawing: %s, Passthrough mode: %s",
                event.position().x(),
                event.position().y(),
                self.drawing,
                self.passthrough_mode,
            )

        if self.passthrough_mode and not self.drawing:
            # In passthrough mode, we still update cursor position for visual effects but don't handle drawing
            self.update()
            return

        if self.drawing:
            self.currentShape["end"] = self.cursor_pos
            self.logger.debug(
                "Updating current shape end position to (%d, %d)", self.cursor_pos.x(), self.cursor_pos.y()
            )
        self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release for completing drawings."""
        self.logger.debug(
            "Mouse release event received - Button: %s, Position: (%d, %d), Drawing: %s, Passthrough mode: %s",
            event.button(),
            event.position().x(),
            event.position().y(),
            self.drawing,
            self.passthrough_mode,
        )

        if self.passthrough_mode:
            self.logger.debug("Mouse release ignored due to passthrough mode")
            return

        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            end_point = event.position().toPoint()
            self.currentShape["end"] = end_point
            self.undoStack.append(self.shapes.copy())
            self.shapes.append(self.currentShape)
            self.redraw_shapes()
            self.currentShape = None
            self.redoStack.clear()
            print(f"{self.shape.capitalize()} drawn")
            self.logger.debug("Shape completed and added to shapes list: %s", self.shape)
            self.update()

    def draw_arrow(self, qp, start, end):
        """Draw an arrow from start to end."""
        qp.drawLine(start, end)

        arrow_size = 10
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
            return

        dx, dy = dx / length, dy / length

        left = QPoint(
            int(end.x() - arrow_size * (dx + dy)),
            int(end.y() - arrow_size * (dy - dx)),
        )
        right = QPoint(
            int(end.x() - arrow_size * (dx - dy)),
            int(end.y() - arrow_size * (dy + dx)),
        )

        qp.drawLine(end, left)
        qp.drawLine(end, right)

    def resizeEvent(self, event):
        """Handle window resize by updating drawing layer."""
        self.drawingLayer = QPixmap(self.size())
        self.drawingLayer.fill(Qt.GlobalColor.transparent)
        self.redraw_shapes()
        super().resizeEvent(event)


class ConfigDialog(QDialog):
    """Dialog for configuring shortcuts and colors."""

    def __init__(self, parent: TransparentWindow):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

    def init_ui(self):
        """Initialize UI for config dialog."""
        self.setWindowTitle("Keyboard Shortcuts")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(8)
        shortcuts = [
            ("L", "Line Tool"),
            ("A", "Arrow Tool"),
            ("R", "Rectangle Tool"),
            ("E", "Ellipse Tool"),
            ("T", "Text Tool"),
            ("H", "Toggle Halo Effect"),
            ("F", "Toggle Filled Shapes"),
            ("O", "Cycle Opacity (100% → 50% → 25%)"),
            ("C", "Clear All Drawings"),
            ("X", "Export to Image"),
            ("Q", "Quit Application"),
            ("Ctrl+Z", "Undo"),
            ("Ctrl+Y", "Redo"),
            ("Ctrl+,", "Show This Dialog"),
            ("M", "Toggle Mouse Mask"),
            ("Shift+F", "Toggle Flashlight Effect"),
            ("Z", "Toggle Magnifier (macOS only)"),
            ("Shift+Z", "Cycle Magnifier Window Size (macOS only)"),
            ("Ctrl+\\", "Toggle Passthrough Mode (Draw ↔ Pass-through)"),
        ]

        for i, (key, description) in enumerate(shortcuts):
            key_label = QLabel(f"<b>{key}</b>")
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            grid.addWidget(key_label, i, 0)
            grid.addWidget(desc_label, i, 1)

        color_layout = QGridLayout()
        color_layout.setSpacing(8)
        self.arrow_color = QColorButton(self.parent.arrowColor)
        self.rect_color = QColorButton(self.parent.rectColor)
        self.ellipse_color = QColorButton(self.parent.ellipseColor)
        self.text_color = QColorButton(self.parent.textColor)
        self.line_color = QColorButton(self.parent.lineColor)

        color_layout.addWidget(QLabel("Arrow Color:"), 0, 0)
        color_layout.addWidget(self.arrow_color, 0, 1)
        color_layout.addWidget(QLabel("Rectangle Color:"), 1, 0)
        color_layout.addWidget(self.rect_color, 1, 1)
        color_layout.addWidget(QLabel("Ellipse Color:"), 2, 0)
        color_layout.addWidget(self.ellipse_color, 2, 1)
        color_layout.addWidget(QLabel("Text Color:"), 3, 0)
        color_layout.addWidget(self.text_color, 3, 1)
        color_layout.addWidget(QLabel("Line Color:"), 4, 0)
        color_layout.addWidget(self.line_color, 4, 1)

        layout.addLayout(grid)
        layout.addSpacing(20)
        layout.addLayout(color_layout)
        layout.addStretch()
        self.setLayout(layout)

    def closeEvent(self, event):
        """Update parent colors on close."""
        self.parent.arrowColor = self.arrow_color.color
        self.parent.rectColor = self.rect_color.color
        self.parent.ellipseColor = self.ellipse_color.color
        self.parent.textColor = self.text_color.color
        self.parent.lineColor = self.line_color.color
        self.parent.save_config()
        super().closeEvent(event)


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
        max_x = max(screen.geometry().x() + screen.geometry().width() for screen in screens)
        max_y = max(screen.geometry().y() + screen.geometry().height() for screen in screens)

        total_width = max_x - min_x
        total_height = max_y - min_y
        aspect_ratio = total_width / total_height if total_height > 0 else 1.0

        # Determine configuration type
        config_type = "horizontal" if aspect_ratio > 2.0 else "vertical" if aspect_ratio < 0.5 else "mixed"

        # Determine complexity
        complexity = "simple" if len(screens) <= 2 else "moderate" if len(screens) <= 4 else "complex"

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
        min_x, min_y, max_x, max_y = self.analyze_monitor_configuration(screens)["bounds"]
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

    def get_selected_screen(self):
        """Return the selected screen object."""
        app = QApplication.instance()
        screens = app.screens()

        if 0 <= self.selected_monitor_index < len(screens):
            return screens[self.selected_monitor_index]

        # Fallback to primary screen if index is invalid
        return app.primaryScreen()


def main():
    app = QApplication(sys.argv)

    # Show monitor selection dialog if multiple monitors are available
    screens = app.screens()
    target_screen = None

    if len(screens) > 1:
        dialog = MonitorSelectionDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            target_screen = dialog.get_selected_screen()
        else:
            # User cancelled, exit application
            sys.exit(0)

    # Create and show the main window
    ex = TransparentWindow(target_screen)
    ex.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
