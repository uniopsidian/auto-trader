from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from typing import Any

from notifier import send_message
from state_store import load_state, save_state
from strategy import BotState


STATE_KEY = "runtime_state"


class Trader:
    def __init__(self) -> None:
        self.order_enabled = os.getenv("ORDER_ENABLED", "false").strip().lower() == "true"
        self.order_qty = int(os.getenv("ORDER_QTY", "3").strip())
        self.price_offset_pct = float(os.getenv("ORDER_PRICE_OFFSET_PCT", "0.10").strip())
        self.bridge = None

    def _get_bridge(self):
        if self.bridge is None:
            from order_bridge import OrderBridge
            self.bridge = OrderBridge()
        return self.bridge

    def restore_state(self, state: BotState) -> BotState:
        raw = load_state(STATE_KEY)
        if not raw:
            return state

        state.recent_high = raw.get("recent_high")
        state.recent_low_after_drop = raw.get("recent_low_after_drop")
        state.drop_detected = raw.get("drop_detected", False)
        state.has_position = raw.get("has_position", False)
        state.entry_price = raw.get("entry_price")
        state.tp1_done = raw.get("tp1_done", False)
        state.position_qty = raw.get("position_qty", 0)
        state.trades_today = raw.get("trades_today", 0)
        state.realized_pnl_pct_today = raw.get("realized_pnl_pct_today", 0.0)
        state.trading_halted_today = raw.get("trading_halted_today", False)
        state.last_trade_date = raw.get("last_trade_date")

        entry_time = raw.get("entry_time")
        if entry_time:
            state.entry_time = datetime.fromisoformat(entry_time)

        return state

    def persist_state(self, state: BotState) -> None:
        payload = asdict(state)
        if state.entry_time:
            payload["entry_time"] = state.entry_time.isoformat()
        save_state(STATE_KEY, payload)

    def _buy_limit_price(self, current_price: float) -> float:
        return current_price * (1 + self.price_offset_pct / 100)

    def _sell_limit_price(self, current_price: float) -> float:
        return current_price * (1 - self.price_offset_pct / 100)

    def enter_position(self, symbol: str, current_price: float, reason: str) -> dict[str, Any]:
        qty = self.order_qty
        limit_price = self._buy_limit_price(current_price)

        if not self.order_enabled:
            send_message(
                f"[모의 매수]\n종목={symbol}\n현재가={current_price:.2f}\n"
                f"지정가={limit_price:.2f}\n수량={qty}\n사유={reason}"
            )
            return {"mock": True, "side": "buy", "limit_price": limit_price, "qty": qty}

        bridge = self._get_bridge()
        result = bridge.place_limit_buy(
            symbol=symbol,
            qty=qty,
            limit_price=limit_price,
        )
        send_message(
            f"[실주문 매수 요청]\n종목={symbol}\n현재가={current_price:.2f}\n"
            f"지정가={limit_price:.2f}\n수량={qty}\n사유={reason}\n결과={result}"
        )
        return {"qty": qty, "result": result}

    def exit_position(
        self,
        symbol: str,
        current_price: float,
        reason: str,
        position_qty: int,
        sell_half: bool = False,
    ) -> dict[str, Any]:
        if sell_half:
            qty = max(1, position_qty // 2)
        else:
            qty = max(1, position_qty)

        limit_price = self._sell_limit_price(current_price)

        if not self.order_enabled:
            send_message(
                f"[모의 매도]\n종목={symbol}\n현재가={current_price:.2f}\n"
                f"지정가={limit_price:.2f}\n수량={qty}\n사유={reason}"
            )
            return {"mock": True, "side": "sell", "limit_price": limit_price, "qty": qty}

        bridge = self._get_bridge()
        result = bridge.place_limit_sell(
            symbol=symbol,
            qty=qty,
            limit_price=limit_price,
        )
        send_message(
            f"[실주문 매도 요청]\n종목={symbol}\n현재가={current_price:.2f}\n"
            f"지정가={limit_price:.2f}\n수량={qty}\n사유={reason}\n결과={result}"
        )
        return {"qty": qty, "result": result}