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
from data.tide_api import get_tide_data, GREAT_HILL_CONSTITUENTS
from data.moon_data import get_moon_events
from data.sun_data import get_sun_events
from render.sky import WIDTH, HEIGHT, GRAPH_MARGIN_TOP, GRAPH_MARGIN_BOTTOM, GRAPH_MARGIN_LEFT, GRAPH_MARGIN_RIGHT
from render.tide import draw_graph_axes, plot_tide_data, apply_wave_background, draw_moon_arc, draw_sun_background
import numpy as np

def add_footer(draw, width, height):
    """Add footer text with generation time"""
    from render.sky import load_font
    font = load_font(20)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    footer_text = f"TIDEMARK | Generated: {current_time}"
    draw.text((width/2 - 200, height - 40), footer_text, fill=0, font=font)

def generate_tide_chart(tide_data, output_path, is_night=None, hours=24, start_time=None):
    """
    Generate a complete tide chart image
    
    Parameters:
    - tide_data: List of dictionaries, each with 'hour', 'minute', 'height', and optional 'type' ('H' or 'L')
    - output_path: Path to save the BMP file
    - is_night: Force night/day mode, or None to determine based on current time
    - hours: Number of hours to display (default: 24)
    - start_time: Starting datetime for the chart (default: midnight)
    """
    # Create blank image with night background (8-bit grayscale)
    img = Image.new('L', (WIDTH, HEIGHT), 225)  # Start with 40% grey (night)
    draw = ImageDraw.Draw(img)
    
    # Find tide min/max for proper scaling
    heights = [point['height'] for point in tide_data]
    tide_min = min(heights) if heights else 0
    tide_max = max(heights) if heights else 4
    
    # Add a small buffer
    # tide_min = max(0, tide_min - 0.2)
    # tide_max = tide_max + 0.2
    
    # Get mean tide level from constituents
    mean_tide_level = GREAT_HILL_CONSTITUENTS['mean_tide_level']
    
    # Calculate graph parameters first (we'll draw axes later)
    graph_top = GRAPH_MARGIN_TOP
    graph_bottom = HEIGHT - GRAPH_MARGIN_BOTTOM
    graph_left = GRAPH_MARGIN_LEFT
    graph_right = WIDTH - GRAPH_MARGIN_RIGHT
    graph_height = graph_bottom - graph_top
    
    # Round tide min/max for better labels
    tide_min_rounded = np.floor(tide_min * 2) / 2
    tide_max_rounded = np.ceil(tide_max * 2) / 2
    if tide_max_rounded - tide_min_rounded < 0.5:
        tide_min_rounded = 0
        tide_max_rounded = 4
    
    graph_params = (graph_top, graph_bottom, graph_left, graph_right, graph_height, tide_min_rounded, tide_max_rounded)
    
    # Get sun data and draw sun background first (bottom layer)
    sun_data = get_sun_events()
    draw_sun_background(img, draw, sun_data, graph_params, mean_tide_level, hours, start_time)
    
    # Get moon data for today
    moon_data = get_moon_events()
    
    # Draw moon arc on top of sun background
    draw_moon_arc(draw, moon_data, graph_params, mean_tide_level, hours, start_time)
    
    # Plot tide data and get curve points
    curve_points = plot_tide_data(draw, WIDTH, HEIGHT, tide_data, graph_params, hours)
    
    # Apply wave background below tide curve
    if curve_points:
        apply_wave_background(img, draw, curve_points, graph_params[1], graph_params[2], graph_params[3], hours, start_time)
        
        # Redraw the tide curve on top of the wave background
        draw.line(curve_points, fill=0, width=3)
        
        # Re-mark high and low tide points
        from render.sky import load_font
        font = load_font(20)
        
        for i, point in enumerate(tide_data):
            # Use hours_since_start if available
            if 'hours_since_start' in point:
                time_val = point['hours_since_start']
            else:
                time_val = point['hour'] + point['minute']/60
            x_pos = graph_params[2] + (time_val / hours) * (graph_params[3] - graph_params[2])
            y_pos = graph_params[1] - ((point['height'] - graph_params[5]) / (graph_params[6] - graph_params[5])) * graph_params[4]
            
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
    
    # Draw graph axes and labels on top of everything
    draw_graph_axes(draw, WIDTH, HEIGHT, tide_min, tide_max, hours, start_time)
    
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
    # Get sample tide data for 36 hours starting from current time
    now = datetime.datetime.now()
    minutes = now.minute
    rounded_minutes = (minutes // 5) * 5
    start_time = now.replace(minute=rounded_minutes, second=0, microsecond=0)
    
    sample_data = get_tide_data(hours=36)
    
    # Generate a day and night version
    generate_tide_chart(sample_data, "/tmp/tide_chart_day.bmp", is_night=False, hours=36, start_time=start_time)
    generate_tide_chart(sample_data, "/tmp/tide_chart_night.bmp", is_night=True, hours=36, start_time=start_time)
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
        # Get actual tide data for 36 hours starting from current time
        now = datetime.datetime.now()
        minutes = now.minute
        rounded_minutes = (minutes // 5) * 5
        start_time = now.replace(minute=rounded_minutes, second=0, microsecond=0)
        
        tide_data = get_tide_data(hours=36)
        
        is_night = None
        if args.night:
            is_night = True
        elif args.day:
            is_night = False
        
        generate_tide_chart(tide_data, args.output, is_night=is_night, hours=36, start_time=start_time)