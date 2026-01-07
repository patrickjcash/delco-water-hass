# Del-Co Water Home Assistant Integration

Home Assistant integration for Delaware County Water Authority (Del-Co Water) to track water usage and billing data. Integrates seamlessly with Home Assistant's Energy dashboard.

## Features

- **Historical water consumption tracking** - View up to 1 year of historical usage data in the Energy Dashboard
- **Cost tracking** - Monitor water costs with historical billing data
- **Account monitoring** - Track current bill, previous balance, payments received, and balance due
- **Energy Dashboard integration** - Seamless integration with Home Assistant's native Energy Dashboard
- **Automatic statistics insertion** - Historical data is automatically backfilled on first setup
- **Automatic updates** - Data refreshes every 24 hours

**Note**: Data granularity depends on your meter type:
- **Standard meters** (non-AMI): Monthly billing data only
- **AMI meters**: May support daily or more frequent readings (if available)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL
6. Select "Integration" as the category
7. Click "Add"
8. Click "Install"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/delco_water` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. In Home Assistant, go to Configuration > Integrations
2. Click the "+ Add Integration" button
3. Search for "Del-Co Water"
4. Enter your Del-Co Water portal credentials (same as delcowaterportal.com)
5. Click Submit

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
- Supports daily and monthly usage data

## Credits

Built for Delaware County Water Authority customers who want to track their water usage in Home Assistant.

## License

MIT License
