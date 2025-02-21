import os
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QBuffer, QIODevice
from screen_mapper import ScreenMapper
import json
import time
from dotenv import load_dotenv
from pathlib import Path
import datetime

class AIController:
    def __init__(self):
        # Load environment variables
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)
        
        # Get API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        # Initialize Gemini with new client format
        self.client = genai.Client(api_key=api_key)
        
        # Initialize ScreenMapper
        self.app = QApplication([])
        self.screen_mapper = ScreenMapper()
        
        # Create screenshots directory if it doesn't exist
        self.screenshots_dir = Path(__file__).parent.parent / 'screenshots'
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # Hide the main window - we'll just use it for screenshots
        self.screen_mapper.hide()
        
    def capture_grid_screenshot(self):
        """Take a screenshot with grid overlay and return as PIL Image"""
        # Take screenshot
        self.screen_mapper.take_screenshot()
        
        # Get the QPixmap with grid overlay
        pixmap = self.screen_mapper.image_label.pixmap()
        
        # Convert QPixmap to PIL Image using QBuffer
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        
        # Convert to PIL Image
        image_data = buffer.data().data()
        buffer.close()
        
        return Image.open(BytesIO(image_data))

    def save_annotated_screenshot(self, image, coordinate, user_request):
        """Save both original and annotated screenshots"""
        # Generate timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save original screenshot
        original_path = self.screenshots_dir / f"screenshot_{timestamp}_original.png"
        image.save(original_path)
        
        # Create annotated version
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        
        # Calculate grid cell size
        cell_width = image.width // 40
        cell_height = image.height // 40
        
        # Calculate coordinate position
        col = (ord(coordinate[0]) - ord('a')) * 26 + (ord(coordinate[1]) - ord('a'))
        row = int(coordinate[2:]) - 1
        
        # Calculate box coordinates
        x1 = col * cell_width
        y1 = row * cell_height
        x2 = x1 + cell_width
        y2 = y1 + cell_height
        
        # Draw highlight box (semi-transparent red)
        draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)
        draw.rectangle([x1+1, y1+1, x2-1, y2-1], fill=(255, 0, 0, 64))
        
        # Add annotation text
        text = f"Request: {user_request}\nCoordinate: {coordinate}"
        draw.text((10, 10), text, fill=(255, 0, 0), stroke_width=2, stroke_fill=(255, 255, 255))
        
        # Save annotated version
        annotated_path = self.screenshots_dir / f"screenshot_{timestamp}_annotated.png"
        annotated.save(annotated_path)
        
        print(f"\nSaved screenshots to:")
        print(f"Original: {original_path}")
        print(f"Annotated: {annotated_path}")

    def execute_action(self, user_request):
        """Process user request and execute action"""
        # Capture screenshot with grid
        image = self.capture_grid_screenshot()
        
        # Prepare prompt for Gemini
        prompt = f"""
        I am showing you a screenshot with a 40x40 coordinate grid overlay.
        The grid uses coordinates like 'aa01' through 'an40'.
        
        User request: {user_request}
        
        Please analyze the screenshot and tell me the exact grid coordinate 
        (in format 'aa01' through 'an40') where I should click to fulfill this request.
        
        ONLY respond with the coordinate in lowercase, nothing else.
        For example: 'ab12' or 'ak40'
        """
        
        # Get response from Gemini using new client format
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, image]
        )
        coordinate = response.text.strip().lower()
        
        # Validate coordinate format
        if not (len(coordinate) == 4 and 
                coordinate[:2].isalpha() and 
                coordinate[2:].isdigit() and
                1 <= int(coordinate[2:]) <= 40):
            raise ValueError(f"Invalid coordinate format: {coordinate}")
        
        # Save screenshots before executing click
        self.save_annotated_screenshot(image, coordinate, user_request)
            
        # Execute click at coordinate
        self.screen_mapper.command_input.setText(coordinate)
        self.screen_mapper.execute_command()
        
        return coordinate

def main():
    try:
        # Create controller
        controller = AIController()
        
        while True:
            try:
                request = input("\nWhat would you like the AI to do? (or 'quit' to exit): ")
                if request.lower() == 'quit':
                    break
                    
                coordinate = controller.execute_action(request)
                print(f"Clicked at coordinate: {coordinate}")
                
            except Exception as e:
                print(f"Error: {e}")
                
    except Exception as e:
        print(f"Initialization error: {e}")
            
if __name__ == "__main__":
    main() 