"""Constants for the Hyperliquid integration."""

from datetime import timedelta

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

# API
API_BASE_URL = "https://api.hyperliquid.xyz"

# Sensor types
SENSOR_ACCOUNT_VALUE = "account_value"
SENSOR_UNREALIZED_PNL = "unrealized_pnl"
SENSOR_MARGIN_USED = "margin_used"
SENSOR_WITHDRAWABLE = "withdrawable"
SENSOR_POSITION = "position"
SENSOR_TOTAL_VAULT_EQUITY = "total_vault_equity"
SENSOR_VAULT = "vault"
SENSOR_PNL_24H = "pnl_24h"
SENSOR_PNL_7D = "pnl_7d"
SENSOR_PNL_30D = "pnl_30d"
SENSOR_PNL_ALL_TIME = "pnl_all_time"
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

# Sensor names
SENSOR_NAMES = {
    SENSOR_ACCOUNT_VALUE: "Account Value",
    SENSOR_UNREALIZED_PNL: "Unrealized PnL",
    SENSOR_MARGIN_USED: "Margin Used",
    SENSOR_WITHDRAWABLE: "Withdrawable",
    SENSOR_TOTAL_VAULT_EQUITY: "Total Vault Equity",
    SENSOR_PNL_24H: "PnL 24h",
    SENSOR_PNL_7D: "PnL 7d",
    SENSOR_PNL_30D: "PnL 30d",
    SENSOR_PNL_ALL_TIME: "PnL All Time",
    SENSOR_REALIZED_PNL_24H: "Realized PnL 24h",
    SENSOR_REALIZED_PNL_7D: "Realized PnL 7d",
    SENSOR_REALIZED_PNL_30D: "Realized PnL 30d",
    SENSOR_TRADES_24H: "Trades 24h",
    SENSOR_FEES_PAID_24H: "Fees Paid 24h",
    SENSOR_FEES_PAID_30D: "Fees Paid 30d",
    SENSOR_FUNDING_24H: "Funding 24h",
    SENSOR_FUNDING_7D: "Funding 7d",
    SENSOR_FUNDING_30D: "Funding 30d",
    SENSOR_OPEN_ORDERS_COUNT: "Open Orders Count",
    SENSOR_REFERRAL_EARNINGS: "Referral Earnings",
    SENSOR_REFERRAL_VOLUME: "Referral Volume",
}

# Units
CURRENCY_USD = "USD"

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
