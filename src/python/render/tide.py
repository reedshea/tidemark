#!/usr/bin/env python3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import datetime

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

def apply_wave_background(img, draw, curve_points, graph_bottom, graph_left, graph_right):
    """Apply wave background image below the tide curve"""
    # Load wave background image
    wave_bg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'wave-background.png')
    if not os.path.exists(wave_bg_path):
        return
    
    wave_bg = Image.open(wave_bg_path)
    wave_width, wave_height = wave_bg.size
    
    # Calculate horizontal offset based on time (for scrolling effect)
    # Scroll through the entire width over 24 hours
    current_time = datetime.datetime.now()
    minutes_since_midnight = current_time.hour * 60 + current_time.minute
    # Complete one full scroll every 24 hours
    scroll_offset = int((minutes_since_midnight / (24 * 60)) * wave_width)
    
    # Create a mask for the area below the tide curve
    mask = Image.new('L', (img.width, img.height), 0)
    mask_draw = ImageDraw.Draw(mask)
    
    # Build polygon points for the area below the curve
    polygon_points = [(graph_left, graph_bottom)]
    polygon_points.extend(curve_points)
    polygon_points.append((graph_right, graph_bottom))
    
    # Fill the area below the curve in the mask
    mask_draw.polygon(polygon_points, fill=255)
    
    # Create a temporary image to composite the wave background
    temp_img = Image.new('L', (img.width, img.height), 255)
    
    # Tile the wave background horizontally, starting from the scroll offset
    graph_width = graph_right - graph_left
    x_start = graph_left
    
    while x_start < graph_right:
        # Calculate how much of the wave image to use
        src_x = (scroll_offset + (x_start - graph_left)) % wave_width
        remaining_width = min(wave_width - src_x, graph_right - x_start)
        
        # Scale the wave height to fit between tide curve and graph bottom
        # Find the average height of the tide curve in this section
        curve_x_start = x_start - graph_left
        curve_x_end = min(curve_x_start + remaining_width, len(curve_points) - 1)
        
        # Get the y-coordinate range for this section
        section_curve_points = [p for p in curve_points if x_start <= p[0] < x_start + remaining_width]
        if section_curve_points:
            min_y = min(p[1] for p in section_curve_points)
            available_height = graph_bottom - min_y
            
            # Scale wave to fit in available height
            if available_height > 0:
                scale_factor = available_height / wave_height
                scaled_height = int(wave_height * scale_factor)
                
                # Crop and scale the wave section
                wave_section = wave_bg.crop((src_x, 0, src_x + remaining_width, wave_height))
                # Use LANCZOS constant directly for compatibility with older Pillow versions
                wave_section = wave_section.resize((remaining_width, scaled_height), Image.LANCZOS)
                
                # Convert to grayscale
                wave_section = wave_section.convert('L')
                
                # Paste the wave section
                temp_img.paste(wave_section, (x_start, graph_bottom - scaled_height))
        
        x_start += remaining_width
    
    # Apply the mask to composite only below the tide curve
    img.paste(temp_img, (0, 0), mask)

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
    
    # Return curve points so they can be used for wave background
    return curve_points
    
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