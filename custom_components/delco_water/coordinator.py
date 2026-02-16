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
from homeassistant.util import dt as dt_util

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
            update_interval=timedelta(hours=24),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Fetch data from API and insert statistics."""
        try:
            # Authenticate and fetch data
            await self.hass.async_add_executor_job(self.api.authenticate)
            account_data = await self.hass.async_add_executor_job(self.api.get_account)

            # Fetch billing with usage from PDFs (new method)
            billing_with_usage = await self.hass.async_add_executor_job(
                self.api.get_billing_with_usage
            )

            # Also fetch regular billing/payment for sensors
            billing_data = await self.hass.async_add_executor_job(
                self.api.get_billing_history
            )
            payment_data = await self.hass.async_add_executor_job(
                self.api.get_payment_history
            )

            # Keep usage API call for sensor display (shows latest month)
            usage_data = await self.hass.async_add_executor_job(
                self.api.get_usage, FREQUENCY_MONTHLY
            )

            data = {
                "account": account_data,
                "usage": usage_data,
                "billing": billing_data,
                "payment": payment_data,
                "billing_with_usage": billing_with_usage,
            }

            # Insert statistics for Energy Dashboard using PDF-parsed data
            await self._insert_statistics(data)

            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _parse_service_date(self, date_str: str) -> datetime:
        """Parse service date (MM/DD/YY) to timezone-aware datetime.

        Uses Home Assistant's local timezone to ensure dates appear correctly
        in the Energy Dashboard regardless of UTC offset.

        Args:
            date_str: Date in MM/DD/YY format (e.g., "08/29/25")

        Returns:
            Timezone-aware datetime at noon local time (to avoid date shifts)
        """
        # Parse the date
        dt = datetime.strptime(date_str, "%m/%d/%y")

        # Get HA's configured timezone
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)

        # Set to noon local time to avoid any date boundary issues
        # when converting to/from UTC
        dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)

        # Make timezone-aware in local timezone, then convert to UTC
        # (HA statistics are stored in UTC)
        if local_tz:
            dt = dt.replace(tzinfo=local_tz)
            dt = dt.astimezone(timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    async def _get_last_stat_time(self, statistic_id: str) -> datetime | None:
        """Get the timestamp of the last inserted statistic."""
        try:
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,
                statistic_id,
                True,
                set(),
            )

            if last_stats and statistic_id in last_stats:
                stats_list = last_stats[statistic_id]
                if stats_list and len(stats_list) > 0:
                    last_stat = stats_list[0]
                    if "start" in last_stat:
                        return datetime.fromtimestamp(
                            last_stat["start"], tz=timezone.utc
                        )
        except Exception as err:
            _LOGGER.warning("Failed to get last statistics for %s: %s", statistic_id, err)

        return None

    async def _insert_statistics(self, data: dict) -> None:
        """Insert long-term statistics for consumption and cost.

        This method uses PDF-parsed billing data to insert aligned usage and
        cost statistics. Both are recorded at the service_to (meter read) date
        to ensure proper alignment in the Energy Dashboard.
        """
        billing_with_usage = data.get("billing_with_usage", [])

        if not billing_with_usage:
            _LOGGER.warning("No billing data with usage available from PDFs")
            return

        # Get last inserted statistics to avoid duplicates
        last_consumption_time = await self._get_last_stat_time(STATISTIC_CONSUMPTION)
        last_cost_time = await self._get_last_stat_time(STATISTIC_COST)

        _LOGGER.debug("Last consumption time: %s", last_consumption_time)
        _LOGGER.debug("Last cost time: %s", last_cost_time)

        # Build statistics lists
        consumption_statistics = []
        cost_statistics = []
        consumption_sum = 0.0
        cost_sum = 0.0

        # Process billing data (already sorted by service_to in API)
        for bill in billing_with_usage:
            try:
                # Parse service_to date as the statistics timestamp
                # This is when the meter was read
                period_start = self._parse_service_date(bill["service_to"])

                # Get values
                gallons = float(bill["usage_gallons"])
                cost = float(bill["charges"])

                # Update cumulative sums (always, even for skipped periods)
                consumption_sum += gallons
                cost_sum += cost

                # Insert consumption statistic if not already present
                if not last_consumption_time or period_start > last_consumption_time:
                    consumption_statistics.append(
                        StatisticData(
                            start=period_start,
                            state=gallons,  # This period's usage
                            sum=consumption_sum,  # Cumulative total
                        )
                    )

                # Insert cost statistic if not already present
                if not last_cost_time or period_start > last_cost_time:
                    cost_statistics.append(
                        StatisticData(
                            start=period_start,
                            state=cost,  # This period's cost
                            sum=cost_sum,  # Cumulative total
                        )
                    )

            except (ValueError, TypeError, KeyError) as err:
                _LOGGER.warning("Failed to process billing record %s: %s", bill, err)
                continue

        # Insert consumption statistics
        if consumption_statistics:
            _LOGGER.info(
                "Inserting %d consumption statistics (starting from %s)",
                len(consumption_statistics),
                consumption_statistics[0]["start"],
            )
            async_add_external_statistics(
                self.hass, CONSUMPTION_METADATA, consumption_statistics
            )
        else:
            _LOGGER.debug("No new consumption statistics to insert")

        # Insert cost statistics
        if cost_statistics:
            _LOGGER.info(
                "Inserting %d cost statistics (starting from %s)",
                len(cost_statistics),
                cost_statistics[0]["start"],
            )
            async_add_external_statistics(
                self.hass, COST_METADATA, cost_statistics
            )
        else:
            _LOGGER.debug("No new cost statistics to insert")
