#!/usr/bin/env python3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

from render.sky import load_font, SKY_HEIGHT, GRAPH_MARGIN_LEFT, GRAPH_MARGIN_RIGHT, GRAPH_MARGIN_BOTTOM, GRAPH_MARGIN_TOP

def draw_graph_axes(draw, width, height, tide_min, tide_max):
    """Draw the graph axes and labels"""
    # Calculate graph area dimensions
    graph_top = SKY_HEIGHT + GRAPH_MARGIN_TOP
    graph_bottom = height - GRAPH_MARGIN_BOTTOM
    graph_left = GRAPH_MARGIN_LEFT
    graph_right = width - GRAPH_MARGIN_RIGHT
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

def plot_tide_data(draw, width, height, tide_data, graph_params):
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