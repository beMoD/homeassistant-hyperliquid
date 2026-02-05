"""DataUpdateCoordinator for Hyperliquid integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any, TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_TRADE_HISTORY_COUNT,
    CONF_TRADE_HISTORY_DAYS,
    CONF_UPDATE_INTERVAL,
    CONF_WALLET_ADDRESS,
    DEFAULT_TRADE_HISTORY_COUNT,
    DEFAULT_TRADE_HISTORY_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class HyperliquidAccountData:
    """Class to hold account data."""

    account_value: float
    unrealized_pnl: float
    margin_used: float
    withdrawable: float
    positions: list[dict[str, Any]]
    vaults: list[dict[str, Any]]
    total_vault_equity: float
    # Phase 1 additions
    pnl_24h: float
    pnl_7d: float
    pnl_30d: float
    pnl_all_time: float
    account_value_history: list[dict[str, Any]]
    realized_pnl_24h: float
    realized_pnl_7d: float
    realized_pnl_30d: float
    trades_24h: int
    fees_paid_24h: float
    fees_paid_30d: float
    recent_trades: list[dict[str, Any]]
    funding_24h: float
    funding_7d: float
    funding_30d: float
    funding_by_coin: dict[str, dict[str, float]]
    open_orders_count: int
    open_orders: list[dict[str, Any]]
    referral_earnings: float
    referral_volume: float
    referral_data: dict[str, Any]


class HyperliquidDataUpdateCoordinator(DataUpdateCoordinator[HyperliquidAccountData]):
    """Class to manage fetching Hyperliquid data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.wallet_address = config_entry.data[CONF_WALLET_ADDRESS]
        self._info = None  # Lazy initialization to avoid blocking

        update_interval = config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
            config_entry=config_entry,
        )

    def _fetch_all_data(self, wallet_address: str) -> dict[str, Any]:
        """Fetch all data from API (runs in executor)."""
        from hyperliquid.info import Info
        from datetime import datetime, timedelta

        if self._info is None:
            self._info = Info(skip_ws=True)

        # Get configuration options
        trade_history_days = self.config_entry.options.get(
            CONF_TRADE_HISTORY_DAYS, DEFAULT_TRADE_HISTORY_DAYS
        )
        trade_history_count = self.config_entry.options.get(
            CONF_TRADE_HISTORY_COUNT, DEFAULT_TRADE_HISTORY_COUNT
        )

        # Fetch core account data
        user_state = self._info.user_state(wallet_address)
        vault_equities = self._info.user_vault_equities(wallet_address)

        # Enrich vault data with details from vaultDetails API
        for vault in vault_equities:
            vault_addr = vault.get("vaultAddress", "")
            if vault_addr:
                try:
                    details = self._info.post("/info", {"type": "vaultDetails", "vaultAddress": vault_addr})
                    vault["vaultName"] = details.get("name", "")
                    vault["apr"] = details.get("apr", 0)
                    vault["leader"] = details.get("leader", "")
                    vault["leaderFraction"] = details.get("leaderFraction", 0)
                    vault["leaderCommission"] = details.get("leaderCommission", 0)
                    vault["maxDistributable"] = details.get("maxDistributable", 0)
                    vault["isClosed"] = details.get("isClosed", False)
                except Exception:
                    pass

        # Fetch Phase 1 data
        portfolio_data = {}
        trade_fills = []
        funding_data = []
        open_orders = []
        referral_data = {}

        try:
            # Portfolio history for P&L tracking
            portfolio_data = self._info.post("/info", {"type": "portfolio", "user": wallet_address}) or {}
        except Exception as err:
            _LOGGER.warning("Failed to fetch portfolio data: %s", err)
            _LOGGER.warning("Endpoint used: portfolio, Wallet: %s", wallet_address)

        try:
            # Trade fills with time filter
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=trade_history_days)).timestamp() * 1000)
            trade_fills = self._info.user_fills_by_time(wallet_address, start_time, end_time) or []
        except Exception as err:
            _LOGGER.debug("Failed to fetch trade fills: %s", err)

        try:
            # Funding payments
            funding_data = self._info.user_fundings(wallet_address) or []
        except Exception as err:
            _LOGGER.debug("Failed to fetch funding data: %s", err)

        try:
            # Open orders
            open_orders = self._info.open_orders(wallet_address) or []
        except Exception as err:
            _LOGGER.debug("Failed to fetch open orders: %s", err)

        try:
            # Referral data
            referral_data = self._info.post("/info", {"type": "referral", "user": wallet_address}) or {}
        except Exception as err:
            _LOGGER.debug("Failed to fetch referral data: %s", err)

        return {
            "user_state": user_state,
            "vault_equities": vault_equities,
            "portfolio_data": portfolio_data,
            "trade_fills": trade_fills,
            "funding_data": funding_data,
            "open_orders": open_orders,
            "referral_data": referral_data,
            "trade_history_count": trade_history_count,
        }

    async def _async_update_data(self) -> HyperliquidAccountData:
        """Fetch data from Hyperliquid API."""
        try:
            # Fetch all data from API (in executor to avoid blocking)
            all_data = await self.hass.async_add_executor_job(
                self._fetch_all_data, self.wallet_address
            )

            return self._parse_data(all_data)

        except Exception as err:
            _LOGGER.error("Error fetching Hyperliquid data: %s", err)
            raise UpdateFailed(f"Error communicating with Hyperliquid API: {err}") from err

    def _parse_data(self, all_data: dict[str, Any]) -> HyperliquidAccountData:
        """Parse user state response into structured data."""
        from datetime import datetime, timedelta

        user_state = all_data["user_state"]
        vault_equities = all_data["vault_equities"]
        portfolio_data = all_data.get("portfolio_data", {})
        trade_fills = all_data.get("trade_fills", [])
        funding_data = all_data.get("funding_data", [])
        open_orders = all_data.get("open_orders", [])
        referral_data = all_data.get("referral_data", {})
        trade_history_count = all_data.get("trade_history_count", DEFAULT_TRADE_HISTORY_COUNT)

        margin_summary = user_state.get("marginSummary", {})
        asset_positions = user_state.get("assetPositions", [])

        # Extract account-level values
        account_value = float(margin_summary.get("accountValue", 0))
        total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
        withdrawable = float(margin_summary.get("withdrawable", 0))

        # Parse positions
        positions = []
        total_unrealized_pnl = 0.0

        for asset_pos in asset_positions:
            position = asset_pos.get("position", {})

            # Skip positions with no size
            size = float(position.get("szi", 0))
            if size == 0:
                continue

            coin = position.get("coin", "")
            entry_price = float(position.get("entryPx", 0))
            position_value = float(position.get("positionValue", 0))
            unrealized_pnl = float(position.get("unrealizedPnl", 0))
            margin_used = float(position.get("marginUsed", 0))
            liquidation_price = position.get("liquidationPx")
            leverage = position.get("leverage", {})
            return_on_equity = float(position.get("returnOnEquity", 0))

            # Determine side based on size sign
            side = "long" if size > 0 else "short"

            # Parse leverage
            leverage_type = leverage.get("type", "cross")
            leverage_value = leverage.get("value", 1)
            if leverage_type == "cross":
                leverage_str = "cross"
            else:
                leverage_str = f"{leverage_value}x"

            # Calculate mark price from position value and size
            mark_price = abs(position_value / size) if size != 0 else 0

            # Handle liquidation price
            if liquidation_price is not None:
                liquidation_price = float(liquidation_price)

            positions.append({
                "coin": coin,
                "size": abs(size),
                "side": side,
                "entry_price": entry_price,
                "mark_price": mark_price,
                "liquidation_price": liquidation_price,
                "leverage": leverage_str,
                "unrealized_pnl": unrealized_pnl,
                "margin_used": margin_used,
                "return_on_equity": return_on_equity * 100,  # Convert to percentage
                "position_value": position_value,
            })

            total_unrealized_pnl += unrealized_pnl

        # Parse vault equities
        vaults = []
        total_vault_equity = 0.0

        for vault in vault_equities:
            vault_address = vault.get("vaultAddress", "")
            vault_name = vault.get("vaultName", vault_address[:10] + "...")
            equity = float(vault.get("equity", 0))

            # Get additional vault details if available
            pnl = float(vault.get("pnl", 0))
            roi = float(vault.get("roi", 0))
            deposit_value = float(vault.get("depositValue", equity))

            apr = float(vault.get("apr", 0))

            # Leader monitoring data
            leader_address = vault.get("leader", "")
            leader_fraction = float(vault.get("leaderFraction", 0)) * 100  # percentage
            leader_commission = float(vault.get("leaderCommission", 0)) * 100  # percentage
            max_distributable = float(vault.get("maxDistributable", 0))
            is_closed = vault.get("isClosed", False)

            # Calculate leader equity from fraction and total vault
            leader_equity = max_distributable * (leader_fraction / 100) if max_distributable > 0 else 0

            vaults.append({
                "vault_address": vault_address,
                "vault_name": vault_name,
                "equity": equity,
                "pnl": pnl,
                "roi": roi * 100 if abs(roi) < 1 else roi,  # Convert to percentage if needed
                "deposit_value": deposit_value,
                "apr": apr,
                "leader_address": leader_address,
                "leader_fraction": leader_fraction,
                "leader_equity": leader_equity,
                "leader_commission": leader_commission,
                "vault_total_value": max_distributable,
                "is_closed": is_closed,
            })

            total_vault_equity += equity

        # Parse Phase 1 data
        # Portfolio history and P&L
        account_value_history = []
        if portfolio_data and isinstance(portfolio_data, dict):
            # Portfolio API returns data nested by timeframe
            all_time_data = portfolio_data.get("allTime", {})
            if isinstance(all_time_data, dict):
                account_value_history = all_time_data.get("accountValueHistory", [])

        pnl_24h = 0.0
        pnl_7d = 0.0
        pnl_30d = 0.0
        pnl_all_time = 0.0

        if account_value_history:
            now = datetime.now()
            cutoff_24h = int((now - timedelta(hours=24)).timestamp() * 1000)
            cutoff_7d = int((now - timedelta(days=7)).timestamp() * 1000)
            cutoff_30d = int((now - timedelta(days=30)).timestamp() * 1000)

            # Find account values at each timeframe
            value_24h_ago = None
            value_7d_ago = None
            value_30d_ago = None
            oldest_value = None

            for entry in account_value_history:
                timestamp = entry.get("time", 0)
                value = float(entry.get("accountValue", 0))

                if timestamp >= cutoff_24h and value_24h_ago is None:
                    value_24h_ago = value
                if timestamp >= cutoff_7d and value_7d_ago is None:
                    value_7d_ago = value
                if timestamp >= cutoff_30d and value_30d_ago is None:
                    value_30d_ago = value

                # Track oldest value for all-time P&L
                if oldest_value is None or timestamp < oldest_value.get("time", float('inf')):
                    oldest_value = entry

            # Calculate P&L
            current_value = account_value
            if value_24h_ago:
                pnl_24h = current_value - value_24h_ago
            if value_7d_ago:
                pnl_7d = current_value - value_7d_ago
            if value_30d_ago:
                pnl_30d = current_value - value_30d_ago
            if oldest_value:
                pnl_all_time = current_value - float(oldest_value.get("accountValue", current_value))

        # Trade fills and realized P&L
        realized_pnl_24h = 0.0
        realized_pnl_7d = 0.0
        realized_pnl_30d = 0.0
        trades_24h = 0
        fees_paid_24h = 0.0
        fees_paid_30d = 0.0
        recent_trades = []

        if trade_fills:
            now = datetime.now()
            cutoff_24h = int((now - timedelta(hours=24)).timestamp() * 1000)
            cutoff_7d = int((now - timedelta(days=7)).timestamp() * 1000)
            cutoff_30d = int((now - timedelta(days=30)).timestamp() * 1000)

            for fill in trade_fills:
                timestamp = fill.get("time", 0)
                closed_pnl = float(fill.get("closedPnl", 0))
                fee = float(fill.get("fee", 0))

                # Count trades and aggregate metrics
                if timestamp >= cutoff_24h:
                    trades_24h += 1
                    realized_pnl_24h += closed_pnl
                    fees_paid_24h += fee

                if timestamp >= cutoff_7d:
                    realized_pnl_7d += closed_pnl

                if timestamp >= cutoff_30d:
                    realized_pnl_30d += closed_pnl
                    fees_paid_30d += fee

            # Keep only the most recent N trades for attributes
            sorted_fills = sorted(trade_fills, key=lambda x: x.get("time", 0), reverse=True)
            for fill in sorted_fills[:trade_history_count]:
                recent_trades.append({
                    "coin": fill.get("coin", ""),
                    "side": fill.get("side", ""),
                    "size": float(fill.get("sz", 0)),
                    "price": float(fill.get("px", 0)),
                    "closed_pnl": float(fill.get("closedPnl", 0)),
                    "fee": float(fill.get("fee", 0)),
                    "timestamp": fill.get("time", 0),
                })

        # Funding payments
        funding_24h = 0.0
        funding_7d = 0.0
        funding_30d = 0.0
        funding_by_coin = {}

        if funding_data:
            now = datetime.now()
            cutoff_24h = int((now - timedelta(hours=24)).timestamp() * 1000)
            cutoff_7d = int((now - timedelta(days=7)).timestamp() * 1000)
            cutoff_30d = int((now - timedelta(days=30)).timestamp() * 1000)

            for funding in funding_data:
                timestamp = funding.get("time", 0)
                coin = funding.get("coin", "")
                usdc = float(funding.get("usdc", 0))
                funding_rate = float(funding.get("fundingRate", 0))

                # Aggregate by timeframe
                if timestamp >= cutoff_24h:
                    funding_24h += usdc
                if timestamp >= cutoff_7d:
                    funding_7d += usdc
                if timestamp >= cutoff_30d:
                    funding_30d += usdc

                # Track by coin for position-specific data
                if coin not in funding_by_coin:
                    funding_by_coin[coin] = {
                        "funding_24h": 0.0,
                        "funding_rate": funding_rate,
                        "count": 0,
                    }

                if timestamp >= cutoff_24h:
                    funding_by_coin[coin]["funding_24h"] += usdc
                    funding_by_coin[coin]["count"] += 1

                # Update to latest funding rate
                if timestamp > funding_by_coin[coin].get("latest_time", 0):
                    funding_by_coin[coin]["funding_rate"] = funding_rate
                    funding_by_coin[coin]["latest_time"] = timestamp

        # Open orders
        parsed_orders = []
        for order in open_orders:
            coin = order.get("coin", "")
            side = order.get("side", "")
            limit_px = float(order.get("limitPx", 0))
            sz = float(order.get("sz", 0))
            oid = order.get("oid", 0)
            order_type = order.get("orderType", "limit")
            trigger_px = order.get("triggerPx")
            reduce_only = order.get("reduceOnly", False)

            parsed_orders.append({
                "coin": coin,
                "side": side,
                "price": limit_px,
                "size": sz,
                "order_id": oid,
                "order_type": order_type,
                "trigger_price": float(trigger_px) if trigger_px else None,
                "reduce_only": reduce_only,
                "filled": 0.0,  # Not provided by API
                "remaining": sz,
            })

        # Referral data
        referral_earnings = 0.0
        referral_volume = 0.0
        referral_info = {}

        if referral_data:
            referral_earnings = float(referral_data.get("totalReferralUsdc", 0))
            referral_volume = float(referral_data.get("totalReferralVolume", 0))
            referral_info = {
                "referrer": referral_data.get("referrer", ""),
                "referee_count": len(referral_data.get("referees", [])),
            }

        return HyperliquidAccountData(
            account_value=account_value,
            unrealized_pnl=total_unrealized_pnl,
            margin_used=total_margin_used,
            withdrawable=withdrawable,
            positions=positions,
            vaults=vaults,
            total_vault_equity=total_vault_equity,
            # Phase 1 additions
            pnl_24h=pnl_24h,
            pnl_7d=pnl_7d,
            pnl_30d=pnl_30d,
            pnl_all_time=pnl_all_time,
            account_value_history=account_value_history,
            realized_pnl_24h=realized_pnl_24h,
            realized_pnl_7d=realized_pnl_7d,
            realized_pnl_30d=realized_pnl_30d,
            trades_24h=trades_24h,
            fees_paid_24h=fees_paid_24h,
            fees_paid_30d=fees_paid_30d,
            recent_trades=recent_trades,
            funding_24h=funding_24h,
            funding_7d=funding_7d,
            funding_30d=funding_30d,
            funding_by_coin=funding_by_coin,
            open_orders_count=len(parsed_orders),
            open_orders=parsed_orders,
            referral_earnings=referral_earnings,
            referral_volume=referral_volume,
            referral_data=referral_info,
        )

    async def async_update_options(self) -> None:
        """Update options and refresh interval."""
        update_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        self.update_interval = timedelta(seconds=update_interval)
        _LOGGER.debug("Updated refresh interval to %s seconds", update_interval)
