# Screen Mapper with Grid

A Python application that creates a 40x40 grid overlay on your screen, allowing you to easily reference and click on specific locations using grid coordinates (like A1, B2, etc.).

## Features

- Take screenshots of your screen
- Automatically overlays a 40x40 grid with letter-number coordinates
- Grid coordinates use Excel-style notation:
  - Columns: A-Z, then AA-AN (40 columns total)
  - Rows: 1-40
- Click on any grid cell by typing its coordinate (e.g., "A1" or "AA40")
- Automatically saves screenshots and grid data for future sessions
- Scrollable interface for large screenshots
- Simple and intuitive UI

## Installation

1. Ensure you have Python 3.8+ installed
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python src/screen_mapper.py
```

2. Using the application:
   - Click "Take Screenshot" to capture your screen
   - The screenshot will be overlaid with a 40x40 grid
   - Each cell is labeled with:
     - Columns: A-Z, then AA-AN
     - Rows: 1-40
   - To click at a specific grid location, type its coordinate (e.g., "A1") in the command input and press Enter

## Controls

- **Take Screenshot Button**: Captures a new screenshot of your screen
- **Command Input**: Enter a grid coordinate (e.g., "A1" or "AA40") and press Enter to click at that location

## Grid System

The grid system divides your screen into a 40x40 matrix:
- Horizontal coordinates: A through Z, then AA through AN (40 columns)
- Vertical coordinates: 1 through 40 (40 rows)
- Examples of valid coordinates:
  - "A1" (top-left corner)
  - "Z20" (middle-right area)
  - "AA1" (27th column, first row)
  - "AN40" (bottom-right corner)

## Data Storage

The application automatically saves:
- The latest screenshot as `screenshot.png`
- Grid data as `markers.json`

These files are loaded automatically when you restart the application. 