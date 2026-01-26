# Del-Co Water Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
![GitHub Release](https://img.shields.io/github/v/release/patrickjcash/delco-water-hass?style=for-the-badge)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg?style=for-the-badge)
![License](https://img.shields.io/github/license/patrickjcash/delco-water-hass?style=for-the-badge)
![IoT Class](https://img.shields.io/badge/IoT%20Class-Cloud%20Polling-yellow.svg?style=for-the-badge)

Home Assistant integration for Delaware County Water Authority (Del-Co Water) to track water usage and billing data. Integrates seamlessly with Home Assistant's Energy dashboard.

## Features

- **Historical water consumption tracking** - View up to 1 year of historical usage data in the Energy Dashboard
- **Per-billing-period granularity** - Accurate usage and cost aligned to actual meter read dates
- **Cost tracking** - Monitor water costs with historical billing data
- **Account monitoring** - Track current bill, previous balance, payments received, and balance due
- **Energy Dashboard integration** - Seamless integration with Home Assistant's native Energy Dashboard
- **Automatic statistics insertion** - Historical data is automatically backfilled on first setup
- **Automatic updates** - Data refreshes every 24 hours

## Data Collection Method

This integration uses a **PDF parsing approach** to extract accurate per-billing-period usage data. This is necessary because Del-Co's API only provides monthly aggregated usage data, which loses granularity when there are multiple meter reads in a single calendar month.

**How it works:**
1. The integration fetches billing history from Del-Co's API
2. For each bill, it downloads the PDF from Del-Co's document storage
3. It parses the PDF to extract exact service period dates and usage amounts
4. Both usage and cost are recorded at the meter read date for proper alignment

**Important Notes:**
- PDF format changes by Del-Co may temporarily break the integration until updated
- Very old bills (12+ months) may not be available for download
- The integration handles three known PDF formats (old, mid, and new)
- If a PDF cannot be parsed, that billing period will be skipped with a warning in logs

## Installation

### Prerequisites
- Home Assistant 2024.1 or newer
- Del-Co Water portal account (delcowaterportal.com)

### HACS (Recommended)

> **Note:** This integration is not yet published in the HACS default repository. You need to add it as a **custom repository** first.

1. **Install HACS** (if not already installed)
   - Follow the official HACS installation guide: https://hacs.xyz/docs/setup/download
   - Restart Home Assistant after HACS installation

2. **Add Custom Repository**

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=patrickjcash&repository=delco-water-hass&category=integration)

   Click the badge above to add this repository to HACS directly, OR:
   - Open HACS in Home Assistant
   - Click on "Integrations"
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add this repository URL: `https://github.com/patrickjcash/delco-water-hass`
   - Select "Integration" as the category
   - Click "Add"

3. **Install Integration**
   - In HACS, search for "Del-Co Water"
   - Click on the integration
   - Click "Download"
   - Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/delco_water` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=delco_water)

1. Click the badge above to add the integration directly, OR navigate to **Settings** → **Devices & Services**
2. Click the "+ Add Integration" button
3. Search for "Del-Co Water"
4. Enter your Del-Co Water portal credentials (same as delcowaterportal.com)
5. Click Submit

The integration will automatically fetch your account data and set up sensors.

## Energy Dashboard Integration

This integration uses **long-term statistics** (not sensors) for Energy Dashboard tracking, following the same pattern as the bronze-certified Opower integration. Historical data is automatically backfilled on first setup.

### Water Consumption Tracking

1. Go to Settings → Dashboards → Energy
2. Under "Water consumption", click "Add Water Source"
3. Select the **statistic**: `Del-Co Water Consumption` (NOT the sensor)
4. Historical data (up to 1 year of monthly readings) will be visible immediately

### Cost Tracking

1. In the Energy Dashboard, under "Water consumption"
2. Click "Add Cost" or configure cost tracking
3. Select the **statistic**: `Del-Co Water Cost`
4. Historical billing data will be displayed alongside consumption

**Note**: The integration provides both sensors (for current values) and statistics (for historical tracking). The Energy Dashboard uses statistics, not sensors.

## Development

### Testing

1. Create a `.env` file with your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run tests:
   ```bash
   python tests/test_api.py
   ```

### API Details

This integration uses the Del-Co Water portal API (powered by Sparqr/ESC):
- Authentication: AWS Cognito
- API Base: `https://delco-api.cloud-esc.com/v2`
- Bill PDFs: Oracle Cloud Storage

**Endpoints used:**
- `/account` - Account information
- `/usage` - Monthly aggregated usage (for sensors)
- `/history/billing` - Billing history with read dates
- `/history/payment` - Payment history
- Bill PDFs via `billDisplayURL` pattern

**Why PDF parsing?**
The `/usage` endpoint returns data aggregated by calendar month, which causes issues when:
- There are 2+ meter reads in a single month (usage is summed, losing per-read detail)
- There are 0 meter reads in a month (no data for that month)

By parsing bill PDFs, we get the exact service period (FROM and TO dates) and precise usage for each billing cycle, enabling accurate alignment of usage and cost data in the Energy Dashboard.

## Credits

Built for Delaware County Water Authority customers who want to track their water usage in Home Assistant.

## License

MIT License
