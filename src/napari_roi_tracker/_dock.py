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


def make_run_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).run_multi_roi_analysis


def make_save_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).save_results


def make_raw_plot_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).plot_raw_main


def make_double_plot_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).plot_double_norm


def make_full_scale_plot_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).plot_full_scale


def make_difference_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).make_difference_plot


def make_save_session_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).save_complete_session


def make_load_session_widget():
    viewer = _get_current_viewer()
    return _get_plugin(viewer).load_complete_session