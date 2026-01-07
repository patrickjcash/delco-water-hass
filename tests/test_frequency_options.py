"""Test different frequency options for usage data."""
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
        self._cognito = Cognito(
            user_pool_id=COGNITO_USER_POOL_ID,
            client_id=COGNITO_CLIENT_ID,
            user_pool_region=COGNITO_REGION,
            username=self.username,
        )
        self._cognito.authenticate(password=self.password)
        self.access_token = self._cognito.access_token
        self.id_token = self._cognito.id_token

    def _get_headers(self):
        """Get headers for API requests."""
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

    def get_usage(self, frequency, start_date=None, end_date=None):
        """Get water usage data."""
        if not self._account_data:
            self.get_account()

        account_info = self._account_data.get("myAccount", {})
        service_addresses = account_info.get("serviceAddresses", [])
        premise_id = service_addresses[0].get("premiseId")
        account_id = account_info.get("accountId")

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


def test_frequency(api, frequency_code, frequency_name):
    """Test a specific frequency option."""
    print(f"\n{'='*60}")
    print(f"Testing: {frequency_name} (code: '{frequency_code}')")
    print(f"{'='*60}")

    try:
        usage_data = api.get_usage(frequency=frequency_code)

        # Check if we got data
        usage = usage_data.get("usage", {})
        status = usage.get("status")
        message = usage.get("message", "")
        usage_history = usage.get("usageHistory", [])

        print(f"Status: {status}")
        if message:
            print(f"Message: {message}")

        if usage_history and len(usage_history) > 0:
            history = usage_history[0]
            usage_data_points = history.get("usageData", [])

            if usage_data_points:
                print(f"✅ SUCCESS - Got {len(usage_data_points)} data points")
                print(f"\nSample data (first 5):")
                for point in usage_data_points[:5]:
                    print(f"  {point.get('period')}: {point.get('value')} {history.get('uom')}")

                if len(usage_data_points) > 5:
                    print(f"\nSample data (last 5):")
                    for point in usage_data_points[-5:]:
                        print(f"  {point.get('period')}: {point.get('value')} {history.get('uom')}")

                return True
            else:
                print(f"❌ EMPTY - No usage data points returned")
                return False
        else:
            print(f"❌ EMPTY - No usage history returned")
            return False

    except Exception as e:
        print(f"❌ ERROR - {e}")
        return False


def main():
    """Test various frequency options."""
    print("="*60)
    print("Del-Co Water API - Frequency Options Test")
    print("="*60)

    username = os.getenv("DELCO_USERNAME")
    password = os.getenv("DELCO_PASSWORD")

    if not username or not password:
        print("ERROR: DELCO_USERNAME and DELCO_PASSWORD must be set")
        return

    api = DelCoWaterAPI(username, password)

    print("\nAuthenticating...")
    api.authenticate()
    print("✓ Authenticated")

    # Test various frequency options
    frequencies = [
        ("D", "Daily"),
        ("W", "Weekly"),
        ("M", "Monthly"),
        ("Q", "Quarterly"),
        ("Y", "Yearly"),
        ("H", "Hourly"),
        ("15", "15-minute intervals"),
        ("30", "30-minute intervals"),
        ("60", "60-minute intervals"),
        ("B", "Biweekly"),
        ("S", "Semi-monthly"),
    ]

    results = {}

    for code, name in frequencies:
        results[code] = test_frequency(api, code, name)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    working = [f"{code} ({name})" for (code, name), success in zip(frequencies, results.values()) if success]
    not_working = [f"{code} ({name})" for (code, name), success in zip(frequencies, results.values()) if not success]

    if working:
        print("\n✅ Working frequencies:")
        for freq in working:
            print(f"  - {freq}")

    if not_working:
        print("\n❌ Not available:")
        for freq in not_working:
            print(f"  - {freq}")


if __name__ == "__main__":
    main()
