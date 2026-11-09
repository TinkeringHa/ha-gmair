import asyncio
from typing import Any

import aiohttp

from .const import (
    AIR_QUALITY_PATH,
    API_BASE,
    CLIENT_ID,
    CLIENT_SECRET,
    DEVICE_CITY_PATH,
    FILTER_CLEAN_PATH,
    FILTER_REPLACE_PATH,
    LIGHT_PATH,
    LOCATION_OVERVIEW_URL,
    MACHINE_LIST_PATH,
    OPERATE_PATH,
    SMS_LOGIN_PATH,
    SMS_REQUEST_PATH,
    SPEED_PATH,
    STATUS_PATH,
    TOKEN_PATH,
)

HEADERS = {
    "Origin": "https://reception.gmair.net",
    "Referer": "https://reception.gmair.net/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0 Safari/537.36",
}

TIMEOUT = aiohttp.ClientTimeout(total=25)

AUTH_STATUS_CODES = (401, 403)


class GmairError(Exception):
    pass


class GmairAuthError(GmairError):
    pass


class GmairApi:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._token: str | None = None
        self._refresh_token: str | None = None

    @property
    def token(self) -> str | None:
        return self._token

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    def set_tokens(self, token: str | None, refresh_token: str | None = None) -> None:
        self._token = token
        self._refresh_token = refresh_token

    async def _async_request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = API_BASE + path
        try:
            if method == "get":
                async with self._session.get(
                    url, params=payload or {}, headers=HEADERS, timeout=TIMEOUT
                ) as resp:
                    status = resp.status
                    text = await resp.text()
                    data = await resp.json(content_type=None) if status == 200 else None
            else:
                async with self._session.post(
                    url, data=payload or {}, headers=HEADERS, timeout=TIMEOUT
                ) as resp:
                    status = resp.status
                    text = await resp.text()
                    data = await resp.json(content_type=None) if status == 200 else None
        except aiohttp.ClientError as err:
            raise GmairError(f"{method.upper()} {path} request error: {err}") from err
        except asyncio.TimeoutError as err:
            raise GmairError(f"{method.upper()} {path} timeout") from err

        if status in AUTH_STATUS_CODES:
            raise GmairAuthError(
                f"{method.upper()} {path} unauthorized: HTTP {status} {text[:200]}".strip()
            )
        if status != 200 or data is None:
            raise GmairError(
                f"{method.upper()} {path} failed: HTTP {status} {text[:160]}"
            )
        return data

    def _with_token(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        data = dict(payload or {})
        if self._token:
            data["access_token"] = self._token
        return data

    async def _async_expect_ok(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = await self._async_request(method, path, self._with_token(payload))
        if data.get("responseCode") != "RESPONSE_OK":
            code = data.get("responseCode")
            description = data.get("description") or data.get("message") or ""
            raise GmairError(f"{method.upper()} {path} returned {code} {description}".strip())
        return data

    async def async_login(self, username: str, password: str) -> str:
        payload = {
            "username": username,
            "password": password,
            "grant_type": "password",
            "client_secret": CLIENT_SECRET,
            "client_id": CLIENT_ID,
            "scope": "select",
        }
        try:
            async with self._session.post(
                API_BASE + TOKEN_PATH, data=payload, headers=HEADERS, timeout=TIMEOUT
            ) as resp:
                if resp.status in AUTH_STATUS_CODES:
                    body = await resp.text()
                    raise GmairAuthError(f"login failed: HTTP {resp.status} {body[:160]}")
                if resp.status != 200:
                    body = await resp.text()
                    raise GmairError(f"login failed: HTTP {resp.status} {body[:160]}")
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise GmairError(f"login request error: {err}") from err
        except asyncio.TimeoutError as err:
            raise GmairError("login request timeout") from err

        token = data.get("access_token")
        if not token:
            raise GmairAuthError("login response without access_token")
        self._token = token
        self._refresh_token = data.get("refresh_token")
        return token

    async def async_refresh(self) -> str | None:
        if not self._refresh_token:
            raise GmairAuthError("no refresh token available")
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
        try:
            async with self._session.post(
                API_BASE + TOKEN_PATH, data=payload, headers=HEADERS, timeout=TIMEOUT
            ) as resp:
                status = resp.status
                body = await resp.text()
                data = await resp.json(content_type=None) if status == 200 else None
        except aiohttp.ClientError as err:
            raise GmairError(f"token refresh request error: {err}") from err
        except asyncio.TimeoutError as err:
            raise GmairError("token refresh request timeout") from err

        if status in AUTH_STATUS_CODES or status != 200 or data is None:
            raise GmairAuthError(f"token refresh failed: HTTP {status} {body[:160]}")

        token = data.get("access_token")
        if not token:
            raise GmairAuthError("refresh response without access_token")
        self._token = token
        self._refresh_token = data.get("refresh_token") or self._refresh_token
        return token

    async def async_request_code(self, phone: str) -> None:
        data = await self._async_request(
            "post", SMS_REQUEST_PATH, {"phone": phone.strip()}
        )
        if data.get("responseCode") != "RESPONSE_OK":
            description = data.get("description") or data.get("message") or ""
            raise GmairAuthError(f"request code rejected: {description}".strip())

    async def async_login_with_code(self, phone: str, code: str) -> str:
        data = await self._async_request(
            "post", SMS_LOGIN_PATH, {"phone": phone.strip(), "code": code.strip()}
        )
        if data.get("responseCode") != "RESPONSE_OK":
            description = data.get("description") or data.get("message") or ""
            raise GmairAuthError(
                f"verification code rejected: {description}".strip()
            )
        return await self.async_login(phone.strip(), code.strip())

    async def async_get_machines(self) -> list[dict[str, Any]]:
        for attempt in range(3):
            try:
                data = await self._async_expect_ok("get", MACHINE_LIST_PATH, {})
                return data.get("data") or []
            except GmairAuthError:
                if attempt == 2:
                    raise
                await asyncio.sleep(1.5)
        return []

    async def async_get_status(self, qrcode: str) -> dict[str, Any]:
        data = await self._async_expect_ok("get", STATUS_PATH, {"qrcode": qrcode})
        return data.get("data") or {}

    async def async_get_air_quality(self, city_id: str) -> dict[str, Any]:
        data = await self._async_expect_ok("get", AIR_QUALITY_PATH, {"cityId": city_id})
        rows = data.get("data") or []
        return rows[0] if rows else {}

    async def async_get_device_city_id(self, qrcode: str) -> str | None:
        data = await self._async_expect_ok("get", DEVICE_CITY_PATH, {"qrcode": qrcode})
        rows = data.get("data") or []
        return rows[0].get("cityId") if rows else None

    async def async_get_city_options(self) -> dict[str, str]:
        async with self._session.get(
            LOCATION_OVERVIEW_URL, headers=HEADERS, timeout=TIMEOUT
        ) as resp:
            if resp.status != 200:
                raise GmairError(f"location overview: HTTP {resp.status}")
            data = await resp.json(content_type=None)
        options: dict[str, str] = {}
        for province in data.get("data") or []:
            for city in province.get("children") or []:
                options[city.get("value")] = (
                    f"{province.get('label')} / {city.get('label')}"
                )
        return options

    async def async_get_filter_state(self, qrcode: str) -> dict[str, Any]:
        clean = await self._async_expect_ok(
            "get", FILTER_CLEAN_PATH, {"qrcode": qrcode}
        )
        replace = await self._async_expect_ok(
            "get", FILTER_REPLACE_PATH, {"qrcode": qrcode}
        )
        return {
            "isNeedClean": (clean.get("data") or {}).get("isNeedClean"),
            "replaceStatus": (replace.get("data") or {}).get("replaceStatus"),
        }

    async def async_operate(self, qrcode: str, key: str, value: str) -> None:
        await self._async_expect_ok(
            "post", OPERATE_PATH.format(key=key, value=value), {"qrcode": qrcode}
        )

    async def async_set_speed(self, qrcode: str, speed: int) -> None:
        await self._async_expect_ok("post", SPEED_PATH, {"qrcode": qrcode, "speed": speed})

    async def async_set_light(self, qrcode: str, light: int) -> None:
        await self._async_expect_ok("post", LIGHT_PATH, {"qrcode": qrcode, "light": light})
