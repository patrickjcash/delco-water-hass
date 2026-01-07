"""Sensor platform for Del-Co Water."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


@dataclass(frozen=True)
class DelCoWaterSensorEntityDescription(SensorEntityDescription):
    """Describes Del-Co Water sensor entity."""

    value_fn: Callable[[dict[str, Any]], StateType] | None = None


def _get_latest_water_usage(data: dict[str, Any]) -> StateType:
    """Extract latest water usage from usage data."""
    usage = data.get("usage", {}).get("usage", {})
    usage_history = usage.get("usageHistory", [])

    if not usage_history:
        return None

    # Get the first history entry (Water Meter Consumption)
    history = usage_history[0]
    usage_data = history.get("usageData", [])

    if not usage_data:
        return None

    # Get the latest data point and convert from HGAL to gallons
    latest = usage_data[-1]
    value = latest.get("value")

    if value is None:
        return None

    try:
        # Convert from hundred gallons (HGAL) to gallons
        return float(value) * 100
    except (ValueError, TypeError):
        return None


def _get_account_balance(data: dict[str, Any]) -> StateType:
    """Extract account balance from account data."""
    account = data.get("account", {}).get("myAccount", {})
    balance = account.get("accountBalance")

    if balance is None:
        return None

    try:
        return float(balance)
    except (ValueError, TypeError):
        return None


def _get_latest_bill(data: dict[str, Any]) -> StateType:
    """Extract latest bill amount from account data."""
    account = data.get("account", {}).get("myAccount", {})
    bill = account.get("latestBillAmount")

    if bill is None:
        return None

    try:
        return float(bill)
    except (ValueError, TypeError):
        return None


def _get_previous_balance(data: dict[str, Any]) -> StateType:
    """Extract previous balance from account data."""
    account = data.get("account", {}).get("myAccount", {})
    previous_balance = account.get("previousBalance")

    if previous_balance is None:
        return None

    try:
        return float(previous_balance)
    except (ValueError, TypeError):
        return None


def _get_payments_received(data: dict[str, Any]) -> StateType:
    """Extract payments received from account data."""
    account = data.get("account", {}).get("myAccount", {})
    # latestPayment is negative (e.g., "-331.7"), so we'll return absolute value
    payments = account.get("latestPayment")

    if payments is None:
        return None

    try:
        return abs(float(payments))
    except (ValueError, TypeError):
        return None


# NOTE: These sensors display current/latest values for informational purposes.
# The Energy Dashboard uses STATISTICS (not sensors) for historical tracking.
# Statistics are inserted by the coordinator in __init__.py via _insert_statistics().
# This follows the Opower pattern for backfilling historical data.

SENSORS: tuple[DelCoWaterSensorEntityDescription, ...] = (
    DelCoWaterSensorEntityDescription(
        key="water_usage",
        name="Water Usage",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.GALLONS,
        suggested_display_precision=0,
        value_fn=_get_latest_water_usage,
        # This sensor shows the latest month's reading
        # Energy Dashboard uses statistic: delco_water:consumption
    ),
    DelCoWaterSensorEntityDescription(
        key="water_cost",
        name="Total Bill Last Period",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        value_fn=_get_latest_bill,
        # This sensor shows the latest bill amount
        # Energy Dashboard uses statistic: delco_water:cost
    ),
    DelCoWaterSensorEntityDescription(
        key="previous_balance",
        name="Previous Balance",
        device_class=SensorDeviceClass.MONETARY,
        state_class=None,
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        value_fn=_get_previous_balance,
    ),
    DelCoWaterSensorEntityDescription(
        key="payments_received",
        name="Payments Received",
        device_class=SensorDeviceClass.MONETARY,
        state_class=None,
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        value_fn=_get_payments_received,
    ),
    DelCoWaterSensorEntityDescription(
        key="account_balance",
        name="Balance Due",
        device_class=SensorDeviceClass.MONETARY,
        state_class=None,  # Balance can go up and down, not accumulating
        native_unit_of_measurement="USD",
        suggested_display_precision=2,
        value_fn=_get_account_balance,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Del-Co Water sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        DelCoWaterSensor(coordinator, description, entry)
        for description in SENSORS
    )


class DelCoWaterSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Del-Co Water sensor."""

    entity_description: DelCoWaterSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        description: DelCoWaterSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # Group sensors under a service device (like Opower does)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Del-Co Water",
            "manufacturer": "Delaware County Water Authority",
            "model": "Water Service",
            "entry_type": "service",  # This is a service, not a physical device
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)
        return None
