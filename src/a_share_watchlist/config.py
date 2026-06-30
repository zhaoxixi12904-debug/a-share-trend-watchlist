from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScreeningConfig:
    min_amount: float = 100_000_000
    min_listing_days: int = 180
    min_turnover: float = 1.0
    max_turnover: float = 20.0
    amount_spike_multiple: float = 1.5
    max_5d_gain: float = 0.25
    ma_window: int = 20
    as_of_date: Optional[str] = None
