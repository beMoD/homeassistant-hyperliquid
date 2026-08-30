"""DataUpdateCoordinator for Hyperliquid integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    API_TIMEOUT,
    CONF_TRADE_HISTORY_COUNT,
    CONF_TRADE_HISTORY_DAYS,
    CONF_UPDATE_INTERVAL,
    CONF_WALLET_ADDRESS,
    DEFAULT_TRADE_HISTORY_COUNT,
    DEFAULT_TRADE_HISTORY_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    FILL_HISTORY_DAYS,
    STAKING_TOKEN,
    UPDATE_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


def _as_float(value: Any, default: float = 0.0) -> float:
    """Coerce an API value to float. The API sends numbers as strings."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class HyperliquidAccountData:
    """Class to hold account data."""

    # Hyperliquid's "Total Equity": spot + perp + vaults + staking. NOT
    # marginSummary.accountValue, which covers the perp side only and reads 0
    # whenever no perp position is open.
    account_value: float
    trading_equity: float
    staking_balance: float
    staking_value: float
    max_drawdown_24h: float
    max_drawdown_7d: float
    max_drawdown_30d: float
    max_drawdown_all_time: float
    unrealized_pnl: float
    margin_used: float
    withdrawable: float
    positions: list[dict[str, Any]]
    vaults: list[dict[str, Any]]
    total_vault_equity: float
    # Phase 1 additions
    # Cut to the exact window; None when the history does not reach back far
    # enough, same as the perp sensors below.
    pnl_24h: float | None
    pnl_7d: float | None
    pnl_30d: float | None
    pnl_all_time: float
    # Perp-only P&L. None means the portfolio history does not reach back far
    # enough for that window — the sensor then reports "unknown" rather than a
    # number that silently covers a shorter span.
    perp_pnl_24h: float | None
    perp_pnl_7d: float | None
    perp_pnl_10d: float | None
    perp_pnl_14d: float | None
    perp_pnl_20d: float | None
    perp_pnl_21d: float | None
    perp_pnl_28d: float | None
    perp_pnl_30d: float | None
    perp_pnl_all_time: float
    # Spot + vaults, derived as total minus perp over the same window.
    non_perp_pnl_24h: float | None
    non_perp_pnl_7d: float | None
    non_perp_pnl_30d: float | None
    non_perp_pnl_all_time: float
    volume_24h: float
    volume_7d: float
    volume_30d: float
    volume_all_time: float
    perp_volume_24h: float
    perp_volume_7d: float
    perp_volume_30d: float
    perp_volume_all_time: float
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
        # token index -> USDC pair name ("@107"), built once from spotMeta.
        # The listing table is static and the response is ~130 KB, so it must
        # not be refetched on every poll; prices come from the much smaller
        # allMids instead.
        self._spot_pairs: dict[int, str] | None = None
        self._known_tokens: set[int] = set()
        self._staking_token: int | None = None

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

        try:
            if self._info is None:
                # Pass a per-request timeout so a hung connection cannot block
                # this executor thread (and the coordinator) forever. The SDK
                # forwards it to requests for both the constructor's meta calls
                # and every later post().
                self._info = Info(skip_ws=True, timeout=API_TIMEOUT)
        except Exception:
            self._info = None
            raise

        try:
            return self._fetch_all_data_inner(wallet_address)
        except Exception:
            self._info = None
            raise

    def _fetch_spot_pairs(self) -> dict[int, str]:
        """Map each spot token index to the name of its USDC pair.

        allMids keys spot markets by pair name ("@107"), while balances key by
        token index, so the two need this table to be joined. Tokens without a
        USDC pair are left out — they have no directly quoted USD price. The
        HYPE index is picked up here too, for the staking balance.
        """
        spot_meta = self._info.post("/info", {"type": "spotMeta"}) or {}

        known: set[int] = set()
        for position, token in enumerate(spot_meta.get("tokens") or []):
            index = token.get("index", position)
            known.add(index)
            if token.get("name") == STAKING_TOKEN:
                self._staking_token = index
        self._known_tokens = known

        pairs: dict[int, str] = {}
        for pair in spot_meta.get("universe") or []:
            tokens = pair.get("tokens") or []
            name = pair.get("name")
            if len(tokens) == 2 and tokens[1] == 0 and name:
                pairs[tokens[0]] = name
        return pairs

    def _fetch_all_data_inner(self, wallet_address: str) -> dict[str, Any]:
        """Inner fetch — called after Info is initialized."""
        from datetime import datetime, timedelta, timezone

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
            _LOGGER.debug("Failed to fetch portfolio data: %s", err)

        try:
            # Trade fills. Always fetched over the full 30d window: the parser
            # buckets them into 24h/7d/30d, so a shorter fetch would silently
            # cap realized_pnl_30d / fees_paid_30d at the fetch window.
            # trade_history_days only narrows the "recent trades" attribute.
            now = datetime.now(tz=timezone.utc)
            end_time = int(now.timestamp() * 1000)
            start_time = int((now - timedelta(days=FILL_HISTORY_DAYS)).timestamp() * 1000)
            trade_fills = self._info.user_fills_by_time(wallet_address, start_time, end_time) or []
        except Exception as err:
            _LOGGER.debug("Failed to fetch trade fills: %s", err)

        try:
            # Funding payments over the last 30 days (single POST; the parser
            # buckets them into the 24h/7d/30d windows). user_funding_history
            # requires an explicit startTime.
            funding_start = int((now - timedelta(days=30)).timestamp() * 1000)
            funding_data = (
                self._info.user_funding_history(wallet_address, funding_start, end_time)
                or []
            )
        except Exception as err:
            _LOGGER.warning("Failed to fetch funding data: %s", err)

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

        # Unified account: spot balances carry the trading collateral, so the
        # perp-only marginSummary no longer describes the account on its own.
        spot_state = {}
        staking = {}
        mids = {}

        try:
            spot_state = self._info.post(
                "/info", {"type": "spotClearinghouseState", "user": wallet_address}
            ) or {}
        except Exception as err:
            _LOGGER.debug("Failed to fetch spot balances: %s", err)

        try:
            staking = self._info.post(
                "/info", {"type": "delegatorSummary", "user": wallet_address}
            ) or {}
        except Exception as err:
            _LOGGER.debug("Failed to fetch staking summary: %s", err)

        try:
            mids = self._info.post("/info", {"type": "allMids"}) or {}
        except Exception as err:
            _LOGGER.debug("Failed to fetch mid prices: %s", err)

        held_tokens = {
            balance.get("token")
            for balance in spot_state.get("balances") or []
            if _as_float(balance.get("total")) != 0
        }
        # Refetch only when a token shows up that the cached listing table has
        # never seen. Comparing against _known_tokens rather than the pair map
        # matters: USDC and any token without a USDC pair are absent from the
        # pairs, and comparing against those would refetch on every poll.
        if self._spot_pairs is None or held_tokens - self._known_tokens:
            try:
                self._spot_pairs = self._fetch_spot_pairs()
            except Exception as err:
                _LOGGER.debug("Failed to fetch spot metadata: %s", err)

        return {
            "spot_state": spot_state,
            "staking": staking,
            "mids": mids,
            "spot_pairs": self._spot_pairs or {},
            "staking_token": self._staking_token,
            "user_state": user_state,
            "vault_equities": vault_equities,
            "portfolio_data": portfolio_data,
            "trade_fills": trade_fills,
            "funding_data": funding_data,
            "open_orders": open_orders,
            "referral_data": referral_data,
            "trade_history_count": trade_history_count,
            "trade_history_days": trade_history_days,
        }

    async def _async_update_data(self) -> HyperliquidAccountData:
        """Fetch data from Hyperliquid API."""
        try:
            # Fetch all data from API (in executor to avoid blocking).
            # Wrap in an overall timeout as a safety net: even with per-request
            # timeouts, a chain of slow-but-alive calls must not stall forever.
            async with asyncio.timeout(UPDATE_TIMEOUT):
                all_data = await self.hass.async_add_executor_job(
                    self._fetch_all_data, self.wallet_address
                )

            return self._parse_data(all_data)

        except TimeoutError as err:
            # Drop the client so the next cycle re-instantiates it cleanly.
            self._info = None
            raise UpdateFailed(
                f"Timed out communicating with Hyperliquid API after {UPDATE_TIMEOUT}s"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Hyperliquid API: {err}") from err

    def _parse_data(self, all_data: dict[str, Any]) -> HyperliquidAccountData:
        """Parse user state response into structured data."""
        from datetime import datetime, timedelta, timezone

        user_state = all_data["user_state"]
        vault_equities = all_data["vault_equities"]
        portfolio_data = all_data.get("portfolio_data", {})
        trade_fills = all_data.get("trade_fills", [])
        funding_data = all_data.get("funding_data", [])
        open_orders = all_data.get("open_orders", [])
        referral_data = all_data.get("referral_data", {})
        spot_state = all_data.get("spot_state", {})
        staking = all_data.get("staking", {})
        mids = all_data.get("mids", {})
        spot_pairs = all_data.get("spot_pairs", {})
        staking_token = all_data.get("staking_token")
        trade_history_count = all_data.get("trade_history_count", DEFAULT_TRADE_HISTORY_COUNT)
        trade_history_days = all_data.get("trade_history_days", DEFAULT_TRADE_HISTORY_DAYS)

        margin_summary = user_state.get("marginSummary", {})
        asset_positions = user_state.get("assetPositions", [])

        # Extract account-level values. marginSummary describes the perp side
        # only; under the unified account the collateral lives in the spot
        # balances, so account_value is assembled further down instead.
        perp_account_value = float(margin_summary.get("accountValue", 0))
        total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
        perp_withdrawable = float(user_state.get("withdrawable", 0))

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
                "roi": roi * 100,  # API returns decimal, convert to percentage
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
        # Portfolio history and P&L. The portfolio endpoint returns a LIST of
        # [period, data] pairs (day/week/month/allTime/perp*), not a dict, and
        # every history entry is a [timestamp, "value"] pair, not a dict.
        portfolio_periods: dict[str, Any] = {}
        if isinstance(portfolio_data, list):
            portfolio_periods = {
                pair[0]: pair[1]
                for pair in portfolio_data
                if isinstance(pair, (list, tuple)) and len(pair) == 2
            }
        elif isinstance(portfolio_data, dict):
            portfolio_periods = portfolio_data

        def _series(period: str, key: str) -> list[tuple[int, float]]:
            """Return one history series as (timestamp_ms, value) tuples."""
            period_data = portfolio_periods.get(period) or {}
            if not isinstance(period_data, dict):
                return []
            series = []
            for entry in period_data.get(key) or []:
                try:
                    series.append((int(entry[0]), float(entry[1])))
                except (TypeError, ValueError, IndexError):
                    continue
            return series

        def _window_pnl(period: str) -> float:
            """P&L over a period, from the API's own cumulative pnlHistory.

            Using pnlHistory rather than the account value keeps deposits and
            withdrawals out of the number, and avoids comparing the portfolio
            total (perps + spot + vaults) against the perp-only accountValue.
            """
            series = _series(period, "pnlHistory")
            if len(series) < 2:
                return 0.0
            return series[-1][1] - series[0][1]

        def _window_delta(period: str, days: float) -> float | None:
            """P&L over exactly `days`, cut out of a period's pnlHistory.

            Returns None when the series does not reach that far back. This
            matters: the month series only spans ~30.8 days, so asking it for
            40 days would otherwise return its full span — a plausible-looking
            number for a window it never covered. The anchor point must sit
            within roughly one sampling interval of the target timestamp.
            """
            series = _series(period, "pnlHistory")
            if len(series) < 2:
                return None

            target = series[-1][0] - int(days * 86_400_000)
            gaps = sorted(
                series[i + 1][0] - series[i][0] for i in range(len(series) - 1)
            )
            tolerance = max(int(gaps[len(gaps) // 2] * 1.5), 6 * 3_600_000)

            anchor = min(series, key=lambda entry: abs(entry[0] - target))
            if abs(anchor[0] - target) > tolerance:
                return None
            return series[-1][1] - anchor[1]

        def _volume(period: str) -> float:
            """Traded volume reported for a period."""
            period_data = portfolio_periods.get(period) or {}
            if not isinstance(period_data, dict):
                return 0.0
            try:
                return float(period_data.get("vlm", 0))
            except (TypeError, ValueError):
                return 0.0

        # Cut to the exact window, like the perp sensors below. The API period
        # is not the window it is named after — "month" spans ~30.8 days — so
        # taking it end-to-end overstated pnl_30d by nearly a day and left it
        # inconsistent with perp_pnl_30d + non_perp_pnl_30d.
        pnl_24h = _window_delta("day", 1)
        pnl_7d = _window_delta("week", 7)
        pnl_30d = _window_delta("month", 30)
        pnl_all_time = _window_pnl("allTime")

        # Perp-only windows. 24h and 7d come from the finer day/week series;
        # everything longer from perpMonth, whose ~10h raster puts the anchor
        # within a few hours of every window boundary.
        perp_pnl_24h = _window_delta("perpDay", 1)
        perp_pnl_7d = _window_delta("perpWeek", 7)
        perp_pnl_10d = _window_delta("perpMonth", 10)
        perp_pnl_14d = _window_delta("perpMonth", 14)
        perp_pnl_20d = _window_delta("perpMonth", 20)
        perp_pnl_21d = _window_delta("perpMonth", 21)
        perp_pnl_28d = _window_delta("perpMonth", 28)
        perp_pnl_30d = _window_delta("perpMonth", 30)
        perp_pnl_all_time = _window_pnl("perpAllTime")

        def _non_perp(total_period: str, perp_period: str, days: float) -> float | None:
            """Spot + vault share of the P&L, over one matched window."""
            total = _window_delta(total_period, days)
            perp = _window_delta(perp_period, days)
            if total is None or perp is None:
                return None
            return total - perp

        non_perp_pnl_24h = _non_perp("day", "perpDay", 1)
        non_perp_pnl_7d = _non_perp("week", "perpWeek", 7)
        non_perp_pnl_30d = _non_perp("month", "perpMonth", 30)
        non_perp_pnl_all_time = pnl_all_time - perp_pnl_all_time

        def _max_drawdown(period: str) -> float:
            """Largest peak-to-trough drop of the account value, in percent."""
            series = _series(period, "accountValueHistory")
            peak = None
            worst = 0.0
            for _, value in series:
                if peak is None or value > peak:
                    peak = value
                if peak and peak > 0:
                    worst = max(worst, (peak - value) / peak)
            return worst * 100

        max_drawdown_24h = _max_drawdown("day")
        max_drawdown_7d = _max_drawdown("week")
        max_drawdown_30d = _max_drawdown("month")
        max_drawdown_all_time = _max_drawdown("allTime")

        # Total volume matches the panel's "Volume" row in its
        # "Perps + Spot + Vaults" setting; the perp_* ones match its perp-only
        # setting.
        volume_24h = _volume("day")
        volume_7d = _volume("week")
        volume_30d = _volume("month")
        volume_all_time = _volume("allTime")

        perp_volume_24h = _volume("perpDay")
        perp_volume_7d = _volume("perpWeek")
        perp_volume_30d = _volume("perpMonth")
        perp_volume_all_time = _volume("perpAllTime")

        # Unified account equity, mirroring Hyperliquid's own panel.
        def _spot_price(token: int) -> float | None:
            """USD mid price of a spot token, via its USDC pair."""
            if token == 0:  # USDC itself
                return 1.0
            pair = spot_pairs.get(token)
            if pair is None:
                return None
            price = mids.get(pair)
            return _as_float(price, 0.0) if price is not None else None

        spot_value = 0.0
        for balance in spot_state.get("balances") or []:
            amount = _as_float(balance.get("total"))
            if amount == 0:
                continue
            price = _spot_price(balance.get("token"))
            if price is None:
                # Token without a USDC pair — no quoted price, so counting it
                # as zero is wrong, but inventing one would be worse.
                _LOGGER.debug("No USD price for spot token %s", balance.get("coin"))
                continue
            spot_value += amount * price

        # "Trading Equity" in the panel: everything available for trading,
        # which is the spot wallet plus whatever sits in the perp account.
        trading_equity = spot_value + perp_account_value

        # Withdrawable is USDC, and under the unified account it is reported
        # per token in the spot state rather than by marginSummary. Fall back
        # to the perp field so accounts that are not unified still work.
        withdrawable = perp_withdrawable
        for entry in spot_state.get("tokenToAvailableAfterMaintenance") or []:
            if isinstance(entry, (list, tuple)) and len(entry) == 2 and entry[0] == 0:
                withdrawable = _as_float(entry[1], perp_withdrawable)
                break

        staking_balance = _as_float(staking.get("delegated"))
        staking_price = (
            _spot_price(staking_token) if staking_token is not None else None
        )
        staking_value = staking_balance * staking_price if staking_price else 0.0

        # "Total Equity": the portfolio endpoint already reports it and is the
        # only source that also covers staking, so prefer it and fall back to
        # summing the parts only if the history is missing.
        equity_series = _series("allTime", "accountValueHistory")
        if equity_series:
            account_value = equity_series[-1][1]
        else:
            account_value = trading_equity + total_vault_equity + staking_value

        # Normalized history for the charting attribute
        account_value_history = [
            {"time": timestamp, "accountValue": value}
            for timestamp, value in _series("allTime", "accountValueHistory")
        ]

        # Trade fills and realized P&L
        realized_pnl_24h = 0.0
        realized_pnl_7d = 0.0
        realized_pnl_30d = 0.0
        trades_24h = 0
        fees_paid_24h = 0.0
        fees_paid_30d = 0.0
        recent_trades = []

        if trade_fills:
            now = datetime.now(tz=timezone.utc)
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

            # Keep only the most recent N trades from the configured window
            cutoff_recent = int(
                (now - timedelta(days=trade_history_days)).timestamp() * 1000
            )
            sorted_fills = sorted(
                (f for f in trade_fills if f.get("time", 0) >= cutoff_recent),
                key=lambda x: x.get("time", 0),
                reverse=True,
            )
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
            now = datetime.now(tz=timezone.utc)
            cutoff_24h = int((now - timedelta(hours=24)).timestamp() * 1000)
            cutoff_7d = int((now - timedelta(days=7)).timestamp() * 1000)
            cutoff_30d = int((now - timedelta(days=30)).timestamp() * 1000)

            for funding in funding_data:
                # userFunding records nest the payment fields under "delta";
                # only "time" and "hash" sit at the top level.
                timestamp = funding.get("time", 0)
                delta = funding.get("delta", {})
                coin = delta.get("coin", "")
                usdc = float(delta.get("usdc", 0))
                funding_rate = float(delta.get("fundingRate", 0))

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
            trading_equity=trading_equity,
            staking_balance=staking_balance,
            staking_value=staking_value,
            max_drawdown_24h=max_drawdown_24h,
            max_drawdown_7d=max_drawdown_7d,
            max_drawdown_30d=max_drawdown_30d,
            max_drawdown_all_time=max_drawdown_all_time,
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
            perp_pnl_24h=perp_pnl_24h,
            perp_pnl_7d=perp_pnl_7d,
            perp_pnl_10d=perp_pnl_10d,
            perp_pnl_14d=perp_pnl_14d,
            perp_pnl_20d=perp_pnl_20d,
            perp_pnl_21d=perp_pnl_21d,
            perp_pnl_28d=perp_pnl_28d,
            perp_pnl_30d=perp_pnl_30d,
            perp_pnl_all_time=perp_pnl_all_time,
            non_perp_pnl_24h=non_perp_pnl_24h,
            non_perp_pnl_7d=non_perp_pnl_7d,
            non_perp_pnl_30d=non_perp_pnl_30d,
            non_perp_pnl_all_time=non_perp_pnl_all_time,
            volume_24h=volume_24h,
            volume_7d=volume_7d,
            volume_30d=volume_30d,
            volume_all_time=volume_all_time,
            perp_volume_24h=perp_volume_24h,
            perp_volume_7d=perp_volume_7d,
            perp_volume_30d=perp_volume_30d,
            perp_volume_all_time=perp_volume_all_time,
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
