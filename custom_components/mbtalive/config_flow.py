import logging
from typing import Dict
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from mbtaclient.handlers.trips_handler import TripsHandler
from mbtaclient.client.mbta_client import MBTAClient
from .const import DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("depart_from"): vol.All(str, vol.Length(min=3)),
        vol.Required("arrive_at"): vol.All(str, vol.Length(min=3)),
        vol.Required("api_key"): str,
    }
)

class MBTAConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MBTA integration.

    This flow allows the user to configure the MBTA integration by providing
    information about the departure and arrival stops, and an API key.
    The integration connects to the MBTA API to fetch trip information.
    """
    VERSION = 1
    _name: str = DEFAULT_NAME

    async def async_step_user(self, user_input=None):
        """Handle the user-initiated configuration step.

        This method processes the user input for configuring the integration,
        including validating the stops and API key. It attempts to connect to
        the MBTA API, and if successful, creates a configuration entry.

        Args:
            user_input (dict): The input from the user containing stop names
                                and optionally an API key.

        Returns:
            dict: The result of the configuration step, either showing the form
                  or creating the configuration entry.
        """
        errors: Dict[str, str] = {}

        if user_input is not None:
            depart_from = user_input.get("depart_from")
            arrive_at = user_input.get("arrive_at")
            api_key = user_input.get("api_key")

            # Lazy logging for user input
            _LOGGER.debug("User input received: %s", user_input)

            try:
                mbta_client = MBTAClient(api_key=api_key)
                await TripsHandler.create(departure_stop_name=depart_from, mbta_client=mbta_client, arrival_stop_name=arrive_at, max_trips=1)

                # If no exceptions are raised, the connection is successful
                _LOGGER.debug("Connection to MBTA API successful.")

            except ValueError as e:
                _LOGGER.error("Invalid input: %s", e)
                errors["base"] = "invalid_input"
            except Exception as e:
                _LOGGER.error("Unexpected error: %s", e)
                errors["base"] = str(e)

            if not errors:
                name = f"{depart_from} to {arrive_at}"
                _LOGGER.debug("Creating entry with name: %s", name)
                return self.async_create_entry(title=name, data=user_input)

        # Lazy logging for showing form with potential errors
        _LOGGER.debug("Showing form with errors (if any)")
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)
