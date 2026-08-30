# Hyperliquid Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/beMoD/homeassistant-hyperliquid.svg)](https://github.com/beMoD/homeassistant-hyperliquid/releases)
[![License](https://img.shields.io/github/license/beMoD/homeassistant-hyperliquid.svg)](https://github.com/beMoD/homeassistant-hyperliquid/blob/master/LICENSE)

A Home Assistant custom integration for monitoring [Hyperliquid](https://hyperliquid.xyz) perpetual trading accounts, positions, and vault deposits in real-time.

## Features

### Account Monitoring
Mirrors the equity panel of the Hyperliquid web interface:
- **Account Value** - Total equity: spot, perps, vaults and staking combined
- **Trading Equity** - Spot balances plus the P&L of open positions
- **Total Vault Equity** - Combined equity across all vault deposits
- **Staking Balance / Staking Value** - Delegated HYPE and its USD equivalent
- **Unrealized PnL** - Sum of all open position P&L
- **Margin Used** - Currently used margin across all positions
- **Withdrawable** - Available balance for withdrawal

### Performance & Statistics
- **P&L** over 24h, 7d, 30d and all time, split into total, perpetuals only
  and non-perp (spot + vaults)
- **Freely chosen perp windows** at 10, 14, 20, 21 and 28 days
- **Realized P&L** and **fees paid** from the actual fills
- **Funding payments** received or paid, over 24h, 7d and 30d
- **Trading volume**, total and perpetuals only
- **Max drawdown** as the largest peak-to-trough drop, per period
- **Trade count** and **open order count**
- **Referral earnings and volume**

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

> **Unified account.** Hyperliquid no longer separates the spot and
> perpetuals account, and this integration is built and verified against that
> unified model — the collateral is read from the spot balances rather than
> from the perpetuals margin summary. `trading_equity` and `withdrawable`
> depend on that assumption; `withdrawable` falls back to the perpetuals field
> when the spot data is missing, but that path is untested. Every other sensor
> is independent of the account type, and both margin modes (cross and
> isolated) are handled the same way.

### Equity

Entity IDs are shown without their `sensor.hyperliquid_<wallet>_` prefix.

| Sensor | Description | Unit |
|--------|-------------|------|
| `account_value` | Total equity: spot, perps, vaults and staking | USD |
| `trading_equity` | Spot balances plus the P&L of open positions | USD |
| `total_vault_equity` | Combined equity across all vault deposits | USD |
| `staking_balance` | Delegated HYPE | HYPE |
| `staking_value` | USD equivalent of the delegated HYPE | USD |
| `unrealized_pnl` | Sum of all open position P&L | USD |
| `margin_used` | Currently used margin | USD |
| `withdrawable` | Available for withdrawal | USD |

### Profit & Loss

Taken from the exchange's own portfolio history, so deposits and withdrawals
do not distort it. Each window is cut to its exact boundary; a sensor reports
`unknown` rather than a number when the history does not reach back far enough.

| Sensor | Description | Unit |
|--------|-------------|------|
| `pnl_24h`, `pnl_7d`, `pnl_30d`, `pnl_all_time` | Total P&L | USD |
| `perp_pnl_24h`, `perp_pnl_7d`, `perp_pnl_30d`, `perp_pnl_all_time` | Perpetuals only | USD |
| `perp_pnl_10d`, `perp_pnl_14d`, `perp_pnl_20d`, `perp_pnl_21d`, `perp_pnl_28d` | Perpetuals, extra windows | USD |
| `non_perp_pnl_24h`, `non_perp_pnl_7d`, `non_perp_pnl_30d`, `non_perp_pnl_all_time` | Spot and vaults | USD |

For any window, `pnl` equals `perp_pnl` plus `non_perp_pnl`.

### Trading Statistics

| Sensor | Description | Unit |
|--------|-------------|------|
| `realized_pnl_24h`, `realized_pnl_7d`, `realized_pnl_30d` | Realized P&L from fills | USD |
| `fees_paid_24h`, `fees_paid_30d` | Trading fees paid | USD |
| `funding_24h`, `funding_7d`, `funding_30d` | Funding received or paid | USD |
| `volume_24h`, `volume_7d`, `volume_30d`, `volume_all_time` | Total traded volume | USD |
| `perp_volume_24h`, `perp_volume_7d`, `perp_volume_30d`, `perp_volume_all_time` | Perpetuals volume | USD |
| `max_drawdown_24h`, `max_drawdown_7d`, `max_drawdown_30d`, `max_drawdown_all_time` | Largest peak-to-trough drop | % |
| `trades_24h` | Number of fills | - |
| `open_orders_count` | Currently open orders | - |
| `referral_earnings`, `referral_volume` | Referral program | USD |

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

This rebuilds the equity panel of the Hyperliquid web interface:

```yaml
type: entities
title: Hyperliquid Account
entities:
  - entity: sensor.hyperliquid_0x1234_account_value
    name: Total Equity
  - entity: sensor.hyperliquid_0x1234_trading_equity
    name: Trading Equity
  - entity: sensor.hyperliquid_0x1234_total_vault_equity
    name: Vault Equity
  - entity: sensor.hyperliquid_0x1234_staking_balance
    name: Staking
  - type: divider
  - entity: sensor.hyperliquid_0x1234_pnl_all_time
    name: PnL
  - entity: sensor.hyperliquid_0x1234_volume_all_time
    name: Volume
  - entity: sensor.hyperliquid_0x1234_max_drawdown_all_time
    name: Max Drawdown
  - type: divider
  - entity: sensor.hyperliquid_0x1234_position_btc
    name: BTC Position
  - entity: sensor.hyperliquid_0x1234_position_eth
    name: ETH Position
```

Perpetuals against spot and vaults over the same window:

```yaml
type: entities
title: Where the PnL comes from
entities:
  - entity: sensor.hyperliquid_0x1234_pnl_30d
    name: Total 30d
  - entity: sensor.hyperliquid_0x1234_perp_pnl_30d
    name: Perpetuals 30d
  - entity: sensor.hyperliquid_0x1234_non_perp_pnl_30d
    name: Spot & Vaults 30d
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

### A P&L sensor reports "unknown"
The exchange's portfolio history does not reach back far enough for that
window. This is deliberate: the monthly series covers about 30.8 days, and the
only series reaching further back is sampled weekly, so a longer window could
only be guessed at. The sensor reports `unknown` instead of a plausible-looking
estimate.

### Account Value reads 0 after upgrading from 0.2.x
Fixed in 0.3.0. Hyperliquid moved to a unified account, where the perpetuals
margin summary the integration used to read reports `0` unless a perp position
is open. `account_value` and `withdrawable` now read the spot balances. Note
that their recorded history from before the upgrade is not comparable.

## Technical Details

- **API**: Hyperliquid REST API (https://api.hyperliquid.xyz)
- **SDK**: Official `hyperliquid-python-sdk` (v0.23.0)
- **Update Method**: Polling via `DataUpdateCoordinator`
- **Authentication**: Read-only (wallet address only, no private key)
- **Account model**: Unified account (spot balances act as collateral)
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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by Hyperliquid. Use at your own risk. This integration is for monitoring purposes only and cannot execute trades.

## Support the Project

If you find this integration useful, consider signing up on Hyperliquid using my referral link — it costs you nothing and helps support development:
Already have an account? Enter code **BEMOD** at [app.hyperliquid.xyz/referrals](https://app.hyperliquid.xyz/referrals) to claim the discount.

**[Sign up with referral link](https://app.hyperliquid.xyz/join/BEMOD)**

You'll receive a **4% fee discount** on your first $25M in trading volume.

## Support

- [Report Issues](https://github.com/beMoD/homeassistant-hyperliquid/issues)
- [Hyperliquid Documentation](https://hyperliquid.gitbook.io/hyperliquid-docs)
- [Home Assistant Community](https://community.home-assistant.io/)



