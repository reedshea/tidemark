#!/usr/bin/env python3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import datetime
import os
import argparse

# E-ink display dimensions (7.8 inch display)
WIDTH = 1872
HEIGHT = 1404

# Sky and graph dimensions
SKY_HEIGHT = 300
GRAPH_MARGIN_LEFT = 100
GRAPH_MARGIN_RIGHT = 50
GRAPH_MARGIN_BOTTOM = 100
GRAPH_MARGIN_TOP = 50

def load_font(size):
    """Load a font with fallbacks for different platforms"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/Library/Fonts/Arial.ttf",                         # macOS
        "/System/Library/Fonts/Supplemental/Arial.ttf"      # Alternative macOS
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    
    # Fallback to default font
    return ImageFont.load_default()

def draw_sky(draw, is_night=False):
    """Draw the sky with sun/moon and day/night features"""
    # Fill sky background
    if is_night:
        # Night sky (black)
        draw.rectangle([(0, 0), (WIDTH, SKY_HEIGHT)], fill=0)
        
        # Add stars
        np.random.seed(42)  # For consistent star pattern
        for _ in range(200):
            x = np.random.randint(0, WIDTH)
            y = np.random.randint(0, SKY_HEIGHT-20)
            size = np.random.choice([2, 3])
            draw.rectangle([(x, y), (x+size, y+size)], fill=255)
        
        # Draw moon
        moon_x, moon_y = WIDTH//2, SKY_HEIGHT//3
        radius = 60
        draw.ellipse([
            (moon_x-radius, moon_y-radius),
            (moon_x+radius, moon_y+radius)
        ], fill=255, outline=0, width=2)
        
    else:
        # Day sky (white with slight gradient)
        draw.rectangle([(0, 0), (WIDTH, SKY_HEIGHT)], fill=255)
        
        # Draw sun with rays
        sun_x, sun_y = WIDTH//2, SKY_HEIGHT//3
        radius = 60
        
        # Draw the sun as a black circle for contrast
        draw.ellipse([
            (sun_x-radius, sun_y-radius),
            (sun_x+radius, sun_y+radius)
        ], fill=0)
        
        # Add sun rays
        ray_length = radius + 30
        for i in range(8):
            angle = i * np.pi / 4
            start_x = sun_x + radius * np.cos(angle)
            start_y = sun_y + radius * np.sin(angle)
            end_x = sun_x + ray_length * np.cos(angle)
            end_y = sun_y + ray_length * np.sin(angle)
            
            draw.line([(start_x, start_y), (end_x, end_y)], fill=0, width=3)
    
    # Add horizon line
    draw.line([(0, SKY_HEIGHT), (WIDTH, SKY_HEIGHT)], fill=0, width=2)
    
    # Add day/night label
    font = load_font(24)
    time_str = "NIGHT" if is_night else "DAY"
    current_time = datetime.datetime.now().strftime("%H:%M")
    label = f"{time_str} - {current_time}"
    
    # Create text box in upper right corner
    text_width = 200
    text_height = 40
    text_x = WIDTH - text_width - 20
    text_y = 20
    
    # Draw label background (inverse of sky color)
    bg_color = 255 if is_night else 0
    fg_color = 0 if is_night else 255
    draw.rectangle([
        (text_x, text_y),
        (text_x + text_width, text_y + text_height)
    ], fill=bg_color, outline=fg_color, width=2)
    
    # Draw text
    draw.text(
        (text_x + 10, text_y + 5),
        label,
        fill=fg_color,
        font=font
    )