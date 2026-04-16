from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _load_official_modules():
    repo_path = os.getenv("KIS_OFFICIAL_REPO_PATH", "").strip()
    if not repo_path:
        raise ValueError("KIS_OFFICIAL_REPO_PATH 값이 비어 있습니다.")

    repo = Path(repo_path)
    user_path = repo / "examples_user"
    overseas_path = user_path / "overseas_stock"

    sys.path.insert(0, str(user_path))
    sys.path.insert(0, str(overseas_path))

    import kis_auth as ka  # type: ignore
    import overseas_stock_functions as osf  # type: ignore

    return ka, osf


class OrderBridge:
    def __init__(self) -> None:
        self.ka, self.osf = _load_official_modules()
        self.ka.auth()
        self.trenv = self.ka.getTREnv()

    def place_limit_buy(self, symbol: str, qty: int, limit_price: float) -> dict[str, Any]:
        mode = os.getenv("ORDER_BRIDGE_MODE", "regular").strip().lower()

        if mode == "regular":
            df = self.osf.order(
                order_dv="buy",
                excg_cd="NASD",
                natn_cd="840",
                ovrs_excg_cd="NASD",
                cano=self.trenv.my_acct,
                acnt_prdt_cd=self.trenv.my_prod,
                pdno=symbol,
                ord_qty=str(qty),
                ovrs_ord_unpr=f"{limit_price:.2f}",
                ctac_tlno=os.getenv("CTAC_TLNO", ""),
                mgco_aptm_odno=os.getenv("MGCO_APTM_ODNO", ""),
                ord_svr_dvsn_cd=os.getenv("ORD_SVR_DVSN_CD", "0"),
                ord_dvsn="00",
            )
            return {"mode": mode, "result": df.to_dict(orient="records") if df is not None else []}

        if mode == "daytime":
            df = self.osf.daytime_order(
                order_dv="buy",
                cano=self.trenv.my_acct,
                acnt_prdt_cd=self.trenv.my_prod,
                ovrs_excg_cd="NASD",
                pdno=symbol,
                ord_qty=str(qty),
                ovrs_ord_unpr=f"{limit_price:.2f}",
                ctac_tlno=os.getenv("CTAC_TLNO", ""),
                mgco_aptm_odno=os.getenv("MGCO_APTM_ODNO", ""),
                ord_svr_dvsn_cd=os.getenv("ORD_SVR_DVSN_CD", "0"),
                ord_dvsn="00",
            )
            return {"mode": mode, "result": df.to_dict(orient="records") if df is not None else []}

        raise NotImplementedError(f"지원하지 않는 ORDER_BRIDGE_MODE 입니다: {mode}")

    def place_limit_sell(self, symbol: str, qty: int, limit_price: float) -> dict[str, Any]:
        mode = os.getenv("ORDER_BRIDGE_MODE", "regular").strip().lower()

        if mode == "regular":
            df = self.osf.order(
                order_dv="sell",
                excg_cd="NASD",
                natn_cd="840",
                ovrs_excg_cd="NASD",
                cano=self.trenv.my_acct,
                acnt_prdt_cd=self.trenv.my_prod,
                pdno=symbol,
                ord_qty=str(qty),
                ovrs_ord_unpr=f"{limit_price:.2f}",
                ctac_tlno=os.getenv("CTAC_TLNO", ""),
                mgco_aptm_odno=os.getenv("MGCO_APTM_ODNO", ""),
                ord_svr_dvsn_cd=os.getenv("ORD_SVR_DVSN_CD", "0"),
                ord_dvsn="00",
            )
            return {"mode": mode, "result": df.to_dict(orient="records") if df is not None else []}

        if mode == "daytime":
            df = self.osf.daytime_order(
                order_dv="sell",
                cano=self.trenv.my_acct,
                acnt_prdt_cd=self.trenv.my_prod,
                ovrs_excg_cd="NASD",
                pdno=symbol,
                ord_qty=str(qty),
                ovrs_ord_unpr=f"{limit_price:.2f}",
                ctac_tlno=os.getenv("CTAC_TLNO", ""),
                mgco_aptm_odno=os.getenv("MGCO_APTM_ODNO", ""),
                ord_svr_dvsn_cd=os.getenv("ORD_SVR_DVSN_CD", "0"),
                ord_dvsn="00",
            )
            return {"mode": mode, "result": df.to_dict(orient="records") if df is not None else []}

        raise NotImplementedError(f"지원하지 않는 ORDER_BRIDGE_MODE 입니다: {mode}")