from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class SessionState:
    mode: str = ""
    result_df: pd.DataFrame | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    track_sources: list[dict[str, Any]] = field(default_factory=list)
    bg_source: dict[str, Any] | None = None
    roi_tracks: list[tuple[Any, Any, Any, Any, int]] = field(default_factory=list)
    bg_track: tuple[Any, Any, Any, Any, int] | None = None
    track_id_overlays: list[tuple[Any, Any, Any, Any, int]] = field(default_factory=list)
    show_track_ids: bool = True
    mask_callback: Any | None = None

    def clear_results(self) -> None:
        self.mode = ""
        self.result_df = None
        self.meta = {}
        self.track_sources = []
        self.bg_source = None
        self.roi_tracks = []
        self.bg_track = None
        self.track_id_overlays = []


SESSION_STATE = SessionState()
