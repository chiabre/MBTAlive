from datetime import timedelta
import logging
from typing import Union

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity

from homeassistant.helpers.entity import generate_entity_id

from mbtaclient.handlers.trains_handler import TrainsHandler
from mbtaclient.handlers.trips_handler import TripsHandler
from mbtaclient.client.mbta_client  import MBTAClient
from mbtaclient.client.mbta_cache_manager  import MBTACacheManager
from mbtaclient.trip import Trip

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class MBTATripCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching trips data for sensors."""

    UPDATE_INTERVAL = timedelta(seconds=20)

    def __init__(self, hass, trips_handler: Union[TripsHandler, TrainsHandler]):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MBTA Trip Data",
            update_interval=self.UPDATE_INTERVAL,
        )
        
        _LOGGER.debug("Initializing data update coordinator")
        
        self.trips_handler: Union[TripsHandler, TrainsHandler] = trips_handler
        self._last_successful_data = None  # Initialize with no data
        self._update_in_progress = False  # Flag to track if an update is in progress

    async def _async_update_data(self):
        """Fetch data from the MBTA API while preserving the last known good data during updates."""
        
        _LOGGER.debug("Starting async data update")
        
        if self._last_successful_data is not None and self._update_in_progress:
            _LOGGER.debug("Update in progress—temporarily using last known good data.")
            return self._last_successful_data  # Provide temporary data while updating

        # Mark the update as in progress
        self._update_in_progress = True

        try:
            _LOGGER.debug("Updating MBTA trips data")
            trips: list[Trip] = await self.trips_handler.update()

            if not trips:  # No trips available (e.g., end of service)
                _LOGGER.warning("No trips available—marking data as unavailable.")
                self._last_successful_data = None  # Clear last successful data
                return None  # Mark sensors as unavailable

            self._last_successful_data = trips  # Store valid data
            _LOGGER.debug("MBTA trips data update complete")
            return trips  # Return new valid data

        except UpdateFailed as e:
            _LOGGER.error("Update failed: %s", e)
            return None  # Mark sensors as unavailable

        except Exception as err:
            _LOGGER.error("Error fetching trips data: %s", err)
            return None  # Mark sensors as unavailable

        finally:
            self._update_in_progress = False  # Reset update flag
            _LOGGER.debug("Async data update complete")

class MBTABaseTripSensor(CoordinatorEntity, SensorEntity):
    """Base class for MBTA trip sensors."""

    def __init__(
        self,
        config_entry_name,
        config_entry_id,
        coordinator: MBTATripCoordinator,
        sensor_name,
        icon
    ):
        """Initialize the base sensor."""
        _LOGGER.debug("Initializing sensor: %s", sensor_name)
        
        super().__init__(coordinator)  # Ensures entity is linked to the coordinator
        
        if isinstance(self, MBTATripSensor) or isinstance(self, MBTANextTripSensor):
            entity_id = f"{sensor_name}"
        else:
            entity_id = f"({config_entry_name}_{sensor_name})"
            
        # Ensure unique ID is stable across reboots
        self._attr_unique_id = f"{config_entry_id}_{sensor_name}".lower().replace(' ', '_')
        
        #entity_id = f"{config_entry_id}_{sensor_name}"

        self._sensor_name = sensor_name
        self._coordinator = coordinator
        self._attr_config_entry_id = config_entry_id  # Link entity to config entry
        self.entity_id = generate_entity_id(
            "sensor.{}",
            f"mbta_{entity_id}",
            hass=self._coordinator.hass
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry_id)}, 
            "name": config_entry_name,
            "manufacturer": "MBTA",
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
        # Sensor is available if the coordinator update was successful
        return self._coordinator.last_update_success

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return self._attr_icon

    async def async_added_to_hass(self):
        """Called when the sensor is added to Home Assistant."""
        await super().async_added_to_hass()
        # Register the sensor to listen for updates from the coordinator
        self._coordinator.async_add_listener(self.async_write_ha_state)

    async def async_update(self):
        """Ensure sensor updates when the coordinator updates."""
        # The coordinator triggers updates automatically, so no need to call async_write_ha_state manually here
        pass


#TRIP


class MBTATripSensor(MBTABaseTripSensor):
    """Sensor for the trip."""

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.departure_countdown:
                return trip.departure_countdown
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.departure_stop_name:
                attributes["from"] = trip.departure_stop_name
            if trip.arrival_stop_name:
                attributes["to"] = trip.arrival_stop_name
            if trip.route_description:
                attributes["type"]  = trip.route_description
            if trip.route_name:
                attributes["line"]  = trip.route_name
            if trip.route_color:
                attributes["color"] = trip.route_color
            if trip.headsign:
                attributes["headsign"] = trip.headsign
            if trip.duration:
                attributes["duration"] = f"{int(round(trip.duration / 60,0))}m"
            if trip.name:
                attributes["train"] = trip.name
            if trip.vehicle_status:
                attributes["status"] = trip.vehicle_status
            if trip.vehicle_latitude:
                attributes["latitude"] = trip.vehicle_latitude
            if trip.vehicle_longitude:
                attributes["longitude"] = trip.vehicle_longitude
            if trip.departure_platform:
                attributes["departure_platform"] = trip.departure_platform
            if trip.departure_time:
                attributes["departure_time"] = trip.departure_time
            if trip.departure_time_to:
                 attributes["departure_time_to"] = f"{int(round(trip.departure_time_to / 60,0))}m"
            if trip.departure_delay:
                 attributes["departure_delay"] = f"{int(round(trip.departure_delay / 60,0))}m"
            if trip.arrival_countdown:
                attributes["arrival_countdown"] = trip.arrival_countdown  
            if trip.arrival_platform:
                attributes["arrival_platform"] = trip.arrival_platform          
            if trip.arrival_time:
                attributes["arrival_time"] = trip.arrival_time
            if trip.arrival_time_to:
                 attributes["arrival_time_to"] = f"{int(round(trip.arrival_time_to / 60,0))}m"
            if trip.arrival_delay:
                 attributes["arrival_delay"] = f"{int(round(trip.arrival_delay / 60,0))}m"
            attributes["alerts"] = []
            if trip.alerts:
                attributes["alerts"] = " # ".join(trip.alerts)
            next_trips = []
            for item in data[1:]:
                if item.departure_countdown:
                    next_trips.append(item.departure_countdown)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTANextTripSensor(MBTABaseTripSensor):
    """Sensor for the trip."""

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            if len(data) >= 1:
                trip: Trip = data[1]
                if trip.departure_countdown:
                    return trip.departure_countdown
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data:
            if len(data)>=1:
                trip: Trip = data[1]
                attributes = {}
                if trip.departure_stop_name:
                    attributes["from"] = trip.departure_stop_name
                if trip.arrival_stop_name:
                    attributes["to"] = trip.arrival_stop_name
                if trip.route_description:
                    attributes["type"]  = trip.route_description
                if trip.route_name:
                    attributes["line"]  = trip.route_name
                if trip.route_color:
                    attributes["color"] = trip.route_color
                if trip.headsign:
                    attributes["headsign"] = trip.headsign
                if trip.duration:
                    attributes["duration"] = f"{int(round(trip.duration / 60,0))}m"
                if trip.name:
                    attributes["train"] = trip.name
                if trip.vehicle_status:
                    attributes["status"] = trip.vehicle_status
                if trip.vehicle_latitude:
                    attributes["latitude"] = trip.vehicle_latitude
                if trip.vehicle_longitude:
                    attributes["longitude"] = trip.vehicle_longitude
                if trip.departure_platform:
                    attributes["departure_platform"] = trip.departure_platform
                if trip.departure_time:
                    attributes["departure_time"] = trip.departure_time
                if trip.departure_time_to:
                    attributes["departure_time_to"] = f"{int(round(trip.departure_time_to / 60,0))}m"
                if trip.departure_delay:
                    attributes["departure_delay"] = f"{int(round(trip.departure_delay / 60,0))}m"
                if trip.arrival_countdown:
                    attributes["arrival_countdown"] = trip.arrival_countdown  
                if trip.arrival_platform:
                    attributes["arrival_platform"] = trip.arrival_platform          
                if trip.arrival_time:
                    attributes["arrival_time"] = trip.arrival_time
                if trip.arrival_time_to:
                    attributes["arrival_time_to"] = f"{int(round(trip.arrival_time_to / 60,0))}m"
                if trip.arrival_delay:
                    attributes["arrival_delay"] = f"{int(round(trip.arrival_delay / 60,0))}m"
                attributes["alerts"] = []
                if trip.alerts:
                    attributes["alerts"] = " # ".join(trip.alerts)
                return attributes  # Return the dictionary of attributes
        return None
    
class MBTATrainSensor(MBTABaseTripSensor):
    """Sensor for trip name."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.name:
                return trip.name
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.name:
                    next_trips.append(item.name)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
        
class MBTAHeadsignSensor(MBTABaseTripSensor):
    """Sensor for trip headsign."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.headsign:
                return trip.headsign
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.headsign:
                    next_trips.append(item.headsign)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTADestinationSensor(MBTABaseTripSensor):
    """Sensor for trip destination."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.destination:
                return trip.destination
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.destination:
                    next_trips.append(item.destination)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
        
class MBTADirectionSensor(MBTABaseTripSensor):
    """Sensor for trip direction."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.direction:
                return trip.direction
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.direction:
                    next_trips.append(item.direction)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
        
class MBTADurationSensor(MBTABaseTripSensor):
    """Sensor for departure time."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.duration:
                return round(trip.duration / 60,0)
        return "unavailable"

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
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.duration:
                    next_trips.append(f"{round(item.duration / 60,0)}m")
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
        
#ROUTE
class MBTARouteNameSensor(MBTABaseTripSensor):
    """Sensor for trip route name."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.route_name:
                return trip.route_name
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.route_name:
                    next_trips.append(item.route_name)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTARouteTypeSensor(MBTABaseTripSensor):
    """Sensor for route type."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.route_description:
                return trip.route_description
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.route_description:
                    next_trips.append(item.route_description)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
      
class MBTARouteColorSensor(MBTABaseTripSensor):
    """Sensor for route type."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.route_color:
                return trip.route_color
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.route_color:
                    next_trips.append(item.route_color)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

#VEHICLE
class MBTAVehicleStatusSensor(MBTABaseTripSensor):
    """Sensor for vehicle status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.vehicle_status:
                return trip.vehicle_status
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.vehicle_status:
                    next_trips.append(item.vehicle_status)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTAVehicleSpeedSensor(MBTABaseTripSensor):
    """Sensor for vehicle speed."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.mbta_vehicle:
                if trip.vehicle_speed:
                    return trip.vehicle_speed
                return 0
        return "unavailable"

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return BinarySensorDeviceClass.UPDATE

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "mph"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.vehicle_speed:
                    next_trips.append(item.vehicle_speed)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTAVehicleLonSensor(MBTABaseTripSensor):
    """Sensor for vehicle longitude."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
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
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.vehicle_longitude:
                    next_trips.append(item.vehicle_longitude)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTAVehicleLatSensor(MBTABaseTripSensor):
    """Sensor for vehicle longlatitude."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
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
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.vehicle_latitude:
                    next_trips.append(item.vehicle_latitude)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTAVehicleLiveData(MBTABaseTripSensor):
    """Sensor for vehicle last update."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            return trip.is_vehicle_data_fresh
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.is_vehicle_data_fresh:
                    next_trips.append(item.is_vehicle_data_fresh)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
        
#DEPARTURE STOP
class MBTADepartureNameSensor(MBTABaseTripSensor):
    """Sensor for departure stop name."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.departure_stop_name:
                return trip.departure_stop_name
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.departure_stop_name:
                    next_trips.append(item.departure_stop_name)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTADeparturePlatformSensor(MBTABaseTripSensor):
    """Sensor for departure platform name.."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.departure_platform:
                return trip.departure_platform
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.departure_platform:
                    next_trips.append(item.departure_platform)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        
class MBTADepartureTimeSensor(MBTABaseTripSensor):
    """Sensor for departure time."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.departure_time:
                return trip.departure_time
        return "unavailable"

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.departure_time:
                    next_trips.append(item.departure_time)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTADepartureDelaySensor(MBTABaseTripSensor):
    """Sensor for departure delay."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.departure_delay:
                return round(trip.departure_delay / 60,0)
        return "unavailable"

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
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.departure_delay:
                    next_trips.append(f"{int(round(item.departure_delay / 60,0))}m")
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTADepartureTimeToSensor(MBTABaseTripSensor):
    """Sensor for departure time to."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.departure_time_to:
                time_to = round(trip.departure_time_to / 60,0)
                if time_to >= 0:
                    return time_to
                elif time_to < 0:
                    return 0
        return "unavailable"

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
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.departure_time_to:
                    departure_time_to = int(round(item.departure_time_to / 60,0))
                    if departure_time_to < 0:
                        departure_time_to = 0
                    next_trips.append(f"{departure_time_to}m")
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTADepartureMBTACountdownSensor(MBTABaseTripSensor):
    """Sensor for departure status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.departure_mbta_countdown:
                return trip.departure_mbta_countdown
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.departure_mbta_countdown:
                    next_trips.append(item.departure_mbta_countdown)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTADepartureCountdownSensor(MBTABaseTripSensor):
    """Sensor for departure countdown."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.departure_countdown:
                return trip.departure_countdown
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.departure_countdown:
                    next_trips.append(item.departure_countdown)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

#ARRIVAL STOP
class MBTAArrivalNameSensor(MBTABaseTripSensor):
    """Sensor for arrival stop name."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.arrival_stop_name:
                return trip.arrival_stop_name
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.arrival_stop_name:
                    next_trips.append(item.arrival_stop_name)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTAArrivalPlatformSensor(MBTABaseTripSensor):
    """Sensor for arrival platform name.."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.arrival_platform:
                return trip.arrival_platform
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.arrival_platform:
                    next_trips.append(item.arrival_platform)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTAArrivalTimeSensor(MBTABaseTripSensor):
    """Sensor for arrival time."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.arrival_time:
                return trip.arrival_time
        return "unavailable"

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.arrival_time:
                    next_trips.append(item.arrival_time)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None

class MBTAArrivalDelaySensor(MBTABaseTripSensor):
    """Sensor for arrival delay."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.arrival_delay:
                return round(trip.arrival_delay / 60,0)
            else:
                return 0  # Default value when there's no delay
        return "unavailable"

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
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.arrival_delay:
                    next_trips.append(f"{int(round(item.arrival_delay / 60,0))}m")
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTAArrivalTimeToSensor(MBTABaseTripSensor):
    """Sensor for arrival time to."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.arrival_time_to:
                time_to = round(trip.arrival_time_to / 60,0)
                if time_to >= 0:
                    return time_to
                elif time_to < 0:
                    return 0
        return "unavailable"

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
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.arrival_time_to:
                    arrival_time_to = int(round(item.arrival_time_to / 60,0))
                    if arrival_time_to < 0:
                        arrival_time_to = 0
                    next_trips.append(f"{arrival_time_to}m")
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        
class MBTAArrivalMBTACountdownSensor(MBTABaseTripSensor):
    """Sensor for arrival status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.arrival_mbta_countdown:
                return trip.arrival_mbta_countdown
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.arrival_mbta_countdown:
                    next_trips.append(item.arrival_mbta_countdown)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTAArrivalCountdownSensor(MBTABaseTripSensor):
    """Sensor for arrival status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            if trip.arrival_countdown:
                return trip.arrival_countdown
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data and len(data) > 0:
            attributes = {}
            next_trips = []
            for item in data[1:]:
                if item.arrival_countdown:
                    next_trips.append(item.arrival_countdown)
            if len(next_trips) >0:
                attributes["next"] = next_trips
            return attributes  # Return the dictionary of attributes
        return None
    
#ALERTS
class MBTAAlertsSensor(MBTABaseTripSensor):
    """Sensor for trip alerts."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            return len(trip.alerts) if trip.alerts else 0  # Return 0 if no alerts
        return "unavailable"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "alerts"  # Count of alerts

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.alerts:
                attributes["alerts"] = " # ".join(trip.alerts)
            return attributes  # Return the dictionary of attributes
        return None

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:

    """
    Set up the MBTA integration from a config entry.

    This function retrieves the MBTAClient instance created (or updated) in the config flow.
    If it doesn't exist (for example, after a restart), it creates a new instance using the
    API key from the config entry.
    """
        
    # Extract configuration data
    depart_from = entry.data.get("depart_from")
    arrive_at = entry.data.get("arrive_at")
    api_key = entry.data.get("api_key")
    max_trips = entry.data.get("max_trips")
    train = entry.data.get("train")
    name = entry.title
    config_entry_id = entry.entry_id
    
    _LOGGER.debug("Setting up MBTA device")

    # Ensure our integration data container exists.
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Retrieve the MBTAClient from hass.data.
    client: MBTAClient = hass.data[DOMAIN].get("mbta_client")
    if not client:
        _LOGGER.debug("MBTAClient not found; creating new instance with API key: %s", api_key)
        client: MBTAClient = MBTAClient(api_key=api_key, cache_manager=MBTACacheManager())
        hass.data[DOMAIN]["mbta_client"] = client
    else:
        _LOGGER.debug("Reusing existing MBTAClient with API key: %s", client._api_key)

    try:
        
        tmp_config_entry_id = f"{depart_from}_{arrive_at}".replace(" ", "_").lower()
        
        if train:
            _LOGGER.debug("Creating TrainsHandler for train %s and stops %s -> %s", train, depart_from, arrive_at)
            trips_handler = await TrainsHandler.create(
                departure_stop_name=depart_from,
                mbta_client=client,
                trip_name=train,
                arrival_stop_name=arrive_at,
                max_trips=max_trips,
            )
            name = f"{train} - {name}"
        else:
            # Validate the API key and stops by attempting to create a TripsHandler.
            _LOGGER.debug("Creating TripsHandler for stops %s -> %s", depart_from, arrive_at)
            trips_handler = await TripsHandler.create(
                departure_stop_name=depart_from,
                mbta_client=client,
                arrival_stop_name=arrive_at,
                max_trips=max_trips,
            )
        
        # Create and refresh the coordinator
        _LOGGER.debug("Setting up data update coordinator")
        coordinator = MBTATripCoordinator(hass, trips_handler)
        _LOGGER.debug("Updating trips data")
        await coordinator.async_config_entry_first_refresh()

        # Get the first trip and determine the route icon
        trip: Trip = coordinator.data[0]
        route_type = trip.mbta_route.type
        icon = {
            0: "mdi:subway-variant",
            1: "mdi:subway-variant",
            2: "mdi:train",
            3: "mdi:bus",
            4: "mdi:ferry",
        }.get(route_type, "mdi:train")
        
        # Create sensors
        _LOGGER.debug("Creating sensors")
        
        sensors = [
            MBTATripSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name=name,
                icon=icon),
            MBTANextTripSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name=f"{name} - Next",
                icon=icon),
            MBTAHeadsignSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Headsign",
                icon="mdi:sign-direction"),
            MBTADestinationSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Destination",
                icon="mdi:sign-direction"),
            MBTADirectionSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Direction",
                icon="mdi:sign-direction"),
            MBTADurationSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Duration",
                icon="mdi:timelapse"),
            MBTARouteNameSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Line",
                icon=icon),
            MBTARouteTypeSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Type",
                icon=icon),
            MBTARouteColorSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Color",
                icon=icon),
            MBTADepartureNameSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="From",
                icon="mdi:bus-stop-uncovered"),
            MBTADepartureTimeSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Departure Time",
                icon="mdi:clock-start"),
            MBTADepartureDelaySensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Departure Delay",
                icon="mdi:clock-alert-outline"),
            MBTADepartureTimeToSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Time To Departure",
                icon="mdi:progress-clock"),
            MBTADepartureMBTACountdownSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Departure MBTA Countdown",
                icon="mdi:timer-marker-outline"),
            MBTADepartureCountdownSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Departure Countdown",
                icon="mdi:timer-marker-outline"),
            MBTAArrivalNameSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="To",
                icon="mdi:bus-stop-uncovered"),
            MBTAArrivalTimeSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Arrival Time",
                icon="mdi:clock-end"),
            MBTAArrivalDelaySensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Arrival Delay",
                icon="mdi:clock-alert-outline"),
            MBTAArrivalTimeToSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Time To Arrival",
                icon="mdi:progress-clock"),
            MBTAArrivalMBTACountdownSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Arrival MBTA Countdown",
                icon="mdi:timer-marker-outline"),
            MBTAArrivalCountdownSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Arrival Countdown",
                icon="mdi:timer-marker-outline"),
            MBTAAlertsSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Alerts",
                icon="mdi:alert-outline"),
        ]

        #If train
        if route_type == 2:
            sensors.append( MBTATrainSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Train",
                icon=icon))

        # Not Bus
        if route_type != 3:
            sensors.append( MBTADeparturePlatformSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Departure Platform",
                icon="mdi:bus-stop-uncovered"))
            sensors.append(MBTAArrivalPlatformSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Arrival Platform",
                icon="mdi:bus-stop-uncovered"))
            
        # Not Ferry
        if route_type != 4:
            sensors.append(MBTAVehicleStatusSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Status",
                icon="mdi:map-marker-radius"))
            sensors.append(MBTAVehicleSpeedSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Speed",
                icon="mdi:speedometer"))
            sensors.append(MBTAVehicleLonSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Longitude",
                icon="mdi:map-marker"))
            sensors.append(MBTAVehicleLatSensor(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Latitude",
                icon="mdi:map-marker"))
            sensors.append(MBTAVehicleLiveData(
                config_entry_name=name,
                config_entry_id=config_entry_id,
                coordinator=coordinator,
                sensor_name="Live Data",
                icon="mdi:signal-variant"))

        # Add the sensors to Home Assistant
        async_add_entities(sensors)
        _LOGGER.debug("Setting up MBTA Trip sensors completed successfully.")
        return True

    except Exception as e:
        _LOGGER.error("Error setting up MBTA Trip sensors: %s", e)
        return False
