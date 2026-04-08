# Napari_Simple_Tracker

`Napari_Simple_Tracker` is a lightweight and user-friendly napari plugin for ROI tracking and FRAP analysis in time-lapse image data.  
It is designed to remain intentionally simple while providing the core functionality typically required for routine quantitative analysis.

- Simple: point-based interaction with minimal configuration
- Practical: tracking, intensity plotting, CSV export, and session save/load are included
- Readable: ROI masks and track IDs are displayed directly in the napari viewer

## Capabilities

### `Simple_Tracker`

- Multi-track ROI tracking
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

## Installation

### Install from napari

1. Launch napari.
2. Open `Plugins -> Install/Uninstall Plugins...`.
3. Search for `napari-simple-tracker` and install it.

This plugin assumes that `napari` is already installed in the environment where you use it.

If you use `Install by name/URL`, enter the package name `napari-simple-tracker`.

### Install from a cloned repository

If you already have a napari environment, you can install the plugin from a local clone:

```bash
git clone https://github.com/Aohirovet/Napari_Simple_Tracker.git
cd Napari_Simple_Tracker
python -m pip install .
```

If you are using a dedicated environment for napari, activate that environment before running `python -m pip install .`.

## Quick Start

```text
Open image
  -> place Points
  -> open plugin
  -> run analysis
  -> inspect masks, plots, and CSV output
```

### Simple Tracker

1. Load a time-series image in napari.
2. Create one `Points` layer for each object to be tracked.
3. Mark the object center across multiple frames.
4. Open `Plugins -> Napari Simple Tracker -> Simple_Tracker`.
5. Press `Run Simple Tracker`.

### FRAP Analysis

1. Load a time-series image in napari.
2. Create `Points` layers for the main ROI.
3. Create one `Points` layer for the reference ROI.
4. Optionally create one `Points` layer for the background ROI.
5. Open `Plugins -> Napari Simple Tracker -> Simple_FRAP_analysis`.
6. Select the relevant layers and ROI radii, then press `Run FRAP Analysis`.

## Documentation

More detailed usage notes, supported image dimensions, output columns, session behavior, and common errors are documented here:

- [Usage guide index](docs/USAGE.md)
- [Simple Tracker guide](docs/USAGE_SIMPLE_TRACKER.md)
- [FRAP Analysis guide](docs/USAGE_FRAP.md)

## License

MIT License
