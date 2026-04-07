from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import napari
import numpy as np
import pandas as pd
from magicgui import magicgui
from magicgui.widgets import Container
from qtpy.QtWidgets import QFileDialog, QMessageBox
from skimage.draw import disk

from ._core import (
    get_frame_2d_from_image,
    remove_layer_if_exists,
    run_analysis_core,
    run_simple_tracker_core,
)
from ._state import SESSION_STATE


class RoiTrackerPlugin:
    def __init__(self, viewer: "napari.Viewer") -> None:
        self.viewer = viewer

        self.simple_tracker_widget = self._build_simple_tracker_system()
        self.frap_analysis_widget = self._build_frap_analysis_system()
        self.session_widget = self._build_session_system()

        self._connect_layer_events()
        self._refresh_and_reconnect()

    def _get_image_layer_choices(self, widget: Any | None = None) -> list[str]:
        return [l.name for l in self.viewer.layers if getattr(l, "_type_string", "") == "image"]

    def _get_points_layer_choices(self, widget: Any | None = None) -> list[str]:
        return [""] + [l.name for l in self.viewer.layers if getattr(l, "_type_string", "") == "points"]

    def _refresh_widget_choices(self, event: Any | None = None) -> None:
        image_choices = self._get_image_layer_choices()
        points_choices = self._get_points_layer_choices()

        for widget_name in ("_simple_run", "_frap_run"):
            widget = getattr(self, widget_name, None)
            if widget is None:
                continue
            try:
                current = widget.image_layer.value
                widget.image_layer.choices = image_choices
                if current in image_choices:
                    widget.image_layer.value = current
                elif len(image_choices) == 1:
                    widget.image_layer.value = image_choices[0]
            except Exception:
                pass

        try:
            current_bg = self._frap_run.bg_points_layer.value
            self._frap_run.bg_points_layer.choices = points_choices
            self._frap_run.bg_points_layer.value = current_bg if current_bg in points_choices else ""
        except Exception:
            pass

    def _connect_layer_name_events(self) -> None:
        for layer in self.viewer.layers:
            if getattr(layer, "_type_string", "") in {"image", "points"}:
                try:
                    layer.events.name.disconnect(self._refresh_widget_choices)
                except Exception:
                    pass
                try:
                    layer.events.name.connect(self._refresh_widget_choices)
                except Exception:
                    pass

    def _refresh_and_reconnect(self, event: Any | None = None) -> None:
        self._connect_layer_name_events()
        self._refresh_widget_choices()

    def _connect_layer_events(self) -> None:
        for event_name in ("inserted", "removed", "reordered"):
            try:
                getattr(self.viewer.layers.events, event_name).connect(self._refresh_and_reconnect)
            except Exception:
                pass

    def _disconnect_old_mask_callback(self) -> None:
        old_callback = SESSION_STATE.mask_callback
        if old_callback is not None:
            try:
                self.viewer.dims.events.current_step.disconnect(old_callback)
            except Exception:
                pass
        SESSION_STATE.mask_callback = None

    def _connect_mask_callback(
        self,
        roi_tracks: list[tuple[Any, Any, Any, Any, int]],
        bg_track: tuple[Any, Any, Any, Any, int] | None,
    ) -> None:
        self._disconnect_old_mask_callback()

        def update_all_masks(event: Any | None = None) -> None:
            current_t = int(self.viewer.dims.current_step[0])
            for mask_layer, t_range, ys, xs, radius in roi_tracks:
                new_mask = np.zeros_like(mask_layer.data, dtype=np.uint8)
                t_range_np = np.asarray(t_range, dtype=int)
                ys_np = np.asarray(ys, dtype=float)
                xs_np = np.asarray(xs, dtype=float)
                if current_t in t_range_np:
                    idx = np.where(t_range_np == current_t)[0][0]
                    rr, cc = disk((int(round(float(ys_np[idx]))), int(round(float(xs_np[idx])))), int(radius), shape=new_mask.shape)
                    new_mask[rr, cc] = 255
                mask_layer.data = new_mask

            if bg_track is not None:
                bg_mask_layer, bg_t_range, bg_ys, bg_xs, bg_radius = bg_track
                new_bg_mask = np.zeros_like(bg_mask_layer.data, dtype=np.uint8)
                bg_t_range_np = np.asarray(bg_t_range, dtype=int)
                bg_ys_np = np.asarray(bg_ys, dtype=float)
                bg_xs_np = np.asarray(bg_xs, dtype=float)
                if current_t in bg_t_range_np:
                    idx = np.where(bg_t_range_np == current_t)[0][0]
                    rr, cc = disk((int(round(float(bg_ys_np[idx]))), int(round(float(bg_xs_np[idx])))), int(bg_radius), shape=new_bg_mask.shape)
                    new_bg_mask[rr, cc] = 255
                bg_mask_layer.data = new_bg_mask

        self.viewer.dims.events.current_step.connect(update_all_masks)
        SESSION_STATE.mask_callback = update_all_masks
        update_all_masks()

    @staticmethod
    def _plot_result_df(df: pd.DataFrame, title_prefix: str, ycol: str) -> None:
        if ycol not in df.columns:
            raise ValueError(f"Column '{ycol}' was not found in the result table.")
        cmap = plt.get_cmap("tab10")
        fig, ax = plt.subplots(figsize=(7, 4))
        for i, (tid, df_plot) in enumerate(df.groupby("track_id")):
            ax.plot(df_plot["frame"], df_plot[ycol], color=cmap(i % 10), lw=2, label=f"Track {tid}")
        ax.set_xlabel("Frame", fontsize=12, fontweight="bold")
        ax.set_ylabel(ycol, fontsize=12, fontweight="bold")
        ax.set_title(title_prefix, fontsize=14, fontweight="bold")
        ax.grid(True, ls="--", alpha=0.5)
        ax.legend(frameon=False)
        plt.tight_layout()
        plt.show()

    def _store_session(
        self,
        mode: str,
        df: pd.DataFrame,
        meta: dict[str, Any],
        track_sources: list[dict[str, Any]],
        bg_source: dict[str, Any] | None,
        roi_tracks: list[tuple[Any, Any, Any, Any, int]],
        bg_track: tuple[Any, Any, Any, Any, int] | None,
    ) -> None:
        SESSION_STATE.mode = mode
        SESSION_STATE.result_df = df.copy()
        SESSION_STATE.meta = dict(meta)
        SESSION_STATE.track_sources = list(track_sources)
        SESSION_STATE.bg_source = bg_source
        SESSION_STATE.roi_tracks = list(roi_tracks)
        SESSION_STATE.bg_track = bg_track

    def _save_result_csv(self) -> None:
        df = SESSION_STATE.result_df
        if df is None or df.empty:
            QMessageBox.warning(None, "Error", "No result table is available. Run an analysis first.")
            return
        path, _ = QFileDialog.getSaveFileName(caption="Save results as CSV", filter="CSV files (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        df.to_csv(path, index=False)
        QMessageBox.information(None, "Saved", f"Result table saved to:\n{path}")

    def _save_session_json(self) -> None:
        df = SESSION_STATE.result_df
        if df is None or df.empty:
            QMessageBox.warning(None, "Error", "No result table is available. Run an analysis first.")
            return
        payload = {
            "session_type": "napari_simple_tracker_and_frap_session_v1",
            "mode": SESSION_STATE.mode,
            "meta": SESSION_STATE.meta,
            "track_sources": SESSION_STATE.track_sources,
            "bg_source": SESSION_STATE.bg_source,
            "result_table": df.to_dict(orient="records"),
        }
        path, _ = QFileDialog.getSaveFileName(caption="Save session", filter="JSON files (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        QMessageBox.information(None, "Saved", f"Session saved to:\n{path}")

    def _restore_session(self) -> None:
        path, _ = QFileDialog.getOpenFileName(caption="Load session", filter="JSON files (*.json)")
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if payload.get("session_type") != "napari_simple_tracker_and_frap_session_v1":
                raise ValueError("Unsupported session format.")
            mode = payload.get("mode", "")
            meta = payload.get("meta", {})
            track_sources = payload.get("track_sources", [])
            bg_source = payload.get("bg_source", None)
            result_table = payload.get("result_table", [])
            if mode not in {"simple_tracker", "frap_analysis"}:
                raise ValueError("Session mode is missing or invalid.")
            if not meta:
                raise ValueError("Session meta data is missing.")

            image_layer_name = meta.get("image_layer", "")
            image_layer_names = self._get_image_layer_choices()
            if image_layer_name not in image_layer_names:
                if len(image_layer_names) == 1:
                    image_layer_name = image_layer_names[0]
                    meta["image_layer"] = image_layer_name
                else:
                    raise ValueError(
                        f"The session expects image layer '{meta.get('image_layer', '')}', but it is not available in the current viewer."
                    )

            self._disconnect_old_mask_callback()
            if bg_source is not None:
                remove_layer_if_exists(self.viewer, bg_source["layer_name"])
                remove_layer_if_exists(self.viewer, f"BG_mask_{bg_source['layer_name']}")
            for ts in track_sources:
                remove_layer_if_exists(self.viewer, ts["layer_name"])
                remove_layer_if_exists(self.viewer, f"TRACK_mask_{ts['layer_name']}")
                remove_layer_if_exists(self.viewer, f"ROI_mask_{ts['layer_name']}")
                if "ref_layer_name" in ts:
                    remove_layer_if_exists(self.viewer, ts["ref_layer_name"])
                    remove_layer_if_exists(self.viewer, f"REF_mask_{ts['ref_layer_name']}")

            for ts in track_sources:
                layer_main = self.viewer.add_points(np.array(ts["points_data"] if mode == "simple_tracker" else ts["main_points_data"], dtype=float), name=ts["layer_name"], size=10, face_color="yellow")
                try:
                    layer_main.edge_color = "black"
                except Exception:
                    pass
                if mode == "frap_analysis":
                    layer_ref = self.viewer.add_points(np.array(ts["ref_points_data"], dtype=float), name=ts["ref_layer_name"], size=10, face_color="cyan")
                    try:
                        layer_ref.edge_color = "black"
                    except Exception:
                        pass
            if bg_source is not None:
                bg_layer = self.viewer.add_points(np.array(bg_source["points_data"], dtype=float), name=bg_source["layer_name"], size=10, face_color="magenta")
                try:
                    bg_layer.edge_color = "black"
                except Exception:
                    pass

            self._refresh_and_reconnect()

            img_layer = self.viewer.layers[image_layer_name]
            image = np.asarray(img_layer.data)
            frame0 = get_frame_2d_from_image(image, 0)
            roi_tracks = []
            bg_track = None

            if mode == "simple_tracker":
                roi_radius = int(meta.get("roi_radius", 5))
                for ts in track_sources:
                    mask_layer = self.viewer.add_image(np.zeros_like(frame0, dtype=np.uint8), name=f"TRACK_mask_{ts['layer_name']}", blending="additive", colormap="cyan", opacity=0.6, visible=True)
                    roi_tracks.append((mask_layer, np.array(ts["t_range"], dtype=int), np.array(ts["ys_interp"], dtype=float), np.array(ts["xs_interp"], dtype=float), roi_radius))
            else:
                main_radius = int(meta.get("main_radius", 5))
                ref_radius = int(meta.get("ref_radius", 5))
                bg_radius = int(meta.get("bg_radius", 5))
                for ts in track_sources:
                    main_mask_layer = self.viewer.add_image(np.zeros_like(frame0, dtype=np.uint8), name=f"ROI_mask_{ts['layer_name']}", blending="additive", colormap="cyan", opacity=0.6, visible=True)
                    roi_tracks.append((main_mask_layer, np.array(ts["common_frames"], dtype=int), np.array(ts["common_main_y"], dtype=float), np.array(ts["common_main_x"], dtype=float), main_radius))
                    ref_mask_layer = self.viewer.add_image(np.zeros_like(frame0, dtype=np.uint8), name=f"REF_mask_{ts['ref_layer_name']}", blending="additive", colormap="yellow", opacity=0.6, visible=True)
                    roi_tracks.append((ref_mask_layer, np.array(ts["common_frames"], dtype=int), np.array(ts["common_ref_y"], dtype=float), np.array(ts["common_ref_x"], dtype=float), ref_radius))
                if bg_source is not None:
                    bg_mask_layer = self.viewer.add_image(np.zeros_like(frame0, dtype=np.uint8), name=f"BG_mask_{bg_source['layer_name']}", blending="additive", colormap="magenta", opacity=0.6, visible=True)
                    bg_track = (bg_mask_layer, np.array(bg_source["t_range"], dtype=int), np.array(bg_source["ys_interp"], dtype=float), np.array(bg_source["xs_interp"], dtype=float), bg_radius)

            self._connect_mask_callback(roi_tracks, bg_track)
            df = pd.DataFrame(result_table) if result_table else None
            if df is None or df.empty:
                raise ValueError("Result table is missing in the session file.")
            self._store_session(mode=mode, df=df, meta=meta, track_sources=track_sources, bg_source=bg_source, roi_tracks=roi_tracks, bg_track=bg_track)
            plot_col = "raw_intensity" if mode == "simple_tracker" else "raw_main_intensity"
            self._plot_result_df(df, title_prefix=f"Restored {mode.replace('_', ' ').title()}", ycol=plot_col)
            QMessageBox.information(None, "Loaded", f"Session restored successfully in mode: {mode}.")
        except Exception as e:
            QMessageBox.warning(None, "Load failed", str(e))

    def _build_simple_tracker_system(self):
        @magicgui(
            call_button="Run Simple Tracker",
            image_layer={"label": "Image layer", "choices": self._get_image_layer_choices},
            roi_radius={"label": "ROI radius (px)", "min": 1, "max": 100, "step": 1, "value": 5},
        )
        def simple_run(image_layer: str, roi_radius: int = 5) -> None:
            if not image_layer:
                QMessageBox.warning(None, "Error", "Select an image layer.")
                return
            try:
                result, meta, track_sources, roi_tracks = run_simple_tracker_core(
                    viewer=self.viewer,
                    image_layer_name=image_layer,
                    roi_radius=roi_radius,
                )
                self._connect_mask_callback(roi_tracks, None)
                self._store_session(
                    mode="simple_tracker",
                    df=result,
                    meta=meta,
                    track_sources=track_sources,
                    bg_source=None,
                    roi_tracks=roi_tracks,
                    bg_track=None,
                )
                self._plot_result_df(result, title_prefix="Simple Tracker Raw Intensity", ycol="raw_intensity")
                QMessageBox.information(None, "Done", "Simple tracking completed.")
            except Exception as e:
                QMessageBox.warning(None, "Simple Tracker failed", str(e))

        @magicgui(call_button="Plot Raw Intensity")
        def simple_plot() -> None:
            df = SESSION_STATE.result_df
            if SESSION_STATE.mode != "simple_tracker" or df is None or df.empty:
                QMessageBox.warning(None, "Error", "No simple tracking result is available.")
                return
            self._plot_result_df(df, title_prefix="Simple Tracker Raw Intensity", ycol="raw_intensity")

        @magicgui(call_button="Save Result CSV")
        def simple_save_csv() -> None:
            if SESSION_STATE.mode != "simple_tracker":
                QMessageBox.warning(None, "Error", "Run Simple Tracker before saving CSV.")
                return
            self._save_result_csv()

        self._simple_run = simple_run
        return Container(widgets=[simple_run, simple_plot, simple_save_csv], labels=False)

    def _build_frap_analysis_system(self):
        @magicgui(
            call_button="Run FRAP Analysis",
            image_layer={"label": "Image layer", "choices": self._get_image_layer_choices},
            main_radius={"label": "Main ROI radius (px)", "min": 1, "max": 100, "step": 1, "value": 5},
            ref_radius={"label": "Reference ROI radius (px)", "min": 1, "max": 100, "step": 1, "value": 5},
            bg_radius={"label": "Background ROI radius (px)", "min": 1, "max": 100, "step": 1, "value": 5},
            bg_points_layer={"label": "Background points layer", "choices": self._get_points_layer_choices},
            reference_prefix={"label": "Reference prefix", "value": "Ref_"},
            bleach_frame={"label": "Bleach start frame", "min": 0, "step": 1, "value": 5},
        )
        def frap_run(
            image_layer: str,
            main_radius: int = 5,
            ref_radius: int = 5,
            bg_radius: int = 5,
            bg_points_layer: str = "",
            reference_prefix: str = "Ref_",
            bleach_frame: int = 5,
        ) -> None:
            if not image_layer:
                QMessageBox.warning(None, "Error", "Select an image layer.")
                return
            try:
                result, meta, track_sources, bg_source, roi_tracks, bg_track = run_analysis_core(
                    viewer=self.viewer,
                    image_layer_name=image_layer,
                    main_radius=main_radius,
                    ref_radius=ref_radius,
                    bg_radius=bg_radius,
                    bg_points_layer_name=bg_points_layer,
                    reference_prefix=reference_prefix,
                    bleach_frame=bleach_frame,
                )
                self._connect_mask_callback(roi_tracks, bg_track)
                self._store_session(
                    mode="frap_analysis",
                    df=result,
                    meta=meta,
                    track_sources=track_sources,
                    bg_source=bg_source,
                    roi_tracks=roi_tracks,
                    bg_track=bg_track,
                )
                self._plot_result_df(result, title_prefix="FRAP Raw Main Intensity", ycol="raw_main_intensity")
                QMessageBox.information(None, "Done", "FRAP analysis completed.")
            except Exception as e:
                QMessageBox.warning(None, "FRAP Analysis failed", str(e))

        @magicgui(call_button="Plot Raw")
        def frap_plot_raw() -> None:
            df = SESSION_STATE.result_df
            if SESSION_STATE.mode != "frap_analysis" or df is None or df.empty:
                QMessageBox.warning(None, "Error", "No FRAP result is available.")
                return
            self._plot_result_df(df, title_prefix="FRAP Raw Main Intensity", ycol="raw_main_intensity")

        @magicgui(call_button="Plot Double Norm")
        def frap_plot_double() -> None:
            df = SESSION_STATE.result_df
            if SESSION_STATE.mode != "frap_analysis" or df is None or df.empty:
                QMessageBox.warning(None, "Error", "No FRAP result is available.")
                return
            self._plot_result_df(df, title_prefix="Double Normalization", ycol="double_norm")

        @magicgui(call_button="Plot Full Scale")
        def frap_plot_full() -> None:
            df = SESSION_STATE.result_df
            if SESSION_STATE.mode != "frap_analysis" or df is None or df.empty:
                QMessageBox.warning(None, "Error", "No FRAP result is available.")
                return
            self._plot_result_df(df, title_prefix="Full-Scale Normalization", ycol="full_scale_norm")

        @magicgui(call_button="Difference Plot", ref_track_id={"label": "Reference track ID", "min": 1, "step": 1, "value": 1})
        def frap_difference(ref_track_id: int = 1) -> None:
            df = SESSION_STATE.result_df
            if SESSION_STATE.mode != "frap_analysis" or df is None or df.empty:
                QMessageBox.warning(None, "Error", "No FRAP result is available.")
                return
            if ref_track_id not in df["track_id"].unique():
                QMessageBox.warning(None, "Error", f"Track ID {ref_track_id} does not exist.")
                return
            ref_df = df[df["track_id"] == ref_track_id][["frame", "full_scale_norm"]].copy().rename(columns={"full_scale_norm": "ref_intensity"})
            cmap = plt.get_cmap("tab10")
            fig, ax = plt.subplots(figsize=(7, 4))
            for i, (tid, dsub) in enumerate(df.groupby("track_id")):
                if tid == ref_track_id:
                    continue
                merged = pd.merge(dsub[["frame", "full_scale_norm"]], ref_df, on="frame", how="inner")
                merged["delta"] = merged["full_scale_norm"] - merged["ref_intensity"]
                ax.plot(merged["frame"], merged["delta"], color=cmap(i % 10), lw=2, label=f"Track {tid} - Track {ref_track_id}")
            ax.axhline(0, color="gray", lw=1, ls="--")
            ax.set_xlabel("Frame", fontsize=12, fontweight="bold")
            ax.set_ylabel("Δ Full Scale", fontsize=12, fontweight="bold")
            ax.set_title(f"Difference vs Track {ref_track_id}", fontsize=14, fontweight="bold")
            ax.grid(True, ls="--", alpha=0.5)
            ax.legend(frameon=False)
            plt.tight_layout()
            plt.show()

        @magicgui(call_button="Save Result CSV")
        def frap_save_csv() -> None:
            if SESSION_STATE.mode != "frap_analysis":
                QMessageBox.warning(None, "Error", "Run FRAP Analysis before saving CSV.")
                return
            self._save_result_csv()

        self._frap_run = frap_run
        return Container(
            widgets=[frap_run, frap_plot_raw, frap_plot_double, frap_plot_full, frap_difference, frap_save_csv],
            labels=False,
        )

    def _build_session_system(self):
        @magicgui(call_button="Save Session")
        def save_session_widget() -> None:
            self._save_session_json()

        @magicgui(call_button="Load Session")
        def load_session_widget() -> None:
            self._restore_session()

        return Container(widgets=[save_session_widget, load_session_widget], labels=False)
