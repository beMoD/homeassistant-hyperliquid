# Hyperliquid Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/beMoD/homeassistant-hyperliquid.svg)](https://github.com/beMoD/homeassistant-hyperliquid/releases)
[![License](https://img.shields.io/github/license/beMoD/homeassistant-hyperliquid.svg)](https://github.com/beMoD/homeassistant-hyperliquid/blob/master/LICENSE)

A Home Assistant custom integration for monitoring [Hyperliquid](https://hyperliquid.xyz) perpetual trading accounts, positions, and vault deposits in real-time.

## Features

### Account Monitoring
- **Account Value** - Total portfolio value
- **Unrealized PnL** - Sum of all open position P&L
- **Margin Used** - Currently used margin across all positions
- **Withdrawable** - Available balance for withdrawal
- **Total Vault Equity** - Combined equity across all vault deposits

### Position Tracking (Dynamic)
Each open perpetual position gets its own sensor showing unrealized PnL with attributes:
- Coin/Trading Pair
- Position Size
- Side (Long/Short)
- Entry Price & Mark Price
- Liquidation Price
- Leverage
- Margin Used
- Return on Equity (ROE)
- Position Value

Sensors automatically appear when positions are opened and disappear when closed.

### Vault Deposits (Dynamic)
Each vault deposit gets its own sensor showing current equity with attributes:
- Vault Name & Address
- Profit & Loss (PnL)
- Return on Investment (ROI)
- Annual Percentage Rate (APR)
- Deposit Value
- **Leader Monitoring:**
  - Leader Address
  - Leader Equity (absolute USD value)
  - Leader Fraction (% of vault TVL)
  - Leader Commission Rate
  - Vault Total Value (TVL)
  - Vault Status (open/closed)

The leader monitoring attributes allow you to track if vault managers are withdrawing capital by monitoring `leader_equity` and `vault_total_value`.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/beMoD/homeassistant-hyperliquid`
6. Select category: "Integration"
7. Click "Add"
8. Find "Hyperliquid" in the integration list and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/hyperliquid` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Hyperliquid"**
4. Enter your Ethereum wallet address (0x...)
   - Only read-only access is used
   - No API key or private key required
5. Click **Submit**

### Options

After adding the integration, you can configure:
- **Update Interval** (10-300 seconds, default: 30s) - How often to poll the Hyperliquid API

To change options:
1. Go to **Settings → Devices & Services**
2. Find the Hyperliquid integration
3. Click **"Configure"**

## Sensors

All sensors are grouped under a single device per wallet address.

### Static Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.hyperliquid_*_account_value` | Total portfolio value | USD |
| `sensor.hyperliquid_*_unrealized_pnl` | Sum of all position P&L | USD |
| `sensor.hyperliquid_*_margin_used` | Used margin | USD |
| `sensor.hyperliquid_*_withdrawable` | Available balance | USD |
| `sensor.hyperliquid_*_total_vault_equity` | Total vault equity | USD |

### Dynamic Sensors (Per Position)

| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.hyperliquid_*_position_*` | Position unrealized PnL | USD |

Attributes: `coin`, `size`, `side`, `entry_price`, `mark_price`, `liquidation_price`, `leverage`, `margin_used`, `return_on_equity`, `position_value`

### Dynamic Sensors (Per Vault)

| Sensor | Description | Unit |
|--------|-------------|------|
| `sensor.hyperliquid_*_vault_*` | Vault equity value | USD |

Attributes: `vault_name`, `vault_address`, `pnl`, `roi`, `deposit_value`, `apr`, `leader_address`, `leader_fraction`, `leader_equity`, `leader_commission`, `vault_total_value`, `is_closed`

## Example Dashboard Card

```yaml
type: entities
title: Hyperliquid Account
entities:
  - entity: sensor.hyperliquid_0x1234_account_value
    name: Portfolio Value
  - entity: sensor.hyperliquid_0x1234_unrealized_pnl
    name: Unrealized PnL
  - entity: sensor.hyperliquid_0x1234_margin_used
    name: Margin Used
  - entity: sensor.hyperliquid_0x1234_withdrawable
    name: Available
  - type: divider
  - entity: sensor.hyperliquid_0x1234_position_btc
    name: BTC Position
  - entity: sensor.hyperliquid_0x1234_position_eth
    name: ETH Position
```

## Example Automation: Liquidation Alert

```yaml
alias: Hyperliquid Liquidation Alert
description: Alert when position is close to liquidation
trigger:
  - platform: template
    value_template: >
      {% set position = state_attr('sensor.hyperliquid_0x1234_position_btc', 'mark_price') %}
      {% set liq = state_attr('sensor.hyperliquid_0x1234_position_btc', 'liquidation_price') %}
      {% set side = state_attr('sensor.hyperliquid_0x1234_position_btc', 'side') %}
      {% if position and liq %}
        {% if side == 'long' %}
          {{ (position - liq) / position < 0.05 }}
        {% else %}
          {{ (liq - position) / position < 0.05 }}
        {% endif %}
      {% else %}
        false
      {% endif %}
action:
  - service: notify.notify
    data:
      title: "⚠️ Hyperliquid Liquidation Warning"
      message: "BTC position is within 5% of liquidation price!"
```

## Example Automation: Vault Leader Withdrawal Alert

```yaml
alias: Vault Leader Withdrawal Alert
description: Alert when vault leader withdraws significant capital
trigger:
  - platform: numeric_state
    entity_id: sensor.hyperliquid_0x1234_vault_myvault
    attribute: leader_equity
    below: 50000  # Alert if leader equity drops below $50k
action:
  - service: notify.notify
    data:
      title: "⚠️ Vault Leader Capital Alert"
      message: >
        Vault leader equity has dropped to ${{ state_attr('sensor.hyperliquid_0x1234_vault_myvault', 'leader_equity') | round(2) }}
```

## Troubleshooting

### Integration fails to load
- Check Home Assistant logs: **Settings → System → Logs**
- Ensure `hyperliquid-python-sdk` is installed correctly
- Verify your wallet address format (must start with 0x followed by 40 hex characters)

### API connection errors
- Verify the wallet address is correct and active on Hyperliquid
- Check if Hyperliquid API is accessible: https://api.hyperliquid.xyz/info
- Increase the update interval if rate-limited

### Sensors not updating
- Check the last update time in the device info
- Verify you have active positions/vault deposits (dynamic sensors only appear when data exists)
- Check Home Assistant logs for errors

## Technical Details

- **API**: Hyperliquid REST API (https://api.hyperliquid.xyz)
- **SDK**: Official `hyperliquid-python-sdk` (v0.21.0)
- **Update Method**: Polling via `DataUpdateCoordinator`
- **Authentication**: Read-only (wallet address only, no private key)
- **Minimum HA Version**: 2024.1.0

## Data Privacy

This integration:
- Only uses your wallet address for read-only API access
- Does not require or store private keys or API keys
- All data fetching happens locally on your Home Assistant instance
- No data is sent to third parties

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by Hyperliquid. Use at your own risk. This integration is for monitoring purposes only and cannot execute trades.

## Support

- [Report Issues](https://github.com/beMoD/homeassistant-hyperliquid/issues)
- [Hyperliquid Documentation](https://hyperliquid.gitbook.io/hyperliquid-docs)
- [Home Assistant Community](https://community.home-assistant.io/)

## Support the Project

If you find this integration useful, consider signing up on Hyperliquid using my referral link — it costs you nothing and helps support development:

**[Sign up with referral link](https://app.hyperliquid.xyz/join/BEMOD)**

You'll receive a **4% fee discount** on your first $25M in trading volume.

Already have an account? Enter code **BEMOD** at [app.hyperliquid.xyz/referrals](https://app.hyperliquid.xyz/referrals) to claim the discount.
