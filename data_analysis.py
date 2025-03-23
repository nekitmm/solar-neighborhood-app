#!/usr/bin/env python3
"""
Script to analyze star data and identify multiple star systems.
Generates an enhanced data file with multiple star system information.
"""

import pandas as pd
import re
import json
import os

# Load the data
data = pd.read_csv('data/stars.csv')

# Dictionary to store star systems
systems = {}

# Pattern to extract component identifiers (A, B, C, etc.)
component_pattern = re.compile(r'(?:^|\s)([A-Z])$')

# Process each row in the data
for idx, row in data.iterrows():
    # Skip rows with empty common names
    if pd.isna(row['Common Name']):
        continue
    
    # Extract the base name and component
    name = row['Common Name']
    component_match = component_pattern.search(name)
    
    # If this star has a component identifier (A, B, C, etc.)
    if component_match:
        component = component_match.group(1)
        base_name = name[:-2]  # Remove the component identifier
        
        # Add the star to the system
        if base_name not in systems:
            systems[base_name] = []
        systems[base_name].append({
            'name': name,
            'component': component,
            'distance': row['Distance (ly)'],
            'separation': row['Separation (AU)'],
            'class': row['Class'] if pd.notna(row['Class']) else None,
            'abs_mag': row['Abs Mag'] if pd.notna(row['Abs Mag']) else None,
            'color': row['Color'] if pd.notna(row['Color']) else None
        })
    
    # Check the Separation column for system information
    separation = row['Separation (AU)']
    if pd.notna(separation) and isinstance(separation, str):
        # Look for patterns like "AB:24 AU" or "AC:14000 AU"
        matches = re.findall(r'([A-Z]{2}):([0-9.]+)', separation)
        
        if matches:
            # This star belongs to a multiple system
            for match in matches:
                components, sep_value = match
                
                # Determine the base name (this is more complex and may need refinement)
                base_name = name
                if component_match:
                    base_name = name[:-2]
                
                # Add the system if it doesn't exist
                if base_name not in systems:
                    systems[base_name] = []
                    
                # Add this star to the system if not already there
                star_exists = False
                for star in systems[base_name]:
                    if star.get('name') == name:
                        star_exists = True
                        break
                        
                if not star_exists:
                    component = 'Unknown'
                    for c in components:
                        if c in name:
                            component = c
                            break
                    
                    systems[base_name].append({
                        'name': name,
                        'component': component,
                        'distance': row['Distance (ly)'],
                        'separation': separation,
                        'class': row['Class'] if pd.notna(row['Class']) else None,
                        'abs_mag': row['Abs Mag'] if pd.notna(row['Abs Mag']) else None,
                        'color': row['Color'] if pd.notna(row['Color']) else None
                    })

# Print the multiple star systems
print("Multiple Star Systems in the Solar Neighborhood:")
print("-------------------------------------------------")

# Filter out systems with only one component
multiple_systems = {}
for system_name, stars in systems.items():
    if len(stars) > 1:  # Only include actual multiple systems
        multiple_systems[system_name] = stars

# Sort systems by distance
sorted_systems = sorted(multiple_systems.items(), 
                        key=lambda x: float(x[1][0]['distance']) if x[1][0]['distance'] else float('inf'))

for system_name, stars in sorted_systems:
    print(f"\n{system_name} System:")
    print(f"  Distance: {stars[0]['distance']} light years")
    print(f"  Components: {len(stars)}")
    for star in sorted(stars, key=lambda x: x['component']):
        print(f"    - {star['name']}")
        if 'separation' in star and star['separation']:
            print(f"      Separation: {star['separation']}")

# Create a simple list of systems with component counts for visualization
system_summary = []
for system_name, stars in multiple_systems.items():
    system_summary.append({
        'name': system_name,
        'distance': float(stars[0]['distance']) if stars[0]['distance'] else None,
        'components': len(stars),
        'stars': stars
    })

# Sort by distance
system_summary.sort(key=lambda x: x['distance'] if x['distance'] is not None else float('inf'))

# Print the summary
print("\n\nMultiple Star Systems Summary:")
print("-----------------------------")
for system in system_summary:
    print(f"{system['name']}: {system['components']} components at {system['distance']} light years")

# Save the multiple star systems information to a JSON file for the visualization
multiple_systems_data = {
    'systems': system_summary
}

# Save to a JSON file in the data directory
with open('data/multiple_systems.json', 'w') as f:
    json.dump(multiple_systems_data, f, indent=2)

print(f"\nMultiple star systems data saved to data/multiple_systems.json")

# Also create a version that's formatted for easier use in the visualization code
visualization_format = {}

# For each star, record which system it belongs to and other system info
for system in system_summary:
    system_name = system['name']
    for star in system['stars']:
        star_name = star['name']
        visualization_format[star_name] = {
            'system_name': system_name,
            'component': star['component'],
            'system_distance': system['distance'],
            'system_components': system['components'],
            'separation': star['separation']
        }

# Save the visualization-friendly format to a separate JSON file
with open('data/star_systems_mapping.json', 'w') as f:
    json.dump(visualization_format, f, indent=2)

print(f"Star-to-system mapping saved to data/star_systems_mapping.json")