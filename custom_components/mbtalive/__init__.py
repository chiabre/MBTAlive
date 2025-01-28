import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the MBTA integration."""
    _LOGGER.info("Setting up MBTA integration.")
    
    try:
        hass.data.setdefault(DOMAIN, {})  # Initialize domain data storage safely
        _LOGGER.debug(f"{DOMAIN} data initialized: {hass.data[DOMAIN]}")
        return True
    except Exception as e:
        _LOGGER.error(f"Error during async_setup: {e}")
        return False

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry for MBTA."""
    _LOGGER.debug(f"Setting up entry: {entry.entry_id}")
    
    try:
        # Example: If using a handler, initialize and store it (commented as placeholder)
        # handler = SomeHandler(entry.data, session=async_get_clientsession(hass))
        # await handler.initialize()
        # hass.data[DOMAIN][entry.entry_id] = handler
        
        _LOGGER.debug(f"Forwarding setup to sensor platform for entry {entry.entry_id}")
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        return True
    except Exception as e:
        _LOGGER.error(f"Error setting up entry {entry.entry_id}: {e}")
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"Unloading MBTA config entry: {entry.entry_id}")
    
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
        if unload_ok:
            _LOGGER.debug(f"Successfully unloaded platforms for entry {entry.entry_id}")
            return True
        else:
            _LOGGER.warning(f"Failed to unload platforms for entry {entry.entry_id}")
            return False
    except Exception as e:
        _LOGGER.error(f"Error during unloading entry {entry.entry_id}: {e}")
        return False
