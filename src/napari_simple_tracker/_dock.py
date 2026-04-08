from __future__ import annotations

import weakref

import napari

from ._widgets import RoiTrackerPlugin

_PLUGIN_INSTANCES: dict[int, tuple[weakref.ReferenceType[object], RoiTrackerPlugin]] = {}


def _get_current_viewer():
    viewer = napari.current_viewer()
    if viewer is None:
        raise RuntimeError("No active napari viewer found.")
    return viewer


def _get_plugin(viewer) -> RoiTrackerPlugin:
    viewer_id = id(viewer)
    cached = _PLUGIN_INSTANCES.get(viewer_id)
    if cached is not None:
        cached_viewer_ref, plugin = cached
        if cached_viewer_ref() is viewer:
            return plugin

    plugin = RoiTrackerPlugin(viewer)

    def _cleanup(_ref) -> None:
        _PLUGIN_INSTANCES.pop(viewer_id, None)

    _PLUGIN_INSTANCES[viewer_id] = (weakref.ref(viewer, _cleanup), plugin)
    return plugin


def make_simple_tracker_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).simple_tracker_widget


def make_frap_analysis_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).frap_analysis_widget
