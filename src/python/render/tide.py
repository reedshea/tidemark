#!/usr/bin/env python3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import datetime
import math

from render.sky import load_font, GRAPH_MARGIN_LEFT, GRAPH_MARGIN_RIGHT, GRAPH_MARGIN_BOTTOM, GRAPH_MARGIN_TOP

def draw_graph_axes(draw, width, height, tide_min, tide_max, hours=24, start_time=None):
    """Draw the graph axes and labels
    
    Parameters:
    - draw: PIL ImageDraw object
    - width, height: Image dimensions
    - tide_min, tide_max: Min/max tide heights for scaling
    - hours: Number of hours to display (default: 24)
    - start_time: Starting datetime for x-axis (default: midnight)
    """
    # Calculate graph area dimensions
    graph_top = GRAPH_MARGIN_TOP
    graph_bottom = height - GRAPH_MARGIN_BOTTOM
    graph_left = GRAPH_MARGIN_LEFT
    graph_right = width - GRAPH_MARGIN_RIGHT
    graph_height = graph_bottom - graph_top
    
    # Draw axes
    draw.line([(graph_left, graph_top), (graph_left, graph_bottom)], fill=0, width=2)  # Y-axis
    draw.line([(graph_left, graph_bottom), (graph_right, graph_bottom)], fill=0, width=2)  # X-axis
    
    # Add height labels with white background
    font = load_font(28)  # Larger font
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
        
        # Removed grid lines
        
        # Label with white background
        height_label = f"{height:.1f}m"
        label_width = 80
        label_height = 30
        label_x = graph_left - 90
        label_y = y_pos - 15
        
        # Draw white background box
        draw.rectangle([
            (label_x, label_y),
            (label_x + label_width, label_y + label_height)
        ], fill=255, outline=0)
        
        # Draw text
        draw.text((label_x + 10, label_y + 3), height_label, fill=0, font=font)
        
        # Tick mark
        draw.line([(graph_left - 5, y_pos), (graph_left, y_pos)], fill=0, width=2)
    
    # Draw horizontal line at zero tide level
    if tide_min_rounded <= 0 <= tide_max_rounded:
        zero_y = graph_bottom - ((0 - tide_min_rounded) / tide_range) * graph_height
        draw.line([(graph_left, zero_y), (graph_right, zero_y)], fill=0, width=2)
    
    # Add time labels (every 3 hours)
    time_font = load_font(20)
    
    # If no start_time provided, use midnight
    if start_time is None:
        start_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Draw time scale for specified hours
    # Calculate interval - for 36 hours, use 4-hour intervals, for 24 hours use 3-hour intervals
    interval = 4 if hours > 24 else 3
    
    for hour_offset in range(0, hours + 1, interval):
        x_pos = graph_left + (hour_offset / hours) * (graph_right - graph_left)
        
        # Draw tick mark
        draw.line([(x_pos, graph_bottom), (x_pos, graph_bottom + 5)], fill=0, width=2)
        
        # Calculate actual time
        label_time = start_time + datetime.timedelta(hours=hour_offset)
        
        # Format label - show date if it's a different day
        if label_time.date() != start_time.date():
            time_label = label_time.strftime("%m/%d %H:%M")
        else:
            time_label = label_time.strftime("%H:%M")
        
        label_width = len(time_label) * 8  # Approximate width
        draw.text((x_pos - label_width/2, graph_bottom + 10), time_label, fill=0, font=time_font)
        
        # Removed vertical grid lines
    
    return graph_top, graph_bottom, graph_left, graph_right, graph_height, tide_min_rounded, tide_max_rounded

def generate_sinusoid_curve(high_low_points, graph_left, graph_right, graph_bottom, graph_height, tide_min, tide_max, hours=24):
    """
    Generate a smooth sine-like curve that passes exactly through high and low tide points.
    Uses cubic spline interpolation to create a natural tide curve.
    
    Parameters:
    - high_low_points: List of (time_in_hours, height) tuples
    - graph_left, graph_right: X-axis boundaries
    - graph_bottom, graph_height: Y-axis parameters
    - tide_min, tide_max: Height range for scaling
    - hours: Total hours to display
    """
    # Sort points by time
    sorted_points = sorted(high_low_points, key=lambda p: p[0])
    
    # Ensure we have proper boundary points for smooth curves
    # The tide API should now provide points at 0:00 and 24:00
    
    # Generate enough points for a smooth curve
    num_points = int(hours * 10)  # 10 points per hour
    curve_points = []
    
    # Get the x range of the graph
    x_range = graph_right - graph_left
    
    # Prepare x and y arrays for interpolation
    times = [p[0] for p in sorted_points]
    heights = [p[1] for p in sorted_points]
    
    # Generate curve points for the visible hour range
    for i in range(num_points + 1):
        # Calculate current time value (0 to hours)
        time_of_day = (i / num_points) * hours
        
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
        x = graph_left + (time_of_day / hours) * x_range
        
        # Convert height to pixel coordinates
        y_pixel = graph_bottom - ((height - tide_min) / (tide_max - tide_min)) * graph_height
        
        # Add the point to our curve
        curve_points.append((int(x), int(y_pixel)))
    
    return curve_points

def apply_wave_background(img, draw, curve_points, graph_bottom, graph_left, graph_right, hours=24, start_time=None):
    """Apply wave background image below the tide curve
    
    Parameters:
    - img: PIL Image object
    - draw: PIL ImageDraw object  
    - curve_points: List of (x, y) points defining the tide curve
    - graph_bottom: Bottom y-coordinate of graph
    - graph_left, graph_right: Left and right x-coordinates of graph
    - hours: Number of hours displayed
    - start_time: Starting datetime for the display
    """
    # Load wave background image
    wave_bg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'wave-background.png')
    if not os.path.exists(wave_bg_path):
        return
    
    wave_bg = Image.open(wave_bg_path)
    wave_width, wave_height = wave_bg.size
    
    # Calculate horizontal offset based on time (for scrolling effect)
    if start_time:
        current_time = start_time
    else:
        current_time = datetime.datetime.now()
    
    # Scroll based on time of day for consistent wave position
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

def plot_tide_data(draw, width, height, tide_data, graph_params, hours=24):
    """Plot the tide data as a smooth bezier curve with high/low points marked
    
    Parameters:
    - draw: PIL ImageDraw object  
    - width, height: Image dimensions
    - tide_data: List of tide data points
    - graph_params: Tuple of graph parameters
    - hours: Number of hours to display
    """
    graph_top, graph_bottom, graph_left, graph_right, graph_height, tide_min, tide_max = graph_params
    graph_width = graph_right - graph_left
    
    
    # First, filter and organize tide data points
    high_tide_points = []
    low_tide_points = []
    boundary_points = []
    
    # If we have actual tide data, use it to separate high/low points
    if tide_data:
        for point in tide_data:
            # Use hours_since_start if available, otherwise calculate from hour/minute
            if 'hours_since_start' in point:
                time_val = point['hours_since_start']
            else:
                time_val = point['hour'] + point['minute']/60
            
            if 0 <= time_val <= hours:  # Only include points in the display range
                if point.get('type') == 'H':
                    high_tide_points.append((time_val, point['height']))
                elif point.get('type') == 'L':
                    low_tide_points.append((time_val, point['height']))
                elif point.get('type') == 'B':
                    boundary_points.append((time_val, point['height']))
    
    # If we don't have enough high or low tide points, generate synthetic ones
    if len(high_tide_points) < 2:
        # Create synthetic high tide points distributed across the time range
        high_tide_points = [(i * hours / 2, 3.0) for i in range(3)]
    
    if len(low_tide_points) < 2:
        # Create synthetic low tide points between high tides
        low_tide_points = [(hours / 4, 0.5), (3 * hours / 4, 0.5)]
    
    # Combine and sort all points by time
    # Include boundary points to ensure smooth curves at edges
    all_points = high_tide_points + low_tide_points + boundary_points
    all_points.sort(key=lambda p: p[0])
    
    # Convert to pixel coordinates
    pixel_points = []
    for t, h in all_points:
        x = graph_left + (t / hours) * graph_width
        y = graph_bottom - ((h - tide_min) / (tide_max - tide_min)) * graph_height
        pixel_points.append((x, y))
    
    # Generate smooth sinusoidal curve
    curve_points = generate_sinusoid_curve(all_points, 
                                        graph_left, graph_right, 
                                        graph_bottom, graph_height,
                                        tide_min, tide_max, hours)
    
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

def draw_sun_background(img, draw, sun_data, graph_params, mean_tide_level, hours=24, start_time=None):
    """Draw sun arc with gradient background representing day/night
    
    Parameters:
    - img: PIL Image object
    - draw: PIL ImageDraw object
    - sun_data: Dictionary with sun event times
    - graph_params: Tuple of graph parameters
    - mean_tide_level: Mean tide level for horizon
    - hours: Number of hours displayed
    - start_time: Starting datetime for the display
    """
    graph_top, graph_bottom, graph_left, graph_right, graph_height, tide_min, tide_max = graph_params
    graph_width = graph_right - graph_left
    
    if not sun_data or not start_time:
        return
    
    # Get sun event times
    nautical_dawn_time = sun_data['nautical_dawn']['hour'] + sun_data['nautical_dawn']['minute'] / 60.0
    sunrise_time = sun_data['sunrise']['hour'] + sun_data['sunrise']['minute'] / 60.0
    sunset_time = sun_data['sunset']['hour'] + sun_data['sunset']['minute'] / 60.0
    nautical_dusk_time = sun_data['nautical_dusk']['hour'] + sun_data['nautical_dusk']['minute'] / 60.0
    
    # Convert to hours since start_time
    start_hour = start_time.hour + start_time.minute / 60.0
    
    # Calculate x positions - handle events that may be on different days
    def time_to_x(event_hour):
        # Calculate hours since start
        hours_since_start = event_hour - start_hour
        if hours_since_start < 0:
            hours_since_start += 24  # Next day
        if hours_since_start > hours:
            return None  # Outside display range
        return graph_left + (hours_since_start / hours) * graph_width
    
    sunrise_x = time_to_x(sunrise_time)
    sunset_x = time_to_x(sunset_time)
    dawn_x = time_to_x(nautical_dawn_time)
    dusk_x = time_to_x(nautical_dusk_time)
    
    # Calculate y position for the horizon (mean tide level)
    horizon_y = graph_bottom - ((mean_tide_level - tide_min) / (tide_max - tide_min)) * graph_height
    
    # Create a gradient mask for the sun's glow
    # We'll draw multiple ellipses with decreasing opacity
    sun_arc_center_x = (sunrise_x + sunset_x) / 2
    sun_arc_width = sunset_x - sunrise_x
    sun_arc_radius = sun_arc_width / 2
    
    # Height should be similar to moon arc - 80% of available space
    available_height = horizon_y - graph_top
    sun_arc_height = available_height * 0.8
    
    # Draw background with distinct zones (no gradient)
    # Night is 40% grey (60% brightness = 153)
    night_color = 224  # 
    twilight_color = 240  # 
    day_color = 255  # White
    draw.rectangle([(0, 0), (img.width, img.height)], fill=night_color)
    
    # Simple approach: Draw circular gradient at noon position
    # Calculate noon position (middle of sunrise and sunset)
    if sunrise_x and sunset_x:
        noon_x = (sunrise_x + sunset_x) / 2
    else:
        # If sunrise or sunset is not visible, estimate based on available data
        noon_x = graph_left + graph_width / 2
    noon_y = img.height * 0.6  # Center at 40% from bottom (60% from top)
    
    # Calculate the radius needed for sunrise/sunset to intersect at horizon
    # Distance from noon to sunrise/sunset horizontally
    if sunrise_x and sunset_x:
        sun_arc_half_width = abs(sunset_x - sunrise_x) / 2
    else:
        sun_arc_half_width = graph_width / 3  # Default estimate
    
    # Distance from center of display to horizon vertically
    center_to_horizon = abs(noon_y - horizon_y)
    # Calculate radius using Pythagorean theorem
    sun_radius = math.sqrt(sun_arc_half_width**2 + center_to_horizon**2)
    
    # Calculate nautical twilight radius
    # Distance from noon to nautical dawn/dusk
    if dawn_x and dusk_x:
        twilight_arc_half_width = abs(dusk_x - dawn_x) / 2
    else:
        twilight_arc_half_width = graph_width / 2  # Default estimate
    twilight_radius = math.sqrt(twilight_arc_half_width**2 + center_to_horizon**2)
    
    # Define transition widths (in pixels)
    sun_twilight_blend = 50  # Blend width between sun and twilight
    twilight_night_blend = 80  # Blend width between twilight and night
    
    # Draw concentric semicircles with gradients at transitions
    num_layers = 60
    max_radius = twilight_radius + twilight_night_blend / 2
    
    for i in range(num_layers, 0, -1):
        radius = (i / num_layers) * max_radius
        
        # Determine color based on radius with smooth transitions
        if radius <= sun_radius - sun_twilight_blend / 2:
            # Core sun area
            color = day_color
        elif radius <= sun_radius + sun_twilight_blend / 2:
            # Sun to twilight transition
            t = (radius - (sun_radius - sun_twilight_blend / 2)) / sun_twilight_blend
            color = int(day_color - (day_color - twilight_color) * t)
        elif radius <= twilight_radius - twilight_night_blend / 2:
            # Core twilight area
            color = twilight_color
        elif radius <= twilight_radius + twilight_night_blend / 2:
            # Twilight to night transition
            t = (radius - (twilight_radius - twilight_night_blend / 2)) / twilight_night_blend
            color = int(twilight_color - (twilight_color - night_color) * t)
        else:
            # Night area
            color = night_color
        
        # Draw semicircle for this layer
        points = []
        for j in range(101):
            angle = math.pi * j / 100  # 0 to pi for semicircle
            x = noon_x + radius * math.cos(angle + math.pi)
            y = noon_y + radius * math.sin(angle + math.pi)
            if y <= noon_y:
                points.append((x, y))
        
        if points:
            points.append((noon_x + radius, noon_y))
            points.append((noon_x - radius, noon_y))
            draw.polygon(points, fill=color)
    
    # Draw rectangles with linear gradients matching the radial transitions
    rect_left = noon_x - twilight_radius - twilight_night_blend / 2
    rect_right = noon_x + twilight_radius + twilight_night_blend / 2
    
    # Draw vertical strips for horizontal gradient
    num_strips = 200
    for i in range(num_strips):
        x_start = rect_left + (rect_right - rect_left) * i / num_strips
        x_end = rect_left + (rect_right - rect_left) * (i + 1) / num_strips
        
        # Calculate distance from center
        x_mid = (x_start + x_end) / 2
        distance_from_center = abs(x_mid - noon_x)
        
        # Determine color based on distance with smooth transitions
        if distance_from_center <= sun_radius - sun_twilight_blend / 2:
            # Core sun area
            color = day_color
        elif distance_from_center <= sun_radius + sun_twilight_blend / 2:
            # Sun to twilight transition
            t = (distance_from_center - (sun_radius - sun_twilight_blend / 2)) / sun_twilight_blend
            color = int(day_color - (day_color - twilight_color) * t)
        elif distance_from_center <= twilight_radius - twilight_night_blend / 2:
            # Core twilight area
            color = twilight_color
        elif distance_from_center <= twilight_radius + twilight_night_blend / 2:
            # Twilight to night transition
            t = (distance_from_center - (twilight_radius - twilight_night_blend / 2)) / twilight_night_blend
            color = int(twilight_color - (twilight_color - night_color) * t)
        else:
            # Night area
            color = night_color
        
        # Draw vertical strip
        draw.rectangle([
            (x_start, noon_y),
            (x_end, img.height)
        ], fill=color)

def draw_moon_arc(draw, moon_data, graph_params, mean_tide_level, hours=24, start_time=None):
    """Draw moon path arc from moonrise to moonset
    
    Parameters:
    - draw: PIL ImageDraw object
    - moon_data: Dictionary with moon event times
    - graph_params: Tuple of graph parameters
    - mean_tide_level: Mean tide level for horizon
    - hours: Number of hours displayed
    - start_time: Starting datetime for the display
    """
    graph_top, graph_bottom, graph_left, graph_right, graph_height, tide_min, tide_max = graph_params
    graph_width = graph_right - graph_left
    
    if not moon_data or not moon_data.get('moonrise') or not moon_data.get('moonset') or not start_time:
        return
    
    # Calculate x positions for moonrise and moonset
    moonrise_time = moon_data['moonrise']['hour'] + moon_data['moonrise']['minute'] / 60.0
    moonset_time = moon_data['moonset']['hour'] + moon_data['moonset']['minute'] / 60.0
    
    # Convert to hours since start_time
    start_hour = start_time.hour + start_time.minute / 60.0
    
    # Calculate hours since start for moonrise and moonset
    moonrise_hours = moonrise_time - start_hour
    if moonrise_hours < 0:
        moonrise_hours += 24
    
    moonset_hours = moonset_time - start_hour
    if moonset_hours < 0:
        moonset_hours += 24
    
    # Handle case where moonset is before moonrise in our time window
    if moonset_hours < moonrise_hours:
        # If moonset is early in our window, it's from previous day's rise
        if moonset_hours < 6:  # Within first 6 hours
            # Don't draw this arc as the moonrise was before our start time
            return
        # Otherwise moonset is after our window
        if moonrise_hours > hours:
            return  # Both events outside our window
    
    # Only draw if both events are within our display window
    if moonrise_hours > hours or moonset_hours > hours:
        return
    
    moonrise_x = graph_left + (moonrise_hours / hours) * graph_width
    moonset_x = graph_left + (moonset_hours / hours) * graph_width
    
    # Calculate y position for the horizon (mean tide level)
    horizon_y = graph_bottom - ((mean_tide_level - tide_min) / (tide_max - tide_min)) * graph_height
    
    # Arc parameters
    arc_width = moonset_x - moonrise_x
    arc_center_x = (moonrise_x + moonset_x) / 2
    
    # Height should be 80% of the available space above horizon
    available_height = horizon_y - graph_top
    arc_height = available_height * 0.8
    arc_radius = arc_width / 2
    
    # Draw dotted arc
    num_dots = 64
    for i in range(num_dots + 1):
        # Calculate angle from 0 to pi (semicircle)
        angle = math.pi * i / num_dots
        
        # Calculate position
        x = arc_center_x - arc_radius * math.cos(angle)
        y = horizon_y - arc_height * math.sin(angle)
        
        # Draw small circle for dotted effect
        # if i % 2 == 0:  # Draw every other dot
        draw.ellipse([(x-2, y-2), (x+2, y+2)], fill=0)
    
    # Draw moon phase at the top of the arc
    moon_x = arc_center_x
    moon_y = horizon_y - arc_height
    draw_moon_phase(draw, moon_x, moon_y, moon_data.get('phase', 0.5))

def draw_moon_phase(draw, x, y, phase):
    """Draw moon with current phase at specified position"""
    moon_radius = 40

    # Draw solid white moon to cover background/arc
    draw.ellipse([
        (x - moon_radius, y - moon_radius),
        (x + moon_radius, y + moon_radius)
    ], fill=255, outline=0, width=3)

    # Draw moon outline (black)
    draw.ellipse([
        (x - moon_radius, y - moon_radius),
        (x + moon_radius, y + moon_radius)
    ], outline=0, width=2)

    # Calculate illuminated portion
    # Phase: 0 = New, 0.25 = First Quarter, 0.5 = Full, 0.75 = Last Quarter

    dark_side_color = 64  # Dark side color (gray)

    if phase < 0.5:
        # Waxing (right side illuminated)
        # Draw the dark left side
        if phase < 0.25:
            # Crescent - dark side is convex
            curve_offset = moon_radius * math.cos(phase * 2 * math.pi)
            points = []
            for i in range(21):
                angle = -math.pi/2 + math.pi * i / 20
                y_offset = moon_radius * math.sin(angle)
                x_offset = curve_offset * math.cos(angle)
                points.append((x + x_offset, y + y_offset))
            # Complete the shape
            for i in range(20, -1, -1):
                angle = -math.pi/2 + math.pi * i / 20
                y_offset = moon_radius * math.sin(angle)
                x_offset = -moon_radius * math.cos(angle)
                points.append((x + x_offset, y + y_offset))
            draw.polygon(points, fill=dark_side_color)  # Gray for dark side
        else:
            # Gibbous - dark side is concave
            curve_offset = moon_radius * math.cos((0.5 - phase) * 2 * math.pi)
            points = []
            for i in range(21):
                angle = -math.pi/2 + math.pi * i / 20
                y_offset = moon_radius * math.sin(angle)
                x_offset = -curve_offset * math.cos(angle)
                points.append((x + x_offset, y + y_offset))
            # Complete the shape
            for i in range(20, -1, -1):
                angle = -math.pi/2 + math.pi * i / 20
                y_offset = moon_radius * math.sin(angle)
                x_offset = -moon_radius * math.cos(angle)
                points.append((x + x_offset, y + y_offset))
            draw.polygon(points, fill=dark_side_color)
    else:
        # Waning (left side illuminated)
        # Draw the dark right side
        if phase < 0.75:
            # Gibbous - dark side is concave
            curve_offset = moon_radius * math.cos((phase - 0.5) * 2 * math.pi)
            points = []
            for i in range(21):
                angle = -math.pi/2 + math.pi * i / 20
                y_offset = moon_radius * math.sin(angle)
                x_offset = curve_offset * math.cos(angle)
                points.append((x + x_offset, y + y_offset))
            # Complete the shape
            for i in range(20, -1, -1):
                angle = -math.pi/2 + math.pi * i / 20
                y_offset = moon_radius * math.sin(angle)
                x_offset = moon_radius * math.cos(angle)
                points.append((x + x_offset, y + y_offset))
            draw.polygon(points, fill=dark_side_color)
        else:
            # Crescent - dark side is convex
            curve_offset = moon_radius * math.cos((1 - phase) * 2 * math.pi)
            points = []
            for i in range(21):
                angle = -math.pi/2 + math.pi * i / 20
                y_offset = moon_radius * math.sin(angle)
                x_offset = -curve_offset * math.cos(angle)
                points.append((x + x_offset, y + y_offset))
            # Complete the shape
            for i in range(20, -1, -1):
                angle = -math.pi/2 + math.pi * i / 20
                y_offset = moon_radius * math.sin(angle)
                x_offset = moon_radius * math.cos(angle)
                points.append((x + x_offset, y + y_offset))
            draw.polygon(points, fill=dark_side_color)