"""API client for Del-Co Water."""
from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
import logging
import re
from typing import Any

import pdfplumber
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

    def _get_bill_pdf_base_url(self) -> str:
        """Get the base URL for bill PDFs from account data."""
        if not self._account_data:
            self.get_account()

        bill_url = self._account_data.get("myAccount", {}).get("billDisplayURL", "")
        if not bill_url:
            raise ValueError("No bill URL found in account data")

        # Extract base URL (everything before the filename)
        return bill_url.rsplit("/", 1)[0]

    def get_bill_pdf(self, bill_id: str, bill_date: str) -> bytes | None:
        """Download a bill PDF.

        Args:
            bill_id: The bill ID from billing history
            bill_date: The bill date in YYYY-MM-DD format

        Returns:
            PDF content as bytes, or None if not found
        """
        try:
            if not self._account_data:
                self.get_account()

            base_url = self._get_bill_pdf_base_url()
            account_id = self._account_data.get("myAccount", {}).get("accountId")
            bill_date_formatted = bill_date.replace("-", "")  # 2025-08-13 -> 20250813

            pdf_url = f"{base_url}/{account_id}_{bill_id}_{bill_date_formatted}.pdf"

            response = requests.get(pdf_url, timeout=30)
            if response.status_code == 200:
                return response.content

            _LOGGER.warning(
                "Bill PDF not found: %s (HTTP %d)", pdf_url, response.status_code
            )
            return None

        except Exception as err:
            _LOGGER.error("Failed to get bill PDF %s: %s", bill_id, err)
            return None

    def parse_bill_pdf(self, pdf_content: bytes) -> dict[str, Any] | None:
        """Parse bill PDF to extract usage data.

        Handles three known PDF formats:
        - new_gallons: Usage in gallons, no hyphen between dates (2025-08+)
        - mid_hgal: Usage in HGAL, hyphen between dates
        - old_hgal: Two-line format with meter ID

        Args:
            pdf_content: Raw PDF bytes

        Returns:
            Dict with service_from, service_to, usage_gallons, charges, etc.
            or None if parsing fails
        """
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                if not pdf.pages:
                    return None

                text = pdf.pages[0].extract_text()
                if not text:
                    return None

                # FORMAT 1 - NEW (2025-08+): Usage in GALLONS, no hyphen between dates
                # Water Residential Charge ADDR PREMISE MM/DD/YY MM/DD/YY PRIOR CURR USAGE $CHG
                new_pattern = (
                    r"Water Residential Charge\s+.*?"
                    r"(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})\s+"
                    r"(\d+)\s+(\d+)\s+(\d+)\s+\$?([\d.]+)"
                )
                match = re.search(new_pattern, text)
                if match:
                    return {
                        "service_from": match.group(1),
                        "service_to": match.group(2),
                        "prior_reading": int(match.group(3)),
                        "current_reading": int(match.group(4)),
                        "usage_gallons": int(match.group(5)),  # Already in gallons
                        "charges": float(match.group(6)),
                        "format": "new_gallons",
                    }

                # FORMAT 2 - MID: Usage in HGAL, hyphen between dates, commas in readings
                # Water (Residential Charge|Charges...) ADDR PREMISE MM/DD/YY - MM/DD/YY ...
                mid_pattern = (
                    r"Water (?:Residential Charge|Charges[^\d]*)\s+.*?"
                    r"(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}/\d{2}/\d{2})\s+"
                    r"([\d,]+)\s+([\d,]+)\s+(\d+)\s+\$?([\d.]+)"
                )
                match = re.search(mid_pattern, text)
                if match:
                    return {
                        "service_from": match.group(1),
                        "service_to": match.group(2),
                        "prior_reading": int(match.group(3).replace(",", "")),
                        "current_reading": int(match.group(4).replace(",", "")),
                        "usage_gallons": int(match.group(5)) * 100,  # HGAL to gallons
                        "charges": float(match.group(6)),
                        "format": "mid_hgal",
                    }

                # FORMAT 3 - OLD: Two-line format with meter ID
                # METER_ID MM/DD/YY - MM/DD/YY Actual PRIOR CURRENT USAGE_HGAL
                # Water Residential Service DAYS TOTAL USAGE ALL METERS HGAL GPD $CHARGE
                old_reading_pattern = (
                    r"(\d+)\s+(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}/\d{2}/\d{2})\s+"
                    r"Actual\s+([\d,]+)\s+([\d,]+)\s+(\d+)"
                )
                old_charge_pattern = (
                    r"Water Residential Service\s+\d+\s+"
                    r"TOTAL USAGE ALL METERS\s+(\d+)\s+[\d.]+\s+\$?([\d.]+)"
                )

                reading_match = re.search(old_reading_pattern, text)
                charge_match = re.search(old_charge_pattern, text)

                if reading_match and charge_match:
                    return {
                        "service_from": reading_match.group(2),
                        "service_to": reading_match.group(3),
                        "prior_reading": int(reading_match.group(4).replace(",", "")),
                        "current_reading": int(reading_match.group(5).replace(",", "")),
                        "usage_gallons": int(reading_match.group(6)) * 100,  # HGAL
                        "charges": float(charge_match.group(2)),
                        "format": "old_hgal",
                    }

                _LOGGER.warning("Could not parse bill PDF - unknown format")
                return None

        except Exception as err:
            _LOGGER.error("Failed to parse bill PDF: %s", err)
            return None

    def get_billing_with_usage(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get billing history enriched with per-period usage from PDFs.

        This method fetches billing history and then downloads/parses each
        bill PDF to extract the actual usage for each billing period.

        Args:
            start_date: Start date in YYYY-MM-DD format (defaults to 1 year ago)
            end_date: End date in YYYY-MM-DD format (defaults to today)

        Returns:
            List of billing records with usage data included
        """
        billing_data = self.get_billing_history(start_date, end_date)
        results = []

        for bill in billing_data.get("billing", []):
            bill_id = bill.get("billId")
            bill_date = bill.get("billDate")

            if not bill_id or not bill_date:
                continue

            pdf_content = self.get_bill_pdf(bill_id, bill_date)
            if not pdf_content:
                _LOGGER.warning(
                    "Could not fetch PDF for bill %s (%s)", bill_id, bill_date
                )
                continue

            parsed = self.parse_bill_pdf(pdf_content)
            if not parsed:
                _LOGGER.warning(
                    "Could not parse PDF for bill %s (%s)", bill_id, bill_date
                )
                continue

            # Merge billing API data with parsed PDF data
            results.append({
                "bill_id": bill_id,
                "bill_date": bill_date,
                "read_date": bill.get("readDate"),
                "due_date": bill.get("dueDate"),
                "bill_amount": bill.get("billAmount"),
                **parsed,
            })

        # Sort by service_to date
        results.sort(
            key=lambda x: datetime.strptime(x["service_to"], "%m/%d/%y")
        )

        _LOGGER.info(
            "Retrieved %d billing records with usage data", len(results)
        )
        return results
