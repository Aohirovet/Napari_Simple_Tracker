# FRAP Analysis Guide

This document describes how to use `Simple_FRAP_analysis` in `napari-roi-tracker`.

## When to Use It

Use `Simple_FRAP_analysis` when you want to analyze FRAP recovery in a main ROI, with optional correction based on a reference ROI and an optional background ROI.

## What It Does

- Runs FRAP analysis with main, reference, and optional background ROIs
- Linearly interpolates coordinates between annotated frames
- Applies background correction
- Computes double normalization
- Computes full-scale normalization
- Displays ROI masks in the napari viewer
- Optionally shows track IDs
- Plots raw, double-normalized, and full-scale-normalized signals
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
- Main, reference, and background roles are assigned from widget selections, not layer-name prefixes.
- Each track must contain points from at least two different frames.
- A single `Points` layer cannot contain multiple points in the same frame.
- `Points` layers must have the same dimensionality as the selected image layer.
- Points outside the image bounds will raise an error.
- After running the analysis, ROI masks follow the currently displayed frame.
- If `Show Track IDs` is enabled, the current frame shows the track number next to each ROI.

## Creating `Points` Layers

1. Load a time-series image into napari.
2. Add `Points` layers for the ROIs you want to analyze.
3. Move through the time slider and click the center of each ROI in the frames you want to annotate.
4. Add points for the same ROI across multiple frames.

Rules:

- One layer = one track
- One frame = at most one point
- At least two annotated frames are required

## Required Layers

- Main ROI `Points` layers: one or more layers
- Reference ROI `Points` layer: optional
- Background ROI `Points` layer: optional

In the current implementation:

- The layer selected in `Reference layer`, if any, is used as the reference ROI.
- The layer selected in `Background points layer`, if any, is used as the background ROI.
- All other `Points` layers are treated as main ROIs.

Recommended naming:

- Main: `Cell_1`, `Cell_2`
- Reference: `Ref`
- Background: `BG`

## Widget Settings

- `Image layer`: image to analyze
- `Main ROI radius (px)`: ROI radius for the main signal
- `Ref radius (px)`: ROI radius for the reference signal
- `Background ROI radius (px)`: ROI radius for the background signal
- `Background points layer`: optional background layer
- `Reference layer`: optional reference layer
- `Bleach start frame`: first frame treated as post-bleach

## Steps

1. Open `Simple_FRAP_analysis`.
2. Select `Image layer`.
3. Optionally select `Reference layer`.
4. Optionally select `Background points layer`.
5. Set the ROI radii.
6. Set `Bleach start frame`.
7. Click `Run FRAP Analysis`.

## Run Results

- Main ROIs are interpolated across frames.
- Reference ROIs are interpolated if provided.
- Background ROI is also interpolated if provided.
- Intensities are measured on shared frames.
- Background correction is applied.
- Double normalization is computed.
- Full-scale normalization is computed.
- Mask layers are added: `ROI_mask_<main_name>`, `REF_mask_<main_name>__<reference_name>`, and `BG_mask_<background_name>`
- A raw main intensity plot is shown.

## Normalization Workflow

The implementation computes FRAP values in this order:

1. `main_bg_corrected = raw_main_intensity - bg_intensity`
2. `ref_bg_corrected = raw_ref_intensity - bg_intensity` when a reference ROI is provided
3. `double_norm` is calculated using the mean intensity of pre-bleach frames
4. `full_scale_norm` is calculated using the first post-bleach `double_norm` value

If no reference ROI is selected, `double_norm` falls back to normalization by the pre-bleach mean of the main ROI only.

Frames before `Bleach start frame` are treated as pre-bleach, and frames from that index onward are treated as post-bleach.
Both groups must exist or the analysis will fail.

## CSV and Graph Outputs

The exported CSV includes these columns, and raw, double-normalized, and full-scale-normalized graphs are available from the widget:

- `track_id`
- `track_name`
- `ref_track_name`
- `frame`
- `main_y`
- `main_x`
- `ref_y`
- `ref_x`
- `raw_main_intensity`
- `raw_ref_intensity`
- `bg_intensity`
- `main_bg_corrected`
- `ref_bg_corrected`
- `double_norm`
- `full_scale_norm`
- `main_pre_mean`
- `ref_pre_mean`
- `double_norm_post0`

## Buttons

- `Run FRAP Analysis`: run the analysis
- `Show Track IDs`: toggle track labels in the viewer
- `Plot Raw`: show the raw main intensity plot
- `Plot Double Norm`: show the double-normalized plot
- `Plot Full Scale`: show the full-scale-normalized plot
- `Save Result CSV`: export the result table as CSV
- `Save Session`: save results and track data as JSON
- `Load Session`: restore a saved session

## Saving and Loading Sessions

After the widget finishes, you can use `Save Session` to export the current session as JSON.

Saved data includes:

- Analysis mode
- Widget settings
- Source `Points` data
- Background-layer information
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

### `has no pre-bleach frames` / `has no post-bleach frames`

`Bleach start frame` is not set appropriately.
Choose a frame index that leaves at least one frame before and after bleaching.
