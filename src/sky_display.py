#!/usr/bin/env python3
import matplotlib.pyplot as plt
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

def draw_graph_axes(draw, tide_min, tide_max):
    """Draw the graph axes and labels"""
    # Calculate graph area dimensions
    graph_top = SKY_HEIGHT + GRAPH_MARGIN_TOP
    graph_bottom = HEIGHT - GRAPH_MARGIN_BOTTOM
    graph_left = GRAPH_MARGIN_LEFT
    graph_right = WIDTH - GRAPH_MARGIN_RIGHT
    graph_height = graph_bottom - graph_top
    
    # Draw axes
    draw.line([(graph_left, graph_top), (graph_left, graph_bottom)], fill=0, width=2)  # Y-axis
    draw.line([(graph_left, graph_bottom), (graph_right, graph_bottom)], fill=0, width=2)  # X-axis
    
    # Add height labels
    font = load_font(20)
    # Round to nearest 0.5m for better labels
    tide_min_rounded = np.floor(tide_min * 2) / 2
    tide_max_rounded = np.ceil(tide_max * 2) / 2
    tide_range = tide_max_rounded - tide_min_rounded
    
    # Need at least 0.5m range, default to 0-4m if tide data is problematic
    if tide_range < 0.5:
        tide_min_rounded = 0
        tide_max_rounded = 4
        tide_range = 4
    
    # Add vertical grid lines and labels
    num_intervals = int(tide_range * 2)  # Every 0.5m
    for i in range(num_intervals + 1):
        height = tide_min_rounded + (i * 0.5)
        y_pos = graph_bottom - ((height - tide_min_rounded) / tide_range) * graph_height
        
        # Grid line (dashed)
        for x in range(graph_left, graph_right, 10):
            draw.line([(x, y_pos), (x+5, y_pos)], fill=0, width=1)
        
        # Label
        height_label = f"{height:.1f}m"
        draw.text((graph_left - 70, y_pos - 10), height_label, fill=0, font=font)
        
        # Tick mark
        draw.line([(graph_left - 5, y_pos), (graph_left, y_pos)], fill=0, width=2)
    
    # Add time labels (every 3 hours)
    time_font = load_font(20)
    
    # Draw 24-hour time scale
    for hour in range(0, 25, 3):
        x_pos = graph_left + (hour / 24) * (graph_right - graph_left)
        
        # Draw tick mark
        draw.line([(x_pos, graph_bottom), (x_pos, graph_bottom + 5)], fill=0, width=2)
        
        # Label
        time_label = f"{hour:02d}:00"
        label_width = len(time_label) * 8  # Approximate width
        draw.text((x_pos - label_width/2, graph_bottom + 10), time_label, fill=0, font=time_font)
        
        # Vertical grid line (dashed)
        if hour > 0 and hour < 24:
            for y in range(graph_top, graph_bottom, 10):
                draw.line([(x_pos, y), (x_pos, y+5)], fill=0, width=1)
    
    return graph_top, graph_bottom, graph_left, graph_right, graph_height, tide_min_rounded, tide_max_rounded

def plot_tide_data(draw, tide_data, graph_params):
    """Plot the tide data as a curve with high/low points marked"""
    graph_top, graph_bottom, graph_left, graph_right, graph_height, tide_min, tide_max = graph_params
    graph_width = graph_right - graph_left
    
    # Extract times and heights
    times = np.array([point['hour'] + point['minute']/60 for point in tide_data])
    heights = np.array([point['height'] for point in tide_data])
    
    # Create more points for a smoother curve
    x_smooth = np.linspace(0, 24, 240)  # 240 points (10 per hour)
    
    # Normalize tide times to 0-24 range for proper interpolation
    times_normalized = times % 24
    
    # Sort the data by time for proper interpolation
    sorted_indices = np.argsort(times_normalized)
    times_sorted = times_normalized[sorted_indices]
    heights_sorted = heights[sorted_indices]
    
    # Use cubic spline interpolation for a smooth curve
    y_smooth = np.interp(x_smooth, times_sorted, heights_sorted)
    
    # Convert to pixel coordinates
    x_pixels = graph_left + (x_smooth / 24) * graph_width
    y_pixels = graph_bottom - ((y_smooth - tide_min) / (tide_max - tide_min)) * graph_height
    
    # Draw the tide curve
    points = list(zip(x_pixels, y_pixels))
    draw.line(points, fill=0, width=3)
    
    # Fill area under the curve
    fill_points = points + [(graph_right, graph_bottom), (graph_left, graph_bottom)]
    draw.polygon(fill_points, fill=0, outline=0)
    
    # Create a cross-hatch pattern by drawing horizontal lines (every 20 pixels)
    for y in range(int(graph_bottom), int(min(y_pixels)) - 20, -20):
        draw.line([(graph_left, y), (graph_right, y)], fill=255, width=1)
    
    # Mark high and low tide points
    font = load_font(20)
    
    for i, point in enumerate(tide_data):
        time_val = point['hour'] + point['minute']/60
        x_pos = graph_left + (time_val / 24) * graph_width
        y_pos = graph_bottom - ((point['height'] - tide_min) / (tide_max - tide_min)) * graph_height
        
        # Draw circle around point
        radius = 8
        draw.ellipse([
            (x_pos-radius, y_pos-radius),
            (x_pos+radius, y_pos+radius)
        ], fill=255, outline=0, width=2)
        
        # Label with time and height
        time_str = f"{point['hour']:02d}:{point['minute']:02d}"
        height_str = f"{point['height']:.1f}m"
        
        # Position label above or below point based on position
        if point.get('type') == 'H':  # High tide
            label_y = y_pos - 40
            label = f"High: {time_str}, {height_str}"
        elif point.get('type') == 'L':  # Low tide
            label_y = y_pos + 25
            label = f"Low: {time_str}, {height_str}"
        else:
            label_y = y_pos - 40 if i % 2 == 0 else y_pos + 25
            label = f"{time_str}, {height_str}"
        
        # Draw label with white background for readability
        text_width = len(label) * 10
        text_height = 25
        draw.rectangle([
            (x_pos - text_width/2, label_y),
            (x_pos + text_width/2, label_y + text_height)
        ], fill=255)
        
        draw.text((x_pos - text_width/2 + 5, label_y), label, fill=0, font=font)

def add_footer(draw):
    """Add footer text with generation time"""
    font = load_font(20)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    footer_text = f"TIDEMARK | Generated: {current_time}"
    draw.text((WIDTH/2 - 200, HEIGHT - 40), footer_text, fill=0, font=font)

def generate_tide_chart(tide_data, output_path, is_night=None):
    """
    Generate a complete tide chart image
    
    Parameters:
    - tide_data: List of dictionaries, each with 'hour', 'minute', 'height', and optional 'type' ('H' or 'L')
    - output_path: Path to save the BMP file
    - is_night: Force night/day mode, or None to determine based on current time
    """
    # Create blank white image (8-bit grayscale)
    img = Image.new('L', (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)
    
    # Determine day/night if not specified
    if is_night is None:
        current_hour = datetime.datetime.now().hour
        is_night = current_hour < 6 or current_hour >= 18
    
    # Draw sky with sun/moon
    draw_sky(draw, is_night)
    
    # Find tide min/max for proper scaling
    heights = [point['height'] for point in tide_data]
    tide_min = min(heights) if heights else 0
    tide_max = max(heights) if heights else 4
    
    # Add a small buffer
    tide_min = max(0, tide_min - 0.2)
    tide_max = tide_max + 0.2
    
    # Draw graph axes and get graph parameters
    graph_params = draw_graph_axes(draw, tide_min, tide_max)
    
    # Plot tide data
    plot_tide_data(draw, tide_data, graph_params)
    
    # Add footer
    add_footer(draw)
    
    # Save as BMP with 8-bit grayscale
    img.save(output_path, "BMP")
    print(f"Tide chart saved to {output_path}")
    return img

def generate_sample_chart():
    """Generate a sample chart with fake tide data"""
    # Sample tide data for demo
    sample_data = [
        {'hour': 0, 'minute': 30, 'height': 0.5, 'type': 'L'},
        {'hour': 6, 'minute': 45, 'height': 3.2, 'type': 'H'},
        {'hour': 12, 'minute': 50, 'height': 0.6, 'type': 'L'},
        {'hour': 19, 'minute': 10, 'height': 3.0, 'type': 'H'},
    ]
    
    # Generate a day and night version
    generate_tide_chart(sample_data, "tide_chart_day.bmp", is_night=False)
    generate_tide_chart(sample_data, "tide_chart_night.bmp", is_night=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate tide chart images for e-ink display')
    parser.add_argument('--sample', action='store_true', help='Generate sample charts with test data')
    parser.add_argument('--night', action='store_true', help='Force night mode')
    parser.add_argument('--day', action='store_true', help='Force day mode')
    parser.add_argument('--output', default='tide_chart.bmp', help='Output file path')
    
    args = parser.parse_args()
    
    if args.sample:
        generate_sample_chart()
    else:
        # TODO: Implement real tide data fetching
        # For now, just use sample data
        sample_data = [
            {'hour': 0, 'minute': 30, 'height': 0.5, 'type': 'L'},
            {'hour': 6, 'minute': 45, 'height': 3.2, 'type': 'H'},
            {'hour': 12, 'minute': 50, 'height': 0.6, 'type': 'L'},
            {'hour': 19, 'minute': 10, 'height': 3.0, 'type': 'H'},
        ]
        
        is_night = None
        if args.night:
            is_night = True
        elif args.day:
            is_night = False
        
        generate_tide_chart(sample_data, args.output, is_night=is_night)