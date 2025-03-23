import pygame
import numpy as np
from pygame.locals import *
import pandas as pd
import math
import json
import os
import time

class PyGameVisualizer:
    """
    Helper class for creating PyGame 3D visualizations of stars.
    """
    def __init__(self, stars_df):
        self.stars_df = stars_df
        self.width = 1024
        self.height = 768
        # Camera position (offset from center)
        self.camera_pos = [0, 0]
        self.zoom = 40  # pixels per lig
        # 3D rotation angles
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.rotation_z = 0.0
        # Star appearance configuration
        self.star_brightness = 1.0
        self.glow_factor = 1.8  # Increased glow factor for more prominen
        # UI state
        self.max_distance = 20.0  # Fixed at 20 light years
        self.show_star_names = False    # Star name labels toggle (default: off)
        self.show_galactic_plane = False  # Galactic plane visualization toggle (default: off)
        self.show_coordinate_grid = False  # Coordinate grid toggle (default: off)
        self.show_galactic_projections = False  # Toggle for showing star projections onto galactic plane
        self.show_multiple_star_inset = True  # Toggle for showing multiple star system inset (default: on)
        self.selected_star = None
        self.info_font = None
        self.paused = False

        # For distance display - store multiple measurements
        self.distance_lines = []  # List of distance measurements as tuples (from_star, t
        # For star hopping routes - store multiple routes
        self.star_hop_routes = []  # List of routes, each route is a list of star names in the hopping s
        # Performance optimization - cache for route information
        self.route_cache = {}  # Cache for route distances, efficienc
        # For rotation center
        self.rotation_center = [0, 0, 0]  # Default to Sun
        self.rotation_center_star = None  # Direct reference to rotation center star (for perfo
        # Performance optimizations
        # Name-indexed lookup cache for stars to avoid repeated DataFrame filtering
        self.star_lookup_cache = {}
        for _, star in self.stars_df.iterrows():
            self.star_lookup_cache[star['name']] = star
        # Pre-calculate screen coordinates for stars (updated each frame)
        self.screen_coords_cache = {}
    def _render_text(self, text, max_width, color=(255, 255, 255)):
        """Helper method to render text that fits within a certain width."""
        rendered_text = self.info_font.render(text, True, color)
        # Check if the rendered text is too wide
        if rendered_text.get_width() > max_width:
            # Find a good cut-off point that fits
            for i in range(len(text) - 3, 0, -1):
                truncated = text[:i] + "..."
                test_render = self.info_font.render(truncated, True, color)
                if test_render.get_width() <= max_width:
                    return test_render
            # If we can't fit it, just return a very short version
            return self.info_font.render(text[:10] + "...", True, color)
        return rendered_text
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    def _world_to_screen(self, x, y, z):
        """Convert 3D world coordinates to 2D screen coordinates with rotation."""
        # Calculate coordinates relative to rotation center
        rel_x = x - self.rotation_center[0]
        rel_y = y - self.rotation_center[1]
        rel_z = z - self.rotation_center[2]
        # Cache rotation values for each frame to avoid recalculating them
        # We don't need to store these as instance variables because this method
        # is called many times in the same frame with the same rotation values
        cos_x = math.cos(self.rotation_x)
        sin_x = math.sin(self.rotation_x)
        cos_y = math.cos(self.rotation_y)
        sin_y = math.sin(self.rotation_y)
        cos_z = math.cos(self.rotation_z)
        sin_z = math.sin(self.rotation_z)
        # Apply rotation around X axis
        y_rot = rel_y * cos_x - rel_z * sin_x
        z_rot = rel_y * sin_x + rel_z * cos_x
        rel_y, rel_z = y_rot, z_rot
        # Apply rotation around Y axis
        x_rot = rel_x * cos_y + rel_z * sin_y
        z_rot = -rel_x * sin_y + rel_z * cos_y
        rel_x, rel_z = x_rot, z_rot
        # Apply rotation around Z axis
        x_rot = rel_x * cos_z - rel_y * sin_z
        y_rot = rel_x * sin_z + rel_y * cos_z
        rel_x, rel_y = x_rot, y_rot
        # Convert to screen coordinates - these calculations are made for each star
        # so optimizing them can have a measurable impact
        screen_x = (self.width * 0.5) + (rel_x * self.zoom) + self.camera_pos[0]
        screen_y = (self.height * 0.5) - (rel_y * self.zoom) + self.camera_pos[1]  # Y is inverted in s creen spac
        # Use z for sizing - simplified calculation
        size_factor = 1 + (rel_z * 0.1)  # Objects with positive Z appear larger
        return screen_x, screen_y, size_factor
       
    def _draw_multiple_star_inset(self, surface):
        """
        Draw a detailed inset visualization of a multiple star system
        when a star that is part of such a system is selected.
        """
        # Get the currently selected star system if any
        selected_system = None
        selected_system_data = None
        
        if self.selected_star:
            # Check if selected star is part of a multiple system
            selected_star_data = self.stars_df[self.stars_df['name'] == self.selected_star]
            
            if not selected_star_data.empty and selected_star_data['is_multiple'].values[0]:
                system_name = selected_star_data['system_name'].values[0]
                if system_name:
                    selected_system = system_name
                    
                    # Find the system data in the systems info
                    if hasattr(self.stars_df, 'system_info') and 'systems' in self.stars_df.system_info:
                        for system in self.stars_df.system_info['systems']:
                            if system['name'] == system_name:
                                selected_system_data = system
                                break
        
        # We only show the inset if we have a selected multiple system
        if not selected_system or not selected_system_data:
            return
            
        # Check if this system has multiple components
        if not isinstance(selected_system_data['components'], int) or selected_system_data['components'] < 2:
            return
        
        # Set up inset parameters
        inset_size = 250  # Size in pixels
        inset_margin = 20  # Margin from the bottom-left corner
        inset_pos = (inset_margin, self.height - inset_size - inset_margin)
        
        # Create a surface for the inset with a semi-transparent background
        inset_surface = pygame.Surface((inset_size, inset_size), pygame.SRCALPHA)
        inset_surface.fill((0, 0, 30, 200))  # Dark blue semi-transparent background
        
        # Add a border around the inset
        pygame.draw.rect(inset_surface, (100, 150, 255, 255), (0, 0, inset_size, inset_size), 2)
        
        # Add title at the top of the inset
        title_font = pygame.font.SysFont('Arial', 16, bold=True)
        title_text = title_font.render(f"{selected_system} System", True, (200, 220, 255, 255))
        title_pos = (inset_size//2 - title_text.get_width()//2, 10)
        inset_surface.blit(title_text, title_pos)
        
        # Add system information below the title
        info_font = pygame.font.SysFont('Arial', 12)
        info_text = f"Distance: {selected_system_data['distance']:.2f} ly"
        info_render = info_font.render(info_text, True, (180, 200, 255, 255))
        info_pos = (inset_size//2 - info_render.get_width()//2, 30)
        inset_surface.blit(info_render, info_pos)
        
        components_text = f"Components: {selected_system_data['components']}"
        components_render = info_font.render(components_text, True, (180, 200, 255, 255))
        components_pos = (inset_size//2 - components_render.get_width()//2, 45)
        inset_surface.blit(components_render, components_pos)
        
        # Calculate scale for the inset view based on separations
        max_separation = 0
        stars = selected_system_data.get('stars', [])
        
        # First, extract all star components and their positions
        star_positions = []
        primary_star = None
        
        # Find the primary star first
        for star in stars:
            if star.get('component', '') == 'A' or ('separation' not in star or not star['separation']):
                primary_star = star
                break
                
        if not primary_star:
            # If we can't identify a primary star, just use the first one
            primary_star = stars[0] if stars else None
            
        # Now find all the component positions relative to the primary
        for star in stars:
            # Skip the primary star - we'll handle it separately
            if star == primary_star:
                star_positions.append({
                    'star': star,
                    'component': star.get('component', 'A'),
                    'x': 0,  # Primary at origin initially
                    'y': 0,
                    'separation': 0,
                    'angle': 0
                })
                continue
                
            # Parse the separation to get distance and angle
            separation_info = star.get('separation', '')
            if isinstance(separation_info, str) and ':' in separation_info:
                try:
                    components, sep_str = separation_info.split(':')
                    sep_value = float(sep_str.split()[0])
                    max_separation = max(max_separation, sep_value)
                    
                    # Calculate position - for simplicity, distribute stars in a circle
                    # In a real visualization, you would use actual orbital data
                    angle = hash(star.get('name', '')) % 360  # Pseudo-random angle based on name
                    angle_rad = math.radians(angle)
                    
                    # Store position relative to primary
                    x_pos = sep_value * math.cos(angle_rad)
                    y_pos = sep_value * math.sin(angle_rad)
                    
                    star_positions.append({
                        'star': star,
                        'component': star.get('component', ''),
                        'x': x_pos,
                        'y': y_pos,
                        'separation': sep_value,
                        'angle': angle
                    })
                except (ValueError, IndexError):
                    pass
        
        # Set a reasonable default if we couldn't extract any separations
        if max_separation == 0:
            max_separation = 100  # Default to 100 AU for visualization
        
        # Calculate scale to fit in the inset with some margin
        display_radius = (inset_size - 80) / 2  # Increased margin for better visibility
        au_to_pixels = display_radius / max_separation
        
        # Find the geometric center of all stars to center the system
        center_of_mass_x = 0
        center_of_mass_y = 0
        
        # If we have positions, calculate center
        if star_positions:
            all_x = [pos['x'] for pos in star_positions]
            all_y = [pos['y'] for pos in star_positions]
            
            # Simple center calculation - average of all points
            avg_x = sum(all_x) / len(star_positions)
            avg_y = sum(all_y) / len(star_positions)
            
            # Offset all star positions to center the system
            for pos in star_positions:
                pos['x'] -= avg_x
                pos['y'] -= avg_y
        
        # Center coordinates for the inset view
        center_x, center_y = inset_size // 2, inset_size // 2 + 20  # Slightly lower center
        
        # Draw all stars
        for pos in star_positions:
            star = pos['star']
            
            # Calculate pixel position
            pixel_x = center_x + pos['x'] * au_to_pixels
            pixel_y = center_y + pos['y'] * au_to_pixels
            
            # Determine size and color based on whether it's primary
            is_primary = (pos['component'] == 'A')
            star_radius = 10 if is_primary else 5
            star_color = (255, 255, 200)  # Default yellow-white
            
            # Adjust color based on spectral class if available
            if 'class' in star and star['class']:
                spectral_class = star['class']
                if spectral_class.startswith('M'):
                    star_color = (255, 100, 100)  # Red for M stars
                elif spectral_class.startswith('K'):
                    star_color = (255, 180, 100)  # Orange for K stars
                elif spectral_class.startswith('G'):
                    star_color = (255, 255, 100)  # Yellow for G stars
                elif spectral_class.startswith('F'):
                    star_color = (255, 255, 200)  # Yellow-white for F stars
                elif spectral_class.startswith('A'):
                    star_color = (200, 200, 255)  # Blue-white for A stars
            
            # Draw the star
            pygame.draw.circle(inset_surface, star_color, (int(pixel_x), int(pixel_y)), star_radius)
            
            # If it's not the primary, draw a line connecting to primary
            if not is_primary and primary_star:
                # Find primary star position
                primary_pos_x = center_x
                primary_pos_y = center_y
                for p in star_positions:
                    if p['component'] == 'A':
                        primary_pos_x = center_x + p['x'] * au_to_pixels
                        primary_pos_y = center_y + p['y'] * au_to_pixels
                        break
                        
                # Draw connection line
                pygame.draw.line(inset_surface, (100, 100, 150), 
                                (int(primary_pos_x), int(primary_pos_y)), 
                                (int(pixel_x), int(pixel_y)), 1)
                
                # Add separation info for components other than primary
                if pos['separation'] > 0:
                    label_font = pygame.font.SysFont('Arial', 10)
                    sep_label = f"{pos['separation']:.1f} AU"
                    sep_render = label_font.render(sep_label, True, (150, 150, 200))
                    
                    # Position label at midpoint of connection line
                    mid_x = (primary_pos_x + pixel_x) / 2
                    mid_y = (primary_pos_y + pixel_y) / 2
                    sep_pos = (int(mid_x - sep_render.get_width() / 2), 
                              int(mid_y - sep_render.get_height() / 2))
                    inset_surface.blit(sep_render, sep_pos)
            
            # Add component label
            component_label = pos['component']
            if component_label:
                label_font = pygame.font.SysFont('Arial', 10)
                label_render = label_font.render(component_label, True, (200, 200, 255))
                label_pos = (int(pixel_x) + star_radius + 2, int(pixel_y) - 5)
                inset_surface.blit(label_render, label_pos)
        
        # Add a legend
        legend_font = pygame.font.SysFont('Arial', 10)
        legend_text = "* Distances not to scale"
        legend_render = legend_font.render(legend_text, True, (150, 150, 200))
        legend_pos = (5, inset_size - 15)
        inset_surface.blit(legend_render, legend_pos)
        
        # Draw the inset onto the main surface
        surface.blit(inset_surface, inset_pos)

    def _draw_star(self, surface, x, y, z, size, color_hex, name, abs_magnitude=None):
        """Draw a single star with enhanced glow effect using pygame."""
        color_rgb = self._hex_to_rgb(color_hex)

        # Special case for the Sun to use a constant size regardless of distance
        if name == 'Sun':
            # Override the star size calculation for the Sun with a fixed value
            # that doesn't depend on size_factor from screen coordinates
            abs_magnitude = 4.83  # The actual absolute magnitude of the Sun

        # Special case for Sirius A - the brightest star in the sky
        is_sirius = (name == 'Sirius A')
        if is_sirius:
            # Use its actual absolute magnitude, which is quite bright
            abs_magnitude = 1.43  # Actual value for Sirius

        # Convert world to screen coordinates
        screen_x, screen_y, size_factor = self._world_to_screen(x, y, z)

        # Scale size based only on absolute magnitude
        # Brighter stars (lower abs_magnitude) should be larger
        if abs_magnitude is not None:
            # For the brightest stars (-5), we want a max size of about 15px
            # For the dimmest stars (15), we want a min size of about 2px
            # Using a linear scale: size = 15 - (abs_magnitude + 5) * (13/20)
            # This gives size=15 at abs_mag=-5, and size=2 at abs_mag=15
            star_size = 15 - (abs_magnitude + 5) * (13/20)
            # Ensure a minimum size
            adjusted_size = max(2, int(star_size))
        else:
            # Default size if no magnitude provided
            adjusted_size = max(2, int(size))

        # Special case for Sun - always use a fixed size
        if name == 'Sun':
            adjusted_size = 7  # Fixed size in pixels for the Sun

        # Special case for Sirius - make it a bit larger than normal calculation
        if is_sirius:
            adjusted_size = 9  # Make Sirius a prominent size

        # Create a refined multi-layered glow effect

        # Set base values that control the overall glow
        num_layers = 5  # Normal stars get 5 layers
        if is_sirius:
            num_layers = 7  # Sirius gets more layers for a richer glow

        # Make brighter stars even smaller - reduce their core and halo sizes
        if abs_magnitude is not None and abs_magnitude < 5:
            # For very bright stars (magnitude < 5), make them smaller
            brightness_scale = max(0.5, (abs_magnitude + 5) / 10)  # Smaller for brighter stars

            # Except for Sirius and Sun which get fixed sizes
            if not (name == 'Sun' or is_sirius):
                adjusted_size = adjusted_size * brightness_scale

            # Ensure Sun keeps its fixed size
            if name == 'Sun':
                adjusted_size = 7
            elif is_sirius:
                adjusted_size = 9

        # The core is the actual star - slightly smaller than the calculated size for better appearance
        core_size = adjusted_size * 0.8

        # Very modest glow intensity scaling
        glow_intensity = 1.0
        if abs_magnitude is not None:
            # Much smaller range - bright stars barely get more glow
            glow_intensity = max(0.8, min(1.1, 0.9 + (10 - abs_magnitude) / 50))

        # Sirius gets extra glow
        if is_sirius:
            glow_intensity = 1.3

        # Maximum size of the outer halo - much smaller multiplier
        max_halo_size = adjusted_size * (1.2 + glow_intensity * 0.3)

        # Sirius gets a larger halo
        if is_sirius:
            max_halo_size = adjusted_size * 1.8

        # Calculate color values
        base_color = color_rgb

        # Create brighter core color
        core_boost = 90 if name == 'Sun' else 70  # Increased brightness for cores
        neon_boost = 50 if name == 'Sun' else 35  # More subtle for halos

        # Sirius gets special boosting
        if is_sirius:
            core_boost = 110  # Make Sirius's core extra bright
            neon_boost = 80   # And its halos more vibrant

        # Brighter core color
        core_color = (min(255, base_color[0] + core_boost),
                     min(255, base_color[1] + core_boost),
                     min(255, base_color[2] + core_boost))

        # Subtler neon color for halos
        neon_color = (min(255, base_color[0] + neon_boost),
                     min(255, base_color[1] + neon_boost),
                     min(255, base_color[2] + neon_boost))

        # Draw multiple glow layers from outside in
        for i in range(num_layers):
            # Calculate progress from outer (0) to inner (1)
            t = i / (num_layers - 1)

            # Calculate size for this layer - quadratic falloff for more natural appearance
            layer_t = t * t
            layer_size = max_halo_size * (1 - layer_t) + core_size * layer_t

            # Alpha progression - start extremely transparent for outer layers
            if is_sirius:
                # Sirius gets more visible outer halos
                if i == 0:  # Outermost layer
                    layer_alpha = 10  # Still subtle but more visible
                else:
                    # Inner layers get progressively more visible, enhanced for Sirius
                    layer_alpha = min(100, 10 + (i * 20))
            else:
                # Regular stars
                if i == 0:  # Outermost layer
                    layer_alpha = 5  # Almost invisible
                else:
                    # Inner layers get progressively more visible, but still subtle
                    layer_alpha = min(80, 5 + (i * 15))

            # Minimal color boost for a more natural starlight appearance
            color_boost = int(neon_boost * t * 0.7)  # Scale down the boost
            layer_color = (min(255, base_color[0] + color_boost),
                          min(255, base_color[1] + color_boost),
                          min(255, base_color[2] + color_boost),
                          layer_alpha)

            # Draw this layer
            size = int(layer_size)
            # Skip drawing if too small
            if size < 1:
                continue

            surface_size = max(1, size * 2)
            layer_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
            pygame.draw.circle(layer_surface, layer_color,
                              (size, size), size)
            surface.blit(layer_surface, (int(screen_x - size), int(screen_y - size)))

        # Draw the star core at the center - much brighter than the glow
        pygame.draw.circle(surface, core_color, (int(screen_x), int(screen_y)), max(1, int(core_size)))

    def _calculate_distance(self, star1, star2):
        """Calculate the 3D distance between two stars in light years."""
        if star1 is None or star2 is None:
            return 0
        # Extract coordinates
        x1, y1, z1 = star1['x'], star1['y'], star1['z']
        x2, y2, z2 = star2['x'], star2['y'], star2['z']
        # Calculate Euclidean distance
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
        return distance

    def _draw_distance_line(self, surface, star1, star2, color=(255, 255, 255), width=1, show_distance=True, precalc_distance=None):
        """Draw a line between two stars with distance label."""
        if star1 is None or star2 is None:
            return

        # Get star names for cache lookup
        star1_name = star1['name']
        star2_name = star2['name']

        # Check screen coordinates cache first (updated once per frame)
        if star1_name in self.screen_coords_cache:
            screen_x1, screen_y1, _ = self.screen_coords_cache[star1_name]
        else:
            x1, y1, z1 = star1['x'], star1['y'], star1['z']
            screen_x1, screen_y1, _ = self._world_to_screen(x1, y1, z1)
            self.screen_coords_cache[star1_name] = (screen_x1, screen_y1, _)

        if star2_name in self.screen_coords_cache:
            screen_x2, screen_y2, _ = self.screen_coords_cache[star2_name]
        else:
            x2, y2, z2 = star2['x'], star2['y'], star2['z']
            screen_x2, screen_y2, _ = self._world_to_screen(x2, y2, z2)
            self.screen_coords_cache[star2_name] = (screen_x2, screen_y2, _)

        # Draw the line
        pygame.draw.line(surface, color,
                        (int(screen_x1), int(screen_y1)),
                        (int(screen_x2), int(screen_y2)),
                        width)

        # Use pre-calculated distance if provided, otherwise calculate it
        if precalc_distance is not None:
            distance = precalc_distance
        else:
            # Calculate actual distance - create a cache key first
            cache_key = (star1_name, star2_name)

            # Try both directions for the cache key
            rev_cache_key = (star2_name, star1_name)

            # Check if this distance is already cached
            if cache_key in self.route_cache and 'distance' in self.route_cache[cache_key]:
                distance = self.route_cache[cache_key]['distance']
            elif rev_cache_key in self.route_cache and 'distance' in self.route_cache[rev_cache_key]:
                distance = self.route_cache[rev_cache_key]['distance']
            else:
                # Calculate and cache
                distance = self._calculate_distance(star1, star2)
                self.route_cache[cache_key] = {'distance': distance}

        # Add distance label in the middle of the line if requested
        if show_distance:
            # Calculate the midpoint of the line
            mid_x = (screen_x1 + screen_x2) / 2
            mid_y = (screen_y1 + screen_y2) / 2

        # Create distance label with a small offset
        distance_font = pygame.font.SysFont('Arial', 12)

        # Format very small distances more clearly (avoid showing 0.00)
        if distance < 0.01:
            distance_text = "<0.01 ly"
        else:
            distance_text = f"{distance:.2f} ly"

        distance_label = distance_font.render(distance_text, True, color)

        # Create a small dark background for better readability
        label_bg = pygame.Surface((distance_label.get_width() + 6, distance_label.get_height() + 4), pygame.SRCALPHA)
        label_bg.fill((0, 0, 0, 150))  # Semi-transparent black
        # Position the background and label
        bg_pos = (int(mid_x - label_bg.get_width() / 2), int(mid_y - label_bg.get_height() / 2))
        label_pos = (int(mid_x - distance_label.get_width() / 2), int(mid_y - distance_label.get_height() / 2))

        # Draw background and label
        surface.blit(label_bg, bg_pos)
        surface.blit(distance_label, label_pos)

    def _draw_star_hop_routes(self, surface):
            """Draw all active star-hopping routes."""
            if not self.star_hop_routes or all(len(route) < 2 for route in self.star_hop_routes):
                return

            # Hop route base colors - we'll create variations for each route
            base_colors = [
                (0, 255, 200),     # Light teal
                (80, 200, 255),    # Light blue
                (160, 140, 255),   # Purple
                (255, 80, 220),    # Pink
                (255, 0, 140),     # Magenta
                (255, 200, 0),     # Gold
                (0, 220, 100),     # Green
                (255, 100, 0),     # Orange
                (180, 220, 255),   # Baby blue
                (0, 180, 255),     # Cyan
            ]

            # Pre-calculate route color gradients for reuse
            route_color_gradients = {}

            # Draw each route with a different base color scheme
            for route_index, route in enumerate(self.star_hop_routes):
                if len(route) < 2:
                    continue
                
                # Select a base color for this route based on its index
                base_color_index = route_index % len(base_colors)
                base_color = base_colors[base_color_index]

                # Check if we've already calculated the color gradient for this base color
                if base_color_index in route_color_gradients:
                    route_colors = route_color_gradients[base_color_index]
                else:
                    # Create a color gradient for this route
                    route_colors = []
                    for i in range(5):  # Create 5 gradient steps
                        # Mix the base color with varying amounts of white
                        mix_factor = 0.8 - (i * 0.15)  # Start bright, get more saturated
                        color = (
                            int(base_color[0] * mix_factor + 255 * (1 - mix_factor)),
                            int(base_color[1] * mix_factor + 255 * (1 - mix_factor)),
                            int(base_color[2] * mix_factor + 255 * (1 - mix_factor))
                        )
                        route_colors.append(color)
                    # Cache the color gradient
                    route_color_gradients[base_color_index] = route_colors

                # Draw a line between each pair of stars in the route
                for i in range(len(route) - 1):
                    # Get star data for both ends of this hop
                    from_star_name = route[i]
                    to_star_name = route[i + 1]

                    # Use the lookup cache instead of filtering dataframe every time
                    if from_star_name in self.star_lookup_cache and to_star_name in self.star_lookup_cache:
                        from_star = self.star_lookup_cache[from_star_name]
                        to_star = self.star_lookup_cache[to_star_name]

                        # Use color based on hop index within this route
                        color_index = i % len(route_colors)
                        hop_color = route_colors[color_index]

                        # Draw thicker lines for the hop route
                        width = 2

                        # Create a unique key for this hop for caching
                        hop_key = (from_star_name, to_star_name)
                        rev_hop_key = (to_star_name, from_star_name)

                        # Check if we've already calculated this distance
                        hop_distance = None
                        if hop_key in self.route_cache and 'distance' in self.route_cache[hop_key]:
                            hop_distance = self.route_cache[hop_key]['distance']
                        elif rev_hop_key in self.route_cache and 'distance' in self.route_cache[rev_hop_key]:
                            hop_distance = self.route_cache[rev_hop_key]['distance']
                        else:
                            # Calculate it for the first time
                            hop_distance = self._calculate_distance(from_star, to_star)
                            # Cache it for future use
                            self.route_cache[hop_key] = {'distance': hop_distance}

                        # Draw the line with the pre-calculated distance
                        self._draw_distance_line(surface, from_star, to_star, color=hop_color, width=width, precalc_distance=hop_distance)

                        # Draw a small circle at each hop point, except start and end which already have indicators
                        if i > 0 and i < len(route) - 1:
                            # Check if screen coordinates are already in cache
                            if from_star_name in self.screen_coords_cache:
                                screen_x, screen_y, _ = self.screen_coords_cache[from_star_name]
                            else:
                                # Calculate screen coordinates
                                x, y, z = from_star['x'], from_star['y'], from_star['z']
                                screen_x, screen_y, _ = self._world_to_screen(x, y, z)
                                self.screen_coords_cache[from_star_name] = (screen_x, screen_y, _)

                            # Draw small hop indicator
                            pygame.draw.circle(surface, hop_color, (int(screen_x), int(screen_y)), 5, 1)

            # Add a legend showing the routes
            if len(self.star_hop_routes) > 0:
                legend_font = pygame.font.SysFont('Arial', 14)

                # Create header
                header = legend_font.render(f"Star-Hopping Routes ({len(self.star_hop_routes)}):", True, (220, 220, 255))

                # For each route, create a summary line
                route_summaries = []
                for i, route in enumerate(self.star_hop_routes):
                    if len(route) < 2:
                        continue

                    # Get start and end stars for this route
                    start_name = route[0]
                    end_name = route[-1]

                    # For better display, show detailed routes when small, compact form when larger
                    if len(route) <= 4:
                        # For short routes, show all stars
                        hops_text = " → ".join(route)
                    elif len(route) <= 6:
                        # For medium routes, show first, middle, and last
                        middle_name = route[len(route)//2]
                        hops_text = f"{start_name} → {middle_name} → {end_name}"
                    else:
                        # For longer routes, just show count of intermediate hops
                        hops_text = f"{start_name} → [{len(route)-2} hops] → {end_name}"

                    # Get or calculate route distances using cache for performance
                    total_hop_distance = 0
                    direct_distance = 0
                    efficiency = 100

                    # Create a unique key for this route
                    route_key = tuple(route)

                    try:
                        # Check if we have cached calculations for this route
                        if route_key in self.route_cache:
                            # Use cached values
                            cached_data = self.route_cache[route_key]
                            total_hop_distance = cached_data['total_distance']
                            direct_distance = cached_data['direct_distance']
                            efficiency = cached_data['efficiency']
                        else:
                            # Calculate values and cache them
                            # Get star data
                            start_star = self.stars_df[self.stars_df['name'] == route[0]].iloc[0]
                            end_star = self.stars_df[self.stars_df['name'] == route[-1]].iloc[0]

                            # Calculate direct distance
                            direct_distance = self._calculate_distance(start_star, end_star)

                            # Calculate total hop distance
                            for j in range(len(route) - 1):
                                from_star = self.stars_df[self.stars_df['name'] == route[j]].iloc[0]
                                to_star = self.stars_df[self.stars_df['name'] == route[j + 1]].iloc[0]
                                total_hop_distance += self._calculate_distance(from_star, to_star)

                            # Calculate efficiency ratio
                            efficiency = direct_distance / total_hop_distance * 100 if total_hop_distance > 0 else 100

                            # Cache the results
                            self.route_cache[route_key] = {
                                'total_distance': total_hop_distance,
                                'direct_distance': direct_distance,
                                'efficiency': efficiency
                            }

                        # Create more compact summary with distances and efficiency
                        route_num = i + 1  # Route number for easier reference
                        summary = f"Route {route_num}: {hops_text} • {total_hop_distance:.2f}ly • {efficiency:.0f}% efficient"

                    except (IndexError, KeyError):
                        # Fallback if there's an issue calculating distances
                        route_num = i + 1  # Route number for easier reference
                        summary = f"Route {route_num}: {hops_text}"

                    # Use the base color for this route
                    base_color_index = i % len(base_colors)
                    summary_color = base_colors[base_color_index]

                    route_summaries.append((summary, summary_color))

                # Calculate dimensions for the legend
                max_width = 500  # Increased max width for legend box
                line_height = 20

                # Render summaries to get actual widths
                rendered_summaries = []
                for summary, color in route_summaries:
                    rendered = legend_font.render(summary, True, color)
                    rendered_summaries.append(rendered)

                # Calculate box width based on widest line
                widest_line = max([header.get_width()] + [r.get_width() for r in rendered_summaries], default=0)
                box_width = min(max_width, widest_line + 30)  # Added more padding

                # Calculate box height
                box_height = 20 + line_height * (len(rendered_summaries) + 1)  # Header + summaries

                # Create semi-transparent background
                legend_bg = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
                legend_bg.fill((0, 0, 0, 180))  # Semi-transparent black

                # Position the legend in the top-right, but with more room than before
                legend_pos = (self.width - box_width - 10, 10)

                # Draw the legend
                surface.blit(legend_bg, legend_pos)

                # Draw header
                surface.blit(header, (legend_pos[0] + 10, legend_pos[1] + 10))

                # Draw route summaries
                y_offset = legend_pos[1] + 10 + line_height
                for i, rendered in enumerate(rendered_summaries):
                    # If the text is still too wide (should be rare now), we need to truncate it
                    if rendered.get_width() > box_width - 20:
                        # Create a clipped version with ellipsis
                        summary_text = route_summaries[i][0]
                        color = route_summaries[i][1]

                        # Estimate how many characters we can fit
                        char_width = rendered.get_width() / len(summary_text)
                        chars_to_show = int((box_width - 40) / char_width)  # -40 for margin and ellipsis

                        # Try to be smarter about truncation - keep the start and end parts
                        if chars_to_show > 20:  # If we can show a reasonable amount
                            # Keep the beginning and end of the text
                            first_part = int(chars_to_show * 0.6)  # Show more of the first part
                            last_part = int(chars_to_show * 0.3)   # and less of the end
                            truncated = summary_text[:first_part] + "..." + summary_text[-last_part:]
                        else:
                            # Simple truncation if very limited space
                            truncated = summary_text[:chars_to_show] + "..."

                        # Render truncated text
                        rendered = legend_font.render(truncated, True, color)

                    surface.blit(rendered, (legend_pos[0] + 10, y_offset))
                    y_offset += line_height

    def _render_stars(self, surface):
        """Render all stars in the scene."""
        # Clear the screen coordinates cache at the start of each frame
        self.screen_coords_cache = {}

        # Create a set of stars involved in distance measurements or star-hopping routes
        important_stars = set()

        # Add stars from distance measurements
        for from_star, to_star in self.distance_lines:
            important_stars.add(from_star)
            important_stars.add(to_star)

        # Add stars from star-hopping routes
        for route in self.star_hop_routes:
            for star_name in route:
                important_stars.add(star_name)

        # Pre-filter stars that should be drawn
        visible_stars = []
        for _, star in self.stars_df.iterrows():
            # Check if this star should be displayed
            within_range = star['distance_ly'] <= self.max_distance
            is_important = star['name'] in important_stars

            # Skip stars that are too far and not important
            if not (within_range or is_important):
                continue

            # Add to the list of stars to draw
            visible_stars.append({
                'star': star,
                'is_important': is_important,
                'is_distance_extended': is_important and not within_range,
                'is_rotation_center': (self.rotation_center_star is not None and
                                    star['name'] == self.rotation_center_star['name'])
            })

        # Draw all visible stars
        for star_info in visible_stars:
            star = star_info['star']
            is_important = star_info['is_important']
            is_distance_extended = star_info['is_distance_extended']
            is_rotation_center = star_info['is_rotation_center']

            # Placeholder size (actual size will be determined by absolute magnitude)
            base_size = 1

            # Calculate screen coordinates for this star - use a faster approach
            try:
                screen_coords = self._world_to_screen(star['x'], star['y'], star['z'])
                screen_x, screen_y, size_factor = screen_coords

                # Cache the screen coordinates for this star for reuse within this frame
                self.screen_coords_cache[star['name']] = screen_coords
            except:
                # In case of any calculation error, use a default off-screen position
                screen_x, screen_y, size_factor = -100, -100, 1
                self.screen_coords_cache[star['name']] = (screen_x, screen_y, size_factor)

            # Draw the star with glow effect, passing name so special stars can get special treatment
            if star['name'] == 'Sun':
                color = '#ffff00'  # Force Sun to be yellow
            elif star['name'] == 'Sirius A':
                color = '#1e64ff'  # Force Sirius to be vivid blue
            else:
                color = star['color']

            self._draw_star(surface, star['x'], star['y'], star['z'], base_size,
                        color, star['name'], star['abs_magnitude'])

            # Special case for important stars - add labels
            if star['name'] == 'Sun':
                # Add "Sun" label - smaller and white
                small_font = pygame.font.SysFont('Arial', 12)
                sun_label = small_font.render("SUN", True, (255, 255, 255))
                label_pos = (int(screen_x) - sun_label.get_width()//2, int(screen_y) + 15)
                surface.blit(sun_label, label_pos)

                # The Sun gets the same rotation center indicator as other stars
                if is_rotation_center:
                    # Draw a circular orbit indicator (same as for other stars)
                    indicator_radius = 15
                    pygame.draw.circle(surface, (100, 200, 255), (int(screen_x), int(screen_y)),
                                    indicator_radius, 1)  # Just the outline
                    # Draw a second circle to make it more noticeable
                    pygame.draw.circle(surface, (100, 200, 255), (int(screen_x), int(screen_y)),
                                    indicator_radius + 5, 1)

            # Add Sirius label and effects
            elif star['name'] == 'Sirius A':
                # Add "SIRIUS" label - blue tint (always visible)
                small_font = pygame.font.SysFont('Arial', 12, bold=True)
                sirius_label = small_font.render("SIRIUS", True, (150, 200, 255))
                label_pos = (int(screen_x) - sirius_label.get_width()//2, int(screen_y) + 15)
                surface.blit(sirius_label, label_pos)

                # Add a blue halo effect just for Sirius
                if not is_rotation_center:  # Only if not already showing rotation indicator
                    halo_size = 20
                    halo_color = (30, 100, 255, 30)  # Blue with low alpha
                    halo_surface = pygame.Surface((halo_size*2, halo_size*2), pygame.SRCALPHA)
                    pygame.draw.circle(halo_surface, halo_color, (halo_size, halo_size), halo_size)
                    surface.blit(halo_surface, (screen_x - halo_size, screen_y - halo_size))

            # Show labels for selected stars or rotation center stars (always visible)
            elif (self.selected_star == star['name'] or is_rotation_center) and star['name'] not in ['Sun', 'Sirius A']:
                # Check if this star is part of any distance measurement (for label enhancement)
                is_in_measurement = any(star['name'] in measurement for measurement in self.distance_lines)

                # Determine label style based on status
                if self.selected_star == star['name'] and is_rotation_center:
                    # Both selected and rotation center - make it stand out more
                    small_font = pygame.font.SysFont('Arial', 12, bold=True)
                    label_color = (220, 220, 255)  # Bright white-purple
                elif is_rotation_center:
                    # Rotation center but not selected
                    small_font = pygame.font.SysFont('Arial', 12, bold=True)
                    label_color = (100, 200, 255)  # Blue for rotation center
                else:
                    # Selected but not rotation center
                    small_font = pygame.font.SysFont('Arial', 12, bold=True)
                    label_color = (255, 220, 100)  # Gold for selection

                # Use the star name as the label text
                label_text = star['name']

                # For stars in measurements, we could use a different color or style instead of symbols
                # But we'll keep it simple and just use the name as is

                # Render the label
                star_label = small_font.render(label_text, True, label_color)
                label_pos = (int(screen_x) - star_label.get_width()//2, int(screen_y) + 15)

                # Add a small background for better readability
                label_bg = pygame.Surface((star_label.get_width() + 4, star_label.get_height() + 2), pygame.SRCALPHA)
                label_bg.fill((0, 0, 0, 120))  # Semi-transparent black
                bg_pos = (label_pos[0] - 2, label_pos[1] - 1)
                surface.blit(label_bg, bg_pos)

                surface.blit(star_label, label_pos)

            # Check if this star is involved in any important visualization feature
            is_in_distance_measurement = any(star['name'] in measurement for measurement in self.distance_lines)
            is_in_star_hop = any(star['name'] in route for route in self.star_hop_routes)
            is_feature_star = is_in_distance_measurement or is_in_star_hop

            # Only show names for stars if:
            # 1. They're part of a distance measurement/route OR star names are enabled
            # 2. They're not already handled (Sun, Sirius A)
            # 3. They're not the selected star or rotation center (already displayed above)
            if ((is_feature_star or self.show_star_names) and
                star['name'] not in ['Sun', 'Sirius A'] and
                self.selected_star != star['name'] and
                not is_rotation_center):

                # Use slightly larger font for stars in features
                font_size = 12 if is_feature_star else 10
                small_font = pygame.font.SysFont('Arial', font_size, bold=is_feature_star)

                # Set color based on star's role - consistent coloring regardless of distance
                if is_in_distance_measurement:
                    text_color = (255, 255, 200)  # Yellow-ish for distance measurements
                elif is_in_star_hop:
                    text_color = (180, 220, 255)  # Blue-ish for star hops
                else:
                    # Default color is slightly brighter if it's an extended star to make it more noticeable
                    text_color = (220, 220, 220) if is_distance_extended else (200, 200, 200)

                # Keep the label simple - just the star name for both regular and extended stars
                label_text = star['name']

                star_label = small_font.render(label_text, True, text_color)

                # Consistent positioning at y+15 (same as selected/rotation center stars)
                label_pos = (int(screen_x) - star_label.get_width()//2, int(screen_y) + 15)

                # Add a small background for better readability
                if is_feature_star or is_distance_extended:
                    label_bg = pygame.Surface((star_label.get_width() + 4, star_label.get_height() + 2), pygame.SRCALPHA)
                    bg_color = (0, 0, 0, 140) if is_distance_extended else (0, 0, 0, 120)
                    label_bg.fill(bg_color)  # Semi-transparent black
                    bg_pos = (label_pos[0] - 2, label_pos[1] - 1)
                    surface.blit(label_bg, bg_pos)

                surface.blit(star_label, label_pos)

            # Highlight selected star with crosshairs (on top of the star)
            if self.selected_star == star['name']:
                # Draw selection indicator as crosshairs
                crosshair_size = 10
                pygame.draw.line(surface, (255, 255, 255),
                                (screen_x - crosshair_size, screen_y), (screen_x + crosshair_size, screen_y))
                pygame.draw.line(surface, (255, 255, 255),
                                (screen_x, screen_y - crosshair_size), (screen_x, screen_y + crosshair_size))

            # Draw rotation center indicator for regular stars (Sun has its own)
            if is_rotation_center and star['name'] != 'Sun':
                # Draw a circular orbit indicator
                indicator_radius = 15
                pygame.draw.circle(surface, (100, 200, 255), (int(screen_x), int(screen_y)),
                                indicator_radius, 1)  # Just the outline
                # Draw a second circle to make it more noticeable
                pygame.draw.circle(surface, (100, 200, 255), (int(screen_x), int(screen_y)),
                                indicator_radius + 5, 1)

      # Solar system rendering removed

    def _render_ui(self, surface):
        """Render UI elements."""
        # If we have a selected star, display its information
        if self.selected_star is not None and self.selected_star in self.star_lookup_cache:
            star_data = self.star_lookup_cache[self.selected_star]

            # Create a smaller, more compact star info panel
            panel_width = 280

            # Use a smaller font for star info
            star_info_font = pygame.font.SysFont('Arial', 14)

            # Extract star color for theming
            color_rgb = self._hex_to_rgb(star_data['color'])

            # Display all available data for the selected star
            if 'original_data' in star_data:
                # Calculate panel height dynamically based on content
                num_items = 4  # Basic items: Name, Distance, Color Index, Spectral Class

                # Add other original data items
                original_data = star_data['original_data']
                for key in sorted(original_data.keys()):
                    if key not in ['Common Name', 'Distance (ly)', 'Class']:  # Skip duplicates and handled items
                        num_items += 1

                # Calculate panel height - no transparent background needed
                line_height = 19  # For smaller font
                panel_height = num_items * line_height + 30  # Some extra padding

                # Start y position for drawing text
                y_offset = 15

                # Basic info first with colored header
                if 'name' in star_data:
                    # Name in star's color with bold for prominence
                    name_font = pygame.font.SysFont('Arial', 16, bold=True)
                    name_text = name_font.render(star_data['name'], True, color_rgb)
                    name_pos = (15, y_offset)
                    surface.blit(name_text, name_pos)
                    y_offset += 22  # Slightly bigger space after name

                # Distance with light blue color
                if 'distance_ly' in star_data:
                    dist_text = star_info_font.render(f"Distance: {star_data['distance_ly']:.2f} ly", True, (150, 200, 255))
                    surface.blit(dist_text, (15, y_offset))
                    y_offset += line_height

                # Add spectral class with color highlighting
                spectral_class = star_data['original_data'].get('Class', 'Unknown')
                spec_prefix = star_info_font.render("Spectral Class: ", True, (200, 200, 200))
                spec_value = star_info_font.render(spectral_class, True, color_rgb)
                surface.blit(spec_prefix, (15, y_offset))
                surface.blit(spec_value, (15 + spec_prefix.get_width(), y_offset))
                y_offset += line_height

                # Add color information with a small colored icon
                if 'color_b_v' in star_data:
                    # Create a small color swatch
                    swatch_size = 8
                    swatch_rect = pygame.Rect(15, y_offset + 4, swatch_size, swatch_size)
                    pygame.draw.rect(surface, color_rgb, swatch_rect)

                    # Display B-V value
                    if isinstance(star_data['color_b_v'], str):
                        # Special case for Sirius - show actual color index instead of SIRIUS_BLUE
                        if star_data['name'] == 'Sirius A' and star_data['color_b_v'] == 'SIRIUS_BLUE':
                            # Actual B-V index for Sirius A is around 0.00
                            color_text = star_info_font.render(f"  Color Index (B-V): 0.00", True, (200, 200, 200))
                        else:
                            color_text = star_info_font.render(f"  Color Index (B-V): {star_data['color_b_v']}", True, (200, 200, 200))
                    else:
                        color_text = star_info_font.render(f"  Color Index (B-V): {star_data['color_b_v']:.2f}", True, (200, 200, 200))
                    surface.blit(color_text, (15 + swatch_size, y_offset))
                    y_offset += line_height

                # Get remaining data from original_data dictionary and sort by key
                # Use alternating colors for easier readability
                use_alt_color = False
                for key in sorted(original_data.keys()):
                    if key not in ['Common Name', 'Distance (ly)', 'Class']:  # Skip duplicates
                        # Alternate between white and light gray
                        if use_alt_color:
                            text_color = (220, 220, 220)
                        else:
                            text_color = (255, 255, 255)
                        use_alt_color = not use_alt_color

                        # Split into label and value
                        label = star_info_font.render(f"{key}: ", True, (180, 180, 180))
                        value = star_info_font.render(f"{original_data[key]}", True, text_color)

                        # Draw label and value
                        surface.blit(label, (15, y_offset))
                        surface.blit(value, (15 + label.get_width(), y_offset))
                        y_offset += line_height
            else:
                # Fallback to basic information if original_data is not available
                # Just display name and distance
                panel_height = 70
                y_offset = 15

                # Name
                name_font = pygame.font.SysFont('Arial', 16, bold=True)
                name_text = name_font.render(star_data['name'], True, color_rgb)
                surface.blit(name_text, (15, y_offset))
                y_offset += 22

                # Distance
                dist_text = star_info_font.render(f"Distance: {star_data['distance_ly']:.2f} ly", True, (150, 200, 255))
                surface.blit(dist_text, (15, y_offset))
                y_offset += line_height

                # Magnitude
                mag_text = star_info_font.render(f"Magnitude: {star_data['abs_magnitude']}", True, (200, 200, 200))
                surface.blit(mag_text, (15, y_offset))

        # Get rotation center star name for display - use cached reference for performance
        rotation_center_name = "Unknown"
        if self.rotation_center_star is not None:
            rotation_center_name = self.rotation_center_star['name']

        # Prepare distance display status text
        if len(self.distance_lines) == 0:
            if self.selected_star and rotation_center_name != self.selected_star:
                # Show preview of what will be measured
                distance_status = f"PREVIEW: {rotation_center_name} → {self.selected_star}"
            else:
                distance_status = "OFF"
        elif len(self.distance_lines) == 1:
            from_star, to_star = self.distance_lines[0]
            distance_status = f"{from_star} → {to_star}"
        else:
            distance_status = f"ON ({len(self.distance_lines)} measurements)"

        # Draw control information
        # Use smaller font for controls
        controls_font = pygame.font.SysFont('Arial', 13)

        # Control groups with color coding
        control_groups = [
            {
                "title": "Navigation",
                "color": (100, 200, 255),  # Blue
                "controls": [
                    {"key": "WASD/Arrows", "action": "Pan camera"},
                    {"key": "Mouse drag", "action": "Rotate view (X/Y)"},
                    {"key": "Q/E", "action": "Rotate Z axis"},
                    {"key": "Mouse wheel", "action": "Zoom in/out"},
                ]
            },
            {
                "title": "View",
                "color": (0, 220, 150),  # Teal
                "controls": [
                    {"key": "R", "action": "Reset view & center on Sun"},
                    {"key": "Shift+Click", "action": "Set rotation center"},
                    {"key": "C", "action": "Center on selected star"},
                    {"key": "0", "action": "Center on Sun"},
                    {"key": "F11", "action": "Toggle fullscreen"},
                ]
            },
            {
                "title": "Features",
                "color": (255, 180, 100),  # Orange
                "controls": [
                    {"key": "Tab", "action": "Toggle solar system"},
                    {"key": "N", "action": f"Toggle star names ({'ON' if self.show_star_names else 'OFF'})"},
                    {"key": "G", "action": f"Toggle galactic plane ({'ON' if self.show_galactic_plane else 'OFF'})"},
                    {"key": "H", "action": f"Toggle coordinate grid ({'ON' if self.show_coordinate_grid else 'OFF'})"},
                    {"key": "M", "action": f"Save distance line ({distance_status})"},
                        {"key": "T", "action": f"Add star-hopping route"},
                        {"key": "Shift+T", "action": "Clear routes"},
                        {"key": "Backspace", "action": "Clear measurements"},
                    ]
                },
                {
                    "title": "Info",
                    "color": (180, 180, 255),  # Lavender
                    "controls": [
                        {"key": "Center", "action": f"{rotation_center_name}"},
                        {"key": "Range", "action": f"{self.max_distance} light years"},
                        {"key": "+/-", "action": "Adjust range"}
                    ]
                }
            ]

        # Calculate total height needed for all groups
        total_height = 0
        line_height = 16
        group_spacing = 5

        for group in control_groups:
            # Group title plus each control item
            total_height += line_height + (len(group["controls"]) * line_height) + group_spacing

        # Set position for starting to draw controls
        y_offset = self.height - total_height - 10
        max_width = 0

        # Draw each control group
        for group in control_groups:
            # Draw group title
            title_font = pygame.font.SysFont('Arial', 14, bold=True)
            title_text = title_font.render(group["title"] + ":", True, group["color"])
            title_pos = (self.width - title_text.get_width() - 10, y_offset)
            surface.blit(title_text, title_pos)
            max_width = max(max_width, title_text.get_width())
            y_offset += line_height

            # Draw each control in this group
            for control in group["controls"]:
                # Draw key in bold
                key_font = pygame.font.SysFont('Arial', 13, bold=True)
                key_text = key_font.render(control["key"], True, (220, 220, 220))

                # Draw action description
                action_text = controls_font.render(": " + control["action"], True, (200, 200, 200))

                # Position and draw
                key_pos = (self.width - key_text.get_width() - action_text.get_width() - 10, y_offset)
                action_pos = (key_pos[0] + key_text.get_width(), y_offset)

                surface.blit(key_text, key_pos)
                surface.blit(action_text, action_pos)

                max_width = max(max_width, key_text.get_width() + action_text.get_width())
                y_offset += line_height

            # Add spacing between groups
            y_offset += group_spacing
    
    def _center_on_star(self, star_coords, star_obj=None):
        """Center the view on a specific star."""
        # Set as rotation center
        self.rotation_center = star_coords.copy()

        # Store direct reference to the rotation center star for performance
        self.rotation_center_star = star_obj

        # If we weren't given the star object, find it
        if self.rotation_center_star is None:
            # One-time search, necessary for direct reference
            for _, star in self.stars_df.iterrows():
                if (abs(star['x'] - self.rotation_center[0]) < 0.0001 and
                    abs(star['y'] - self.rotation_center[1]) < 0.0001 and
                    abs(star['z'] - self.rotation_center[2]) < 0.0001):
                    self.rotation_center_star = star
                    break

        # Reset view parameters
        self.camera_pos = [0, 0]
        # self.rotation_x = 0.0
        # self.rotation_y = 0.0
        # self.rotation_z = 0.0

    def _calculate_star_hop_route(self):
        """Calculate an optimal star-hopping route between rotation center and selected star.
        This uses a greedy algorithm to find a path that minimizes individual hop distances
        while ensuring we get closer to our destination with each hop."""
        if self.selected_star is None:
            return []

        # Use direct reference to rotation center star for performance
        rotation_center_star = None
        if self.rotation_center_star is not None:
            rotation_center_star = self.rotation_center_star['name']
        else:
            # Fall back to coordinate match if direct reference is missing
            for _, star in self.stars_df.iterrows():
                if (abs(star['x'] - self.rotation_center[0]) < 0.0001 and
                    abs(star['y'] - self.rotation_center[1]) < 0.0001 and
                    abs(star['z'] - self.rotation_center[2]) < 0.0001):
                    rotation_center_star = star['name']
                    break

        if rotation_center_star is None or rotation_center_star == self.selected_star:
            return []

        # Get coordinates of start and end stars using the lookup cache
        start_star = self.star_lookup_cache[rotation_center_star]
        end_star = self.star_lookup_cache[self.selected_star]

        # Direct distance between start and end - check cache first
        cache_key = (rotation_center_star, self.selected_star)
        rev_cache_key = (self.selected_star, rotation_center_star)

        if cache_key in self.route_cache and 'distance' in self.route_cache[cache_key]:
            direct_distance = self.route_cache[cache_key]['distance']
        elif rev_cache_key in self.route_cache and 'distance' in self.route_cache[rev_cache_key]:
            direct_distance = self.route_cache[rev_cache_key]['distance']
        else:
            direct_distance = self._calculate_distance(start_star, end_star)
            self.route_cache[cache_key] = {'distance': direct_distance}

        # If stars are very close, no need for hopping
        if direct_distance < 2.0:
            return [rotation_center_star, self.selected_star]

        # Initialize route with start point
        route = [rotation_center_star]
        current_star = start_star

        # Build a list of candidate stars instead of filtering the dataframe each time
        candidate_stars = []
        for name, star in self.star_lookup_cache.items():
            if (name != rotation_center_star and
                name != self.selected_star and
                star['distance_ly'] <= self.max_distance):
                candidate_stars.append(star)

        # Maximum allowed detour factor - how much longer the path can be compared to direct distance
        max_detour_factor = 2.0  # Increased to allow more exploration

        # Maximum number of hops to prevent excessive detours (increased to 10)
        max_hops = 10

        # Maximum hop distance as a factor of the direct distance
        max_hop_distance = direct_distance * 0.7  # Reduced to encourage smaller hops

        # Set for tracking visited stars
        visited = {rotation_center_star}

        # Keep track of the previous distance to destination to ensure we're making progress
        prev_dist_to_end = direct_distance

        # Keep adding hops until we reach the end or hit the maximum
        for _ in range(max_hops):
            # Calculate remaining distance to end
            dist_to_end = self._calculate_distance(current_star, end_star)

            # If we're close enough to the end, just go directly there
            if dist_to_end < max_hop_distance * 0.6:  # Slightly reduced threshold
                route.append(self.selected_star)
                break

            # Calculate total distance traveled so far
            total_distance = 0
            prev_star = start_star
            for star_name in route[1:]:  # Skip the first star
                star = self.star_lookup_cache[star_name]
                total_distance += self._calculate_distance(prev_star, star)
                prev_star = star

            # Check if we've already gone too far out of the way
            if total_distance > direct_distance * max_detour_factor - dist_to_end:
                # If detour is too long, just go directly to end
                route.append(self.selected_star)
                break

            # Find the best next hop
            best_hop = None
            best_score = float('inf')

            # Flag to track if we found any hop that gets us closer
            found_closer_hop = False

            for hop_star in candidate_stars:
                if hop_star['name'] in visited:
                    continue

                # Calculate distances for this hop
                hop_distance = self._calculate_distance(current_star, hop_star)
                to_end_distance = self._calculate_distance(hop_star, end_star)

                # Skip if hop is too short (likely a double star) or too long
                if hop_distance < 0.5 or hop_distance > max_hop_distance:
                    continue

                # Check if this hop gets us closer to the destination
                gets_closer = to_end_distance < dist_to_end

                # If we've already found at least one hop that gets us closer,
                # only consider hops that also get us closer
                if found_closer_hop and not gets_closer:
                    continue

                # If this is the first hop that gets us closer, clear previous candidates
                if gets_closer and not found_closer_hop:
                    best_hop = None
                    best_score = float('inf')
                    found_closer_hop = True

                # Enhanced scoring function:
                # - Heavy penalty for hops that don't get us closer
                # - When comparing hops that do get us closer, prefer shorter current hop
                #   and greater progress toward destination

                if gets_closer:
                    # For hops that get us closer, calculate a balanced score
                    # This prioritizes shorter current hops while rewarding progress toward destination
                    progress_factor = (dist_to_end - to_end_distance) / dist_to_end  # How much closer as proportion
                    hop_factor = 1 - min(1, hop_distance / max_hop_distance)  # Shorter hops score better

                    # Weighted score: 60% based on hop length, 40% based on progress toward destination
                    score = (hop_distance / 2) - (progress_factor * dist_to_end / 3)
                else:
                    # For hops that don't get us closer, add a large penalty
                    penalty = (to_end_distance - dist_to_end) * 2  # Penalty scales with how much farther
                    score = hop_distance + penalty

                if score < best_score:
                    best_score = score
                    best_hop = hop_star['name']

            # If no suitable hop was found, go directly to end
            if best_hop is None:
                route.append(self.selected_star)
                break

            # Add the best hop to our route
            route.append(best_hop)
            visited.add(best_hop)
            current_star = self.star_lookup_cache[best_hop]

            # Update previous distance to track progress
            prev_dist_to_end = dist_to_end

        # Make sure end point is in the route, but check for very short final hop
        if route[-1] != self.selected_star:
            # Get the last star in the current route
            last_star = self.star_lookup_cache[route[-1]]
            end_star = self.star_lookup_cache[self.selected_star]

            # Calculate distance to end
            final_hop_distance = self._calculate_distance(last_star, end_star)

            # Only add the final destination if it's not too close to the last hop
            # (prevents 0.00 ly hops that can appear with very close binary stars)
            if final_hop_distance >= 0.05:  # Lower threshold for final hop
                route.append(self.selected_star)

        return route

    def _handle_mouse_click(self, pos, set_rotation_center=False):
        """Handle mouse clicks for star selection and setting rotation center."""
        mouse_x, mouse_y = pos

        # Find closest star to the mouse click
        closest_star = None
        closest_distance = float('inf')
        closest_coords = None
        closest_star_obj = None

        # Iterate only over visible stars using the screen coordinates cache
        for star_name, (screen_x, screen_y, _) in self.screen_coords_cache.items():
            # Get the actual star object
            star = self.star_lookup_cache[star_name]

            # Only consider stars within the maximum distance
            if star['distance_ly'] > self.max_distance:
                continue

            # Distance from click to star
            distance = ((mouse_x - screen_x) ** 2 + (mouse_y - screen_y) ** 2) ** 0.5

            # Size and hit area based only on absolute magnitude
            # Use the same calculation as in _draw_star for consistency
            star_size = 15 - (star['abs_magnitude'] + 5) * (13/20)
            # Hit size should be larger than visual size for easier selection
            hit_size = max(5, star_size * self.glow_factor)

            # If within the star's hit area and closer than previous matches
            if distance < hit_size and distance < closest_distance:
                closest_distance = distance
                closest_star = star_name
                closest_coords = [star['x'], star['y'], star['z']]
                closest_star_obj = star

        # Update selected star
        self.selected_star = closest_star

        # If requested, also set this star as rotation center
        if set_rotation_center and closest_coords and closest_star_obj is not None:
            # Use the already retrieved star object for direct reference
            self._center_on_star(closest_coords, closest_star_obj)
            return True

        return False

    def _set_sun_as_rotation_center(self):
        """Set the Sun as the center of rotation."""
        # Use the star lookup cache for better performance
        if 'Sun' in self.star_lookup_cache:
            sun = self.star_lookup_cache['Sun']
            self.selected_star = 'Sun'
            # Center on the Sun, passing the star object for performance
            self._center_on_star([sun['x'], sun['y'], sun['z']], sun)
            return True
        return False

    def _save_view(self, slot=1):
        """Save the current view settings to a file."""
        # Create a dict with all current view settings
        view_data = {
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "rotation_z": self.rotation_z,
            "camera_pos": self.camera_pos,
            "zoom": self.zoom,
            "max_distance": self.max_distance,
            "show_star_names": self.show_star_names,
            "show_galactic_plane": self.show_galactic_plane,
            "show_coordinate_grid": self.show_coordinate_grid,
            "show_galactic_projections": self.show_galactic_projections,
            "show_multiple_star_inset": self.show_multiple_star_inset,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Add rotation center star
        if self.rotation_center_star is not None:
            view_data["rotation_center_star"] = self.rotation_center_star["name"]

        # Add selected star if any
        if self.selected_star:
            view_data["selected_star"] = self.selected_star

        # Add distance lines
        if self.distance_lines:
            view_data["distance_lines"] = self.distance_lines

        # Add star hop routes (list of lists)
        if self.star_hop_routes:
            view_data["star_hop_routes"] = self.star_hop_routes

        # Create directory if it doesn't exist
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saved_views")
        os.makedirs(save_dir, exist_ok=True)

        # Save to file
        file_path = os.path.join(save_dir, f"view_{slot}.json")
        with open(file_path, "w") as f:
            json.dump(view_data, f, indent=2)

        return f"View saved to slot {slot}"

    def _load_view(self, slot=1):
        """Load view settings from a file."""
        # Build file path
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saved_views")
        file_path = os.path.join(save_dir, f"view_{slot}.json")

        # Check if file exists
        if not os.path.exists(file_path):
            return f"No saved view in slot {slot}"

        # Load file
        try:
            with open(file_path, "r") as f:
                view_data = json.load(f)

            # Apply basic view settings
            self.rotation_x = view_data.get("rotation_x", 0)
            self.rotation_y = view_data.get("rotation_y", 0)
            self.rotation_z = view_data.get("rotation_z", 0)
            self.camera_pos = view_data.get("camera_pos", [0, 0])
            self.zoom = view_data.get("zoom", 40)
            self.max_distance = view_data.get("max_distance", 20.0)
            self.show_star_names = view_data.get("show_star_names", False)
            self.show_galactic_plane = view_data.get("show_galactic_plane", False)
            self.show_coordinate_grid = view_data.get("show_coordinate_grid", False)
            self.show_galactic_projections = view_data.get("show_galactic_projections", False)
            self.show_multiple_star_inset = view_data.get("show_multiple_star_inset", True)

            # Set rotation center star if provided
            rotation_center_name = view_data.get("rotation_center_star")
            if rotation_center_name and rotation_center_name in self.star_lookup_cache:
                star = self.star_lookup_cache[rotation_center_name]
                self._center_on_star([star['x'], star['y'], star['z']], star)

            # Set selected star if provided
            self.selected_star = view_data.get("selected_star")

            # Set distance lines if provided
            if "distance_lines" in view_data:
                self.distance_lines = view_data["distance_lines"]

            # Set star hop routes if provided
            if "star_hop_routes" in view_data:
                self.star_hop_routes = view_data["star_hop_routes"]

            return f"Loaded view from slot {slot} (saved {view_data.get('timestamp', 'unknown')})"

        except Exception as e:
            return f"Error loading view: {str(e)}"

    def handle_input(self, events):
        """Process user input events."""
        for event in events:
            if event.type == QUIT:
                return False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return False
                # Use Shift+P to pause/unpause
                elif event.key == K_p and (pygame.key.get_pressed()[K_LSHIFT] or pygame.key.get_pressed()[K_RSHIFT]):
                    self.paused = not self.paused
                # Use regular P to toggle galactic projections
                elif event.key == K_p:
                    self.show_galactic_projections = not self.show_galactic_projections
                # Use 'I' to toggle multiple star inset
                elif event.key == K_i:
                    self.show_multiple_star_inset = not self.show_multiple_star_inset
                # Tab key functionality removed
                # Toggle star names with 'N' key
                elif event.key == K_n:
                    self.show_star_names = not self.show_star_names
                # Toggle galactic plane with 'G' key
                elif event.key == K_g:
                    self.show_galactic_plane = not self.show_galactic_plane
                # Toggle coordinate grid with 'H' key
                elif event.key == K_h:
                    self.show_coordinate_grid = not self.show_coordinate_grid
                # Distance filter adjustments
                elif event.key == K_EQUALS or event.key == K_PLUS:
                    self.max_distance = min(20.0, self.max_distance + 1.0)
                elif event.key == K_MINUS:
                    self.max_distance = max(3.0, self.max_distance - 1.0)
                # Reset view completely and center on Sun
                elif event.key == K_r:
                    self._set_sun_as_rotation_center()
                # Center on Sun
                elif event.key == K_0 or event.key == K_KP0:
                    self._set_sun_as_rotation_center()
                # Center on currently selected star
                elif event.key == K_c and self.selected_star:
                    # Find the selected star's coordinates
                    selected = self.stars_df[self.stars_df['name'] == self.selected_star]
                    if not selected.empty:
                        star = selected.iloc[0]
                        # Center on the selected star
                        self._center_on_star([star['x'], star['y'], star['z']])

                # Save view with F keys
                elif event.key in [K_F1, K_F2, K_F3, K_F4, K_F5]:
                    # Save the current view to a slot (F1-F5 correspond to slots 1-5)
                    slot = event.key - K_F1 + 1
                    message = self._save_view(slot)
                    print(message)

                # Load view with Shift+F keys
                elif event.key in [K_F1, K_F2, K_F3, K_F4, K_F5] and (pygame.key.get_pressed()[K_LSHIFT] or pygame.key.get_pressed()[K_RSHIFT]):
                    # Load view from a slot (F1-F5 correspond to slots 1-5)
                    slot = event.key - K_F1 + 1
                    message = self._load_view(slot)
                    print(message)

                # Toggle distance measurement for the selected star
                elif event.key == K_m and self.selected_star:
                    # Find the current rotation center star
                    rotation_center_name = "Unknown"
                    for _, star in self.stars_df.iterrows():
                        if (abs(star['x'] - self.rotation_center[0]) < 0.0001 and
                            abs(star['y'] - self.rotation_center[1]) < 0.0001 and
                            abs(star['z'] - self.rotation_center[2]) < 0.0001):
                            rotation_center_name = star['name']
                            break

                    # Don't allow measuring from a star to itself
                    if self.selected_star == rotation_center_name:
                        return True

                    # Create the measurement pair
                    measurement = (rotation_center_name, self.selected_star)

                    # Check if this exact measurement is already being tracked
                    if measurement in self.distance_lines:
                        # Remove it
                        self.distance_lines.remove(measurement)
                    else:
                        # Add it to the fixed distance lines
                        self.distance_lines.append(measurement)

                # Clear all distance measurements with Backspace
                elif event.key == K_BACKSPACE:
                    self.distance_lines = []

                # Add a new star-hopping route with T key
                elif event.key == K_t:
                    # Check if Shift+T is pressed (clear routes)
                    if pygame.key.get_pressed()[K_LSHIFT] or pygame.key.get_pressed()[K_RSHIFT]:
                        self.star_hop_routes = []
                        # Routes cleared (debug message removed)
                    # Regular T key - add new route if a star is selected
                    elif self.selected_star:
                        # Calculate a new route
                        new_route = self._calculate_star_hop_route()

                        # Add the route if it's valid (has at least 1 star and reaches close to destination)
                        if len(new_route) >= 1:
                            # If the route doesn't end at the destination (due to minimum hop filtering),
                            # check if the last hop gets close enough to the destination
                            if new_route[-1] != self.selected_star:
                                # Get stars for distance check
                                last_star = self.star_lookup_cache[new_route[-1]]
                                dest_star = self.star_lookup_cache[self.selected_star]

                                # Calculate distance from last hop to destination
                                final_distance = self._calculate_distance(last_star, dest_star)

                                # If we're very close to destination (< 0.05 ly), consider the route valid
                                if final_distance < 0.05:
                                    # Route is valid - the algorithm avoided adding a very short finalhop
                                    self.star_hop_routes.append(new_route)
                                else:
                                    # If not close enough, add the destination explicitly for completeness
                                    complete_route = new_route.copy()
                                    complete_route.append(self.selected_star)
                                    self.star_hop_routes.append(complete_route)
                            else:
                                # Route already ends at destination
                                self.star_hop_routes.append(new_route)

            elif event.type == MOUSEBUTTONDOWN:
                # Set rotation center on Shift+click
                if event.button == 1:  # Left click
                    keys = pygame.key.get_pressed()
                    if keys[K_LSHIFT] or keys[K_RSHIFT]:
                        # Set clicked star as rotation center
                        self._handle_mouse_click(event.pos, set_rotation_center=True)
                    else:
                        # Just select the star without changing rotation center
                        self._handle_mouse_click(event.pos)
                # Mouse wheel - Change center of rotation if a star is selected
                elif (event.button == 4 or event.button == 5) and self.selected_star:  # Scroll
                    # Find the selected star's coordinates
                    selected = self.stars_df[self.stars_df['name'] == self.selected_star]
                    if not selected.empty:
                        star = selected.iloc[0]
                        # Center on the selected star
                        self._center_on_star([star['x'], star['y'], star['z']])

                    # Also adjust zoom
                    if event.button == 4:  # Scroll up
                        self.zoom = min(400, self.zoom * 1.1)
                    elif event.button == 5:  # Scroll down
                        self.zoom = max(5, self.zoom / 1.1)
                # Just zoom if no star is selected
                elif event.button == 4:  # Scroll up
                    self.zoom = min(400, self.zoom * 1.1)
                elif event.button == 5:  # Scroll down
                    self.zoom = max(5, self.zoom / 1.1)

            # Handle rotation with mouse drag
            elif event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[0]:  # Left mouse button held
                    rel_x, rel_y = event.rel
                    # Use relative mouse movement for rotation
                    # Scale down the rotation amount
                    self.rotation_y += rel_x * 0.01
                    self.rotation_x += rel_y * 0.01

        # Continuous input for camera movement
        keys = pygame.key.get_pressed()

        # Pan the camera
        if keys[K_w] or keys[K_UP]:
            self.camera_pos[1] -= 5
        if keys[K_s] or keys[K_DOWN]:
            self.camera_pos[1] += 5

        if keys[K_a] or keys[K_LEFT]:
            self.camera_pos[0] -= 5
        if keys[K_d] or keys[K_RIGHT]:
            self.camera_pos[0] += 5

        # Z-axis rotation with Q and E keys
        if keys[K_q]:
            self.rotation_z += 0.02
        if keys[K_e]:
            self.rotation_z -= 0.02

        return True

    def _draw_coordinate_grid(self, surface):
        """Draw a coordinate grid as a semi-transparent reference."""
        if not self.show_coordinate_grid:
            return

        # Use a subtle gray color for the grid
        plane_color = (80, 80, 100, 40)  # Light blue-gray with low alpha

        # Calculate the size of the plane based on maximum distance
        plane_size = self.max_distance * self.zoom
        grid_spacing = 5.0 * self.zoom  # Grid lines every 5 light years

        # Create a surface for the plane with alpha channel
        plane_surface = pygame.Surface((int(plane_size * 2), int(plane_size * 2)), pygame.SRCALPHA)

        # Draw a semi-transparent circle representing the plane boundary
        pygame.draw.circle(plane_surface, plane_color,
                        (int(plane_size), int(plane_size)),
                        int(plane_size), 0)

        # Draw grid lines
        grid_color = (100, 100, 120, 30)  # Slightly more visible than plane
        for i in range(-int(self.max_distance), int(self.max_distance) + 1, 5):
            if i == 0:  # Make the central axes more visible
                line_color = (150, 150, 200, 50)
                line_width = 2
            else:
                line_color = grid_color
                line_width = 1

            # Convert grid coordinates to surface coordinates
            pos = i * self.zoom + plane_size

            # Draw horizontal and vertical grid lines
            pygame.draw.line(plane_surface, line_color,
                            (0, int(pos)),
                            (int(plane_size * 2), int(pos)),
                            line_width)
            pygame.draw.line(plane_surface, line_color,
                            (int(pos), 0),
                            (int(pos), int(plane_size * 2)),
                            line_width)

        # Convert world coordinates of (0,0,0) to screen coordinates
        center_x, center_y, _ = self._world_to_screen(0, 0, 0)

        # Offset the plane to center it on the Sun
        offset_x = int(center_x - plane_size)
        offset_y = int(center_y - plane_size)

        # Blit the plane surface onto the screen
        surface.blit(plane_surface, (offset_x, offset_y))

    def _draw_galactic_projections(self, surface):
        """Draw projection lines from each star to the galactic plane."""
        if not self.show_galactic_projections or not self.show_galactic_plane:
            return

        # Process all visible stars within the max distance
        for star_name, star in self.star_lookup_cache.items():
            # Skip stars outside the maximum distance
            if star['distance_ly'] > self.max_distance:
                continue

            # Skip the Sun (at 0,0,0)
            if star_name == 'Sun':
                continue

            # Get the star's 3D coordinates
            x, y, z = star['x'], star['y'], star['z']

            # Calculate the projection point on the galactic plane (z=0)
            # Simply set z to 0 while keeping x and y the same
            projection_x, projection_y, projection_z = x, y, 0

            # Convert both points to screen coordinates
            star_screen_x, star_screen_y, _ = self._world_to_screen(x, y, z)
            proj_screen_x, proj_screen_y, _ = self._world_to_screen(projection_x, projection_y, projection_z)

            # Draw a line from the star to its projection on the galactic plane
            # Use a solid, subtle line for a clean appearance
            if z != 0:  # Only draw if the star is not already on the galactic plane
                # Use a very dark color for all projection lines
                # Dark gray with low transparency for a subtle but visible effect
                line_color = (40, 40, 60, 50)  # Very dark blue-gray

                # Draw a solid line from star to projection
                pygame.draw.line(surface, line_color,
                                (int(star_screen_x), int(star_screen_y)),
                                (int(proj_screen_x), int(proj_screen_y)),
                                1)  # Width of 1 pixel

                # Draw a small marker at the projection point
                marker_color = (50, 50, 70, 70)  # Slightly more visible than the line
                pygame.draw.circle(surface, marker_color, (int(proj_screen_x), int(proj_screen_y)), 2)

    def _draw_galactic_plane(self, surface):
        """Draw the galactic plane (b=0) based on the galactic coordinate system."""
        if not self.show_galactic_plane:
            return

        # Get the maximum extent based on the view distance
        max_extent = self.max_distance * 1.2

        # Draw distance circles first - each circle is generated directly in the galactic plane
        circle_distances = [5, 10, 15, 20]
        circle_color = (80, 90, 120, 20)  # Extremely dark blue-gray with minimal alpha

        # Simple font for distance labels
        distance_font = pygame.font.SysFont('Arial', 11)

        for distance in circle_distances:
            # Only draw circles within the maximum distance
            if distance <= self.max_distance:
                # Generate points for a circle in the galactic plane at this distance
                circle_points_world = []
                num_points = 48  # Number of points for the circle

                for i in range(num_points + 1):
                    # Angle around the circle
                    angle = (i / num_points) * 2 * math.pi

                    # Calculate point at the given distance in the galactic plane (z=0)
                    x = distance * math.cos(angle)  # Circle in galactic plane
                    y = distance * math.sin(angle)
                    z = 0  # Always in the z=0 plane (galactic plane)

                    circle_points_world.append((x, y, z))

                # Convert world coordinates to screen coordinates
                circle_points_screen = []
                for point in circle_points_world:
                    x, y, z = point
                    screen_x, screen_y, _ = self._world_to_screen(x, y, z)
                    circle_points_screen.append((int(screen_x), int(screen_y)))

                # Draw the circle by connecting the points
                if len(circle_points_screen) > 2:
                    pygame.draw.lines(surface, circle_color, True, circle_points_screen, 1)

                    # Create label at a specific point on the circle (e.g., 45 degrees)
                    label_angle = math.radians(45)  # Top-right position
                    label_x_world = distance * math.cos(label_angle)
                    label_y_world = distance * math.sin(label_angle)
                    label_z_world = 0  # In galactic plane

                    label_x, label_y, _ = self._world_to_screen(label_x_world, label_y_world, label_z_world)

                    # Create label - with a matching extremely subtle color
                    label_text = f"{distance} ly"
                    label = distance_font.render(label_text, True, (120, 140, 180, 100))

                    # Position slightly offset from the circle point
                    offset = 5
                    surface.blit(label, (label_x + offset, label_y - label.get_height() - offset))

        # Now draw the galactic plane as a filled disk
        # Create a set of points on the galactic plane edge
        # Each with b=0 (galactic latitude = 0) and varying l (galactic longitude)
        plane_points_world = []

        # Generate points for a complete circle around the galactic plane
        num_points = 48  # Number of points around the circle
        for i in range(num_points + 1):
            # Galactic longitude from 0 to 360 degrees
            gal_l = (i / num_points) * 360

            # Convert galactic coordinates (l, b=0) to Cartesian
            l_rad = math.radians(gal_l)

            # These equations match the ones in data_loader.py for consistency
            # For b=0, sin(b)=0 and cos(b)=1, so z=0 and we're in the x-y plane
            x = max_extent * math.cos(0) * math.cos(l_rad)  # cos(0) = 1
            y = max_extent * math.cos(0) * math.sin(l_rad)  # cos(0) = 1
            z = max_extent * math.sin(0)  # This is always 0 since sin(0) = 0

            plane_points_world.append((x, y, z))

        # Convert world coordinates to screen coordinates
        plane_points_screen = []
        for point in plane_points_world:
            x, y, z = point
            screen_x, screen_y, _ = self._world_to_screen(x, y, z)
            plane_points_screen.append((int(screen_x), int(screen_y)))

        # Draw the galactic plane as a closed polygon
        if len(plane_points_screen) > 2:
            # Create a semi-transparent surface for the plane
            plane_color = (120, 150, 220, 20)  # Light blue with low alpha (even more subtle)

            # Find the bounding box for our polygon to create the surface
            min_x = min(p[0] for p in plane_points_screen)
            max_x = max(p[0] for p in plane_points_screen)
            min_y = min(p[1] for p in plane_points_screen)
            max_y = max(p[1] for p in plane_points_screen)

            width = max_x - min_x + 20  # Add some padding
            height = max_y - min_y + 20

            # Create a surface that covers the polygon
            plane_surface = pygame.Surface((width, height), pygame.SRCALPHA)

            # Adjust points to be relative to the surface
            adjusted_points = [(p[0] - min_x + 10, p[1] - min_y + 10) for p in plane_points_screen]

            # Draw the filled polygon on the surface
            pygame.draw.polygon(plane_surface, plane_color, adjusted_points)

            # Outline the edge of the plane with a slightly brighter color
            edge_color = (160, 180, 250, 40)  # Make edge slightly less visible
            pygame.draw.polygon(plane_surface, edge_color, adjusted_points, 1)  # Thinner line

            # Draw the plane surface on the main screen
            surface.blit(plane_surface, (min_x - 10, min_y - 10))

            # Draw an arrow from the Sun toward the galactic center
            # Get screen coordinates for Sun (0,0,0) and galactic center direction
            sun_x, sun_y, _ = self._world_to_screen(0, 0, 0)  # The Sun's position
            gc_x, gc_y, _ = self._world_to_screen(max_extent, 0, 0)  # Galactic center direction

            # Calculate the disk radius in screen coordinates
            # Convert a point on the edge of the disk to screen coordinates
            # First, convert world radius to screen coordinates
            edge_x, edge_y, _ = self._world_to_screen(max_extent, 0, 0)  # Point at disk edge
            # Calculate disk radius in screen pixels
            disk_radius = math.sqrt((edge_x - sun_x)**2 + (edge_y - sun_y)**2)

            # Calculate arrow direction vector
            dx = gc_x - sun_x
            dy = gc_y - sun_y

            # Normalize and scale the direction vector
            length = math.sqrt(dx**2 + dy**2)
            if length > 0:
                # Make arrow exactly the length of the disk radius
                arrow_length = disk_radius  # Exactly match the disk radius

                # Normalized direction
                ndx = dx / length
                ndy = dy / length

                # Calculate arrow endpoint
                end_x = sun_x + ndx * arrow_length
                end_y = sun_y + ndy * arrow_length

                # Calculate arrow head points - make slightly smaller
                head_size = 8
                # Perpendicular vector for arrow head
                perp_x = -ndy
                perp_y = ndx

                # Calculate the points for the arrow head
                head1_x = end_x - ndx * head_size + perp_x * head_size * 0.5
                head1_y = end_y - ndy * head_size + perp_y * head_size * 0.5
                head2_x = end_x - ndx * head_size - perp_x * head_size * 0.5
                head2_y = end_y - ndy * head_size - perp_y * head_size * 0.5

                # Draw the arrow - thinner line
                arrow_color = (220, 240, 255, 180)  # Slightly less opaque
                pygame.draw.line(surface, arrow_color, (sun_x, sun_y), (end_x, end_y), 1)
                pygame.draw.polygon(surface, arrow_color, [
                    (end_x, end_y),
                    (head1_x, head1_y),
                    (head2_x, head2_y)
                ])

                # Add a label for the arrow near the end point (galactic center)
                label_font = pygame.font.SysFont('Arial', 12)
                label_text = "Galactic Center"  # Removed the arrow symbol
                label = label_font.render(label_text, True, arrow_color)

                # Position the label near the arrow end
                # Calculate a position near the arrow end but not directly on it
                label_x = end_x + ndx * 5  # Slightly beyond the arrow head
                label_y = end_y + ndy * 5 - label.get_height() / 2  # Centered vertically

                # Add a small background for better readability
                label_bg = pygame.Surface((label.get_width() + 6, label.get_height() + 2), pygame.SRCALPHA)
                label_bg.fill((0, 0, 0, 120))  # Semi-transparent black

                # Draw background and label
                surface.blit(label_bg, (label_x - 3, label_y - 1))
                surface.blit(label, (label_x, label_y))

    def render(self, screen):
        """Main render function."""
        # Clear the screen
        screen.fill((0, 0, 0))

        # Draw coordinate grid if enabled (should be behind everything)
        self._draw_coordinate_grid(screen)

        # Draw galactic plane if enabled (should be behind stars but in front of grid)
        self._draw_galactic_plane(screen)

        # Render stars
        self._render_stars(screen)

        # Draw galactic projections if enabled (after stars are drawn)
        self._draw_galactic_projections(screen)

        # Draw multiple star systems inset if enabled
        self._draw_multiple_star_inset(screen)

        # Colors for distance lines - rotate through these colors
        distance_colors = [
            (255, 255, 255),  # White
            (255, 255, 0),    # Yellow
            (0, 255, 255),    # Cyan
            (255, 128, 0),    # Orange
            (180, 180, 255),  # Light blue
            (255, 180, 180),  # Light pink
            (180, 255, 180),  # Light green
        ]

        # Use direct reference to rotation center star for performance
        rotation_center_star = self.rotation_center_star

        # Draw all persistent distance lines with different colors
        for i, measurement in enumerate(self.distance_lines):
            from_star_name, to_star_name = measurement

            # Get both stars using the name lookup cache
            if from_star_name in self.star_lookup_cache and to_star_name in self.star_lookup_cache:
                from_star = self.star_lookup_cache[from_star_name]
                to_star = self.star_lookup_cache[to_star_name]

                # Use a different color for each line (cycling through the available colors)
                color_index = i % len(distance_colors)
                line_color = distance_colors[color_index]

                # Draw the distance line with appropriate color
                self._draw_distance_line(screen, from_star, to_star, color=line_color, width=1)

        # Draw all star-hopping routes
        if self.star_hop_routes:
            self._draw_star_hop_routes(screen)

        # Also draw a temporary distance line from current rotation center to selected star
        if (rotation_center_star is not None and
            self.selected_star and
            self.selected_star != rotation_center_star['name']):

            # Check if this exact measurement is already shown persistently
            current_measurement = (rotation_center_star['name'], self.selected_star)
            rev_measurement = (self.selected_star, rotation_center_star['name'])

            if (current_measurement not in self.distance_lines and
                rev_measurement not in self.distance_lines and
                self.selected_star in self.star_lookup_cache):

                selected_star = self.star_lookup_cache[self.selected_star]

                # Draw a gray line for temporary selection
                self._draw_distance_line(screen, rotation_center_star, selected_star, color=(180, 180, 180), width=1)

                # We don't need to add extra name labels here - the rotation center should already have
                # its name displayed by the rotation center indicator code
                # Let's use the preview line only as a visual indicator of the pending measurement

        # Render UI
        self._render_ui(screen)

class StarApp:
    """
    Interactive application for star visualization using PyGame.
    """
    def __init__(self, stars_df, max_distance=20.0, fullscreen=False):
        self.stars_df = stars_df
        self.max_distance = max_distance
        self.fullscreen = fullscreen

        # Initialize PyGame
        pygame.init()

        # Set initial window size
        if self.fullscreen:
            # Get the screen info to set a proper fullscreen size
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        else:
            self.width = 1024
            self.height = 768
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

        # Update window caption to reflect actual max distance
        pygame.display.set_caption(f"{max_distance}LY - 3D Stellar Neighborhood Visualization")

        # Create visualizer
        self.visualizer = PyGameVisualizer(stars_df)
        self.visualizer.width = self.width
        self.visualizer.height = self.height
        self.visualizer.max_distance = self.max_distance  # Set initial max distance
        self.visualizer.info_font = pygame.font.SysFont('Arial', 18)

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        self.fullscreen = not self.fullscreen

        if self.fullscreen:
            # Get current display info
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        else:
            # Return to windowed mode with default size
            self.width = 1024
            self.height = 768
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

        # Update visualizer dimensions
        self.visualizer.width = self.width
        self.visualizer.height = self.height

    def run(self):
        """Run the main game loop."""
        clock = pygame.time.Clock()
        running = True

        while running:
            # Process events
            events = pygame.event.get()

            # Handle window-specific events before passing to visualizer
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break

                # Handle window resize events
                elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    self.width, self.height = event.size
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                    self.visualizer.width = self.width
                    self.visualizer.height = self.height

                # Handle fullscreen toggle with F11 key
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()

            # Process remaining events with the visualizer
            if running:
                running = self.visualizer.handle_input(events)

            # Render the scene
            self.visualizer.render(self.screen)

            # Update the display
            pygame.display.flip()

            # Cap the framerate
            clock.tick(60)

        # Cleanup
        pygame.quit()