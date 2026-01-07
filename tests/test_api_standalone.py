"""Standalone test script for Del-Co Water API (no Home Assistant dependencies)."""
import json
import os
from datetime import datetime, timedelta

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

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
