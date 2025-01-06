from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    client = hass.data[DOMAIN][config_entry.entry_id]
    trips = await hass.async_add_executor_job(client.get_trips)
    entities = [MBTATripSensor(client, trip) for trip in trips]
    async_add_entities(entities, True)

class MBTATripSensor(SensorEntity):
    def __init__(self, client, trip):
        self.client = client
        self.trip = trip
        self._state = None
        self._attr_name = f"Trip {trip['id']}"

    async def async_update(self):
        trip_info = await self.hass.async_add_executor_job(
            self.client.get_trip_info, self.trip["id"]
        )
        self._state = trip_info["status"]
        self._attr_extra_state_attributes = {
            "departure_time": trip_info["departure_time"],
            "arrival_time": trip_info["arrival_time"],
            "route": trip_info["route_name"]
        }
