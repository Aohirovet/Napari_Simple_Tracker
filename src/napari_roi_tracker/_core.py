from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from skimage.draw import disk


def get_frame_2d_from_image(image: np.ndarray, t_index: int) -> np.ndarray:
    if image.ndim == 5:
        return image[t_index, 0, 0, :, :]
    if image.ndim == 4:
        return image[t_index, 0, :, :]
    if image.ndim == 3:
        return image[t_index, :, :]
    raise ValueError(f"未対応の画像次元です: ndim={image.ndim}")


def extract_tyx_from_points(pts: np.ndarray, image_ndim: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if pts.ndim != 2 or pts.shape[0] == 0:
        raise ValueError("Pointsデータが不正です。")

    if pts.shape[1] >= 5 and image_ndim >= 5:
        t_ax, y_ax, x_ax = 0, 3, 4
    elif pts.shape[1] >= 4 and image_ndim >= 4:
        t_ax, y_ax, x_ax = 0, 2, 3
    elif pts.shape[1] >= 3:
        t_ax, y_ax, x_ax = 0, 1, 2
    else:
        raise ValueError("Pointsレイヤーの次元が不足しています。")

    frames = pts[:, t_ax].astype(int)
    ys = pts[:, y_ax].astype(float)
    xs = pts[:, x_ax].astype(float)

    idx = np.argsort(frames)
    return frames[idx], ys[idx], xs[idx]


def interpolate_track(frames: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None]:
    if len(frames) < 2:
        return None, None, None

    ys_interp: list[np.ndarray] = []
    xs_interp: list[np.ndarray] = []
    for f0, f1, y0, y1, x0, x1 in zip(frames[:-1], frames[1:], ys[:-1], ys[1:], xs[:-1], xs[1:]):
        n = max(f1 - f0, 1)
        ys_interp.append(np.linspace(y0, y1, n, endpoint=False))
        xs_interp.append(np.linspace(x0, x1, n, endpoint=False))

    ys_interp.append(np.array([ys[-1]]))
    xs_interp.append(np.array([xs[-1]]))

    return np.arange(frames[0], frames[-1] + 1), np.concatenate(ys_interp), np.concatenate(xs_interp)


def measure_roi_mean(frame2d: np.ndarray, y: float, x: float, radius: int) -> float:
    rr, cc = disk((int(round(y)), int(round(x))), radius, shape=frame2d.shape)
    roi = frame2d[rr, cc]
    return float(np.nanmean(roi))


def compute_double_and_full_scale(df_track: pd.DataFrame, bleach_frame: int) -> pd.DataFrame:
    df_track = df_track.copy().sort_values("frame")

    pre_mask = df_track["frame"] < bleach_frame
    post_mask = df_track["frame"] >= bleach_frame

    track_id = df_track["track_id"].iloc[0]
    if pre_mask.sum() == 0:
        raise ValueError(
            f"track_id={track_id} に pre-bleach frame がありません。"
            f" bleach_frame を小さくしすぎていないか確認してください。"
        )
    if post_mask.sum() == 0:
        raise ValueError(
            f"track_id={track_id} に post-bleach frame がありません。"
            f" bleach_frame を大きくしすぎていないか確認してください。"
        )

    roi1_pre = float(np.nanmean(df_track.loc[pre_mask, "main_bg_corrected"]))
    roi2_pre = float(np.nanmean(df_track.loc[pre_mask, "ref_bg_corrected"]))

    eps = 1e-12
    roi1_pre = roi1_pre if abs(roi1_pre) > eps else np.nan
    roi2_pre = roi2_pre if abs(roi2_pre) > eps else np.nan

    df_track["double_norm"] = (
        (df_track["main_bg_corrected"] / roi1_pre)
        * (roi2_pre / df_track["ref_bg_corrected"].replace(0, np.nan))
    )

    post0_idx = df_track.loc[post_mask, "frame"].idxmin()
    post0_val = float(df_track.loc[post0_idx, "double_norm"])

    denom = 1.0 - post0_val
    df_track["full_scale_norm"] = np.nan if abs(denom) < eps else (df_track["double_norm"] - post0_val) / denom
    df_track["main_pre_mean"] = roi1_pre
    df_track["ref_pre_mean"] = roi2_pre
    df_track["double_norm_post0"] = post0_val
    return df_track


def infer_reference_layer_name(main_layer_name: str, reference_prefix: str = "Ref_") -> str:
    return f"{reference_prefix}{main_layer_name}"


def run_analysis_core(
    viewer: Any,
    image_layer_name: str,
    main_radius: int,
    ref_radius: int,
    bg_radius: int,
    bg_points_layer_name: str = "",
    reference_prefix: str = "Ref_",
    bleach_frame: int = 5,
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]], dict[str, Any] | None, list[tuple[Any, Any, Any, Any, int]], tuple[Any, Any, Any, Any, int] | None]:
    if image_layer_name not in [l.name for l in viewer.layers]:
        raise ValueError(f"画像レイヤー '{image_layer_name}' が見つかりません。")

    img_layer = viewer.layers[image_layer_name]
    image = np.asarray(img_layer.data)
    bg_layer_name = bg_points_layer_name.strip() if bg_points_layer_name else ""

    all_point_layers = [l for l in viewer.layers if getattr(l, "_type_string", "") == "points"]
    point_layers_main = [l for l in all_point_layers if l.name != bg_layer_name and not l.name.startswith(reference_prefix)]
    if not point_layers_main:
        raise ValueError("解析対象の main Pointsレイヤーが見つかりません。")

    all_dfs: list[pd.DataFrame] = []
    roi_tracks: list[tuple[Any, Any, Any, Any, int]] = []
    track_sources: list[dict[str, Any]] = []
    bg_df: pd.DataFrame | None = None
    bg_track = None
    bg_source = None

    if bg_layer_name:
        if bg_layer_name not in [l.name for l in viewer.layers]:
            raise ValueError(f"Background Pointsレイヤー '{bg_layer_name}' が見つかりません。")
        bg_layer = viewer.layers[bg_layer_name]
        bg_pts = np.asarray(bg_layer.data)
        bg_frames, bg_ys, bg_xs = extract_tyx_from_points(bg_pts, image.ndim)
        if len(bg_frames) < 2:
            raise ValueError("Background Pointsは少なくとも2点必要です。")
        bg_t_range, bg_ys_interp, bg_xs_interp = interpolate_track(bg_frames, bg_ys, bg_xs)
        assert bg_t_range is not None and bg_ys_interp is not None and bg_xs_interp is not None

        bg_intensities = []
        for tt, y, x in zip(bg_t_range, bg_ys_interp, bg_xs_interp):
            frame2d = get_frame_2d_from_image(image, int(tt))
            bg_intensities.append(measure_roi_mean(frame2d, float(y), float(x), bg_radius))

        bg_df = pd.DataFrame({
            "frame": bg_t_range,
            "bg_y": bg_ys_interp,
            "bg_x": bg_xs_interp,
            "bg_intensity": bg_intensities,
        })

        bg_mask_name = f"BG_mask_{bg_layer.name}"
        remove_layer_if_exists(viewer, bg_mask_name)
        frame0 = get_frame_2d_from_image(image, 0)
        bg_mask_layer = viewer.add_image(
            np.zeros_like(frame0, dtype=np.uint8),
            name=bg_mask_name,
            blending="additive",
            colormap="magenta",
            opacity=0.6,
            visible=True,
        )
        bg_track = (bg_mask_layer, bg_t_range, bg_ys_interp, bg_xs_interp, bg_radius)
        bg_source = {
            "layer_name": bg_layer.name,
            "points_data": bg_pts.tolist(),
            "frames": bg_frames.tolist(),
            "ys": bg_ys.tolist(),
            "xs": bg_xs.tolist(),
            "t_range": bg_t_range.tolist(),
            "ys_interp": bg_ys_interp.tolist(),
            "xs_interp": bg_xs_interp.tolist(),
        }

    frame0 = get_frame_2d_from_image(image, 0)
    for i, main_layer in enumerate(point_layers_main, start=1):
        ref_layer_name = infer_reference_layer_name(main_layer.name, reference_prefix=reference_prefix)
        if ref_layer_name not in [l.name for l in viewer.layers]:
            raise ValueError(f"main ROI '{main_layer.name}' に対応する reference ROI '{ref_layer_name}' が見つかりません。")
        ref_layer = viewer.layers[ref_layer_name]

        main_pts = np.asarray(main_layer.data)
        ref_pts = np.asarray(ref_layer.data)
        main_frames, main_ys, main_xs = extract_tyx_from_points(main_pts, image.ndim)
        ref_frames, ref_ys, ref_xs = extract_tyx_from_points(ref_pts, image.ndim)
        if len(main_frames) < 2:
            raise ValueError(f"main ROI '{main_layer.name}' は少なくとも2点必要です。")
        if len(ref_frames) < 2:
            raise ValueError(f"reference ROI '{ref_layer_name}' は少なくとも2点必要です。")

        main_t_range, main_ys_interp, main_xs_interp = interpolate_track(main_frames, main_ys, main_xs)
        ref_t_range, ref_ys_interp, ref_xs_interp = interpolate_track(ref_frames, ref_ys, ref_xs)
        assert main_t_range is not None and main_ys_interp is not None and main_xs_interp is not None
        assert ref_t_range is not None and ref_ys_interp is not None and ref_xs_interp is not None

        common_frames = np.intersect1d(main_t_range, ref_t_range)
        if bg_df is not None:
            common_frames = np.intersect1d(common_frames, bg_df["frame"].to_numpy())
        if len(common_frames) == 0:
            raise ValueError(f"'{main_layer.name}' と '{ref_layer_name}' の共通frameがありません。")

        main_raw, main_y_common, main_x_common = [], [], []
        for tt in common_frames:
            idx = np.where(main_t_range == tt)[0][0]
            y, x = main_ys_interp[idx], main_xs_interp[idx]
            frame2d = get_frame_2d_from_image(image, int(tt))
            main_raw.append(measure_roi_mean(frame2d, float(y), float(x), main_radius))
            main_y_common.append(float(y))
            main_x_common.append(float(x))

        ref_raw, ref_y_common, ref_x_common = [], [], []
        for tt in common_frames:
            idx = np.where(ref_t_range == tt)[0][0]
            y, x = ref_ys_interp[idx], ref_xs_interp[idx]
            frame2d = get_frame_2d_from_image(image, int(tt))
            ref_raw.append(measure_roi_mean(frame2d, float(y), float(x), ref_radius))
            ref_y_common.append(float(y))
            ref_x_common.append(float(x))

        df = pd.DataFrame({
            "track_id": i,
            "track_name": main_layer.name,
            "ref_track_name": ref_layer_name,
            "frame": common_frames,
            "main_y": main_y_common,
            "main_x": main_x_common,
            "ref_y": ref_y_common,
            "ref_x": ref_x_common,
            "raw_main_intensity": main_raw,
            "raw_ref_intensity": ref_raw,
        })
        df = pd.merge(df, bg_df[["frame", "bg_intensity"]], on="frame", how="left") if bg_df is not None else df.assign(bg_intensity=np.nan)
        df["main_bg_corrected"] = df["raw_main_intensity"] - df["bg_intensity"].fillna(0)
        df["ref_bg_corrected"] = df["raw_ref_intensity"] - df["bg_intensity"].fillna(0)
        df = compute_double_and_full_scale(df, bleach_frame=bleach_frame)
        all_dfs.append(df)

        main_mask_layer_name = f"ROI_mask_{main_layer.name}"
        remove_layer_if_exists(viewer, main_mask_layer_name)
        main_mask_layer = viewer.add_image(
            np.zeros_like(frame0, dtype=np.uint8),
            name=main_mask_layer_name,
            blending="additive",
            colormap="cyan",
            opacity=0.6,
            visible=True,
        )
        roi_tracks.append((main_mask_layer, common_frames, np.array(main_y_common), np.array(main_x_common), main_radius))

        ref_mask_layer_name = f"REF_mask_{ref_layer.name}"
        remove_layer_if_exists(viewer, ref_mask_layer_name)
        ref_mask_layer = viewer.add_image(
            np.zeros_like(frame0, dtype=np.uint8),
            name=ref_mask_layer_name,
            blending="additive",
            colormap="yellow",
            opacity=0.6,
            visible=True,
        )
        roi_tracks.append((ref_mask_layer, common_frames, np.array(ref_y_common), np.array(ref_x_common), ref_radius))

        track_sources.append({
            "track_id": i,
            "layer_name": main_layer.name,
            "ref_layer_name": ref_layer.name,
            "main_points_data": main_pts.tolist(),
            "ref_points_data": ref_pts.tolist(),
            "main_frames": main_frames.tolist(),
            "main_ys": main_ys.tolist(),
            "main_xs": main_xs.tolist(),
            "ref_frames": ref_frames.tolist(),
            "ref_ys": ref_ys.tolist(),
            "ref_xs": ref_xs.tolist(),
            "main_t_range": main_t_range.tolist(),
            "main_ys_interp": main_ys_interp.tolist(),
            "main_xs_interp": main_xs_interp.tolist(),
            "ref_t_range": ref_t_range.tolist(),
            "ref_ys_interp": ref_ys_interp.tolist(),
            "ref_xs_interp": ref_xs_interp.tolist(),
            "common_frames": common_frames.tolist(),
            "common_main_y": np.array(main_y_common).tolist(),
            "common_main_x": np.array(main_x_common).tolist(),
            "common_ref_y": np.array(ref_y_common).tolist(),
            "common_ref_x": np.array(ref_x_common).tolist(),
        })

    if not all_dfs:
        raise ValueError("有効なトラックが見つかりませんでした。")

    result = pd.concat(all_dfs, ignore_index=True)
    meta = {
        "image_layer": image_layer_name,
        "main_radius": int(main_radius),
        "ref_radius": int(ref_radius),
        "bg_radius": int(bg_radius),
        "bg_points_layer": bg_layer_name,
        "reference_prefix": reference_prefix,
        "bleach_frame": int(bleach_frame),
        "track_layers": [ts["layer_name"] for ts in track_sources],
        "ref_track_layers": [ts["ref_layer_name"] for ts in track_sources],
    }
    return result, meta, track_sources, bg_source, roi_tracks, bg_track


def remove_layer_if_exists(viewer: Any, name: str) -> None:
    try:
        if name in [l.name for l in viewer.layers]:
            try:
                viewer.layers.remove(viewer.layers[name])
            except Exception:
                viewer.layers.remove(name)
    except Exception:
        pass
