import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
from mbtaclient import MBTAClient, MBTAException

class MBTAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                client = MBTAClient(api_key=user_input["api_key"])
                await self.hass.async_add_executor_job(client.get_routes)
                return self.async_create_entry(title="MBTA", data=user_input)
            except MBTAException:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_key"): str
            }),
            errors=errors
        )
