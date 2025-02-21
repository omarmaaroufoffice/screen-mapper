import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QLineEdit, QScrollArea, QMessageBox)
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QFontMetrics, QScreen
from mss import mss
from PIL import Image
import numpy as np
from pynput.mouse import Controller, Button
import os
import time

class ClickableLabel(QLabel):
    clicked = Signal(QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(event.position().toPoint())

class ScreenMapper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mouse = Controller()
        self.markers = {}  # Dictionary to store markers {label: QPoint}
        self.screenshot_path = "screenshot.png"
        self.markers_path = "markers.json"
        self.grid_size = 40  # 40x40 grid
        self.test_mode = False
        
        # Get the primary screen
        self.screen = QApplication.primaryScreen()
        self.screen_geometry = self.screen.geometry()
        self.screen_size = self.screen_geometry.size()
        
        # Store actual screen dimensions
        self.actual_width = self.screen_size.width()
        self.actual_height = self.screen_size.height()
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Screen Mapper')
        # Set window size to match screen size
        self.setGeometry(0, 0, self.actual_width, self.actual_height)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create controls
        controls_layout = QHBoxLayout()
        
        # Screenshot button
        self.screenshot_btn = QPushButton('Take Screenshot')
        self.screenshot_btn.clicked.connect(self.take_screenshot)
        controls_layout.addWidget(self.screenshot_btn)
        
        # Test Grid button
        self.test_btn = QPushButton('Test Grid')
        self.test_btn.clicked.connect(self.test_grid)
        controls_layout.addWidget(self.test_btn)
        
        # Command input
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText('Enter grid coordinate (e.g. aa01) to click')
        self.command_input.returnPressed.connect(self.execute_command)
        controls_layout.addWidget(self.command_input)
        
        # Add controls to main layout
        layout.addLayout(controls_layout)
        
        # Create scroll area for screenshot
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create image label
        self.image_label = ClickableLabel(self)
        self.image_label.clicked.connect(self.add_marker)
        scroll_area.setWidget(self.image_label)
        
        # Add scroll area to main layout
        layout.addWidget(scroll_area)
        
        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Load existing screenshot and markers if they exist
        self.load_existing_data()
        
    def take_screenshot(self):
        with mss() as sct:
            # Get the main monitor
            monitor = sct.monitors[1]  # Primary monitor
            
            # Ensure we capture the full screen
            screenshot = sct.grab({
                'top': 0,
                'left': 0,
                'width': self.actual_width,
                'height': self.actual_height
            })
            
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            img.save(self.screenshot_path)
            
            # Display the screenshot
            self.display_screenshot()
            
            # Clear existing markers
            self.markers.clear()
            self.save_markers()
            
    def display_screenshot(self):
        if os.path.exists(self.screenshot_path):
            pixmap = QPixmap(self.screenshot_path)
            self.draw_grid_and_markers(pixmap)
            
    def draw_grid_and_markers(self, pixmap):
        if not pixmap.isNull():
            # Create a copy of the pixmap to draw on
            drawing_pixmap = QPixmap(pixmap)
            painter = QPainter(drawing_pixmap)
            
            # Enable anti-aliasing for smoother lines
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set up grid properties
            cell_width = pixmap.width() // self.grid_size
            cell_height = pixmap.height() // self.grid_size
            
            # Set up painter properties for grid
            # Using bright cyan with 50% transparency
            grid_pen = QPen(QColor(0, 255, 255, 127), 2)  # Bright cyan, 50% transparent
            painter.setPen(grid_pen)
            
            # Configure font for grid labels - using monospace for consistent recognition
            font = QFont("Courier")  # Monospace font
            font.setPixelSize(16)  # Larger size for better visibility
            font.setBold(True)
            font.setStyleStrategy(QFont.PreferAntialias)
            painter.setFont(font)
            font_metrics = QFontMetrics(font)
            
            # Draw grid cells with coordinates
            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    x = col * cell_width
                    y = row * cell_height
                    
                    # Draw cell rectangle
                    painter.drawRect(x, y, cell_width, cell_height)
                    
                    # Create cell coordinate label with consistent format
                    coord = f"{self.get_column_label(col)}{row + 1:02d}"
                    
                    # Calculate text position to center it in the cell
                    text_width = font_metrics.horizontalAdvance(coord)
                    text_height = font_metrics.height()
                    text_x = x + (cell_width - text_width) // 2
                    text_y = y + (cell_height + text_height) // 2
                    
                    # Draw background rectangle for text
                    text_rect = QRect(text_x - 4, text_y - text_height, text_width + 8, text_height + 4)
                    
                    if self.test_mode and coord in self.markers:
                        # Use bright green with 50% transparency for valid cells in test mode
                        painter.fillRect(text_rect, QColor(0, 255, 0, 127))  # Bright green, 50% transparent
                    else:
                        # Use black with 50% transparency for regular mode
                        painter.fillRect(text_rect, QColor(0, 0, 0, 127))  # 50% transparent black
                    
                    # Draw coordinate text in high-contrast color with 50% transparency
                    painter.setPen(QPen(QColor(255, 255, 0, 127)))  # Bright yellow, 50% transparent
                    painter.drawText(text_x, text_y, coord)
                    painter.setPen(grid_pen)  # Restore grid pen
            
            # Draw markers
            if not self.test_mode:
                # Use magenta with 50% transparency for markers
                marker_pen = QPen(QColor(255, 0, 255, 127), 3)  # Bright magenta, 50% transparent
                painter.setPen(marker_pen)
                
                for label, point in self.markers.items():
                    # Draw marker circle
                    painter.drawEllipse(point, 8, 8)  # Larger circles for better visibility
                    
                    # Draw label with semi-transparent background and text
                    text_width = font_metrics.horizontalAdvance(label)
                    text_height = font_metrics.height()
                    text_rect = QRect(point.x() + 12, point.y() - text_height//2,
                                    text_width + 8, text_height + 4)
                    
                    painter.fillRect(text_rect, QColor(0, 0, 0, 127))  # 50% transparent black
                    painter.setPen(QPen(QColor(255, 255, 0, 127)))  # 50% transparent yellow
                    painter.drawText(point.x() + 16, point.y() + text_height//2, label)
            
            painter.end()
            self.image_label.setPixmap(drawing_pixmap)
            
    def get_column_label(self, index):
        """Convert numeric index to two-letter label (aa-zz)"""
        # Format consistently for AI recognition
        first_letter = chr(97 + (index // 26))  # a-z for first letter
        second_letter = chr(97 + (index % 26))  # a-z for second letter
        return f"{first_letter}{second_letter}".lower()  # Ensure lowercase
            
    def get_grid_coordinates(self, pos):
        """Convert pixel position to grid coordinates"""
        if not hasattr(self, 'image_label') or not self.image_label.pixmap():
            return None
            
        cell_width = self.image_label.pixmap().width() // self.grid_size
        cell_height = self.image_label.pixmap().height() // self.grid_size
        
        col = pos.x() // cell_width
        row = pos.y() // cell_height
        
        if 0 <= col < self.grid_size and 0 <= row < self.grid_size:
            return f"{self.get_column_label(col)}{row + 1:02d}"  # Two digits with leading zero
        return None
        
    def get_grid_center(self, coord):
        """Convert grid coordinates to pixel position"""
        if not self.image_label.pixmap():
            return None
            
        # Convert to lowercase and remove any whitespace
        coord = coord.lower().strip()
        
        # Check format: should be 4 characters (2 letters + 2 numbers)
        if len(coord) != 4:
            return None
            
        letters = coord[:2]
        numbers = coord[2:]
            
        try:
            # Validate letters are a-z
            if not (letters[0].isalpha() and letters[1].isalpha()):
                return None
                
            # Calculate column index
            first_letter_val = ord(letters[0]) - 97
            second_letter_val = ord(letters[1]) - 97
            col = first_letter_val * 26 + second_letter_val
            
            # Parse row number (1-40)
            row = int(numbers) - 1
            
            # Validate ranges
            if not (0 <= col < self.grid_size and 0 <= row < self.grid_size):
                return None
            if not (1 <= int(numbers) <= 40):
                return None
                
            # Calculate actual screen position
            cell_width = self.actual_width // self.grid_size
            cell_height = self.actual_height // self.grid_size
            
            # Return center of the cell in actual screen coordinates
            x = (col * cell_width) + (cell_width // 2)
            y = (row * cell_height) + (cell_height // 2)
            return QPoint(x, y)
                
        except (ValueError, IndexError):
            return None
        
    def add_marker(self, pos):
        grid_coord = self.get_grid_coordinates(pos)
        if grid_coord:
            self.markers[grid_coord] = pos
            self.save_markers()
            self.display_screenshot()
            
    def execute_command(self):
        """Execute click at the specified coordinate"""
        coord = self.command_input.text().strip().lower()
        point = self.get_grid_center(coord)
        if point:
            # Move mouse to position first
            self.mouse.position = (point.x(), point.y())
            
            # Wait briefly to ensure proper window focus
            time.sleep(0.1)
            
            # Click to focus window/element
            self.mouse.click(Button.left)
            
            # Wait half a second before actual action click
            time.sleep(0.5)
            
            # Perform action click
            self.mouse.click(Button.left)
            
            self.command_input.clear()
        else:
            # Show error message for invalid coordinate
            QMessageBox.warning(self, "Invalid Coordinate", 
                              f"The coordinate '{coord}' is not valid.\n" +
                              "Format should be: aann\n" +
                              "where:\n" +
                              "- aa is two letters (a-z)\n" +
                              "- nn is two digits (01-40)\n" +
                              "Examples: aa01, ab40, zz20")
            
    def save_markers(self):
        markers_dict = {label: (point.x(), point.y()) for label, point in self.markers.items()}
        with open(self.markers_path, 'w') as f:
            json.dump(markers_dict, f)
            
    def load_existing_data(self):
        if os.path.exists(self.markers_path):
            with open(self.markers_path, 'r') as f:
                markers_dict = json.load(f)
                self.markers = {label: QPoint(x, y) for label, (x, y) in markers_dict.items()}
        
        if os.path.exists(self.screenshot_path):
            self.display_screenshot()

    def test_grid(self):
        """Test all grid coordinates systematically"""
        self.test_mode = True
        self.markers.clear()
        
        # Create a test image with white background
        test_image = Image.new('RGB', (1920, 1080), 'white')
        test_image.save(self.screenshot_path)
        
        # Display the test grid
        self.display_screenshot()
        
        # Test each coordinate
        invalid_coords = []
        valid_coords = []
        total_coords = self.grid_size * self.grid_size
        processed = 0
        
        # Test all possible combinations
        for row in range(1, 41):
            for col in range(self.grid_size):
                coord = f"{self.get_column_label(col)}{row:02d}"  # Two digits with leading zero
                point = self.get_grid_center(coord)
                if point is None:
                    invalid_coords.append(coord)
                else:
                    valid_coords.append(coord)
                processed += 1
                self.status_label.setText(f"Testing coordinates: {processed}/{total_coords}")
                QApplication.processEvents()
        
        # Add all valid coordinates to markers for display
        for coord in valid_coords:
            self.markers[coord] = self.get_grid_center(coord)
        
        # Display results
        self.display_screenshot()
        
        if invalid_coords:
            QMessageBox.warning(self, "Test Results", 
                              f"Found {len(invalid_coords)} invalid coordinates:\n" +
                              ", ".join(invalid_coords))
        else:
            QMessageBox.information(self, "Test Results", 
                                  f"All coordinates are valid!\n" +
                                  f"Tested {len(valid_coords)} coordinates\n" +
                                  "Format: aann (aa=letters, nn=01-40)\n" +
                                  "Examples: aa01, ab40, zz20")
        
        self.test_mode = False
        self.status_label.setText("Grid test completed")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ScreenMapper()
    ex.show()
    sys.exit(app.exec()) 