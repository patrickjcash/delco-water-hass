"""Constants for the Del-Co Water integration."""

from homeassistant.components.recorder.statistics import StatisticMetaData
from homeassistant.const import UnitOfVolume

DOMAIN = "delco_water"

# API endpoints
API_BASE_URL = "https://delco-api.cloud-esc.com/v2"
COGNITO_REGION = "us-east-2"
COGNITO_USER_POOL_ID = "us-east-2_OicSaC5QT"
COGNITO_CLIENT_ID = "2uh8gm2iusiquj7m2tt55dfpce"

# Usage frequency options
# Note: Only monthly frequency is available for non-AMI meters
# AMI (Advanced Metering Infrastructure) meters may support additional frequencies
FREQUENCY_DAILY = "D"  # Only available for AMI meters
FREQUENCY_WEEKLY = "W"  # Only available for AMI meters
FREQUENCY_MONTHLY = "M"  # Available for all meters

# Statistics IDs for Energy Dashboard
STATISTIC_CONSUMPTION = f"{DOMAIN}:consumption"
STATISTIC_COST = f"{DOMAIN}:cost"

# Statistic names
STAT_NAME_CONSUMPTION = "Del-Co Water Consumption"
STAT_NAME_COST = "Del-Co Water Cost"

# Units
UNIT_GALLONS = UnitOfVolume.GALLONS
UNIT_CURRENCY = "USD"

# Statistics metadata for Energy Dashboard
CONSUMPTION_METADATA = StatisticMetaData(
    has_mean=False,
    has_sum=True,
    name=STAT_NAME_CONSUMPTION,
    source=DOMAIN,
    statistic_id=STATISTIC_CONSUMPTION,
    unit_of_measurement=UnitOfVolume.GALLONS,
)

COST_METADATA = StatisticMetaData(
    has_mean=False,
    has_sum=True,
    name=STAT_NAME_COST,
    source=DOMAIN,
    statistic_id=STATISTIC_COST,
    unit_of_measurement=UNIT_CURRENCY,
)
