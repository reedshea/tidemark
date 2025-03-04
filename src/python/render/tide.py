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

def generate_sinusoid_curve(high_low_points, graph_left, graph_right, graph_bottom, graph_height, tide_min, tide_max):
    """
    Generate a smooth sine-like curve that passes exactly through high and low tide points.
    Uses cubic spline interpolation to create a natural tide curve.
    """
    # Sort points by time
    sorted_points = sorted(high_low_points, key=lambda p: p[0])
    
    # Make sure points wrap around for 24-hour cycle
    # If first point is not at time=0, add a wrapping point from the end
    if sorted_points[0][0] > 0:
        # Find the last point before 24:00
        last_point = max([p for p in sorted_points if p[0] < 24], key=lambda p: p[0])
        # Calculate time difference to wrap around
        time_diff = 24 - last_point[0]
        # Add a copy of the first point, but with time shifted to before 0
        sorted_points.insert(0, (sorted_points[0][0] - time_diff, sorted_points[0][1]))
        
    # Similarly, if the last point is not at time=24, add wrapping from the beginning
    if sorted_points[-1][0] < 24:
        # Find the first point after 0:00
        first_point = min([p for p in sorted_points if p[0] > 0], key=lambda p: p[0])
        # Calculate time difference to wrap around
        time_diff = first_point[0]
        # Add a copy of the last point, but with time shifted to after 24
        sorted_points.append((sorted_points[-1][0] + time_diff, sorted_points[-1][1]))
    
    # Generate enough points for a smooth curve
    num_points = 240  # 10 points per hour
    curve_points = []
    
    # Get the x range of the graph
    x_range = graph_right - graph_left
    
    # Prepare x and y arrays for interpolation
    times = [p[0] for p in sorted_points]
    heights = [p[1] for p in sorted_points]
    
    # Create the smooth curve
    for i in range(num_points + 1):
        # Calculate current time value (0-24 hours)
        time_of_day = (i / num_points) * 24
        
        # Find the surrounding data points
        if time_of_day <= times[0]:
            # If before the first point, use linear interpolation
            idx_next = 0
            while idx_next < len(times) and time_of_day > times[idx_next]:
                idx_next += 1
            idx_prev = idx_next - 1
            
            # Linear interpolation for height
            if idx_prev >= 0:
                t_ratio = (time_of_day - times[idx_prev]) / (times[idx_next] - times[idx_prev])
                height = heights[idx_prev] + t_ratio * (heights[idx_next] - heights[idx_prev])
            else:
                height = heights[idx_next]
        elif time_of_day >= times[-1]:
            # If after the last point, use linear interpolation
            idx_prev = len(times) - 1
            while idx_prev >= 0 and time_of_day < times[idx_prev]:
                idx_prev -= 1
            idx_next = idx_prev + 1
            
            # Linear interpolation for height
            if idx_next < len(times):
                t_ratio = (time_of_day - times[idx_prev]) / (times[idx_next] - times[idx_prev])
                height = heights[idx_prev] + t_ratio * (heights[idx_next] - heights[idx_prev])
            else:
                height = heights[idx_prev]
        else:
            # Find surrounding points for interpolation
            idx_next = 0
            while idx_next < len(times) and time_of_day > times[idx_next]:
                idx_next += 1
            idx_prev = idx_next - 1
            
            # Get 4 points for cubic interpolation (2 before, 2 after if possible)
            idx_p0 = max(0, idx_prev - 1)
            idx_p1 = idx_prev
            idx_p2 = idx_next
            idx_p3 = min(len(times) - 1, idx_next + 1)
            
            # Normalize time for interpolation (0-1 between the surrounding points)
            t = (time_of_day - times[idx_prev]) / (times[idx_next] - times[idx_prev])
            
            # Cubic interpolation (cardinal spline)
            t2 = t * t
            t3 = t2 * t
            
            # Catmull-Rom spline
            height = (
                0.5 * (
                    (2 * heights[idx_p1]) +
                    (-heights[idx_p0] + heights[idx_p2]) * t +
                    (2 * heights[idx_p0] - 5 * heights[idx_p1] + 4 * heights[idx_p2] - heights[idx_p3]) * t2 +
                    (-heights[idx_p0] + 3 * heights[idx_p1] - 3 * heights[idx_p2] + heights[idx_p3]) * t3
                )
            )
        
        # Calculate x coordinate
        x = graph_left + (time_of_day / 24) * x_range
        
        # Convert height to pixel coordinates
        y_pixel = graph_bottom - ((height - tide_min) / (tide_max - tide_min)) * graph_height
        
        # Add the point to our curve
        curve_points.append((int(x), int(y_pixel)))
    
    return curve_points

def plot_tide_data(draw, width, height, tide_data, graph_params):
    """Plot the tide data as a smooth bezier curve with high/low points marked"""
    graph_top, graph_bottom, graph_left, graph_right, graph_height, tide_min, tide_max = graph_params
    graph_width = graph_right - graph_left
    
    # First, filter and organize tide data points
    high_tide_points = []
    low_tide_points = []
    
    # If we have actual tide data, use it to separate high/low points
    if tide_data:
        for point in tide_data:
            time_val = point['hour'] + point['minute']/60
            if 0 <= time_val <= 24:  # Only include points in the 24-hour range
                if point.get('type') == 'H':
                    high_tide_points.append((time_val, point['height']))
                elif point.get('type') == 'L':
                    low_tide_points.append((time_val, point['height']))
    
    # If we don't have enough high or low tide points, generate synthetic ones
    if len(high_tide_points) < 2:
        high_tide_points = [(0, 3.0), (12, 3.0), (24, 3.0)]
    
    if len(low_tide_points) < 2:
        low_tide_points = [(6, 0.5), (18, 0.5)]
    
    # Combine and sort all points by time
    all_points = high_tide_points + low_tide_points
    all_points.sort(key=lambda p: p[0])
    
    # Convert to pixel coordinates
    pixel_points = []
    for t, h in all_points:
        x = graph_left + (t / 24) * graph_width
        y = graph_bottom - ((h - tide_min) / (tide_max - tide_min)) * graph_height
        pixel_points.append((x, y))
    
    # Generate smooth sinusoidal curve
    curve_points = generate_sinusoid_curve(all_points, 
                                        graph_left, graph_right, 
                                        graph_bottom, graph_height,
                                        tide_min, tide_max)
    
    # Draw the tide curve with a simple smooth line, no fill or texture
    if curve_points:
        # Draw the curve with a clean line
        draw.line(curve_points, fill=0, width=3)
    
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