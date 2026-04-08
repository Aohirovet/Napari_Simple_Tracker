# Simple Tracker Guide

This document describes how to use `Simple_Tracker` in `napari-simple-tracker`.

## When to Use It

Use `Simple_Tracker` when you want to follow the position of cells, particles, or other objects over time and measure the mean intensity inside a circular ROI centered on each tracked position.

## What It Does

- Tracks multiple `Points` layers
- Linearly interpolates coordinates between annotated frames
- Measures mean intensity in a circular ROI for each frame
- Displays ROI masks in the napari viewer
- Optionally shows track IDs
- Plots raw intensity
- Exports results as CSV
- Saves and loads sessions as JSON

## Supported Image Shapes

The plugin assumes time-lapse image layers with one of these shapes:

- 3D: `T, Y, X`
- 4D: `T, C, Y, X`
- 5D: `T, Z, C, Y, X`

The current implementation extracts a 2D image from each time point as follows:

- 3D: `image[t, :, :]`
- 4D: `image[t, 0, :, :]`
- 5D: `image[t, 0, 0, :, :]`

For 4D and 5D data, only the first channel and first z-plane are used.

## Important Rules Before You Start

- The analysis is performed on `Points` layers.
- One `Points` layer is treated as one track.
- Each track must contain points from at least two different frames.
- A single `Points` layer cannot contain multiple points in the same frame.
- `Points` layers must have the same dimensionality as the selected image layer.
- Points outside the image bounds will raise an error.
- After running the analysis, ROI masks follow the currently displayed frame.
- If `Show Track IDs` is enabled, the current frame shows the track number next to each ROI.

## Creating `Points` Layers

1. Load a time-series image into napari.
2. Add a `Points` layer.
3. Move through the time slider and click the center of the object in each frame you want to annotate.
4. Add points for the same object across multiple frames.

Rules:

- One layer = one track
- One frame = at most one point
- At least two annotated frames are required

## Preparation

- Prepare one image layer for analysis.
- Create one `Points` layer for each object you want to track.

Example layer names:

- `Cell_1`
- `Cell_2`
- `Cell_3`

## Widget Settings

- `Image layer`: image to analyze
- `ROI radius (px)`: radius of the circular ROI used for intensity measurement

## Steps

1. Open `Simple_Tracker`.
2. Select `Image layer`.
3. Set `ROI radius (px)`.
4. Click `Run Simple Tracker`.

## Run Results

- One track is created for each `Points` layer.
- Missing frames are filled by linear interpolation.
- A mask layer named `Track_<original_points_name>` is added for each track.
- A raw intensity plot is shown.
- The result table is stored in the current session.

## CSV and Graph Outputs

The exported CSV includes these columns, and a raw intensity graph is also available from the widget:

- `track_id`
- `track_name`
- `frame`
- `y`
- `x`
- `raw_intensity`

## Buttons

- `Run Simple Tracker`: run the analysis
- `Show Track IDs`: toggle track labels in the viewer
- `Plot Raw Intensity`: show the raw intensity plot again
- `Save Result CSV`: export the result table as CSV
- `Save Session`: save results and track data as JSON
- `Load Session`: restore a saved session

## Saving and Loading Sessions

After the widget finishes, you can use `Save Session` to export the current session as JSON.

Saved data includes:

- Analysis mode
- Widget settings
- Source `Points` data
- Track ID display state
- Result table

`Load Session` restores:

- `Points` layers
- ROI mask layers
- Track ID display state
- Result table
- Result plots

Notes:

- Image data itself is not stored in the session file.
- The image layer used when saving must be present in the current viewer.
- If the current viewer contains only one image layer, the session is automatically reconnected to that layer.

## Common Errors

### `contains only one point`

The layer contains only one annotated point.
Add points in at least two different frames.

### `contains multiple points on the same time frame`

The layer contains more than one point in the same frame.
Keep only one point per frame in each layer.

### `does not match the selected image layer dimensions`

The `Points` layer was likely created on data with different dimensions.
Recreate the points on the same image layer used for analysis.

### `contains points outside the selected image layer bounds`

One or more points are outside the image area.
Move the points so they fall inside the image bounds.
