import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import GmairApi, GmairAuthError, GmairError
from .const import (
    AUTH_PASSWORD,
    AUTH_SMS,
    CONF_AUTH_METHOD,
    CONF_CITY_ID,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN,
    CONF_USERNAME,
    DEFAULT_CITY_ID,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import GmairCoordinator

_LOGGER = logging.getLogger(__name__)


async def _async_authenticate(hass: HomeAssistant, entry: ConfigEntry) -> GmairApi:
    api = GmairApi(
        async_create_clientsession(hass, cookie_jar=aiohttp.DummyCookieJar())
    )
    method = entry.data.get(CONF_AUTH_METHOD, AUTH_PASSWORD)

    if method == AUTH_SMS:
        token = entry.data.get(CONF_TOKEN)
        if not token:
            raise ConfigEntryAuthFailed("missing access token, reauth required")
        api.set_tokens(token, entry.data.get(CONF_REFRESH_TOKEN))
        return api

    if CONF_PASSWORD not in entry.data:
        raise ConfigEntryAuthFailed("missing credentials, reauth required")

    try:
        await api.async_login(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    except GmairAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except GmairError as err:
        raise ConfigEntryNotReady(str(err)) from err
    return api


def _async_persist_tokens(
    hass: HomeAssistant, entry: ConfigEntry, api: GmairApi
) -> None:
    new_data: dict[str, str] = {}
    if api.token and api.token != entry.data.get(CONF_TOKEN):
        new_data[CONF_TOKEN] = api.token
    if api.refresh_token and api.refresh_token != entry.data.get(CONF_REFRESH_TOKEN):
        new_data[CONF_REFRESH_TOKEN] = api.refresh_token
    if new_data:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, **new_data}
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = await _async_authenticate(hass, entry)
    _async_persist_tokens(hass, entry, api)

    try:
        machines = await api.async_get_machines()
    except GmairAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except GmairError as err:
        raise ConfigEntryNotReady(str(err)) from err

    if not machines:
        raise ConfigEntryNotReady("no machine found in this account")

    city_id = entry.options.get(CONF_CITY_ID) or DEFAULT_CITY_ID
    if CONF_CITY_ID not in entry.options:
        try:
            city_id = (
                await api.async_get_device_city_id(machines[0]["codeValue"])
                or DEFAULT_CITY_ID
            )
        except GmairError as err:
            _LOGGER.debug("city id for %s failed: %s", machines[0]["codeValue"], err)

    coordinator = GmairCoordinator(hass, entry, api, machines, city_id)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform(platform) for platform in PLATFORMS]
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


@callback
async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
