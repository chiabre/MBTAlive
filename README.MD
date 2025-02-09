# MBTALive Sensor for Home Assistant  

MBTALive is an independent project and is not affiliated with or endorsed by the Massachusetts Bay Transportation Authority (MBTA). Transit data is provided by the MBTA.  

## Overview  

MBTALive is a Home Assistant integration that provides real-time MBTA transit data, helping you monitor your commute and stay updated with transit information directly in Home Assistant.  

### Key Features:  
- **Trip and Train Tracking**: Monitor trips (departure → arrival stops) and Commuter Rail trains (train number-based tracking).  
- **Multi-Mode Support**: Works with trains, subways, buses, and ferries.  
- **Live Transit Data**: Get arrival/departure times, delays, alerts, platforms, and more.  
- **Autodiscovery**: Automatically finds the fastest direct trip between provided stops.  
- **Custom Tracking**: Choose how many subsequent trips and trains to track.  

## Features  

- **Real-time MBTA transit data** for trains, subways, and buses, including geolocation and live status updates (e.g., "in transit to," "stopped at").  
- **Schedule-based data for ferries** (no live tracking).  
- **Tracking options**:  
  - **Trip basis**: Direct connections from departure to arrival stop, **tracked until departure**.  
  - **Train basis** (Commuter Rail only): Tracks a specific train from departure to arrival stop.  
- **Customizable tracking**: Define how many subsequent trips/trains to track (default: 2).  
- **Two default sensors per trip/train**:  
  - **Upcoming trip**: First trip arriving at the departure stop.  
  - **Next trip**: The following one.  
- **Additional sensors (28 per trip/train, disabled by default)** with extended details.  
- **Trips sorted by arrival time at the destination** (fastest route prioritization).  
- **Frequent updates (every 20 sec)** for precise tracking.  
- **Optimized API usage**: Multiple caching layers reduce API calls and improve efficiency.  

### Screenshots  
Subways  
![subway](images/subway.png)  

Trains  
![train](images/train.png)  

Buses (No platform)  
![bus](images/bus.png)  

Ferries (No live update, no geolocation)  
![ferry](images/ferry.png)  

## Installation  

### 1. Install HACS (if not already installed)  
Follow the [HACS installation guide](https://hacs.xyz/).  

### 2. Add MBTALive to HACS  
1. Open **Home Assistant → HACS**.  
2. Click the three dots (top-right) → **Custom repositories**.  
3. Add `https://github.com/chiabre/MBTAlive` under **Repository** as an **Integration**.  
4. Click **Add**.  

### 3. Install MBTALive  
1. Find **MBTALive** in HACS.  
2. Click **Install** and choose a version (**2.0+ required for HACS**).  

### 4. Configure the Integration  
1. Restart Home Assistant.  
2. Go to **Settings → Devices & Services → + Add Integration**.  
3. Search for **MBTALive** and enter the required information:  
   - **Station Names**: Use valid MBTA station names (e.g., "South Station," "Park Street"). See [MBTA Stops](https://www.mbta.com/stops/subway).  
   - **MBTA API Key**:  
     1. Visit the [MBTA API Page](https://api-v3.mbta.com/).  
     2. Sign up and generate a free API key.  
   - **Number of subsequent trips to track**: Set how many upcoming trips to monitor.  
   - **Train Number**: Enter a valid Commuter Rail train number. Train numbers are listed in the [Commuter Rail Schedules](https://www.mbta.com/schedules/commuter-rail).  
     - **Note**: Setting a train number will switch the trip to train-based tracking (tracked until arrival).  

## Updating  

HACS will notify you when an update is available. To update:  
1. Go to **HACS → MBTALive**.  
2. Click **Update**.  
3. Restart Home Assistant.  

## Contributing  

Contributions are welcome! Feel free to open an issue or submit a pull request.  

## Support  

For help, open an issue in this GitHub repository.  
