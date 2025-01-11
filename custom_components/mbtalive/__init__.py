import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the MBTA integration."""
    _LOGGER.info("Setting up MBTA integration.")
    hass.data[DOMAIN] = {}  # Initialize the domain storage for the integration (optional)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry for MBTA."""
    _LOGGER.debug(f"Setting up entry: {entry.entry_id}")
    
    try:
        # Initialize the handler (replace SomeHandler with actual handler class)
        # handler = SomeHandler(entry.data, session=async_get_clientsession(hass))
        # await handler.initialize()
        
        # # Store the handler for later use (optional)
        # hass.data[DOMAIN][entry.entry_id] = handler
        #_LOGGER.debug(f"Handler initialized and stored for entry {entry.entry_id}")
        
        # Forward the setup to the sensor platform
        return await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    except Exception as e:
        _LOGGER.error(f"Error setting up entry {entry.entry_id}: {e}")
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"Unloading MBTA config entry: {entry.entry_id}")
    
    # # Unload associated platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, ["sensor"]):
        _LOGGER.debug(f"Successfully unloaded platforms for {entry.entry_id}")
        return True
    
    _LOGGER.warning(f"Failed to unload platforms for {entry.entry_id}")
    return False