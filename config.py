from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    kis_app_key: str
    kis_app_secret: str
    kis_hts_id: str
    kis_account_no: str
    kis_account_prod: str
    kis_base_url: str

    kakao_access_token: str
    kakao_refresh_token: str
    kakao_rest_api_key: str
    kakao_client_secret: str

    target_market: str
    target_symbol: str
    use_mock: bool

    check_interval_seconds: int
    drop_from_recent_high_pct: float
    rebound_from_low_pct: float

    stop_loss_pct: float
    take_profit_1_pct: float
    take_profit_2_pct: float

    max_hold_minutes: int
    max_trades_per_day: int
    position_size_pct: float
    no_trade_first_minutes: int
    daily_loss_limit_pct: float


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"환경변수 {name} 값이 비어 있습니다.")
    return value


def load_settings() -> Settings:
    return Settings(
        kis_app_key=_require("KIS_APP_KEY"),
        kis_app_secret=_require("KIS_APP_SECRET"),
        kis_hts_id=_require("KIS_HTS_ID"),
        kis_account_no=_require("KIS_ACCOUNT_NO"),
        kis_account_prod=_require("KIS_ACCOUNT_PROD"),
        kis_base_url=os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443").strip(),

        kakao_access_token=_require("KAKAO_ACCESS_TOKEN"),
        kakao_refresh_token=_require("KAKAO_REFRESH_TOKEN"),
        kakao_rest_api_key=_require("KAKAO_REST_API_KEY"),
        kakao_client_secret=os.getenv("KAKAO_CLIENT_SECRET", "").strip(),

        target_market=os.getenv("TARGET_MARKET", "NAS").strip(),
        target_symbol=os.getenv("TARGET_SYMBOL", "TQQQ").strip(),
        use_mock=os.getenv("USE_MOCK", "false").strip().lower() == "true",

        check_interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "15").strip()),
        drop_from_recent_high_pct=float(os.getenv("DROP_FROM_RECENT_HIGH_PCT", "1.2").strip()),
        rebound_from_low_pct=float(os.getenv("REBOUND_FROM_LOW_PCT", "0.4").strip()),

        stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", "0.8").strip()),
        take_profit_1_pct=float(os.getenv("TAKE_PROFIT_1_PCT", "1.0").strip()),
        take_profit_2_pct=float(os.getenv("TAKE_PROFIT_2_PCT", "1.8").strip()),

        max_hold_minutes=int(os.getenv("MAX_HOLD_MINUTES", "60").strip()),
        max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "2").strip()),
        position_size_pct=float(os.getenv("POSITION_SIZE_PCT", "10").strip()),
        no_trade_first_minutes=int(os.getenv("NO_TRADE_FIRST_MINUTES", "30").strip()),
        daily_loss_limit_pct=float(os.getenv("DAILY_LOSS_LIMIT_PCT", "1.5").strip()),
    )
