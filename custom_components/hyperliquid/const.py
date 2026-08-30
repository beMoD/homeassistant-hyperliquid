"""Constants for the Hyperliquid integration."""

DOMAIN = "hyperliquid"

# Configuration
CONF_WALLET_ADDRESS = "wallet_address"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_TRADE_HISTORY_COUNT = "trade_history_count"
CONF_TRADE_HISTORY_DAYS = "trade_history_days"

# Defaults
DEFAULT_UPDATE_INTERVAL = 30  # seconds
MIN_UPDATE_INTERVAL = 10
MAX_UPDATE_INTERVAL = 300
DEFAULT_TRADE_HISTORY_COUNT = 20
MIN_TRADE_HISTORY_COUNT = 10
MAX_TRADE_HISTORY_COUNT = 100
DEFAULT_TRADE_HISTORY_DAYS = 7
MIN_TRADE_HISTORY_DAYS = 1
MAX_TRADE_HISTORY_DAYS = 30

# Fills are always fetched over this window so the 24h/7d/30d buckets are
# complete regardless of CONF_TRADE_HISTORY_DAYS, which only limits the
# "recent trades" attribute list.
FILL_HISTORY_DAYS = 30

# Per-request HTTP timeout (seconds) passed to the SDK so a hung connection
# cannot freeze the executor thread (and with it the coordinator) indefinitely.
API_TIMEOUT = 30
# Overall budget for one full update cycle (all API calls combined), used as a
# safety net via async_timeout in case individual requests are slow but alive.
UPDATE_TIMEOUT = 120

# Sensor types
SENSOR_ACCOUNT_VALUE = "account_value"
SENSOR_UNREALIZED_PNL = "unrealized_pnl"
SENSOR_MARGIN_USED = "margin_used"
SENSOR_WITHDRAWABLE = "withdrawable"
SENSOR_POSITION = "position"
SENSOR_TOTAL_VAULT_EQUITY = "total_vault_equity"
SENSOR_VAULT = "vault"
# Unified account breakdown, mirroring Hyperliquid's own equity panel.
# account_value above is the panel's "Total Equity"; marginSummary only ever
# describes the perp side, which is 0 while no perp position is open.
SENSOR_TRADING_EQUITY = "trading_equity"
SENSOR_STAKING_BALANCE = "staking_balance"
SENSOR_STAKING_VALUE = "staking_value"
SENSOR_MAX_DRAWDOWN_24H = "max_drawdown_24h"
SENSOR_MAX_DRAWDOWN_7D = "max_drawdown_7d"
SENSOR_MAX_DRAWDOWN_30D = "max_drawdown_30d"
SENSOR_MAX_DRAWDOWN_ALL_TIME = "max_drawdown_all_time"
SENSOR_PNL_24H = "pnl_24h"
SENSOR_PNL_7D = "pnl_7d"
SENSOR_PNL_30D = "pnl_30d"
SENSOR_PNL_ALL_TIME = "pnl_all_time"
# Perp-only P&L, from the portfolio endpoint's perp* periods. Unlike the
# pnl_* sensors above (which take a whole series end-to-end) these are cut to
# the exact window: perpMonth actually spans ~30.8 days, so an uncut "30d"
# would overstate the window by nearly a day.
SENSOR_PERP_PNL_24H = "perp_pnl_24h"
SENSOR_PERP_PNL_7D = "perp_pnl_7d"
SENSOR_PERP_PNL_10D = "perp_pnl_10d"
SENSOR_PERP_PNL_14D = "perp_pnl_14d"
SENSOR_PERP_PNL_20D = "perp_pnl_20d"
SENSOR_PERP_PNL_21D = "perp_pnl_21d"
SENSOR_PERP_PNL_28D = "perp_pnl_28d"
SENSOR_PERP_PNL_30D = "perp_pnl_30d"
SENSOR_PERP_PNL_ALL_TIME = "perp_pnl_all_time"
# Everything that is not a perp position: spot holdings plus vaults. The API
# has no bucket for this, it is total minus perp over the same window.
SENSOR_NON_PERP_PNL_24H = "non_perp_pnl_24h"
SENSOR_NON_PERP_PNL_7D = "non_perp_pnl_7d"
SENSOR_NON_PERP_PNL_30D = "non_perp_pnl_30d"
SENSOR_NON_PERP_PNL_ALL_TIME = "non_perp_pnl_all_time"
# Trading volume, from each period's "vlm" field. The unprefixed sensors are
# the total (perps + spot + vaults), the perp_* ones the perp share.
SENSOR_VOLUME_24H = "volume_24h"
SENSOR_VOLUME_7D = "volume_7d"
SENSOR_VOLUME_30D = "volume_30d"
SENSOR_VOLUME_ALL_TIME = "volume_all_time"
SENSOR_PERP_VOLUME_24H = "perp_volume_24h"
SENSOR_PERP_VOLUME_7D = "perp_volume_7d"
SENSOR_PERP_VOLUME_30D = "perp_volume_30d"
SENSOR_PERP_VOLUME_ALL_TIME = "perp_volume_all_time"
SENSOR_REALIZED_PNL_24H = "realized_pnl_24h"
SENSOR_REALIZED_PNL_7D = "realized_pnl_7d"
SENSOR_REALIZED_PNL_30D = "realized_pnl_30d"
SENSOR_TRADES_24H = "trades_24h"
SENSOR_FEES_PAID_24H = "fees_paid_24h"
SENSOR_FEES_PAID_30D = "fees_paid_30d"
SENSOR_FUNDING_24H = "funding_24h"
SENSOR_FUNDING_7D = "funding_7d"
SENSOR_FUNDING_30D = "funding_30d"
SENSOR_OPEN_ORDERS_COUNT = "open_orders_count"
SENSOR_ORDER = "order"
SENSOR_REFERRAL_EARNINGS = "referral_earnings"
SENSOR_REFERRAL_VOLUME = "referral_volume"

# Units
CURRENCY_USD = "USD"
# Staking on Hyperliquid is HYPE only, so the balance is denominated in HYPE
# and its USD equivalent is a separate sensor.
TOKEN_HYPE = "HYPE"
PERCENTAGE = "%"

# Only HYPE can be staked on Hyperliquid, so the staking balance is quoted in
# HYPE and its USD equivalent is derived from the HYPE spot price.
STAKING_TOKEN = TOKEN_HYPE

# Attributes for position sensors
ATTR_COIN = "coin"
ATTR_SIZE = "size"
ATTR_ENTRY_PRICE = "entry_price"
ATTR_LIQUIDATION_PRICE = "liquidation_price"
ATTR_LEVERAGE = "leverage"
ATTR_UNREALIZED_PNL = "unrealized_pnl"
ATTR_MARGIN_USED = "margin_used"
ATTR_RETURN_ON_EQUITY = "return_on_equity"
ATTR_POSITION_VALUE = "position_value"
ATTR_MARK_PRICE = "mark_price"
ATTR_SIDE = "side"

# Attributes for vault sensors
ATTR_VAULT_ADDRESS = "vault_address"
ATTR_VAULT_NAME = "vault_name"
ATTR_EQUITY = "equity"
ATTR_PNL = "pnl"
ATTR_ROI = "roi"
ATTR_DEPOSIT_VALUE = "deposit_value"
ATTR_APR = "apr"
ATTR_LEADER_ADDRESS = "leader_address"
ATTR_LEADER_FRACTION = "leader_fraction"
ATTR_LEADER_EQUITY = "leader_equity"
ATTR_LEADER_COMMISSION = "leader_commission"
ATTR_VAULT_TOTAL_VALUE = "vault_total_value"
ATTR_IS_CLOSED = "is_closed"

# Attributes for order sensors
ATTR_ORDER_ID = "order_id"
ATTR_ORDER_TYPE = "order_type"
ATTR_PRICE = "price"
ATTR_FILLED = "filled"
ATTR_REMAINING = "remaining"
ATTR_TRIGGER_PRICE = "trigger_price"
ATTR_REDUCE_ONLY = "reduce_only"

# Attributes for funding data
ATTR_FUNDING_RATE = "funding_rate"
ATTR_FUNDING_24H = "funding_24h"
ATTR_ESTIMATED_FUNDING_DAILY = "estimated_funding_daily"

# Attributes for trade history
ATTR_RECENT_TRADES = "recent_trades"
ATTR_ACCOUNT_VALUE_HISTORY = "account_value_history"

# Attributes for referral data
ATTR_REFERRER = "referrer"
ATTR_REFEREE_COUNT = "referee_count"
