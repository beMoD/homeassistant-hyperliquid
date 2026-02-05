# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
