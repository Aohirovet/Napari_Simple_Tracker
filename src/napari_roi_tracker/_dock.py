from __future__ import annotations

import napari

from ._widgets import RoiTrackerPlugin


PLUGIN_INSTANCE_ATTRIBUTE = "_roi_tracker_plugin_instance"


def napari_experimental_provide_dock_widget():
    return [
        (make_run_widget, {"name": "ROI Tracker: 解析実行"}),
        (make_save_widget, {"name": "ROI Tracker: 結果を保存"}),
        (make_raw_plot_widget, {"name": "ROI Tracker: Raw グラフ"}),
        (make_double_plot_widget, {"name": "ROI Tracker: Double Norm グラフ"}),
        (make_full_scale_plot_widget, {"name": "ROI Tracker: Full Scale グラフ"}),
        (make_difference_widget, {"name": "ROI Tracker: 差分グラフ作成"}),
        (make_save_session_widget, {"name": "ROI Tracker: 完全復元セッション保存"}),
        (make_load_session_widget, {"name": "ROI Tracker: 完全復元セッション読込"}),
    ]


def _get_plugin(viewer: "napari.Viewer") -> RoiTrackerPlugin:
    plugin = getattr(viewer, PLUGIN_INSTANCE_ATTRIBUTE, None)
    if plugin is None:
        plugin = RoiTrackerPlugin(viewer)
        setattr(viewer, PLUGIN_INSTANCE_ATTRIBUTE, plugin)
    return plugin


def make_run_widget(viewer: "napari.Viewer"):
    return _get_plugin(viewer).run_multi_roi_analysis


def make_save_widget(viewer: "napari.Viewer"):
    return _get_plugin(viewer).save_results


def make_raw_plot_widget(viewer: "napari.Viewer"):
    return _get_plugin(viewer).plot_raw_main


def make_double_plot_widget(viewer: "napari.Viewer"):
    return _get_plugin(viewer).plot_double_norm


def make_full_scale_plot_widget(viewer: "napari.Viewer"):
    return _get_plugin(viewer).plot_full_scale


def make_difference_widget(viewer: "napari.Viewer"):
    return _get_plugin(viewer).make_difference_plot


def make_save_session_widget(viewer: "napari.Viewer"):
    return _get_plugin(viewer).save_complete_session


def make_load_session_widget(viewer: "napari.Viewer"):
    return _get_plugin(viewer).load_complete_session
