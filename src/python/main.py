#!/usr/bin/env python3
"""
Tidemark - Main Python entry point for generating tide charts

This script generates bitmap images for display on an e-ink screen.
It combines tide data with visualizations of sky, time, and weather.
"""

import argparse
import datetime
import os
from PIL import Image, ImageDraw, ImageFont

# Import local modules
from data.tide_api import get_tide_data
from render.sky import draw_sky, WIDTH, HEIGHT
from render.tide import draw_graph_axes, plot_tide_data

def add_footer(draw, width, height):
    """Add footer text with generation time"""
    from render.sky import load_font
    font = load_font(20)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    footer_text = f"TIDEMARK | Generated: {current_time}"
    draw.text((width/2 - 200, height - 40), footer_text, fill=0, font=font)

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
    graph_params = draw_graph_axes(draw, WIDTH, HEIGHT, tide_min, tide_max)
    
    # Plot tide data
    plot_tide_data(draw, WIDTH, HEIGHT, tide_data, graph_params)
    
    # Add footer
    add_footer(draw, WIDTH, HEIGHT)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save as BMP with 8-bit grayscale
    img.save(output_path, "BMP")
    print(f"Tide chart saved to {output_path}")
    return img

def generate_sample_chart():
    """Generate a sample chart with sample tide data"""
    # Get sample tide data
    sample_data = get_tide_data()
    
    # Generate a day and night version
    generate_tide_chart(sample_data, "/tmp/tide_chart_day.bmp", is_night=False)
    generate_tide_chart(sample_data, "/tmp/tide_chart_night.bmp", is_night=True)
    print("Sample charts generated")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate tide chart images for e-ink display')
    parser.add_argument('--sample', action='store_true', help='Generate sample charts with test data')
    parser.add_argument('--night', action='store_true', help='Force night mode')
    parser.add_argument('--day', action='store_true', help='Force day mode')
    parser.add_argument('--output', default='/tmp/tide_chart.bmp', help='Output file path')
    
    args = parser.parse_args()
    
    if args.sample:
        generate_sample_chart()
    else:
        # Get actual tide data
        tide_data = get_tide_data()
        
        is_night = None
        if args.night:
            is_night = True
        elif args.day:
            is_night = False
        
        generate_tide_chart(tide_data, args.output, is_night=is_night)