from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class SessionState:
    result_df: pd.DataFrame | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    track_sources: list[dict[str, Any]] = field(default_factory=list)
    bg_source: dict[str, Any] | None = None
    roi_tracks: list[tuple[Any, Any, Any, Any, int]] = field(default_factory=list)
    bg_track: tuple[Any, Any, Any, Any, int] | None = None
    mask_callback: Any | None = None


SESSION_STATE = SessionState()
