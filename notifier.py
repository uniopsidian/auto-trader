from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests

from config import load_settings


ENV_PATH = Path(".env")


def _write_env_value(key: str, value: str) -> None:
    if not ENV_PATH.exists():
        raise FileNotFoundError(".env 파일을 찾을 수 없습니다.")

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    replaced = False
    new_lines = []

    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            replaced = True
        else:
            new_lines.append(line)

    if not replaced:
        new_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def refresh_kakao_token() -> str:
    settings = load_settings()

    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": settings.kakao_rest_api_key,
        "client_secret": settings.kakao_client_secret,
        "refresh_token": settings.kakao_refresh_token,
    }

    response = requests.post(url, data=data, timeout=15)
    response.raise_for_status()
    token_data = response.json()

    new_access_token = token_data.get("access_token")
    new_refresh_token = token_data.get("refresh_token")

    if not new_access_token:
        raise RuntimeError(f"카카오 토큰 갱신 실패: {token_data}")

    _write_env_value("KAKAO_ACCESS_TOKEN", new_access_token)

    if new_refresh_token:
        _write_env_value("KAKAO_REFRESH_TOKEN", new_refresh_token)

    return new_access_token


def _send_with_token(access_token: str, text: str) -> requests.Response:
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_text = f"[{now}]\n{text}"

    template_object = {
        "object_type": "text",
        "text": full_text,
        "link": {
            "web_url": "https://developers.kakao.com",
            "mobile_web_url": "https://developers.kakao.com",
        },
    }

    return requests.post(
        url,
        headers=headers,
        data={"template_object": json.dumps(template_object, ensure_ascii=False)},
        timeout=15,
    )


def send_message(text: str) -> None:
    settings = load_settings()

    response = _send_with_token(settings.kakao_access_token, text)

    if response.status_code == 401:
        new_access_token = refresh_kakao_token()
        response = _send_with_token(new_access_token, text)

    response.raise_for_status()