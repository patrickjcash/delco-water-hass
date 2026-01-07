# Development Guide

## Project Structure

```
del-co-water-usage/
├── custom_components/
│   └── delco_water/
│       ├── __init__.py          # Integration setup and coordinator
│       ├── api.py               # API client for Del-Co Water
│       ├── config_flow.py       # Configuration flow
│       ├── const.py             # Constants
│       ├── manifest.json        # Integration metadata
│       ├── sensor.py            # Sensor entities
│       ├── strings.json         # UI strings
│       └── translations/
│           └── en.json          # English translations
├── tests/
│   ├── test_api.py              # Test suite (requires Home Assistant)
│   └── test_api_standalone.py  # Standalone test suite
├── .env                         # Environment variables (DO NOT COMMIT)
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── hacs.json                    # HACS metadata
├── LICENSE                      # MIT License
├── README.md                    # User documentation
├── DEVELOPMENT.md               # This file
└── requirements.txt             # Python dependencies
```

## API Details

### Platform
- **Provider**: Sparqr (ESC cloud platform)
- **Base URL**: `https://delco-api.cloud-esc.com/v2`
- **Authentication**: AWS Cognito
  - Region: `us-east-2`
  - User Pool ID: `us-east-2_OicSaC5QT`
  - Client ID: `2uh8gm2iusiquj7m2tt55dfpce`

### Endpoints

1. **POST /account**
   - Returns account information, billing details, service addresses
   - Body: `{"AccessToken": "..."}`

2. **POST /usage**
   - Returns water usage data
   - Supports frequencies: `M` (monthly), `D` (daily - if AMI meter)
   - Body:
     ```json
     {
       "AccessToken": "...",
       "premiseId": "...",
       "accountId": "...",
       "frequency": "M",
       "startDate": "2025-01-07",
       "endDate": "2026-01-07",
       "service": "SEWER",
       "admin": false,
       "email": "..."
     }
     ```

3. **POST /auth/ic**
   - Returns installation/connection auth token
   - Body: `{"AccessToken": "..."}`

### Data Format

Usage data is returned in HGAL (hundred gallons):
```json
{
  "accountId": "...",
  "usage": {
    "status": "true",
    "premiseId": "...",
    "frequency": "M",
    "usageHistory": [
      {
        "uom": "HGAL",
        "sqi": "Water Meter Consumption",
        "usageData": [
          {"period": "2025-01", "value": "80"},
          {"period": "2025-03", "value": "70"}
        ]
      }
    ]
  }
}
```

## Testing

### Setup

1. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

### Run Tests

```bash
source venv/bin/activate
python tests/test_api_standalone.py
```

This will:
- Authenticate with Cognito
- Fetch account data
- Fetch IC data
- Fetch monthly usage data
- Attempt to fetch daily usage data (may not be available for non-AMI meters)

## Home Assistant Integration

### Installation for Testing

1. Copy `custom_components/delco_water` to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click "+ Add Integration"
5. Search for "Del-Co Water"
6. Enter your credentials

### Sensors Created

1. **Water Usage** (`sensor.delco_water_water_usage`)
   - Device class: `water`
   - State class: `total_increasing`
   - Unit: gallons
   - Shows cumulative water usage (latest reading from monthly data)

2. **Account Balance** (`sensor.delco_water_account_balance`)
   - Device class: `monetary`
   - Unit: USD
   - Shows current account balance

3. **Latest Bill Amount** (`sensor.delco_water_latest_bill`)
   - Device class: `monetary`
   - Unit: USD
   - Shows the amount of the most recent bill

### Energy Dashboard

The water usage sensor is automatically compatible with Home Assistant's Energy dashboard:
1. Go to Configuration > Energy
2. Click "Add Water Source"
3. Select "Del-Co Water - Water Usage"

## Notes

- The integration updates every 6 hours (configurable in `__init__.py`)
- **Data granularity is limited by meter type**:
  - Non-AMI meters: Only monthly (M) frequency available
  - AMI meters: May support daily (D) or weekly (W) frequencies
  - Tested frequencies: D, W, M, Q, Y, H, 15, 30, 60, B, S - only M returned data for non-AMI meters
- Usage values are stored in HGAL (hundred gallons) in the API and converted to gallons in the sensor
- The API returns: `"HGAL-Water Measurement not found for the Device for the given period"` for unsupported frequencies

## Future Enhancements

- [ ] Support for multiple service addresses
- [ ] Historical data import for long-term tracking
- [ ] Bill payment notifications
- [ ] Leak detection alerts (if daily data becomes available)
- [ ] Configurable update interval
- [ ] Support for other ESC-based water utilities
