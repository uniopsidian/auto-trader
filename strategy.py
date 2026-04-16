from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BotState:
    recent_high: float | None = None
    recent_low_after_drop: float | None = None
    drop_detected: bool = False

    has_position: bool = False
    entry_price: float | None = None
    entry_time: datetime | None = None
    tp1_done: bool = False
    position_qty: int = 0

    trades_today: int = 0
    realized_pnl_pct_today: float = 0.0
    trading_halted_today: bool = False
    last_trade_date: str | None = None


@dataclass(frozen=True)
class Signal:
    action: str
    reason: str


def reset_day_if_needed(state: BotState, current_date_str: str) -> None:
    if state.last_trade_date != current_date_str:
        state.trades_today = 0
        state.realized_pnl_pct_today = 0.0
        state.trading_halted_today = False
        state.last_trade_date = current_date_str


def update_price_context(
    state: BotState,
    current_price: float,
    drop_from_recent_high_pct: float,
) -> None:
    if state.has_position:
        return

    if state.recent_high is None or current_price > state.recent_high:
        state.recent_high = current_price
        state.recent_low_after_drop = None
        state.drop_detected = False
        return

    drop_pct = ((state.recent_high - current_price) / state.recent_high) * 100

    if drop_pct >= drop_from_recent_high_pct:
        state.drop_detected = True
        if state.recent_low_after_drop is None or current_price < state.recent_low_after_drop:
            state.recent_low_after_drop = current_price


def check_entry_signal(
    state: BotState,
    current_price: float,
    rebound_from_low_pct: float,
    max_trades_per_day: int,
    trading_allowed: bool,
) -> Signal:
    if not trading_allowed:
        return Signal("HOLD", "거래 가능 시간이 아님")

    if state.trading_halted_today:
        return Signal("HOLD", "일일 손실 한도 도달로 거래 중지")

    if state.trades_today >= max_trades_per_day:
        return Signal("HOLD", "일일 최대 진입 횟수 도달")

    if state.has_position:
        return Signal("HOLD", "이미 포지션 보유 중")

    if not state.drop_detected or state.recent_low_after_drop is None:
        return Signal("HOLD", "눌림 조건 미충족")

    rebound_pct = ((current_price - state.recent_low_after_drop) / state.recent_low_after_drop) * 100

    if rebound_pct >= rebound_from_low_pct:
        return Signal(
            "BUY",
            f"눌림 후 반등 확인 | 저점 {state.recent_low_after_drop:.2f} → 현재가 {current_price:.2f} | 반등률 {rebound_pct:.2f}%"
        )

    return Signal("HOLD", "반등 조건 미충족")


def check_exit_signal(
    state: BotState,
    current_price: float,
    stop_loss_pct: float,
    take_profit_1_pct: float,
    take_profit_2_pct: float,
    max_hold_minutes: int,
    now: datetime,
) -> Signal:
    if not state.has_position or state.entry_price is None or state.entry_time is None:
        return Signal("HOLD", "포지션 없음")

    pnl_pct = ((current_price - state.entry_price) / state.entry_price) * 100
    hold_minutes = (now - state.entry_time).total_seconds() / 60

    if pnl_pct <= -stop_loss_pct:
        return Signal("SELL_ALL", f"손절 조건 충족 | 손익률 {pnl_pct:.2f}%")

    if not state.tp1_done and pnl_pct >= take_profit_1_pct:
        return Signal("SELL_HALF", f"1차 익절 조건 충족 | 손익률 {pnl_pct:.2f}%")

    if pnl_pct >= take_profit_2_pct:
        return Signal("SELL_ALL", f"2차 익절 조건 충족 | 손익률 {pnl_pct:.2f}%")

    if hold_minutes >= max_hold_minutes:
        return Signal("SELL_ALL", f"시간 청산 조건 충족 | 보유시간 {hold_minutes:.1f}분")

    return Signal("HOLD", "청산 조건 미충족")