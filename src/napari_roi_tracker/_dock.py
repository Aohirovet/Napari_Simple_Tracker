from __future__ import annotations

import napari

from ._widgets import RoiTrackerPlugin

PLUGIN_INSTANCE_ATTRIBUTE = "_roi_tracker_plugin_instance"


def _get_current_viewer():
    viewer = napari.current_viewer()
    if viewer is None:
        raise RuntimeError("No active napari viewer found.")
    return viewer


def _get_plugin(viewer) -> RoiTrackerPlugin:
    plugin = getattr(viewer, PLUGIN_INSTANCE_ATTRIBUTE, None)
    if plugin is None:
        plugin = RoiTrackerPlugin(viewer)
        setattr(viewer, PLUGIN_INSTANCE_ATTRIBUTE, plugin)
    return plugin


def make_simple_tracker_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).simple_tracker_widget


def make_frap_analysis_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).frap_analysis_widget


def make_session_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).session_widget
