# Solar Neighborhood Visualization

A 3D interactive visualization of stars within 20 light years of our Sun.

This is just a small project, generated almost entirely using Claude Code research preview.

<br/>
<p align="center">
    <img width="100%" src="https://raw.githubusercontent.com/nekitmm/solar-neighborhood-app/main/screenshot.png" alt="Example screenshot of the app">
</p>
<br/>

## Features

- Visualize stars with accurate positions and colors based on spectral class
- Interactive 3D navigation with keyboard/mouse controls
- Center view on selected stars
- Toggle display of star names
- Visualize the galactic plane and coordinate grid
- Show projections of stars onto the galactic plane
- Display detailed information about multiple star systems
- Measure distances between stars
- Create and visualize "star-hopping" routes between stars
- Save and restore different view positions

## Installation

```bash
# Clone this repository
git clone https://github.com/yourusername/solar-neighbourhood-app.git
cd solar-neighbourhood-app

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the application with the following command:

```bash
python main.py
```

On Windows I run it from Powershell, running from WSL is a bit tricky.

### Command Line Options

- `--max-distance`: Maximum distance from Sun in light years (default: 20)
- `--fullscreen`: Run in fullscreen mode

### Examples

```bash
# Run the application with default settings
python main.py

# Show only stars within 10 light years
python main.py --max-distance 10

# Run in fullscreen mode
python main.py --fullscreen
```

## Data Sources

Star data is sourced from [Atlas of the Universe](http://www.atlasoftheuniverse.com/nearstar.html). Special thanks to Richard Powell for compiling and providing this data (as of 2006).

The star dataset includes:
- Star names
- Distances from the Sun in light years
- 3D coordinates (x, y, z)
- Absolute magnitudes
- B-V color indices (converted to RGB for visualization)
- Spectral classification


## Future Improvements

- Add more stars with data from astronomical catalogs
- Include proper motion vectors
- Add search functionality
- Include more stellar properties