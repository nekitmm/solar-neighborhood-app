# Solar Neighborhood Visualization

A 3D interactive visualization of stars within 20 light years of our Sun.

This is just a small project, generated almost entirely using Claude Code research preview.

<br/>
<p align="center">
    <img width="100%" src="https://raw.githubusercontent.com/nekitmm/solar-neighborhood-app/main/screenshot.png" alt="Example screenshot of the app">
</p>
<br/>

## Features

- Visualize stars with accurate positions and colors
- Interactive 3D rotation and zoom
- Filter stars by distance
- Highlight bright stars
- View detailed information about each star
- Measure distances
- Create "star-hopping" routes between stars
- etc.

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
- `--port`: Port to run dash app on (default: 8050)

### Examples

```bash
# Run the application with default settings
python main.py


# Show only stars within 10 light years
python main.py --max-distance 10

# Run on a different port
python main.py --port 8080
```

## Data Sources

The star dataset includes:
- Star names
- Distances from the Sun in light years
- 3D coordinates (x, y, z)
- Absolute magnitudes
- B-V color indices (converted to RGB for visualization)


## Future Improvements

- Add more stars with data from astronomical catalogs
- Include proper motion vectors
- Add search functionality
- Include more stellar properties