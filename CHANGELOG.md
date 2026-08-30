# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-08-30

Hyperliquid moved to a unified account, which broke the sensors that read the
perpetuals margin summary. Fixing that changes what three existing sensors
mean, hence the minor version bump.

### Breaking

- **`account_value` now reports total equity, not the perp account.** It read
  `marginSummary.accountValue`, which under the unified account describes the
  perpetuals side only and is `0` whenever no perp position is open. It now
  reports what Hyperliquid's own panel calls "Total Equity" — spot, perps,
  vaults and staking combined. On a spot-only account this jumps from `0` to
  the real balance, so its recorded history from before the update is not
  comparable.
- **`withdrawable` now reads the spot balances.** Same cause; the value comes
  from `spotClearinghouseState.tokenToAvailableAfterMaintenance` (USDC), and
  falls back to the perpetuals field so non-unified accounts keep working.
- **`pnl_24h`, `pnl_7d` and `pnl_30d` are cut to the exact window.** They used
  a whole portfolio period, but a period is not the window it is named after:
  the `month` period spans about 30.8 days, so `pnl_30d` covered nearly an
  extra day and could not be reconciled against the new perp/non-perp split.
  `pnl_30d` therefore shifts by roughly 15%. `pnl_all_time` is unchanged.
- These three sensors can now report `unknown` instead of a number when the
  portfolio history does not reach back far enough for their window.

### Added

- **Perp-only P&L**: `perp_pnl_24h`, `perp_pnl_7d`, `perp_pnl_30d` and
  `perp_pnl_all_time`, from the portfolio endpoint's `perp*` periods.
- **Freely chosen P&L windows**: `perp_pnl_10d`, `perp_pnl_14d`,
  `perp_pnl_20d`, `perp_pnl_21d` and `perp_pnl_28d`, cut from `perpMonth`.
  Longer windows are deliberately absent — see below.
- **Spot and vault share of the P&L**: `non_perp_pnl_24h`, `non_perp_pnl_7d`,
  `non_perp_pnl_30d` and `non_perp_pnl_all_time`, as total minus perp over the
  same window. Named "non-perp" rather than "spot" because vaults are included.
- **Equity breakdown**, mirroring Hyperliquid's panel: `trading_equity`,
  `staking_balance` (in HYPE — only HYPE can be staked) and `staking_value`
  (its USD equivalent).
- **Max drawdown**: `max_drawdown_24h`, `max_drawdown_7d`, `max_drawdown_30d`
  and `max_drawdown_all_time`, as the largest peak-to-trough drop in percent.
- **Trading volume**: `volume_24h/7d/30d/all_time` for the total and
  `perp_volume_24h/7d/30d/all_time` for the perpetuals share.

### Notes

- P&L windows are refused rather than approximated when the history does not
  cover them. The `month` series spans ~30.8 days, so a 40-day window would
  otherwise have silently returned the 30.8-day figure, and the only series
  reaching further back is sampled weekly. The sensor reports `unknown`
  instead.
- Valuing the spot balances needs prices. The listing table (`spotMeta`, about
  130 KB) is fetched once and cached, and only refetched when a token appears
  that it does not know; prices come from `allMids` (about 16 KB) each cycle.
- This release is built and verified against the unified account. `withdrawable`
  and `trading_equity` assume spot and perps share one pool; both fall back to
  the perpetuals fields when the spot data is missing, but that path is
  untested. Every other sensor is independent of the account type.

## [0.2.14] - 2026-08-27

### Fixed
- **30d sensors were capped at the trade history window**: fills are now always
  fetched over a full 30 days, so `realized_pnl_30d` and `fees_paid_30d` are no
  longer limited by the `trade_history_days` option (default 7). That option now
  only limits the "recent trades" attribute list, as intended.
- **All `pnl_*` sensors always read 0**: the `portfolio` endpoint returns a list
  of `[period, data]` pairs (not a dict) and its history entries are
  `[timestamp, value]` pairs (not dicts), so the parser never found any data.
  P&L is now taken from the API's own cumulative `pnlHistory` per period
  (`day`/`week`/`month`/`allTime`), which excludes deposits and withdrawals and
  avoids comparing the portfolio total (perps + spot + vaults) against the
  perp-only account value.

## [0.2.3] - 2025-02-09

### Fixed
- Add all missing Phase 1 constants to `const.py` that were never committed with v0.2.1 (sensor types, attributes for orders, funding, trades, referrals)
- Use correct default values from development version (trade history: 20 count / 7 days)

## [0.2.2] - 2025-02-09 [YANKED]

### Fixed
- Partial fix for missing constants - only added 4 of ~30 missing constants

## [0.2.1] - 2025-02-05

### Added
- **Historical Performance Tracking**
  - P&L sensors for multiple timeframes (24h, 7d, 30d, all-time)
  - Account value history data for charting
  - Realized P&L tracking from closed trades

- **Trade History & Statistics**
  - Trade count sensor (last 24h)
  - Fees paid sensors (24h and 30d)
  - Recent trades list in sensor attributes (configurable count)
  - Smart aggregation with time-filtered API calls

- **Funding Payments**
  - Total funding sensors (24h, 7d, 30d)
  - Per-position funding rate and 24h funding
  - Estimated daily funding cost/income for each position

- **Open Orders Monitoring**
  - Open orders count sensor
  - Dynamic sensors for each active order
  - Order details: type, price, size, trigger price, reduce-only status

- **Referral Program Tracking**
  - Referral earnings sensor (total USDC)
  - Referral volume sensor
  - Referee count in attributes

- **Configuration Options**
  - Trade history count (10-100, default 20)
  - Trade history days (1-30, default 7)
  - Configurable update intervals

### Fixed
- **Entity Naming**: Fixed generic "monetary_balance" entity IDs - entities now have descriptive names (e.g., `pnl_24h`, `funding_7d`, `account_value`)
- **P&L Data**: Corrected portfolio API endpoint from `accountPortfolio` to `portfolio` to properly fetch P&L data and account value history
- **Entity Cleanup**: Closed positions and filled orders are now automatically removed from the entity registry instead of showing as "unavailable"
- **API Compatibility**: Added type checking for portfolio API responses to handle edge cases

### Enhanced
- Position sensors now include funding data attributes
- Account sensors include historical data for charting
- Better API rate limiting with configurable history depth
- Improved error logging for portfolio API failures (warning level instead of debug)

### Changed
- Account sensor unique IDs now include `_v2` suffix to force recreation with correct entity names (one-time migration)
- Removed `translation_key` from sensor descriptions in favor of explicit `name` attributes
- Version bumped from 0.1.5 to 0.2.1

### Technical Details
- Extended HyperliquidAccountData dataclass with Phase 1 fields
- Added `_fetch_all_data` method to fetch portfolio, trades, funding, orders, and referrals
- Implemented smart time-based filtering for trade history
- Added dynamic order sensor tracking similar to positions
- Changed `_attr_has_entity_name = False` for account sensors to enable descriptive entity IDs
- Fixed portfolio data extraction to use nested structure: `portfolio_data["allTime"]["accountValueHistory"]`
- Added automatic entity registry cleanup for dynamic sensors (positions, orders)

## [0.1.5] - 2025-01-31

### Fixed
- Icon and manifest improvements for HACS compatibility

## [0.1.0] - 2025-01-28

### Added
- Initial release
- Account monitoring (value, unrealized PnL, margin used, withdrawable)
- Dynamic position sensors with real-time P&L
- Dynamic vault deposit sensors
- Vault leader monitoring (equity, commission, APR)
- HACS compliance
