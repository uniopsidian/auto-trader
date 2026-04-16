from __future__ import annotations

import time
from typing import Any

import requests

from config import Settings


class KISClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.kis_base_url.rstrip("/")
        self.app_key = settings.kis_app_key
        self.app_secret = settings.kis_app_secret
        self.access_token: str | None = None
        self.token_expire_at: float = 0.0

    def _issue_token(self) -> str:
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {
            "content-type": "application/json",
        }
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        response = requests.post(url, headers=headers, json=body, timeout=15)
        response.raise_for_status()
        data = response.json()

        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 0)

        if not access_token:
            raise RuntimeError(f"토큰 발급 실패: {data}")

        self.access_token = access_token
        expires_in = int(data.get("expires_in", 86400))
        self.token_expire_at = time.time() + max(expires_in - 300, 300)
        return access_token

    def _get_token(self) -> str:
        if self.access_token and time.time() < self.token_expire_at:
            return self.access_token
        return self._issue_token()

    def get_overseas_price(self, market: str, symbol: str) -> dict[str, Any]:
    """
    해외주식 현재가 조회
    market 예시: NAS, NYS, AMS
    symbol 예시: AAPL, TSLA, NVDA
    """
    url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
    params = {
        "AUTH": "",
        "EXCD": market,
        "SYMB": symbol,
    }

    for attempt in range(2):
        token = self._get_token()

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "HHDFS00000300",
        }

        response = requests.get(url, headers=headers, params=params, timeout=15)

        if response.status_code == 401 and attempt == 0:
            self.access_token = None
            self.token_expire_at = 0.0
            continue

        response.raise_for_status()
        data = response.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(f"해외주식 현재가 조회 실패: {data}")

        return data

    raise RuntimeError("해외주식 현재가 조회 실패: 401 인증 재시도 후에도 실패")
