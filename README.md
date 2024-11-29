<p align="center">
  <img src="https://github.com/namuan/annotate-it/raw/main/assets/icon.png" width="128px"/>
</p>
<h1 align="center">Draw, Label, Present—Your Ideas, Amplified</h1>

![](assets/demo.gif)

## Usage

The app works with keyboard shortcuts.

### Keyboard Shortcuts

- `A/a`: Switch to arrow drawing mode
- `R/r`: Switch to rectangle drawing mode
- `E/e`: Switch to ellipse drawing mode
- `T/t`: Switch to text input mode
- `L/l`: Switch to line drawing mode
- `F/f`: Toggle filled shapes on/off
- `O/o`: Cycle through opacity levels (100% → 50% → 25%)
- `H/h`: Toggle halo effect on/off
- `C/c`: Clear all drawings
- `Q/q`: Quit the application
- `Ctrl+Z`: Undo last action
- `Ctrl+Y`: Redo last undone action
- `Cmd+, (Ctrl+, on Windows/Linux)`: Open configuration dialog

## Halo Effect

The application features a halo effect that highlights the cursor position and current drawing tool color.
By default, the halo effect is enabled when the application starts.

- To toggle the halo effect on or off, press the `H` or `h` key.
- The halo color corresponds to the color of the currently selected drawing tool.

## Configuration

Press `Cmd+,` (or `Ctrl+,` on Windows/Linux) to open the configuration dialog. This dialog allows you to:

- View all keyboard shortcuts
- Customize colors for different drawing tools:
    - Arrow color
    - Rectangle color
    - Ellipse color
    - Text color
    - Line color

Changes to colors are applied immediately after closing the configuration dialog.

## Getting Started

* Install the required dependencies:

```shell
pip install -r requirements.txt
```

* Run the application:

```shell
python main.py
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or create issues for bugs and
feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
