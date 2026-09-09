"""Regression tests for bill PDF URL retrieval."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def _load_api_module() -> ModuleType:
    """Load api.py without importing Home Assistant-only package modules."""
    package = ModuleType("custom_components.delco_water")
    package.__path__ = [str(ROOT / "custom_components" / "delco_water")]
    sys.modules.setdefault("custom_components", ModuleType("custom_components"))
    sys.modules["custom_components.delco_water"] = package

    constants = ModuleType("custom_components.delco_water.const")
    constants.API_BASE_URL = "https://delco-api.cloud-esc.com/v2"
    constants.COGNITO_CLIENT_ID = "client-id"
    constants.COGNITO_REGION = "us-east-2"
    constants.COGNITO_USER_POOL_ID = "user-pool-id"
    constants.FREQUENCY_DAILY = "D"
    sys.modules[constants.__name__] = constants

    module_name = "custom_components.delco_water.api"
    spec = importlib.util.spec_from_file_location(
        module_name,
        ROOT / "custom_components" / "delco_water" / "api.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


api_module = _load_api_module()


class TestBillPdfUrls(unittest.TestCase):
    """Test the current Del-Co per-bill URL API."""

    def setUp(self) -> None:
        self.api = api_module.DelCoWaterAPI("user@example.com", "password")
        self.api.access_token = "access-token"

    def test_get_bill_pdf_url_uses_per_bill_endpoint(self) -> None:
        response = Mock()
        response.json.return_value = {
            "data": {
                "onlineBillURL": "https://objectstorage.example/bill.pdf",
                "billDoesNotExists": "",
            }
        }

        with patch.object(api_module.requests, "post", return_value=response) as post:
            result = self.api._get_bill_pdf_url("bill-id")

        self.assertEqual(result, "https://objectstorage.example/bill.pdf")
        response.raise_for_status.assert_called_once_with()
        post.assert_called_once_with(
            "https://delco-api.cloud-esc.com/v2/billing/getBillURL",
            headers={
                "Authorization": "Bearer access-token",
                "Content-Type": "application/json",
            },
            json={
                "email": "user@example.com",
                "billId": "bill-id",
                "isAdmin": False,
                "AccessToken": "access-token",
            },
            timeout=30,
        )

    def test_get_bill_pdf_downloads_returned_url(self) -> None:
        response = Mock(status_code=200, content=b"pdf-content")

        with (
            patch.object(
                self.api,
                "_get_bill_pdf_url",
                return_value="https://objectstorage.example/bill.pdf",
            ),
            patch.object(api_module.requests, "get", return_value=response) as get,
        ):
            result = self.api.get_bill_pdf("bill-id", "2026-08-12")

        self.assertEqual(result, b"pdf-content")
        get.assert_called_once_with(
            "https://objectstorage.example/bill.pdf", timeout=30
        )

    def test_get_bill_pdf_url_returns_none_when_bill_is_not_ready(self) -> None:
        response = Mock()
        response.json.return_value = {
            "data": {
                "onlineBillURL": "",
                "billDoesNotExists": "Bill is not available",
            }
        }

        with (
            patch.object(api_module.requests, "post", return_value=response),
            self.assertLogs(api_module._LOGGER, level="DEBUG") as logs,
        ):
            result = self.api._get_bill_pdf_url("bill-id")

        self.assertIsNone(result)
        self.assertIn("Bill PDF URL unavailable", logs.output[0])
        response.raise_for_status.assert_called_once_with()

    def test_get_bill_pdf_skips_download_when_url_is_unavailable(self) -> None:
        with (
            patch.object(self.api, "_get_bill_pdf_url", return_value=None),
            patch.object(api_module.requests, "get") as get,
        ):
            result = self.api.get_bill_pdf("bill-id", "2026-09-09")

        self.assertIsNone(result)
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
