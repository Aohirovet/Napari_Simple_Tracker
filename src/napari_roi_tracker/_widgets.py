from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import napari
import numpy as np
import pandas as pd
from magicgui import magicgui
from qtpy.QtWidgets import QFileDialog, QMessageBox

from ._core import (
    get_frame_2d_from_image,
    run_analysis_core,
    remove_layer_if_exists,
)
from ._state import SESSION_STATE


class RoiTrackerPlugin:
    def __init__(self, viewer: "napari.Viewer") -> None:
        self.viewer = viewer
        self.run_multi_roi_analysis = self._build_run_widget()
        self.save_results = self._build_save_results_widget()
        self.plot_raw_main = self._build_plot_raw_widget()
        self.plot_double_norm = self._build_plot_double_widget()
        self.plot_full_scale = self._build_plot_full_scale_widget()
        self.make_difference_plot = self._build_difference_widget()
        self.save_complete_session = self._build_save_session_widget()
        self.load_complete_session = self._build_load_session_widget()
        self._connect_layer_events()
        self._refresh_and_reconnect()

    def widget_list(self) -> list[Any]:
        return [
            self.run_multi_roi_analysis,
            self.save_results,
            self.plot_raw_main,
            self.plot_double_norm,
            self.plot_full_scale,
            self.make_difference_plot,
            self.save_complete_session,
            self.load_complete_session,
        ]

    def _get_image_layer_choices(self, widget: Any | None = None) -> list[str]:
        return [l.name for l in self.viewer.layers if getattr(l, "_type_string", "") == "image"]

    def _get_points_layer_choices(self, widget: Any | None = None) -> list[str]:
        return [""] + [l.name for l in self.viewer.layers if getattr(l, "_type_string", "") == "points"]

    def _refresh_image_layer_choices(self, event: Any | None = None) -> None:
        choices = self._get_image_layer_choices()
        try:
            current_value = self.run_multi_roi_analysis.image_layer.value
            self.run_multi_roi_analysis.image_layer.choices = choices
            if current_value in choices:
                self.run_multi_roi_analysis.image_layer.value = current_value
            elif len(choices) == 1:
                self.run_multi_roi_analysis.image_layer.value = choices[0]
        except Exception:
            pass

    def _refresh_points_layer_choices(self, event: Any | None = None) -> None:
        choices = self._get_points_layer_choices()
        try:
            current_bg = self.run_multi_roi_analysis.bg_points_layer.value
            self.run_multi_roi_analysis.bg_points_layer.choices = choices
            self.run_multi_roi_analysis.bg_points_layer.value = current_bg if current_bg in choices else ""
        except Exception:
            pass

    def _connect_layer_name_events(self) -> None:
        for layer in self.viewer.layers:
            if getattr(layer, "_type_string", "") in {"image", "points"}:
                callback = self._refresh_image_layer_choices if layer._type_string == "image" else self._refresh_points_layer_choices
                try:
                    layer.events.name.disconnect(callback)
                except Exception:
                    pass
                try:
                    layer.events.name.connect(callback)
                except Exception:
                    pass

    def _refresh_and_reconnect(self, event: Any | None = None) -> None:
        self._connect_layer_name_events()
        self._refresh_image_layer_choices()
        self._refresh_points_layer_choices()

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

    def _connect_mask_callback(self, roi_tracks: list[tuple[Any, Any, Any, Any, int]], bg_track: tuple[Any, Any, Any, Any, int] | None) -> None:
        self._disconnect_old_mask_callback()

        def update_all_masks(event: Any | None = None) -> None:
            current_t = int(self.viewer.dims.current_step[0])
            for mask_layer, t_range, ys, xs, radius in roi_tracks:
                new_mask = np.zeros_like(mask_layer.data, dtype=np.uint8)
                if current_t in t_range:
                    idx = np.where(t_range == current_t)[0][0]
                    rr, cc = __import__("skimage.draw", fromlist=["disk"]).disk(
                        (int(round(float(ys[idx]))), int(round(float(xs[idx])))), radius, shape=new_mask.shape
                    )
                    new_mask[rr, cc] = 255
                mask_layer.data = new_mask
            if bg_track is not None:
                bg_mask_layer, bg_t_range, bg_ys, bg_xs, bg_radius = bg_track
                new_bg_mask = np.zeros_like(bg_mask_layer.data, dtype=np.uint8)
                if current_t in bg_t_range:
                    idx = np.where(bg_t_range == current_t)[0][0]
                    rr, cc = __import__("skimage.draw", fromlist=["disk"]).disk(
                        (int(round(float(bg_ys[idx]))), int(round(float(bg_xs[idx])))), bg_radius, shape=new_bg_mask.shape
                    )
                    new_bg_mask[rr, cc] = 255
                bg_mask_layer.data = new_bg_mask

        self.viewer.dims.events.current_step.connect(update_all_masks)
        SESSION_STATE.mask_callback = update_all_masks
        update_all_masks()

    @staticmethod
    def _plot_result_df(df: pd.DataFrame, title_prefix: str = "FRAP Analysis", ycol: str = "full_scale_norm") -> None:
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

    def _build_run_widget(self):
        @magicgui(
            call_button="解析実行",
            image_layer={"label": "画像レイヤー選択", "choices": self._get_image_layer_choices},
            main_radius={"label": "Main ROI半径(px)", "min": 1, "max": 100, "step": 1, "value": 5},
            ref_radius={"label": "Ref ROI半径(px)", "min": 1, "max": 100, "step": 1, "value": 5},
            bg_radius={"label": "Background ROI半径(px)", "min": 1, "max": 100, "step": 1, "value": 5},
            bg_points_layer={"label": "Background Pointsレイヤー", "choices": self._get_points_layer_choices},
            reference_prefix={"label": "褪色参照ROI prefix", "value": "Ref_"},
            bleach_frame={"label": "ブリーチ開始frame", "min": 0, "step": 1, "value": 5},
        )
        def run_multi_roi_analysis(
            image_layer: str,
            main_radius: int = 5,
            ref_radius: int = 5,
            bg_radius: int = 5,
            bg_points_layer: str = "",
            reference_prefix: str = "Ref_",
            bleach_frame: int = 5,
        ) -> None:
            if not image_layer:
                QMessageBox.warning(None, "エラー", "画像レイヤーを選択してください。")
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
                self._plot_result_df(result, title_prefix="Raw Main Intensity", ycol="raw_main_intensity")
                SESSION_STATE.result_df = result.copy()
                SESSION_STATE.meta = meta
                SESSION_STATE.track_sources = track_sources
                SESSION_STATE.bg_source = bg_source
                SESSION_STATE.roi_tracks = roi_tracks
                SESSION_STATE.bg_track = bg_track
                QMessageBox.information(
                    None,
                    "完了",
                    "解析が完了しました。\n"
                    "表示中のグラフは生データです。\n"
                    "CSVには生データ・背景補正後・double normalization・full scale normalization をすべて保存します。",
                )
            except Exception as e:
                QMessageBox.warning(None, "解析失敗", str(e))

        return run_multi_roi_analysis

    def _build_save_results_widget(self):
        @magicgui(call_button="結果を保存 (CSV)")
        def save_results() -> None:
            df = SESSION_STATE.result_df
            if df is None or df.empty:
                QMessageBox.warning(None, "エラー", "保存する結果がありません。先に解析を実行してください。")
                return
            path, _ = QFileDialog.getSaveFileName(caption="CSVとして保存", filter="CSV files (*.csv)")
            if not path:
                return
            df.to_csv(path, index=False)
            QMessageBox.information(None, "保存完了", f"解析結果を保存しました:\n{path}")

        return save_results

    def _build_plot_raw_widget(self):
        @magicgui(call_button="Raw グラフ")
        def plot_raw_main() -> None:
            df = SESSION_STATE.result_df
            if df is None or df.empty:
                QMessageBox.warning(None, "エラー", "解析結果がありません。")
                return
            self._plot_result_df(df, title_prefix="Raw Main Intensity", ycol="raw_main_intensity")

        return plot_raw_main

    def _build_plot_double_widget(self):
        @magicgui(call_button="Double Normalization グラフ")
        def plot_double_norm() -> None:
            df = SESSION_STATE.result_df
            if df is None or df.empty:
                QMessageBox.warning(None, "エラー", "解析結果がありません。")
                return
            self._plot_result_df(df, title_prefix="Double Normalization", ycol="double_norm")

        return plot_double_norm

    def _build_plot_full_scale_widget(self):
        @magicgui(call_button="Full Scale グラフ")
        def plot_full_scale() -> None:
            df = SESSION_STATE.result_df
            if df is None or df.empty:
                QMessageBox.warning(None, "エラー", "解析結果がありません。")
                return
            self._plot_result_df(df, title_prefix="Full Scale Normalization", ycol="full_scale_norm")

        return plot_full_scale

    def _build_difference_widget(self):
        @magicgui(call_button="差分グラフ作成", ref_track_id={"label": "基準トラックID", "min": 1, "step": 1, "value": 1})
        def make_difference_plot(ref_track_id: int = 1) -> None:
            df = SESSION_STATE.result_df
            if df is None or df.empty:
                QMessageBox.warning(None, "エラー", "解析結果がありません。先に『解析実行』してください。")
                return
            if ref_track_id not in df["track_id"].unique():
                QMessageBox.warning(None, "エラー", f"Track ID {ref_track_id} は存在しません。")
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

        return make_difference_plot

    def _build_save_session_widget(self):
        @magicgui(call_button="完全復元セッション保存")
        def save_complete_session() -> None:
            df = SESSION_STATE.result_df
            if df is None or df.empty:
                QMessageBox.warning(None, "エラー", "保存する解析結果がありません。")
                return
            meta = SESSION_STATE.meta
            track_sources = SESSION_STATE.track_sources
            bg_source = SESSION_STATE.bg_source
            path, _ = QFileDialog.getSaveFileName(caption="完全復元セッション保存", filter="JSON files (*.json)")
            if not path:
                return
            if not path.lower().endswith(".json"):
                path += ".json"
            payload = {
                "session_type": "napari_roi_frap_double_norm_complete_restore_v2",
                "meta": meta,
                "track_sources": track_sources,
                "bg_source": bg_source,
                "result_table": df.to_dict(orient="records"),
            }
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            QMessageBox.information(None, "保存完了", f"完全復元セッションを保存しました:\n{path}")

        return save_complete_session

    def _build_load_session_widget(self):
        @magicgui(call_button="完全復元セッション読込")
        def load_complete_session() -> None:
            path, _ = QFileDialog.getOpenFileName(caption="完全復元セッション読込", filter="JSON files (*.json)")
            if not path:
                return
            try:
                payload = json.loads(Path(path).read_text(encoding="utf-8"))
                if payload.get("session_type", "") != "napari_roi_frap_double_norm_complete_restore_v2":
                    QMessageBox.warning(None, "エラー", "対応していないセッション形式です。")
                    return
                meta = payload.get("meta", {})
                track_sources = payload.get("track_sources", [])
                bg_source = payload.get("bg_source", None)
                result_table = payload.get("result_table", [])
                if not meta:
                    QMessageBox.warning(None, "エラー", "meta情報がありません。")
                    return
                image_layer_name = meta.get("image_layer", "")
                image_layer_names = [l.name for l in self.viewer.layers if getattr(l, "_type_string", "") == "image"]
                if image_layer_name not in image_layer_names:
                    if len(image_layer_names) == 1:
                        image_layer_name = image_layer_names[0]
                        meta["image_layer"] = image_layer_name
                    else:
                        QMessageBox.warning(None, "画像レイヤー不足", f"セッションが参照する画像レイヤー '{meta.get('image_layer', '')}' が現在のviewerにありません。\n対象画像を1枚だけ表示した状態で再度読込してください。")
                        return

                self._disconnect_old_mask_callback()
                if bg_source is not None:
                    remove_layer_if_exists(self.viewer, bg_source["layer_name"])
                    remove_layer_if_exists(self.viewer, f"BG_mask_{bg_source['layer_name']}")
                for ts in track_sources:
                    remove_layer_if_exists(self.viewer, ts["layer_name"])
                    remove_layer_if_exists(self.viewer, ts["ref_layer_name"])
                    remove_layer_if_exists(self.viewer, f"ROI_mask_{ts['layer_name']}")
                    remove_layer_if_exists(self.viewer, f"REF_mask_{ts['ref_layer_name']}")

                for ts in track_sources:
                    layer_main = self.viewer.add_points(np.array(ts["main_points_data"], dtype=float), name=ts["layer_name"], size=10, face_color="yellow")
                    try:
                        layer_main.edge_color = "black"
                    except Exception:
                        pass
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
                main_radius = int(meta.get("main_radius", 5))
                ref_radius = int(meta.get("ref_radius", 5))
                bg_radius = int(meta.get("bg_radius", 5))

                roi_tracks = []
                for ts in track_sources:
                    main_mask_layer = self.viewer.add_image(np.zeros_like(frame0, dtype=np.uint8), name=f"ROI_mask_{ts['layer_name']}", blending="additive", colormap="cyan", opacity=0.6, visible=True)
                    roi_tracks.append((main_mask_layer, np.array(ts["common_frames"], dtype=int), np.array(ts["common_main_y"], dtype=float), np.array(ts["common_main_x"], dtype=float), main_radius))
                    ref_mask_layer = self.viewer.add_image(np.zeros_like(frame0, dtype=np.uint8), name=f"REF_mask_{ts['ref_layer_name']}", blending="additive", colormap="yellow", opacity=0.6, visible=True)
                    roi_tracks.append((ref_mask_layer, np.array(ts["common_frames"], dtype=int), np.array(ts["common_ref_y"], dtype=float), np.array(ts["common_ref_x"], dtype=float), ref_radius))

                bg_track = None
                if bg_source is not None:
                    bg_mask_layer = self.viewer.add_image(np.zeros_like(frame0, dtype=np.uint8), name=f"BG_mask_{bg_source['layer_name']}", blending="additive", colormap="magenta", opacity=0.6, visible=True)
                    bg_track = (bg_mask_layer, np.array(bg_source["t_range"], dtype=int), np.array(bg_source["ys_interp"], dtype=float), np.array(bg_source["xs_interp"], dtype=float), bg_radius)

                self._connect_mask_callback(roi_tracks, bg_track)
                df = pd.DataFrame(result_table) if result_table else None
                SESSION_STATE.result_df = df
                SESSION_STATE.meta = meta
                SESSION_STATE.track_sources = track_sources
                SESSION_STATE.bg_source = bg_source
                SESSION_STATE.roi_tracks = roi_tracks
                SESSION_STATE.bg_track = bg_track
                if df is not None and not df.empty:
                    self._plot_result_df(df, title_prefix="Restored Raw Main", ycol="raw_main_intensity")
                QMessageBox.information(None, "読込完了", "完全復元セッションを読み込みました。\nmain ROI / reference ROI / background / mask / 結果テーブルを復元しました。")
            except Exception as e:
                QMessageBox.warning(None, "読込失敗", f"完全復元セッション読込に失敗しました:\n{e}")

        return load_complete_session
