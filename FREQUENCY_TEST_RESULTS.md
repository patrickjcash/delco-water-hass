# Frequency Options Test Results

Date: 2026-01-07
Meter Type: Non-AMI (isAMI: "N")

## Frequencies Tested

| Code | Frequency | Result | Notes |
|------|-----------|--------|-------|
| M | Monthly | ✅ Working | 10 data points returned |
| D | Daily | ❌ Not available | "HGAL-Water Measurement not found" |
| W | Weekly | ❌ Not available | "HGAL-Water Measurement not found" |
| Q | Quarterly | ❌ Not available | "HGAL-Water Measurement not found" |
| Y | Yearly | ❌ Not available | "HGAL-Water Measurement not found" |
| H | Hourly | ❌ Not available | "HGAL-Water Measurement not found" |
| 15 | 15-minute | ❌ Not available | "HGAL-Water Measurement not found" |
| 30 | 30-minute | ❌ Not available | "HGAL-Water Measurement not found" |
| 60 | 60-minute | ❌ Not available | "HGAL-Water Measurement not found" |
| B | Biweekly | ❌ Not available | "HGAL-Water Measurement not found" |
| S | Semi-monthly | ❌ Not available | "HGAL-Water Measurement not found" |

## Conclusion

For non-AMI meters, only **monthly (M)** frequency is supported. This provides:
- Monthly billing cycle data
- Historical data going back 1 year
- Sufficient granularity for energy dashboard tracking

## AMI Meters

If your water meter is upgraded to AMI (Advanced Metering Infrastructure), additional frequencies may become available:
- Daily (D) - Most likely to be supported
- Weekly (W) - Potentially available
- Other frequencies - Dependent on utility implementation

The integration code already supports these frequencies and will automatically use them if your meter is upgraded.

## Test Script

The test script `tests/test_frequency_options.py` can be re-run anytime to check for additional frequency support:

```bash
source venv/bin/activate
python tests/test_frequency_options.py
```
