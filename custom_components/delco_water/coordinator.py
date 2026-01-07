"""DataUpdateCoordinator for Del-Co Water."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    StatisticData,
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DelCoWaterAPI
from .const import (
    CONSUMPTION_METADATA,
    COST_METADATA,
    FREQUENCY_MONTHLY,
    STATISTIC_CONSUMPTION,
    STATISTIC_COST,
)

_LOGGER = logging.getLogger(__name__)


class DelCoWaterCoordinator(DataUpdateCoordinator):
    """Del-Co Water data update coordinator."""

    def __init__(self, hass: HomeAssistant, api: DelCoWaterAPI) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Del-Co Water",
            update_interval=timedelta(hours=6),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Fetch data from API and insert statistics."""
        try:
            # Authenticate and fetch data
            await self.hass.async_add_executor_job(self.api.authenticate)
            account_data = await self.hass.async_add_executor_job(self.api.get_account)
            usage_data = await self.hass.async_add_executor_job(
                self.api.get_usage, FREQUENCY_MONTHLY
            )
            billing_data = await self.hass.async_add_executor_job(
                self.api.get_billing_history
            )
            payment_data = await self.hass.async_add_executor_job(
                self.api.get_payment_history
            )

            data = {
                "account": account_data,
                "usage": usage_data,
                "billing": billing_data,
                "payment": payment_data,
            }

            # Insert statistics for Energy Dashboard
            await self._insert_statistics(data)

            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _insert_statistics(self, data: dict) -> None:
        """Insert long-term statistics for consumption and cost.

        This method follows the Opower pattern for backfilling historical data
        into Home Assistant's statistics database. The Energy Dashboard uses
        these statistics, not the sensor values directly.
        """
        # Get last inserted statistics to avoid duplicates
        # On first run, this will return empty, which is fine
        try:
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,
                STATISTIC_CONSUMPTION,
                True,
                set(),
            )
            _LOGGER.debug("get_last_statistics returned: %s", last_stats)
        except Exception as err:
            _LOGGER.warning("Failed to get last statistics: %s", err)
            last_stats = {}

        last_consumption_time = None
        if last_stats and STATISTIC_CONSUMPTION in last_stats:
            stats_list = last_stats[STATISTIC_CONSUMPTION]
            if stats_list and len(stats_list) > 0:
                last_stat = stats_list[0]
                _LOGGER.debug("Last stat entry: %s", last_stat)
                # StatisticsRow has 'start' as a float timestamp
                if "start" in last_stat:
                    last_consumption_time = datetime.fromtimestamp(
                        last_stat["start"], tz=timezone.utc
                    )
                    _LOGGER.debug("Last consumption time: %s", last_consumption_time)
                else:
                    _LOGGER.warning("Last stat missing 'start' key: %s", last_stat)

        # Parse usage history from API
        usage = data.get("usage", {}).get("usage", {})
        usage_history = usage.get("usageHistory", [])

        if not usage_history:
            _LOGGER.debug("No usage history data available")
            return

        # Extract usage data points (HGAL format)
        usage_data_list = usage_history[0].get("usageData", [])

        if not usage_data_list:
            _LOGGER.debug("No usage data points available")
            return

        # Build consumption statistics with cumulative sum
        consumption_statistics = []
        consumption_sum = 0.0

        for data_point in usage_data_list:
            # Parse period "2025-01" to timestamp
            period_str = data_point.get("period")
            value_str = data_point.get("value")

            if not period_str or not value_str:
                continue

            try:
                # Convert period to month start timestamp
                period_start = datetime.strptime(period_str, "%Y-%m").replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                )

                # Skip if we've already inserted this period
                if last_consumption_time and period_start <= last_consumption_time:
                    # Still need to add to sum for correct cumulative calculation
                    gallons = float(value_str) * 100  # Convert HGAL to gallons
                    consumption_sum += gallons
                    continue

                # Convert HGAL to gallons
                gallons = float(value_str) * 100
                consumption_sum += gallons

                consumption_statistics.append(
                    StatisticData(
                        start=period_start,
                        state=gallons,  # This period's usage
                        sum=consumption_sum,  # Cumulative total
                    )
                )

            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse usage data point %s: %s", data_point, err)
                continue

        # Insert consumption statistics
        if consumption_statistics:
            _LOGGER.info(
                "Inserting %d consumption statistics (starting from %s)",
                len(consumption_statistics),
                consumption_statistics[0]["start"],
            )
            async_add_external_statistics(self.hass, CONSUMPTION_METADATA, consumption_statistics)

        # Insert cost statistics from billing data
        await self._insert_cost_statistics(data)

    async def _insert_cost_statistics(self, data: dict) -> None:
        """Insert cost statistics from billing history.

        Billing data format:
        {
            "accountId": "...",
            "billing": [
                {
                    "billDate": "2025-01-15",
                    "billAmount": "41.1",
                    "readDate": "2025-01-07"
                },
                ...
            ]
        }
        """
        # Get last inserted cost statistics
        try:
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,
                STATISTIC_COST,
                True,
                set(),
            )
            _LOGGER.debug("get_last_statistics (cost) returned: %s", last_stats)
        except Exception as err:
            _LOGGER.warning("Failed to get last cost statistics: %s", err)
            last_stats = {}

        last_cost_time = None
        if last_stats and STATISTIC_COST in last_stats:
            stats_list = last_stats[STATISTIC_COST]
            if stats_list and len(stats_list) > 0:
                last_stat = stats_list[0]
                if "start" in last_stat:
                    last_cost_time = datetime.fromtimestamp(
                        last_stat["start"], tz=timezone.utc
                    )
                    _LOGGER.debug("Last cost time: %s", last_cost_time)

        # Parse billing history
        billing = data.get("billing", {}).get("billing", [])

        if not billing:
            _LOGGER.debug("No billing history data available")
            return

        # Build cost statistics with cumulative sum
        cost_statistics = []
        cost_sum = 0.0

        for bill in billing:
            bill_date_str = bill.get("billDate")
            bill_amount_str = bill.get("billAmount")

            if not bill_date_str or not bill_amount_str:
                continue

            try:
                # Parse bill date "2025-01-15" to timestamp (use read date for period alignment)
                read_date_str = bill.get("readDate")
                if read_date_str:
                    # Use read date to align with usage period
                    period_start = datetime.strptime(read_date_str, "%Y-%m-%d").replace(
                        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                    )
                else:
                    # Fall back to bill date
                    period_start = datetime.strptime(bill_date_str, "%Y-%m-%d").replace(
                        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                    )

                # Skip if we've already inserted this period
                if last_cost_time and period_start <= last_cost_time:
                    # Still need to add to sum for correct cumulative calculation
                    cost = float(bill_amount_str)
                    cost_sum += cost
                    continue

                # Parse cost
                cost = float(bill_amount_str)
                cost_sum += cost

                cost_statistics.append(
                    StatisticData(
                        start=period_start,
                        state=cost,  # This bill's amount
                        sum=cost_sum,  # Cumulative total
                    )
                )

            except (ValueError, TypeError) as err:
                _LOGGER.warning("Failed to parse billing data point %s: %s", bill, err)
                continue

        # Insert cost statistics
        if cost_statistics:
            _LOGGER.info(
                "Inserting %d cost statistics (starting from %s)",
                len(cost_statistics),
                cost_statistics[0]["start"],
            )
            async_add_external_statistics(self.hass, COST_METADATA, cost_statistics)
