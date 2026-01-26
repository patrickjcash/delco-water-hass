"""Standalone test script for Del-Co Water API (no Home Assistant dependencies)."""
import json
import os
import re
from datetime import datetime, timedelta
from io import BytesIO

import pdfplumber
import requests
from pycognito import Cognito
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
API_BASE_URL = "https://delco-api.cloud-esc.com/v2"
COGNITO_REGION = "us-east-2"
COGNITO_USER_POOL_ID = "us-east-2_OicSaC5QT"
COGNITO_CLIENT_ID = "2uh8gm2iusiquj7m2tt55dfpce"
FREQUENCY_DAILY = "D"
FREQUENCY_MONTHLY = "M"


class DelCoWaterAPI:
    """API client for Del-Co Water."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.access_token = None
        self.id_token = None
        self._cognito = None
        self._account_data = None

    def authenticate(self) -> None:
        """Authenticate with AWS Cognito."""
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

        print(f"✓ Authentication successful")

    def _get_headers(self):
        """Get headers for API requests."""
        if not self.access_token:
            raise ValueError("Not authenticated")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_account(self):
        """Get account information."""
        response = requests.post(
            f"{API_BASE_URL}/account",
            headers=self._get_headers(),
            json={"AccessToken": self.access_token},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        self._account_data = data
        return data

    def get_usage(self, frequency=FREQUENCY_DAILY, start_date=None, end_date=None):
        """Get water usage data."""
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

    def get_ic(self):
        """Get IC (Installation/Connection) authentication data."""
        response = requests.post(
            f"{API_BASE_URL}/auth/ic",
            headers=self._get_headers(),
            json={"AccessToken": self.access_token},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_billing_history(self, start_date=None, end_date=None):
        """Get billing history data."""
        if not self._account_data:
            self.get_account()

        account_info = self._account_data.get("myAccount", {})
        account_id = account_info.get("accountId")

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

    def _get_bill_pdf_base_url(self):
        """Get the base URL for bill PDFs."""
        if not self._account_data:
            self.get_account()

        bill_url = self._account_data.get("myAccount", {}).get("billDisplayURL", "")
        return bill_url.rsplit("/", 1)[0]

    def get_bill_pdf(self, bill_id, bill_date):
        """Download a bill PDF."""
        if not self._account_data:
            self.get_account()

        base_url = self._get_bill_pdf_base_url()
        account_id = self._account_data.get("myAccount", {}).get("accountId")
        bill_date_formatted = bill_date.replace("-", "")

        pdf_url = f"{base_url}/{account_id}_{bill_id}_{bill_date_formatted}.pdf"

        response = requests.get(pdf_url, timeout=30)
        if response.status_code == 200:
            return response.content
        return None

    def parse_bill_pdf(self, pdf_content):
        """Parse bill PDF to extract usage data."""
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            if not pdf.pages:
                return None

            text = pdf.pages[0].extract_text()
            if not text:
                return None

            # FORMAT 1 - NEW: Usage in GALLONS, no hyphen between dates
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
                    "usage_gallons": int(match.group(5)),
                    "charges": float(match.group(6)),
                    "format": "new_gallons",
                }

            # FORMAT 2 - MID: Usage in HGAL, hyphen between dates
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
                    "usage_gallons": int(match.group(5)) * 100,
                    "charges": float(match.group(6)),
                    "format": "mid_hgal",
                }

            # FORMAT 3 - OLD: Two-line format with meter ID
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
                    "usage_gallons": int(reading_match.group(6)) * 100,
                    "charges": float(charge_match.group(2)),
                    "format": "old_hgal",
                }

            return None

    def get_billing_with_usage(self, start_date=None, end_date=None):
        """Get billing history enriched with per-period usage from PDFs."""
        billing_data = self.get_billing_history(start_date, end_date)
        results = []

        for bill in billing_data.get("billing", []):
            bill_id = bill.get("billId")
            bill_date = bill.get("billDate")

            if not bill_id or not bill_date:
                continue

            pdf_content = self.get_bill_pdf(bill_id, bill_date)
            if not pdf_content:
                continue

            parsed = self.parse_bill_pdf(pdf_content)
            if not parsed:
                continue

            results.append({
                "bill_id": bill_id,
                "bill_date": bill_date,
                "read_date": bill.get("readDate"),
                **parsed,
            })

        results.sort(key=lambda x: datetime.strptime(x["service_to"], "%m/%d/%y"))
        return results


def test_authentication():
    """Test authentication with Cognito."""
    print("Testing authentication...")
    username = os.getenv("DELCO_USERNAME")
    password = os.getenv("DELCO_PASSWORD")

    if not username or not password:
        print("ERROR: DELCO_USERNAME and DELCO_PASSWORD must be set in .env file")
        return None

    api = DelCoWaterAPI(username, password)
    api.authenticate()

    print(f"  Access Token: {api.access_token[:50]}...")
    print(f"  ID Token: {api.id_token[:50]}...")

    return api


def test_account(api):
    """Test getting account information."""
    print("\nTesting account data...")
    account_data = api.get_account()

    print(f"✓ Account data retrieved")
    print(f"\n{json.dumps(account_data, indent=2)}")

    # Extract key information
    my_account = account_data.get("myAccount", {})
    print(f"\nAccount Summary:")
    print(f"  Account ID: {my_account.get('accountId')}")
    print(f"  Name: {my_account.get('personName')}")
    print(f"  Email: {my_account.get('email')}")
    print(f"  Current Balance: ${my_account.get('accountBalance')}")
    print(f"  Latest Bill: ${my_account.get('latestBillAmount')}")
    print(f"  Due Date: {my_account.get('dueDate')}")

    service_addresses = my_account.get("serviceAddresses", [])
    if service_addresses:
        print(f"\nService Addresses:")
        for addr in service_addresses:
            print(f"  - {addr.get('serviceAddress')}")
            print(f"    Premise ID: {addr.get('premiseId')}")


def test_ic(api):
    """Test getting IC (Installation/Connection) data."""
    print("\nTesting IC data...")
    ic_data = api.get_ic()

    print(f"✓ IC data retrieved")
    print(f"\n{json.dumps(ic_data, indent=2)}")


def test_usage_monthly(api):
    """Test getting monthly usage data."""
    print("\nTesting monthly usage data...")
    usage_data = api.get_usage(frequency=FREQUENCY_MONTHLY)

    print(f"✓ Monthly usage data retrieved")
    print(f"\n{json.dumps(usage_data, indent=2)}")

    # Extract usage information
    usage = usage_data.get("usage", {})
    usage_history = usage.get("usageHistory", [])

    if usage_history:
        print(f"\nMonthly Usage Summary:")
        for history in usage_history:
            uom = history.get("uom")
            sqi = history.get("sqi")
            print(f"\n  {sqi} ({uom}):")
            for data_point in history.get("usageData", []):
                period = data_point.get("period")
                value = data_point.get("value")
                print(f"    {period}: {value} {uom}")


def test_usage_daily(api):
    """Test getting daily usage data."""
    print("\nTesting daily usage data...")
    usage_data = api.get_usage(frequency=FREQUENCY_DAILY)

    print(f"✓ Daily usage data retrieved")
    print(f"\n{json.dumps(usage_data, indent=2)}")

    # Extract usage information
    usage = usage_data.get("usage", {})
    usage_history = usage.get("usageHistory", [])

    if usage_history:
        print(f"\nDaily Usage Summary:")
        for history in usage_history:
            uom = history.get("uom")
            sqi = history.get("sqi")
            print(f"\n  {sqi} ({uom}):")
            data_points = history.get("usageData", [])
            print(f"    Total data points: {len(data_points)}")
            if data_points:
                print(f"    Sample (first 10):")
                for data_point in data_points[:10]:
                    period = data_point.get("period")
                    value = data_point.get("value")
                    print(f"      {period}: {value} {uom}")
                print(f"    Sample (last 10):")
                for data_point in data_points[-10:]:
                    period = data_point.get("period")
                    value = data_point.get("value")
                    print(f"      {period}: {value} {uom}")


def test_billing_history(api):
    """Test getting billing history."""
    print("\nTesting billing history...")
    billing_data = api.get_billing_history()

    print(f"✓ Billing history retrieved")
    print(f"  Total bills: {len(billing_data.get('billing', []))}")

    for bill in billing_data.get("billing", []):
        print(f"  - {bill.get('billDate')}: ${bill.get('billAmount')} (read: {bill.get('readDate')})")


def test_billing_with_usage(api):
    """Test getting billing with usage from PDFs."""
    print("\nTesting billing with usage (PDF parsing)...")
    billing_with_usage = api.get_billing_with_usage()

    print(f"✓ Billing with usage retrieved")
    print(f"  Total bills parsed: {len(billing_with_usage)}")

    print("\n  Per-Billing-Period Usage:")
    print("  " + "-" * 70)
    print(f"  {'Service Period':<25} {'Usage (gal)':<15} {'Cost':<12} {'Format'}")
    print("  " + "-" * 70)

    for bill in billing_with_usage:
        period = f"{bill['service_from']} - {bill['service_to']}"
        usage = f"{bill['usage_gallons']:,}"
        cost = f"${bill['charges']:.2f}"
        fmt = bill["format"]
        print(f"  {period:<25} {usage:<15} {cost:<12} {fmt}")

    # Verify totals match API
    print("\n  Verification (grouped by service_to month):")
    from collections import defaultdict
    monthly = defaultdict(int)
    for bill in billing_with_usage:
        month = "20" + bill["service_to"][6:8] + "-" + bill["service_to"][0:2]
        monthly[month] += bill["usage_gallons"] // 100  # HGAL

    for month in sorted(monthly.keys()):
        print(f"    {month}: {monthly[month]} HGAL")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Del-Co Water API Test Suite")
    print("=" * 60)

    # Test authentication
    api = test_authentication()
    if not api:
        return

    try:
        # Test account
        test_account(api)

        # Test IC
        test_ic(api)

        # Test monthly usage
        test_usage_monthly(api)

        # Test daily usage
        test_usage_daily(api)

        # Test billing history
        test_billing_history(api)

        # Test billing with usage (PDF parsing)
        test_billing_with_usage(api)

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
