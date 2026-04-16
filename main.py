from __future__ import annotations

import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import load_settings
from kis_client import KISClient
from notifier import send_message
from state_store import init_db
from strategy import (
    BotState,
    check_entry_signal,
    check_exit_signal,
    reset_day_if_needed,
    update_price_context,
)
from trader import Trader


def is_us_regular_session_trade_time(now: datetime, no_trade_first_minutes: int) -> bool:
    """
    한국시간 기준 단순 처리:
    서머타임 기준 미국 정규장 22:30 ~ 05:00
    장 시작 후 no_trade_first_minutes 동안은 거래 금지

    주의:
    - 이 함수는 서머타임을 단순 가정한 버전입니다.
    - 나중에 서버 운영 단계에서는 미국 장 시간 계산을 더 정확히 바꾸는 것이 좋습니다.
    """
    start = now.replace(hour=22, minute=30, second=0, microsecond=0)
    allowed_start = start + timedelta(minutes=no_trade_first_minutes)

    if now.hour >= 22:
        return now >= allowed_start
    if now.hour < 5:
        return True
    return False


def main() -> None:
    settings = load_settings()
    client = KISClient(settings)

    init_db()
    trader = Trader()
    state = trader.restore_state(BotState())

    send_message(
        f"봇 시작\n"
        f"종목={settings.target_symbol}\n"
        f"시장={settings.target_market}\n"
        f"체크주기={settings.check_interval_seconds}초\n"
        f"하락감지={settings.drop_from_recent_high_pct}%\n"
        f"반등확인={settings.rebound_from_low_pct}%\n"
        f"손절={settings.stop_loss_pct}%\n"
        f"익절1={settings.take_profit_1_pct}%\n"
        f"익절2={settings.take_profit_2_pct}%\n"
        f"최대보유={settings.max_hold_minutes}분\n"
        f"일최대진입={settings.max_trades_per_day}회"
    )

    while True:
        try:
            now = datetime.now(ZoneInfo("Asia/Seoul"))
            date_str = now.strftime("%Y-%m-%d")
            reset_day_if_needed(state, date_str)

            result = client.get_overseas_price(
                market=settings.target_market,
                symbol=settings.target_symbol,
            )

            output = result.get("output", {})
            last_price_raw = output.get("last")

            if not last_price_raw:
                print(f"[{now:%Y-%m-%d %H:%M:%S}] 현재가를 읽지 못했습니다.")
                time.sleep(settings.check_interval_seconds)
                continue

            current_price = float(last_price_raw)

            trading_allowed = is_us_regular_session_trade_time(
                now=now,
                no_trade_first_minutes=settings.no_trade_first_minutes,
            )

            if not state.has_position:
                update_price_context(
                    state=state,
                    current_price=current_price,
                    drop_from_recent_high_pct=settings.drop_from_recent_high_pct,
                )

                entry_signal = check_entry_signal(
                    state=state,
                    current_price=current_price,
                    rebound_from_low_pct=settings.rebound_from_low_pct,
                    max_trades_per_day=settings.max_trades_per_day,
                    trading_allowed=trading_allowed,
                )

                print(
                    f"[{now:%Y-%m-%d %H:%M:%S}] "
                    f"가격={current_price:.2f} "
                    f"최근고점={state.recent_high} "
                    f"눌림저점={state.recent_low_after_drop} "
                    f"거래가능={trading_allowed} "
                    f"진입신호={entry_signal.action} "
                    f"사유={entry_signal.reason}"
                )

                if entry_signal.action == "BUY":
                    order_result = trader.enter_position(
                        symbol=settings.target_symbol,
                        current_price=current_price,
                        reason=entry_signal.reason,
                    )

                    qty = order_result.get("qty", 3)

                    state.has_position = True
                    state.entry_price = current_price
                    state.entry_time = now
                    state.tp1_done = qty
                    state.trades_today += 1

                    trader.persist_state(state)

                    print(
                        f"[{now:%Y-%m-%d %H:%M:%S}] "
                        f"매수 요청 완료 | 가격={current_price:.2f} | 수량={qty} | 결과={order_result}"
                    )

            else:
                exit_signal = check_exit_signal(
                    state=state,
                    current_price=current_price,
                    stop_loss_pct=settings.stop_loss_pct,
                    take_profit_1_pct=settings.take_profit_1_pct,
                    take_profit_2_pct=settings.take_profit_2_pct,
                    max_hold_minutes=settings.max_hold_minutes,
                    now=now,
                )

                if state.entry_price is None:
                    print(f"[{now:%Y-%m-%d %H:%M:%S}] entry_price가 비어 있어 상태를 초기화합니다.")
                    state.has_position = False
                    state.entry_time = None
                    state.tp1_done = False
                    trader.persist_state(state)
                    time.sleep(settings.check_interval_seconds)
                    continue

                pnl_pct = ((current_price - state.entry_price) / state.entry_price) * 100

                print(
                    f"[{now:%Y-%m-%d %H:%M:%S}] "
                    f"보유중 가격={current_price:.2f} "
                    f"진입가={state.entry_price:.2f} "
                    f"손익률={pnl_pct:.2f}% "
                    f"청산신호={exit_signal.action} "
                    f"사유={exit_signal.reason}"
                )

                if exit_signal.action == "SELL_HALF":
                    order_result = trader.exit_position(
                        symbol=settings.target_symbol,
                        current_price=current_price,
                        reason=exit_signal.reason,
                        position_qty=state.position_qty,
                        sell_half=True,
                    )

                    state.tp1_done = True
                    state.position_qty = max(1, state.position_qty // 2)
                    trader.persist_state(state)

                    print(
                        f"[{now:%Y-%m-%d %H:%M:%S}] "
                        f"1차 익절 요청 완료 | 가격={current_price:.2f} | 결과={order_result}"
                    )

                elif exit_signal.action == "SELL_ALL":
                    order_result = trader.exit_position(
                        symbol=settings.target_symbol,
                        current_price=current_price,
                        reason=exit_signal.reason,
                        position_qty=state.position_qty,
                        sell_half=False,
                    )

                    state.realized_pnl_pct_today += pnl_pct

                    state.has_position = False
                    state.entry_price = None
                    state.entry_time = None
                    state.tp1_done = False
                    state.position_qty = 0
                    state.recent_high = current_price
                    state.recent_low_after_drop = None
                    state.drop_detected = False

                    if state.realized_pnl_pct_today <= -settings.daily_loss_limit_pct:
                        state.trading_halted_today = True
                        send_message(
                            f"[거래 중지]\n"
                            f"오늘 누적손익률={state.realized_pnl_pct_today:.2f}%로"
                            f"일일 손실 한도={-settings.daily_loss_limit_pct:.2f}% 도달"
                        )

                    trader.persist_state(state)

                    print(
                        f"[{now:%Y-%m-%d %H:%M:%S}] "
                        f"전량 매도 요청 완료 | 가격={current_price:.2f} | "
                        f"손익률={pnl_pct:.2f}% | 결과={order_result}"
                    )

        except KeyboardInterrupt:
            send_message("봇이 수동으로 종료되었습니다.")
            print("사용자 요청으로 종료합니다.")
            break

        except Exception as e:
            error_text = f"[오류] {type(e).__name__}: {e}"
            print(error_text)
            try:
                send_message(error_text)
            except Exception as notify_error:
                print(f"[알림 실패] {type(notify_error).__name__}: {notify_error}")

        time.sleep(settings.check_interval_seconds)


if __name__ == "__main__":
    main()
