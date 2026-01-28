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
    CONF_UPDATE_INTERVAL,
    CONF_WALLET_ADDRESS,
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

    def _fetch_all_data(self, wallet_address: str) -> tuple[dict, list]:
        """Fetch user state and vault equities from API (runs in executor)."""
        from hyperliquid.info import Info

        if self._info is None:
            self._info = Info(skip_ws=True)

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

        return user_state, vault_equities

    async def _async_update_data(self) -> HyperliquidAccountData:
        """Fetch data from Hyperliquid API."""
        try:
            # Fetch all data from API (in executor to avoid blocking)
            user_state, vault_equities = await self.hass.async_add_executor_job(
                self._fetch_all_data, self.wallet_address
            )

            return self._parse_data(user_state, vault_equities)

        except Exception as err:
            _LOGGER.error("Error fetching Hyperliquid data: %s", err)
            raise UpdateFailed(f"Error communicating with Hyperliquid API: {err}") from err

    def _parse_data(self, user_state: dict[str, Any], vault_equities: list[dict[str, Any]]) -> HyperliquidAccountData:
        """Parse user state response into structured data."""
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

        return HyperliquidAccountData(
            account_value=account_value,
            unrealized_pnl=total_unrealized_pnl,
            margin_used=total_margin_used,
            withdrawable=withdrawable,
            positions=positions,
            vaults=vaults,
            total_vault_equity=total_vault_equity,
        )

    async def async_update_options(self) -> None:
        """Update options and refresh interval."""
        update_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        self.update_interval = timedelta(seconds=update_interval)
        _LOGGER.debug("Updated refresh interval to %s seconds", update_interval)
