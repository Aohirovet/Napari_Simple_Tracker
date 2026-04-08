# Napari_Simple_Tracker

[![PyPI version 1.1.8](https://img.shields.io/badge/PyPI-1.1.8-blue)](https://pypi.org/project/napari-simple-tracker/1.1.8/)
[![Python 3.10-3.14](https://img.shields.io/badge/Python-3.10--3.14-green)](https://pypi.org/project/napari-simple-tracker/)
[![napari hub](https://img.shields.io/badge/napari--hub-plugin-orange)](https://napari-hub.org/plugins/napari-simple-tracker.html)

`Napari_Simple_Tracker` is a lightweight, easy-to-use napari plugin for ROI tracking and FRAP analysis in time-lapse imaging data.  
It is intentionally simple while still providing the core tools needed for routine quantitative analysis.

- Simple: point-based interaction with minimal configuration
- Practical: tracking, intensity plotting, CSV export, and session save/load are included
- Readable: ROI masks and track IDs are displayed directly in the napari viewer

## Capabilities

### `Simple_Tracker`

- Multi ROI tracking
- Linear interpolation across frames
- Mean intensity measurement within circular ROIs
- Plot generation
- CSV export
- Session save/load

### `Simple_FRAP_analysis`

- FRAP analysis using a main ROI, with optional reference and background ROIs
- Background correction
- Double normalization
- Full-scale normalization
- Plot generation
- CSV export
- Session save/load

## Examples

### `Simple_Tracker`

![Simple Tracker demo](https://raw.githubusercontent.com/Aohirovet/Napari_Simple_Tracker/main/Simple_Tracker.gif)

### `Multiple_track`

![Multiple track demo](https://raw.githubusercontent.com/Aohirovet/Napari_Simple_Tracker/main/Multiple_track.gif)

### `Simple_FRAP_analysis`

![FRAP Analysis demo](https://raw.githubusercontent.com/Aohirovet/Napari_Simple_Tracker/main/FRAP_Analysis.gif)

## Installation

This package is published on PyPI as `napari-simple-tracker`.

### Install with pip

Install the plugin in an environment where `napari` is already installed:

```bash
python -m pip install napari-simple-tracker
```

### Install from napari

1. Launch napari.
2. Open `Plugins -> Install/Uninstall Plugins...`.
3. Use `Install by name/URL`.
4. Enter the package name `napari-simple-tracker` and install it.

### Install from source

To install the latest local version from this repository:

```bash
git clone https://github.com/Aohirovet/Napari_Simple_Tracker.git
cd Napari_Simple_Tracker
python -m pip install .
```

If you use a dedicated environment for napari, activate it before running the install command.

## Usage

After installation, open napari and launch either widget from:

`Plugins -> Napari Simple Tracker -> Simple_Tracker`

or

`Plugins -> Napari Simple Tracker -> Simple_FRAP_analysis`

## Quick Start

```text
Open image
  -> place Points
  -> open plugin
  -> run analysis
  -> inspect masks, plots, and CSV output
```

### `Simple_Tracker`

1. Load a time-series image in napari.
2. Create one `Points` layer for each object to be tracked.
3. Mark the object center across multiple frames.
4. Open `Plugins -> Napari Simple Tracker -> Simple_Tracker`.
5. Press `Run Simple Tracker`.

### `Simple_FRAP_analysis`

1. Load a time-series image in napari.
2. Create `Points` layers for the main ROI.
3. Create one `Points` layer for the reference ROI.
4. Optionally create one `Points` layer for the background ROI.
5. Open `Plugins -> Napari Simple Tracker -> Simple_FRAP_analysis`.
6. Select the relevant layers and ROI radii, then press `Run FRAP Analysis`.

## Documentation

Detailed usage notes, supported image dimensions, output columns, session behavior, and common errors are documented here:

- [Usage guide index](https://github.com/Aohirovet/Napari_Simple_Tracker/blob/main/docs/USAGE.md)
- [Simple Tracker guide](https://github.com/Aohirovet/Napari_Simple_Tracker/blob/main/docs/USAGE_SIMPLE_TRACKER.md)
- [FRAP Analysis guide](https://github.com/Aohirovet/Napari_Simple_Tracker/blob/main/docs/USAGE_FRAP.md)

## Release Note

For every new public release, increment the version in `pyproject.toml` before publishing to PyPI or expecting changes to appear on napari-hub.

## License

MIT License
