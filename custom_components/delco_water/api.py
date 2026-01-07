"""API client for Del-Co Water."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

import requests
from pycognito import Cognito

from .const import (
    API_BASE_URL,
    COGNITO_CLIENT_ID,
    COGNITO_REGION,
    COGNITO_USER_POOL_ID,
    FREQUENCY_DAILY,
)

_LOGGER = logging.getLogger(__name__)


class DelCoWaterAPI:
    """API client for Del-Co Water."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.access_token: str | None = None
        self.id_token: str | None = None
        self._cognito: Cognito | None = None
        self._account_data: dict[str, Any] | None = None

    def authenticate(self) -> None:
        """Authenticate with AWS Cognito."""
        try:
            # Initialize Cognito client
            self._cognito = Cognito(
                user_pool_id=COGNITO_USER_POOL_ID,
                client_id=COGNITO_CLIENT_ID,
                user_pool_region=COGNITO_REGION,
                username=self.username,
            )

            # Authenticate
            self._cognito.authenticate(password=self.password)

            # Get tokens
            self.access_token = self._cognito.access_token
            self.id_token = self._cognito.id_token

            _LOGGER.debug("Successfully authenticated with Cognito")

        except Exception as err:
            _LOGGER.error("Authentication failed: %s", err)
            raise

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        if not self.access_token:
            raise ValueError("Not authenticated")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_account(self) -> dict[str, Any]:
        """Get account information."""
        try:
            # The account endpoint expects AccessToken in body
            response = requests.post(
                f"{API_BASE_URL}/account",
                headers=self._get_headers(),
                json={"AccessToken": self.access_token},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            self._account_data = data  # Cache for usage requests
            return data
        except Exception as err:
            _LOGGER.error("Failed to get account data: %s", err)
            raise

    def get_usage(
        self,
        frequency: str = FREQUENCY_DAILY,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get water usage data.

        Args:
            frequency: Usage frequency - 'D' for daily, 'M' for monthly
            start_date: Start date in YYYY-MM-DD format (defaults to 1 year ago)
            end_date: End date in YYYY-MM-DD format (defaults to today)
        """
        try:
            # Get account data first if not cached
            if not self._account_data:
                self.get_account()

            # Extract required fields from account data
            account_info = self._account_data.get("myAccount", {})
            service_addresses = account_info.get("serviceAddresses", [])

            if not service_addresses:
                raise ValueError("No service addresses found in account")

            premise_id = service_addresses[0].get("premiseId")
            account_id = account_info.get("accountId")

            # Default date range: 1 year
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            payload = {
                "AccessToken": self.access_token,
                "premiseId": premise_id,
                "accountId": account_id,
                "frequency": frequency,
                "startDate": start_date,
                "endDate": end_date,
                "service": "SEWER",
                "admin": False,
                "email": self.username,
            }

            response = requests.post(
                f"{API_BASE_URL}/usage",
                headers=self._get_headers(),
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as err:
            _LOGGER.error("Failed to get usage data: %s", err)
            raise

    def get_ic(self) -> dict[str, Any]:
        """Get IC (Installation/Connection) authentication data."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/ic",
                headers=self._get_headers(),
                json={"AccessToken": self.access_token},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as err:
            _LOGGER.error("Failed to get IC data: %s", err)
            raise

    def get_billing_history(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get billing history data.

        Args:
            start_date: Start date in YYYY-MM-DD format (defaults to 1 year ago)
            end_date: End date in YYYY-MM-DD format (defaults to today)

        Returns:
            Billing history with dates and amounts
        """
        try:
            # Get account data first if not cached
            if not self._account_data:
                self.get_account()

            account_info = self._account_data.get("myAccount", {})
            account_id = account_info.get("accountId")

            # Default date range: 1 year
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            payload = {
                "AccessToken": self.access_token,
                "accountId": account_id,
                "startDate": start_date,
                "endDate": end_date,
                "admin": False,
                "email": self.username,
            }

            response = requests.post(
                f"{API_BASE_URL}/history/billing",
                headers=self._get_headers(),
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as err:
            _LOGGER.error("Failed to get billing history: %s", err)
            raise

    def get_payment_history(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get payment history data.

        Args:
            start_date: Start date in YYYY-MM-DD format (defaults to 2 years ago)
            end_date: End date in YYYY-MM-DD format (defaults to today)

        Returns:
            Payment history with dates, amounts, tender types and sources
        """
        try:
            # Get account data first if not cached
            if not self._account_data:
                self.get_account()

            account_info = self._account_data.get("myAccount", {})
            account_id = account_info.get("accountId")

            # Default date range: 2 years (as shown in user's CURL example)
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

            payload = {
                "AccessToken": self.access_token,
                "accountId": account_id,
                "startDate": start_date,
                "endDate": end_date,
                "admin": False,
                "email": self.username,
            }

            response = requests.post(
                f"{API_BASE_URL}/history/payment",
                headers=self._get_headers(),
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as err:
            _LOGGER.error("Failed to get payment history: %s", err)
            raise
