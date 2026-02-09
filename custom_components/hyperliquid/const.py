"""Constants for the Hyperliquid integration."""

from datetime import timedelta

DOMAIN = "hyperliquid"

# Configuration
CONF_WALLET_ADDRESS = "wallet_address"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_TRADE_HISTORY_DAYS = "trade_history_days"
CONF_TRADE_HISTORY_COUNT = "trade_history_count"

# Defaults
DEFAULT_UPDATE_INTERVAL = 30  # seconds
MIN_UPDATE_INTERVAL = 10
MAX_UPDATE_INTERVAL = 300
DEFAULT_TRADE_HISTORY_DAYS = 30
DEFAULT_TRADE_HISTORY_COUNT = 10

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

# Sensor names
SENSOR_NAMES = {
    SENSOR_ACCOUNT_VALUE: "Account Value",
    SENSOR_UNREALIZED_PNL: "Unrealized PnL",
    SENSOR_MARGIN_USED: "Margin Used",
    SENSOR_WITHDRAWABLE: "Withdrawable",
    SENSOR_TOTAL_VAULT_EQUITY: "Total Vault Equity",
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
