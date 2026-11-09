import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GmairApi, GmairAuthError, GmairError
from .const import CONF_REFRESH_TOKEN, CONF_TOKEN, DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class GmairCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: GmairApi,
        machines: list[dict[str, Any]],
        city_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.api = api
        self.machines = machines
        self.city_id = city_id
        self.air: dict[str, Any] = {}
        self.filters: dict[str, dict[str, Any]] = {}

    async def _async_refresh_auth(self) -> None:
        token = await self.api.async_refresh()
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={
                **self.entry.data,
                CONF_TOKEN: token,
                CONF_REFRESH_TOKEN: self.api.refresh_token,
            },
        )

    async def _async_collect(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for machine in self.machines:
            qrcode = machine["codeValue"]
            result[qrcode] = await self.api.async_get_status(qrcode)

        for machine in self.machines:
            qrcode = machine["codeValue"]
            try:
                self.filters[qrcode] = await self.api.async_get_filter_state(qrcode)
            except GmairError as err:
                _LOGGER.debug("filter state for %s failed: %s", qrcode, err)

        try:
            self.air = await self.api.async_get_air_quality(self.city_id)
        except GmairError as err:
            _LOGGER.debug("air quality for %s failed: %s", self.city_id, err)

        return result

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            return await self._async_collect()
        except GmairAuthError:
            pass
        except GmairError as err:
            raise UpdateFailed(str(err)) from err

        try:
            await self._async_refresh_auth()
        except GmairAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GmairError as err:
            raise UpdateFailed(str(err)) from err

        try:
            return await self._async_collect()
        except GmairAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GmairError as err:
            raise UpdateFailed(str(err)) from err
