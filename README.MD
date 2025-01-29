# MBTALive Sensor for Home Assistant

## Overview

This Home Assistant integration allows to track live MBTA (Massachusetts Bay Transportation Authority) transits. 

## Features

- Real-time MBTA transit schedules and predictions.
- Configurable departure, and arrival stops.
- Frequent updates (default scan interval: 30 seconds).

## Installation

1. **HACS Installation (if not already installed):**

   If you don't have HACS (Home Assistant Community Store) installed, follow the instructions on the [HACS website](https://hacs.xyz/) to install it.

2. **Add this repository to HACS:**

   * Open Home Assistant and go to the HACS section.
   * Click the three dots in the top right corner and select "Custom repositories".
   * Add the following URL as a repository: `https://github.com/chiabre/MBTAlive`.
   * Select the category "Integration".
   * Click "Add".

3. **Install the MBTAlive integration:**

   * After adding the repository, you should see the MBTAlive integration in the HACS store.
   * Click on the MBTAlive integration.
   * Click "Install". 
   * Choose the version you want to install (only 2.X support hacs).
   * Click "Install" again.

4. **Configure the integration:**

   * After installation, restart Home Assistant.
   * Go to "Settings" -> "Devices & Services".
   * Click "+ Add Integration".
   * Search for "MBTAlive" and select it.
   * Follow the on-screen instructions to configure the integration:
    * both st (this will depend on the specific configuration options your integration requires, such as API keys, usernames, passwords, etc.).

## Updating

When a new version of the MBTAlive integration is released, you will be notified in HACS.  To update:

1. Go to the HACS section in Home Assistant.
2. Find the MBTAlive integration.
3. Click the update button.
4. Restart Home Assistant after the update is complete.

## Contributing

Contributions are welcome!  Please open an issue or submit a pull request if you have any suggestions, bug reports, or improvements.

## Support

If you have any questions or need help with the MBTAlive integration, please open an issue on this GitHub repository.

## Code of Conduct

Please note that this project has a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to abide by its terms.  (Create a `CODE_OF_CONDUCT.md` file if you don't have one already).

## Credits

(Add any credits to libraries, APIs, or other resources you used.)

## License

(Specify the license under which your integration is distributed.  For example: MIT License)

## Getting Your MBTA API Key

To use this integration, you'll need an API key from the Massachusetts Bay Transportation Authority (MBTA). Follow these steps to obtain your key:

1. Visit the [MBTA API Documentation Page](https://api-v3.mbta.com/).
2. Sign up for a free account if you haven't already.
3. Once logged in, generate a new API key.
