# Live Annotation: Alternatives to Snapshot-Based Drawing

This document explores approaches to support drawing annotations directly over the live desktop instead of painting over a captured screenshot. It summarizes how each option works, pros/cons, complexity, and key platform considerations for macOS with PyQt6 + pyobjc.

## Goals and Constraints
- True “glass pane” effect: annotations appear on top of whatever is currently on-screen, with the desktop continuing to update underneath.
- Minimal latency and CPU usage; smooth user interactions.
- Multi-monitor support (one or more displays, different DPIs/scale factors).
- Works (as much as possible) with full-screen apps and across Spaces on macOS.
- Avoid Screen Recording permission if possible; if needed, request it only for specific effects (e.g., magnifier).
- Keep the current PyQt6 tool logic and QPainter-based shapes where practical.

---

## Option 1: Qt Transparent Always-On-Top Overlay Window(s)
Technique
- Create a frameless, translucent QWidget covering each display: use WA_TranslucentBackground, FramelessWindowHint, WindowStaysOnTopHint, Tool.
- Directly paint annotations in paintEvent using QPainter, with no background (transparent window = live screen is visible behind it).
- Toggle input handling: accept mouse/keyboard only during “draw mode”; otherwise set WA_TransparentForMouseEvents so clicks pass through to apps underneath.
- For better reliability on macOS full-screen and Spaces, adjust native window level/behavior via pyobjc (NSWindow.level, canJoinAllSpaces, fullScreenAuxiliary).

Pros
- Zero-copy “live” view (no frame capture), lowest latency and power usage.
- No Screen Recording permission required for general annotation.
- Reuses current QPainter-based shapes and logic; minimal rewrite of drawing code.
- Very responsive; repaint only when annotations change.

Cons
- Must carefully manage input pass-through vs. capture to avoid blocking the user’s underlying apps.
- Multi-monitor requires one overlay window per screen and correct coordinate/DPI mapping.
- To stay reliably above full-screen apps and across Spaces, a tiny Cocoa bridge is recommended to set NSWindow level/collection behavior.

Complexity: Medium

---

## Option 2: Native Cocoa Overlay (NSPanel/NSWindow) via pyobjc
Technique
- Create a non-activating NSPanel/NSWindow with clear background on top of the desktop.
- Set NSWindow.level appropriately (e.g., above normal) and collectionBehavior to canJoinAllSpaces and fullScreenAuxiliary.
- Toggle ignoresMouseEvents to switch between pass-through and drawing modes.
- Render annotations via Core Animation/Quartz or embed a Qt view (hybrid approach).

Pros
- Most control over window level/behavior on macOS; reliable with full-screen/Spaces.
- Fine-grained control of input pass-through.

Cons
- macOS-specific code paths and lifecycle to integrate with the existing PyQt app.
- Slightly more complex interop between Qt and Cocoa.

Complexity: Medium–High

---

## Option 3: Live Screen Capture + Compositing (ScreenCaptureKit / CGDisplayStream)
Technique
- Stream the desktop frames continuously (per display), draw annotations on top, and present this stream in a window.

Pros
- Predictable rendering pipeline; similar to today’s screenshot approach but continuous.
- Can capture a single app/window or full display (depending on API).

Cons
- Requires Screen Recording permission (user prompt and privacy settings).
- Adds latency (1–2 frames) and higher CPU/GPU usage compared to a glass overlay.
- Users interact with a “video of the desktop” rather than the actual desktop, so true input pass-through is not possible.

Complexity: Medium–High

---

## Option 4: Hybrid Overlay + Targeted Pixel Sampling (for effects)
Technique
- Use Option 1 overlay for general annotation.
- For effects that require pixels (magnifier/flashlight), sample a small region under the cursor with Quartz (e.g., CGDisplayCreateImageForRect) only when needed.

Pros
- Keeps the overlay path fast and permission-free for typical annotation use.
- Effect-specific pixel sampling is sporadic and cheaper than full-time streaming.

Cons
- On modern macOS versions, any on-screen pixel capture may still require Screen Recording permission.
- Additional complexity to integrate sampling, scaling, and Retina handling.

Complexity: Medium

---

## Option 5: GPU-Accelerated Overlay (QOpenGLWidget/CAMetalLayer)
Technique
- Render the overlay with an accelerated layer (OpenGL/Metal) for very smooth animations and heavy visual effects.

Pros
- Best performance headroom for complex effects, transitions, particles.

Cons
- Higher implementation complexity; driver/platform nuances.
- Still needs the same window-level and input pass-through handling as Option 1/2.

Complexity: High

---

## Option 6: Virtual Display Mirroring Pipeline
Technique
- Mirror the desktop into a controlled surface (virtual display or mirroring target), draw annotations, and present the result.

Pros
- Maximum isolation and control over the rendered content.

Cons
- Overkill for annotation, requires advanced APIs/permissions, and may degrade UX.
- Not suitable for lightweight, low-latency on-screen markup.

Complexity: Very High

---

## Recommendations
Primary: Option 1 (Qt Overlay) with a small Cocoa bridge
- Best match for current PyQt6 + QPainter architecture: minimal rewrite and no continuous capture.
- True live desktop underneath; lowest latency and no recording permission for standard annotation.
- Augment with native tweaks: set NSWindow.level, canJoinAllSpaces, and fullScreenAuxiliary for robust behavior with full-screen apps and Spaces.
- If magnifier/spotlight effects are needed, combine with Option 4’s targeted pixel sampling.

Secondary: Option 2 (Native Cocoa Overlay) as a fallback
- If Qt overlay proves unreliable in edge cases (certain full-screen contexts), the native NSPanel overlay provides the strongest control on macOS.
- Keep the rest of the app and tool logic in Qt; use pyobjc for window management and a drawable surface.

---

## High-Level Implementation Plan (Primary Option)
1) Overlay Manager per Display
- Create one transparent, always-on-top overlay window per QScreen with devicePixelRatio-aware geometry.
- Sync overlay geometry when displays change or the cursor moves across screens.

2) Rendering and State
- Maintain the current annotation model (shapes, pens, fills, text) and paint them in the overlay’s paintEvent.
- No backing screenshot; repaint only on changes to annotations or hover feedback.

3) Input Modes
- Two modes: “Pass-through” (ignore mouse/keyboard) and “Draw” (capture input on overlay).
- Global hotkeys to toggle modes; in draw mode, the overlay accepts events; exiting draw mode returns to pass-through.

4) macOS-Specific Window Behavior
- Via pyobjc, set NSWindow.level to stay reliably on top; set collectionBehavior to canJoinAllSpaces | fullScreenAuxiliary.
- Optionally set non-activating panel behavior to avoid stealing focus when not drawing.

5) Effects Requiring Pixels (Optional)
- Implement targeted pixel sampling only when needed (e.g., magnifier), with proper scaling for Retina.
- Gate this behind a permission check and a graceful fallback if permission is denied.

This approach keeps the UX simple, responsive, and privacy-friendly while leveraging the existing PyQt6 architecture.
