# MBTALive Sensor for Home Assistant

## Overview

This Home Assistant integration allows you to track live MBTA (Massachusetts Bay Transportation Authority) transit schedules and predictions. By configuring your desired routes, departure, and arrival stops, you can receive real-time updates on expected arrival and departure times, delays, and other transit information.

This project is inspired by the [MBTA Predictions](https://github.com/dhanani94/mbta_predictions). It aims to address the new API key requirement and enhance the original project with additional features and customization options (WIP).

## Features

- Real-time MBTA transit schedules and predictions.
- Configurable routes, departure, and arrival stops.
- Time offsets for precise scheduling.
- Support for round trips.
- Frequent updates (default scan interval: 30 seconds).

## Installation

1. Get the [MBTA api key](##-Getting-Your-MBTA-API-Key).
2. Obtaion the [configuration valeus](##-How-to-Obtain-Configuration-Values)
2. Copy the custom_component directory into the root directory.

## Configuration

To enable this sensor, add the following lines to your `configuration.yaml` file:

### Configuration Variables

- **api_key**: (Required) Your MBTA API key.
- **trips**: (Optional) A list of trips to monitor. Each trip can have the following attributes:
  - **name**: (Optional) A custom name for the trip. Defaults to `MBTA`.
  - **route**: (Required) The route name.
  - **depart_from**: (Required) The departure stop name.
  - **arrive_at**: (Required) The arrival stop name.
  - **round_trip**: (Optional) Whether to include the return trip. Defaults to `false`.
  - **offset_minutes**: (Optional) Time offset in minutes, trips leaving earlier than the offset won't be shown. Defaults to `0`.
  - **trips_limit**: (Optional) The maximum number of trips to show. Defaults to `2`.

### Example Configuration

```yaml
sensor:
  - platform: mbta
    api_key: YOUR_MBTA_API_KEY
    trips:
      - name: "Morning Commute"
        route: "Red Line"
        depart_from: "Alewife"
        arrive_at: "Harvard"
        round_trip: false
        offset_minutes: 10
        trips_limit: 5
      - name: "Evening Commute"
        route: "Red Line"
        depart_from: "Harvard"
        arrive_at: "Alewife"
        round_trip: true
        offset_minutes: 5
        trips_limit: 3
```        

## Getting Your MBTA API Key

To use this integration, you'll need an API key from the Massachusetts Bay Transportation Authority (MBTA). Follow these steps to obtain your key:

1. Visit the [MBTA API Documentation Page](https://api-v3.mbta.com/).
2. Sign up for a free account if you haven't already.
3. Once logged in, generate a new API key.

## How to Obtain Configuration Values

### Route
1. Visit the [MBTA website](https://www.mbta.com).
2. Navigate to the "Schedules & Maps" section.
3. Choose the line you are interested in, such as the "Red Line." The name of the route (e.g., "Red Line") is the value you will use for the `route` configuration option.

### Depart_from
1. On the MBTA website, find the schedule for your chosen route (e.g., "Red Line").
2. Look at the list of stations along the route.
3. Choose your departure station (e.g., "Alewife"). This is the value you will use for the `depart_from` configuration option.

### Arrive_at
1. Similarly, on the MBTA website, look at the list of stations along your chosen route.
2. Choose your arrival station (e.g., "South Station"). This is the value you will use for the `arrive_at` configuration option.
