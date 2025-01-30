from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import generate_entity_id

from mbtaclient.handlers.trips_handler import TripsHandler
from mbtaclient.client.mbta_client  import MBTAClient
from mbtaclient.client.mbta_cache_manager  import MBTACacheManager
from mbtaclient.trip import Trip
from mbtaclient.stop import StopType

_LOGGER = logging.getLogger(__name__)

class MBTATripCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching trips data for sensors."""

    def __init__(self, hass, trips_handler: TripsHandler):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MBTA Trip Data",
            update_interval=timedelta(seconds=15),
        )
        self.trips_handler: TripsHandler = trips_handler

    async def _async_update_data(self):
        """Fetch data from the MBTA API."""
        try:
            _LOGGER.debug("Fetching trips data from MBTA API")
            trips: list[Trip] = await self.trips_handler.update()
            if not trips:
                raise UpdateFailed("No trips returned from the MBTA API.")
            return trips
        except UpdateFailed as e:
            _LOGGER.error(f"Update failed: {e}")
            raise  # Re-raise to propagate the error
        except Exception as err:
            _LOGGER.error(f"Error fetching trips data: {err}")
            raise UpdateFailed(f"Error fetching trips data: {err}")

class MBTABaseTripSensor(SensorEntity):
    """Base class for MBTA trip sensors."""

    def __init__(
        self,
        config_entry_name,
        config_entry_id,
        coordinator,
        sensor_name,
        icon):
        """Initialize the base sensor."""

        self._attr_config_entry_id = config_entry_id  # Link entity to config entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{config_entry_id}-{sensor_name}"  # Unique ID for the entity
        self._sensor_name = sensor_name
        self.entity_id = generate_entity_id(
            "sensor.{}",
            f"({config_entry_name}_{sensor_name})",
            hass=self._coordinator.hass
        )
        self._attr_device_info = {
            "identifiers": {(config_entry_id,)},
            "name": config_entry_name,
            "model": "MBTA Live Trip Info",
        }
        self._attr_icon = icon 

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._sensor_name}"

    @property
    def available(self):
        """Return if the sensor is available."""
        return self._coordinator.last_update_success

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return self._attr_icon

    async def async_update(self):
        """Fetch the latest data from the coordinator."""
        await self._coordinator.async_request_refresh()


#TRIP
class MBTANameSensor(MBTABaseTripSensor):
    """Sensor for trip name."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.name:
                return trip.name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.name:
                    next.append(item.name)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTAHeadsignSensor(MBTABaseTripSensor):
    """Sensor for trip headsign."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.headsign:
                return trip.headsign
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            attributes = {}
            trip: Trip = self._coordinator.data[0]    
            if trip.direction_destination:
                attributes["destination"]  = trip.direction_destination
            if trip.direction_name:
                attributes["direction"]  = trip.direction_name
            if len(self._coordinator.data) > 0:
                next = []
                for item in self._coordinator.data[1:]:
                    if item.headsign:
                        next.append(item.headsign)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes

        return None

class MBTADestinationSensor(MBTABaseTripSensor):
    """Sensor for trip destination."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.direction_destination:
                return trip.direction_destination
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.direction_destination:
                    next.append(item.direction_destination)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTADirectionSensor(MBTABaseTripSensor):
    """Sensor for trip direction."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.direction_name:
                return trip.direction_name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.direction_name:
                    next.append(item.direction_name)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTADurationSensor(MBTABaseTripSensor):
    """Sensor for departure time."""        

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.duration:
                return round(trip.duration.total_seconds() / 60,0)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.duration:
                    next.append(round(item.duration.total_seconds() / 60,0))
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
#ROUTE
class MBTARouteNameSensor(MBTABaseTripSensor):
    """Sensor for trip route name."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.route_name:
                return trip.route_name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            attributes = {}
            if trip.route_description:
                attributes["type"] = trip.route_description
            if trip.route_color:
                attributes["color"] = f"#{trip.route_color}"
            if len(self._coordinator.data) > 0:
                next = []
                for item in self._coordinator.data[1:]:
                    if item.route_name:
                        next.append(item.route_name)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes

        return None

class MBTARouteTypeSensor(MBTABaseTripSensor):
    """Sensor for route type."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.route_description:
                return trip.route_description
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.route_description:
                    next.append(item.route_description)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
      
class MBTARouteColorSensor(MBTABaseTripSensor):
    """Sensor for route type."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.route_color:
                return f"#{trip.route_color}"
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.route_color:
                    next.append(f"#{item.route_color}")
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes  
        
        
#VEHICLE
class MBTAVehicleLonSensor(MBTABaseTripSensor):
    """Sensor for vehicle longitude."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.vehicle_longitude:
                return trip.vehicle_longitude
        return "unavailable"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "°"  # Degrees symbol for geographic coordinates

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            attributes = {}
            if trip.vehicle_updated_at:
                attributes["updated_at"]  = trip.vehicle_updated_at.replace(tzinfo=None)
            if len(self._coordinator.data) > 0:
                next = []
                for item in self._coordinator.data[1:]:
                    if item.vehicle_longitude:
                        next.append(item.vehicle_longitude)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes

        return None

class MBTAVehicleLatSensor(MBTABaseTripSensor):
    """Sensor for vehicle longlatitude."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.vehicle_latitude:
                return trip.vehicle_latitude
        return "unavailable"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "°"  # Degrees symbol for geographic coordinates
        
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            attributes = {}
            if trip.vehicle_updated_at:
                 attributes["updated_at"]  = trip.vehicle_updated_at.replace(tzinfo=None)
            if len(self._coordinator.data) > 0:
                next = []
                for item in self._coordinator.data[1:]:
                    if item.vehicle_latitude:
                        next.append(item.vehicle_latitude)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        return None

class MBTAVehicleLastUpdateSensor(MBTABaseTripSensor):
    """Sensor for vehicle last update."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.vehicle_updated_at:
                return trip.vehicle_updated_at.replace(tzinfo=None)
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.vehicle_updated_at:
                    next.append(item.vehicle_updated_at.replace(tzinfo=None))
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
#DEPARTURE STOP
class MBTADepartureNameSensor(MBTABaseTripSensor):
    """Sensor for departure stop name."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.departure_stop_name:
                return trip.departure_stop_name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            attributes = {}
            if trip.departure_platform_name:
                attributes["platform"]  = trip.departure_platform_name
            if trip.departure_status:
                attributes["live update"] = trip.departure_status
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTADeparturePlatformSensor(MBTABaseTripSensor):
    """Sensor for departure platform name.."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.departure_platform_name:
                return trip.departure_platform_name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.departure_platform_name:
                    next.append(item.departure_platform_name)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTADepartureTimeSensor(MBTABaseTripSensor):
    """Sensor for departure time."""        

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.departure_time:
                return trip.departure_time.replace(tzinfo=None)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            attributes = {}
            if trip.departure_deltatime:
                 attributes["delay"]  = f"{int(round(trip.departure_deltatime.total_seconds() / 60,0))}m"
            if trip.departure_time_to:
                 attributes["time to"]  = f"{int(round(trip.departure_time_to.total_seconds() / 60,0))}m"
            if len(self._coordinator.data) > 0:
                next = []
                for item in self._coordinator.data[1:]:
                    if item.departure_time:
                        next.append(item.departure_time.replace(tzinfo=None))
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        return None

class MBTADepartureDelaySensor(MBTABaseTripSensor):
    """Sensor for departure delay."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.departure_deltatime:
                return round(trip.departure_deltatime.total_seconds() / 60,0)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.departure_deltatime:
                    next.append(f"{int(round(item.departure_deltatime.total_seconds() / 60,0))}m")
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTADepartureTimeToSensor(MBTABaseTripSensor):
    """Sensor for departure time to."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.departure_time_to:
                time_to = round(trip.departure_time_to.total_seconds() / 60,0)
                if time_to >= 0:
                    return time_to
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.departure_time_to:
                    next.append(f"{int(round(item.departure_time_to.total_seconds() / 60,0))}m")
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
        
class MBTADepartureStatusSensor(MBTABaseTripSensor):
    """Sensor for departure status."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.departure_status:
                return trip.departure_status
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.departure_status:
                    next.append(item.departure_status)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
#ARRIVAL STOP
class MBTAArrivalNameSensor(MBTABaseTripSensor):
    """Sensor for arrival stop name."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.arrival_stop_name:
                return trip.arrival_stop_name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            attributes = {}
            if trip.arrival_platform_name:
                 attributes["platform"]  = trip.arrival_platform_name
            if trip.arrival_status:
                attributes["status"] = trip.arrival_status
            return attributes  # Return the dictionary of attributes

        return None
    
class MBTAArrivalPlatformSensor(MBTABaseTripSensor):
    """Sensor for arrival platform name.."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.arrival_platform_name:
                return trip.arrival_platform_name
        return None
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.arrival_platform_name:
                    next.append(item.arrival_platform_name)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes

class MBTAArrivalTimeSensor(MBTABaseTripSensor):
    """Sensor for arrival time."""        

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.arrival_time:
                return trip.arrival_time.replace(tzinfo=None)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            attributes = {}
            trip: Trip = self._coordinator.data[0]
            if trip.arrival_deltatime:
                attributes["delay"] = f"{int(round(trip.arrival_deltatime.total_seconds() / 60,0))}m"
            if trip.arrival_time_to:
                attributes["time to"] = f"{int(round(trip.arrival_time_to.total_seconds() / 60,0))}m"
            if trip.arrival_status:
                attributes["status"] = trip.arrival_status
            if len(self._coordinator.data) > 0:
                next = []
                for item in self._coordinator.data[1:]:
                    if item.arrival_time:
                        next.append(item.arrival_time.replace(tzinfo=None))
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        return None

class MBTAArrivalDelaySensor(MBTABaseTripSensor):
    """Sensor for arrival delay."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.arrival_deltatime:
                return round(trip.arrival_deltatime.total_seconds() / 60,0)
            else:
                return 0  # Default value when there's no delay
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.arrival_deltatime:
                    next.append(round(item.arrival_deltatime.total_seconds() / 60,0))
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTAArrivalTimeToSensor(MBTABaseTripSensor):
    """Sensor for arrival time to."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.arrival_time_to:
                time_to = round(trip.arrival_time_to.total_seconds() / 60,0)
                if time_to >= 0:
                    return time_to
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.arrival_time_to:
                    next.append(round(item.arrival_time_to.total_seconds() / 60,0))
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTAArrivalStatusSensor(MBTABaseTripSensor):
    """Sensor for arrival status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.arrival_status:
                return trip.arrival_status
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data and len(self._coordinator.data) > 0:
            attributes = {}
            next = []
            for item in self._coordinator.data[1:]:
                if item.arrival_status:
                    next.append(item.arrival_status)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes

#ALERTS
class MBTAAlertsSensor(MBTABaseTripSensor):
    """Sensor for trip alerts."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            if trip.mbta_alerts:
                return len(trip.mbta_alerts)
        return 0

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "alerts"  # Count of alerts

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data[0]
            attributes = {}
            # Add alerts
            if trip.mbta_alerts:
                alerts = ", ".join(mbta_alert.short_header for mbta_alert in trip.mbta_alerts)
                attributes["alerts"] = alerts
            return attributes  # Return the dictionary of attributes
        return None

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up MBTA Trip sensors")

    # Extract configuration data
    depart_from = entry.data.get("depart_from")
    arrive_at = entry.data.get("arrive_at")
    api_key = entry.data.get("api_key")
    name = entry.title
    config_entry_id = entry.entry_id

    try:
        _LOGGER.debug(f"Initializing MBTAClient with API key {api_key}")

        mbta_client = MBTAClient(api_key=api_key,cache_manager=MBTACacheManager())
        
        _LOGGER.debug(f"Creating TripsHandler for departure from {depart_from} to {arrive_at}")

        trips_handler = await TripsHandler.create(departure_stop_name=depart_from, mbta_client=mbta_client,arrival_stop_name=arrive_at, sort_by=StopType.ARRIVAL, max_trips=2)

        # Create and refresh the coordinator
        coordinator = MBTATripCoordinator(hass, trips_handler)

        _LOGGER.debug("Refreshing coordinator")

        await coordinator.async_config_entry_first_refresh()

        # Get the first trip and determine the route icon
        trip: Trip = coordinator.data[0]
        route_type = trip.route_type
        icon = {
            0: "mdi:subway-variant",
            1: "mdi:subway-variant",
            2: "mdi:train",
            3: "mdi:bus",
            4: "mdi:ferry",
        }.get(route_type, "mdi:train")

        # Create sensors
        _LOGGER.debug("Creating sensors for trip data")
        sensors = [
            MBTAHeadsignSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Headsign",icon="mdi:sign-direction"),
            MBTADestinationSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Destination",icon="mdi:sign-direction"),
            MBTADirectionSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Direction",icon="mdi:sign-direction"),
            MBTADurationSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Duration",icon="mdi:timelapse"),  
            MBTARouteNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Line",icon=icon),
            MBTARouteTypeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Type",icon=icon),
            MBTARouteColorSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Color",icon=icon),
            MBTAVehicleLonSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Vehicle Longitude",icon="mdi:map-marker"),
            MBTAVehicleLatSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Vehicle Latitude",icon="mdi:map-marker"),
            MBTAVehicleLastUpdateSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Vehicle Last Update",icon="mdi:update"),
            MBTADepartureNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="From",icon="mdi:bus-stop-uncovered",),
            MBTADepartureTimeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Time",icon="mdi:clock-start"),
            MBTADepartureDelaySensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Delay",icon="mdi:clock-alert-outline"),
            MBTADepartureTimeToSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Time To Departure",icon="mdi:progress-clock"),
            MBTADepartureStatusSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Live Status",icon="mdi:wifi"),
            MBTAArrivalNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="To",icon="mdi:bus-stop-uncovered"),
            MBTAArrivalTimeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Time",icon="mdi:clock-end"),
            MBTAArrivalDelaySensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Delay",icon="mdi:clock-alert-outline"),
            MBTAArrivalTimeToSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Time To Arrival",icon="mdi:progress-clock"),
            MBTAArrivalStatusSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Live Status",icon="mdi:wifi"),
            MBTAAlertsSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Alerts",icon="mdi:alert-outline"),
        ]

        if route_type == 2:
            mbta_name_sensor = MBTANameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Train",icon=icon)
            sensors.append(mbta_name_sensor)
        if route_type != 3:
            mbta_departure_platform_sensor = MBTADeparturePlatformSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Platform",icon="mdi:bus-stop-uncovered")
            sensors.append(mbta_departure_platform_sensor)
            mbta_arrival_platform_sensor = MBTAArrivalPlatformSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Platform",icon="mdi:bus-stop-uncovered")
            sensors.append(mbta_arrival_platform_sensor)

        # Add the sensors to Home Assistant
        async_add_entities(sensors)
        _LOGGER.debug("Setting up MBTA Trip sensors completed successfully.")
        return True

    except Exception as e:
        _LOGGER.error(f"Error setting up MBTA Trip sensors: {e}")
        return False
