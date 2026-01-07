# Deployment Guide

## Deploy to Remote Home Assistant (Docker/Portainer)

### Target System
- Host: `your-username@your-ha-server-ip`
- Docker Management: **Portainer**
- Config Path: `~/path/to/home-assistant/config/custom_components/`

### Step 1: Copy Integration Files

**Initial Installation:**

Run this from your local machine:

```bash
cd /path/to/del-co-water-usage

# Clean any local pycache files first
find custom_components/delco_water -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Copy files
scp -r custom_components/delco_water your-username@your-ha-server:/path/to/home-assistant/config/custom_components/
```

**Updating to New Version:**

Use the same commands, but clean pycache first to avoid permission errors:

```bash
cd /path/to/del-co-water-usage

# Clean any local pycache files
find custom_components/delco_water -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Copy files (will overwrite existing)
scp -r custom_components/delco_water your-username@your-ha-server:/path/to/home-assistant/config/custom_components/
```

**Alternative: Use rsync (cleaner, excludes pycache automatically):**

```bash
cd /path/to/del-co-water-usage
rsync -av --exclude='__pycache__' --exclude='*.pyc' custom_components/delco_water/ your-username@your-ha-server:/path/to/home-assistant/config/custom_components/delco_water/
```

### Step 2: Restart Home Assistant

**Option A: Via Portainer Web UI**
1. Open Portainer (usually `http://your-server-ip:9000`)
2. Go to Containers
3. Find your Home Assistant container
4. Click the restart icon (🔄)

**Option B: Via SSH/CLI**

```bash
# Find the container name/ID
ssh your-username@your-server "docker ps | grep home-assistant"

# Restart the container (replace CONTAINER_NAME with actual name)
ssh your-username@your-server "docker restart CONTAINER_NAME"

# Common container names:
# - home-assistant
# - homeassistant
# - smart_home-home-assistant-1
```

### Verify Installation

1. Wait for Home Assistant to restart (check logs)
2. Go to Settings → Devices & Services
3. Click "+ Add Integration"
4. Search for "Del-Co Water"
5. If it appears, the installation was successful!

### Troubleshooting

If the integration doesn't appear:

1. Check file permissions:
   ```bash
   ssh your-username@your-server "ls -la /path/to/home-assistant/config/custom_components/delco_water/"
   ```

2. Check Home Assistant logs:
   ```bash
   ssh your-username@your-server "docker logs home-assistant | grep delco"
   ```

3. Verify all files are present:
   ```bash
   ssh your-username@your-server "find /path/to/home-assistant/config/custom_components/delco_water -type f"
   ```

### Files Included

- `__init__.py` - Integration coordinator
- `api.py` - API client
- `config_flow.py` - Configuration flow
- `const.py` - Constants
- `manifest.json` - Integration metadata
- `sensor.py` - Sensor entities
- `strings.json` - UI strings
- `translations/en.json` - English translations

Total size: ~8KB

---

## Updating the Integration

### Quick Update Process

1. **Copy updated files**:
   ```bash
   cd /path/to/del-co-water-usage

   # Clean pycache first
   find custom_components/delco_water -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

   # Copy files
   scp -r custom_components/delco_water your-username@your-ha-server:/path/to/home-assistant/config/custom_components/
   ```

   Or use rsync:
   ```bash
   rsync -av --exclude='__pycache__' --exclude='*.pyc' custom_components/delco_water/ your-username@your-ha-server:/path/to/home-assistant/config/custom_components/delco_water/
   ```

2. **Restart Home Assistant** (via Portainer or SSH - see Step 2 above)

3. **Verify update**:
   - Go to Settings → Devices & Services → Del-Co Water
   - Check that version matches `manifest.json` (currently 0.2.0)

### Version-Specific Notes

#### v0.2.0 - Statistics Support
- **New feature**: Historical data now available in Energy Dashboard
- **What changed**: Integration now inserts long-term statistics for historical consumption tracking
- **Action required after update**:
  1. Wait for coordinator to refresh (or manually trigger via Developer Tools → Services → `homeassistant.update_entity`)
  2. Check Developer Tools → Statistics for `delco_water:consumption`
  3. Configure Energy Dashboard: Settings → Dashboards → Energy → Add Water Source → Select statistic `delco_water:consumption`
- **Note**: Historical data (1 year of monthly readings) will be backfilled automatically on first refresh

#### v0.1.0 - Initial Release
- Basic sensor support for water usage, cost, and account balance
