"""Sensor platform for Hyperliquid integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ACCOUNT_VALUE_HISTORY,
    ATTR_APR,
    ATTR_COIN,
    ATTR_DEPOSIT_VALUE,
    ATTR_ENTRY_PRICE,
    ATTR_EQUITY,
    ATTR_ESTIMATED_FUNDING_DAILY,
    ATTR_FILLED,
    ATTR_FUNDING_24H,
    ATTR_FUNDING_RATE,
    ATTR_IS_CLOSED,
    ATTR_LEADER_ADDRESS,
    ATTR_LEADER_COMMISSION,
    ATTR_LEADER_EQUITY,
    ATTR_LEADER_FRACTION,
    ATTR_LEVERAGE,
    ATTR_LIQUIDATION_PRICE,
    ATTR_MARGIN_USED,
    ATTR_MARK_PRICE,
    ATTR_ORDER_ID,
    ATTR_ORDER_TYPE,
    ATTR_PNL,
    ATTR_POSITION_VALUE,
    ATTR_PRICE,
    ATTR_RECENT_TRADES,
    ATTR_REDUCE_ONLY,
    ATTR_REFEREE_COUNT,
    ATTR_REFERRER,
    ATTR_REMAINING,
    ATTR_RETURN_ON_EQUITY,
    ATTR_ROI,
    ATTR_SIDE,
    ATTR_SIZE,
    ATTR_TRIGGER_PRICE,
    ATTR_UNREALIZED_PNL,
    ATTR_VAULT_ADDRESS,
    ATTR_VAULT_NAME,
    ATTR_VAULT_TOTAL_VALUE,
    CONF_WALLET_ADDRESS,
    CURRENCY_USD,
    DOMAIN,
    SENSOR_ACCOUNT_VALUE,
    SENSOR_FEES_PAID_24H,
    SENSOR_FEES_PAID_30D,
    SENSOR_FUNDING_24H,
    SENSOR_FUNDING_7D,
    SENSOR_FUNDING_30D,
    SENSOR_MARGIN_USED,
    SENSOR_OPEN_ORDERS_COUNT,
    SENSOR_PNL_24H,
    SENSOR_PNL_30D,
    SENSOR_PNL_7D,
    SENSOR_PNL_ALL_TIME,
    SENSOR_REALIZED_PNL_24H,
    SENSOR_REALIZED_PNL_30D,
    SENSOR_REALIZED_PNL_7D,
    SENSOR_REFERRAL_EARNINGS,
    SENSOR_REFERRAL_VOLUME,
    SENSOR_TOTAL_VAULT_EQUITY,
    SENSOR_TRADES_24H,
    SENSOR_UNREALIZED_PNL,
    SENSOR_WITHDRAWABLE,
)
from .coordinator import HyperliquidAccountData, HyperliquidDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HyperliquidSensorEntityDescription(SensorEntityDescription):
    """Describes Hyperliquid sensor entity."""

    value_fn: Callable[[HyperliquidAccountData], float | None]


ACCOUNT_SENSORS: tuple[HyperliquidSensorEntityDescription, ...] = (
    HyperliquidSensorEntityDescription(
        key=SENSOR_ACCOUNT_VALUE,
        name="Account Value",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.account_value,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_UNREALIZED_PNL,
        name="Unrealized PnL",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.unrealized_pnl,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_MARGIN_USED,
        name="Margin Used",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.margin_used,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_WITHDRAWABLE,
        name="Withdrawable",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.withdrawable,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_TOTAL_VAULT_EQUITY,
        name="Total Vault Equity",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.total_vault_equity,
    ),
    # Phase 1: Historical P&L
    HyperliquidSensorEntityDescription(
        key=SENSOR_PNL_24H,
        name="PnL 24h",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.pnl_24h,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_PNL_7D,
        name="PnL 7d",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.pnl_7d,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_PNL_30D,
        name="PnL 30d",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.pnl_30d,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_PNL_ALL_TIME,
        name="PnL All Time",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.pnl_all_time,
    ),
    # Phase 1: Realized P&L
    HyperliquidSensorEntityDescription(
        key=SENSOR_REALIZED_PNL_24H,
        name="Realized PnL 24h",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.realized_pnl_24h,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_REALIZED_PNL_7D,
        name="Realized PnL 7d",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.realized_pnl_7d,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_REALIZED_PNL_30D,
        name="Realized PnL 30d",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.realized_pnl_30d,
    ),
    # Phase 1: Trade statistics
    HyperliquidSensorEntityDescription(
        key=SENSOR_TRADES_24H,
        name="Trades 24h",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.trades_24h,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_FEES_PAID_24H,
        name="Fees Paid 24h",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.fees_paid_24h,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_FEES_PAID_30D,
        name="Fees Paid 30d",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.fees_paid_30d,
    ),
    # Phase 1: Funding
    HyperliquidSensorEntityDescription(
        key=SENSOR_FUNDING_24H,
        name="Funding 24h",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.funding_24h,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_FUNDING_7D,
        name="Funding 7d",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.funding_7d,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_FUNDING_30D,
        name="Funding 30d",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.funding_30d,
    ),
    # Phase 1: Open orders
    HyperliquidSensorEntityDescription(
        key=SENSOR_OPEN_ORDERS_COUNT,
        name="Open Orders Count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.open_orders_count,
    ),
    # Phase 1: Referrals
    HyperliquidSensorEntityDescription(
        key=SENSOR_REFERRAL_EARNINGS,
        name="Referral Earnings",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.referral_earnings,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_REFERRAL_VOLUME,
        name="Referral Volume",
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=0,
        value_fn=lambda data: data.referral_volume,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hyperliquid sensor based on a config entry."""
    coordinator: HyperliquidDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    wallet_address = entry.data[CONF_WALLET_ADDRESS]

    entities: list[SensorEntity] = []

    # Add account sensors
    for description in ACCOUNT_SENSORS:
        entities.append(
            HyperliquidAccountSensor(
                coordinator=coordinator,
                description=description,
                wallet_address=wallet_address,
            )
        )

    # Add dynamic sensors for positions, vaults, and orders
    if coordinator.data:
        for position in coordinator.data.positions:
            entities.append(
                HyperliquidPositionSensor(
                    coordinator=coordinator,
                    wallet_address=wallet_address,
                    coin=position["coin"],
                )
            )

        for vault in coordinator.data.vaults:
            entities.append(
                HyperliquidVaultSensor(
                    coordinator=coordinator,
                    wallet_address=wallet_address,
                    vault_address=vault["vault_address"],
                    vault_name=vault["vault_name"],
                )
            )

        for order in coordinator.data.open_orders:
            entities.append(
                HyperliquidOrderSensor(
                    coordinator=coordinator,
                    wallet_address=wallet_address,
                    order_id=order["order_id"],
                    coin=order["coin"],
                )
            )

    async_add_entities(entities)

    # Set up listener to add/remove position, vault, and order sensors dynamically
    @callback
    def async_update_entities() -> None:
        """Handle position, vault, and order changes."""
        if not coordinator.data:
            return

        registry = er.async_get(hass)
        new_entities = []

        # Handle positions
        current_coins = {pos["coin"] for pos in coordinator.data.positions}
        existing_positions = hass.data[DOMAIN].get(f"{entry.entry_id}_position_entities", {})
        existing_coins = set(existing_positions.keys())

        # Add new positions
        for coin in current_coins - existing_coins:
            entity = HyperliquidPositionSensor(
                coordinator=coordinator,
                wallet_address=wallet_address,
                coin=coin,
            )
            new_entities.append(entity)
            existing_positions[coin] = entity

        # Remove closed positions
        for coin in existing_coins - current_coins:
            unique_id = f"{wallet_address}_position_{coin}"
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id:
                _LOGGER.info("Removing closed position entity: %s", entity_id)
                registry.async_remove(entity_id)
            del existing_positions[coin]

        hass.data[DOMAIN][f"{entry.entry_id}_position_entities"] = existing_positions

        # Handle vaults
        current_vaults = {v["vault_address"] for v in coordinator.data.vaults}
        existing_vaults = hass.data[DOMAIN].get(f"{entry.entry_id}_vault_entities", {})
        existing_vault_addrs = set(existing_vaults.keys())

        # Add new vaults
        for vault in coordinator.data.vaults:
            if vault["vault_address"] not in existing_vault_addrs:
                entity = HyperliquidVaultSensor(
                    coordinator=coordinator,
                    wallet_address=wallet_address,
                    vault_address=vault["vault_address"],
                    vault_name=vault["vault_name"],
                )
                new_entities.append(entity)
                existing_vaults[vault["vault_address"]] = entity

        # Remove withdrawn vaults
        for vault_address in existing_vault_addrs - current_vaults:
            unique_id = f"{wallet_address}_vault_{vault_address}"
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id:
                _LOGGER.info("Removing withdrawn vault entity: %s", entity_id)
                registry.async_remove(entity_id)
            del existing_vaults[vault_address]

        hass.data[DOMAIN][f"{entry.entry_id}_vault_entities"] = existing_vaults

        # Handle orders
        current_order_ids = {order["order_id"] for order in coordinator.data.open_orders}
        existing_orders = hass.data[DOMAIN].get(f"{entry.entry_id}_order_entities", {})
        existing_order_ids = set(existing_orders.keys())

        # Add new orders
        for order in coordinator.data.open_orders:
            if order["order_id"] not in existing_order_ids:
                entity = HyperliquidOrderSensor(
                    coordinator=coordinator,
                    wallet_address=wallet_address,
                    order_id=order["order_id"],
                    coin=order["coin"],
                )
                new_entities.append(entity)
                existing_orders[order["order_id"]] = entity

        # Remove filled/cancelled orders
        for order_id in existing_order_ids - current_order_ids:
            unique_id = f"{wallet_address}_order_{order_id}"
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id:
                _LOGGER.info("Removing filled/cancelled order entity: %s", entity_id)
                registry.async_remove(entity_id)
            del existing_orders[order_id]

        hass.data[DOMAIN][f"{entry.entry_id}_order_entities"] = existing_orders

        if new_entities:
            async_add_entities(new_entities)

    # Initialize entity tracking
    hass.data[DOMAIN][f"{entry.entry_id}_position_entities"] = {
        pos["coin"]: None for pos in (coordinator.data.positions if coordinator.data else [])
    }
    hass.data[DOMAIN][f"{entry.entry_id}_vault_entities"] = {
        v["vault_address"]: None for v in (coordinator.data.vaults if coordinator.data else [])
    }
    hass.data[DOMAIN][f"{entry.entry_id}_order_entities"] = {
        order["order_id"]: None for order in (coordinator.data.open_orders if coordinator.data else [])
    }

    # Register listener for updates
    entry.async_on_unload(
        coordinator.async_add_listener(async_update_entities)
    )


class HyperliquidAccountSensor(
    CoordinatorEntity[HyperliquidDataUpdateCoordinator], SensorEntity
):
    """Representation of a Hyperliquid account sensor."""

    entity_description: HyperliquidSensorEntityDescription
    _attr_has_entity_name = False  # Changed from True to get descriptive entity IDs

    def __init__(
        self,
        coordinator: HyperliquidDataUpdateCoordinator,
        description: HyperliquidSensorEntityDescription,
        wallet_address: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._wallet_address = wallet_address
        short_address = f"{wallet_address[:6]}...{wallet_address[-4:]}"

        # Use v2 suffix to force new entity IDs after fixing naming issue
        self._attr_unique_id = f"{wallet_address}_{description.key}_v2"

        # Create descriptive name that becomes entity_id
        sensor_name = description.name if description.name else description.key.replace('_', ' ').title()
        self._attr_name = f"Hyperliquid {short_address} {sensor_name}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, wallet_address)},
            name=f"Hyperliquid {short_address}",
            manufacturer="Hyperliquid",
            model="Perpetuals Account",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes for specific sensors."""
        if self.coordinator.data is None:
            return None

        attributes = {}

        # Add account value history for P&L sensors (for charting)
        if self.entity_description.key in [
            SENSOR_PNL_24H,
            SENSOR_PNL_7D,
            SENSOR_PNL_30D,
            SENSOR_PNL_ALL_TIME,
        ]:
            attributes[ATTR_ACCOUNT_VALUE_HISTORY] = self.coordinator.data.account_value_history

        # Add recent trades for trade statistics sensors
        if self.entity_description.key in [
            SENSOR_TRADES_24H,
            SENSOR_FEES_PAID_24H,
            SENSOR_FEES_PAID_30D,
            SENSOR_REALIZED_PNL_24H,
            SENSOR_REALIZED_PNL_7D,
            SENSOR_REALIZED_PNL_30D,
        ]:
            attributes[ATTR_RECENT_TRADES] = self.coordinator.data.recent_trades

        # Add referral data for referral sensors
        if self.entity_description.key in [SENSOR_REFERRAL_EARNINGS, SENSOR_REFERRAL_VOLUME]:
            attributes.update(self.coordinator.data.referral_data)

        return attributes if attributes else None


class HyperliquidPositionSensor(
    CoordinatorEntity[HyperliquidDataUpdateCoordinator], SensorEntity
):
    """Representation of a Hyperliquid position sensor."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = CURRENCY_USD
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: HyperliquidDataUpdateCoordinator,
        wallet_address: str,
        coin: str,
    ) -> None:
        """Initialize the position sensor."""
        super().__init__(coordinator)
        self._wallet_address = wallet_address
        self._coin = coin
        short_address = f"{wallet_address[:6]}...{wallet_address[-4:]}"

        self._attr_unique_id = f"{wallet_address}_position_{coin}"
        self._attr_name = f"{coin} Position PnL"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, wallet_address)},
            name=f"Hyperliquid {short_address}",
            manufacturer="Hyperliquid",
            model="Perpetuals Account",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the unrealized PnL of the position."""
        position = self._get_position()
        if position is None:
            return None
        return position.get(ATTR_UNREALIZED_PNL)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional position attributes."""
        position = self._get_position()
        if position is None:
            return None

        attributes = {
            ATTR_COIN: position.get("coin"),
            ATTR_SIZE: position.get("size"),
            ATTR_SIDE: position.get("side"),
            ATTR_ENTRY_PRICE: position.get("entry_price"),
            ATTR_MARK_PRICE: position.get("mark_price"),
            ATTR_LIQUIDATION_PRICE: position.get("liquidation_price"),
            ATTR_LEVERAGE: position.get("leverage"),
            ATTR_MARGIN_USED: position.get("margin_used"),
            ATTR_RETURN_ON_EQUITY: position.get("return_on_equity"),
            ATTR_POSITION_VALUE: position.get("position_value"),
        }

        # Add funding data if available
        if self.coordinator.data and self.coordinator.data.funding_by_coin:
            coin = position.get("coin")
            if coin in self.coordinator.data.funding_by_coin:
                funding_info = self.coordinator.data.funding_by_coin[coin]
                attributes[ATTR_FUNDING_RATE] = funding_info.get("funding_rate", 0)
                attributes[ATTR_FUNDING_24H] = funding_info.get("funding_24h", 0)

                # Estimate daily funding (funding happens every 1 hour, so 24 times per day)
                funding_rate = funding_info.get("funding_rate", 0)
                position_value = position.get("position_value", 0)
                attributes[ATTR_ESTIMATED_FUNDING_DAILY] = funding_rate * position_value * 24

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        return self._get_position() is not None

    def _get_position(self) -> dict[str, Any] | None:
        """Get position data for this coin."""
        if self.coordinator.data is None:
            return None

        for position in self.coordinator.data.positions:
            if position.get("coin") == self._coin:
                return position

        return None


class HyperliquidOrderSensor(
    CoordinatorEntity[HyperliquidDataUpdateCoordinator], SensorEntity
):
    """Representation of a Hyperliquid open order sensor."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = CURRENCY_USD
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: HyperliquidDataUpdateCoordinator,
        wallet_address: str,
        order_id: int,
        coin: str,
    ) -> None:
        """Initialize the order sensor."""
        super().__init__(coordinator)
        self._wallet_address = wallet_address
        self._order_id = order_id
        self._coin = coin
        short_address = f"{wallet_address[:6]}...{wallet_address[-4:]}"

        self._attr_unique_id = f"{wallet_address}_order_{order_id}"
        self._attr_name = f"{coin} Order {order_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, wallet_address)},
            name=f"Hyperliquid {short_address}",
            manufacturer="Hyperliquid",
            model="Perpetuals Account",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the order value (price * size)."""
        order = self._get_order()
        if order is None:
            return None
        price = order.get(ATTR_PRICE, 0)
        size = order.get(ATTR_SIZE, 0)
        return price * size

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional order attributes."""
        order = self._get_order()
        if order is None:
            return None

        return {
            ATTR_COIN: order.get("coin"),
            ATTR_SIDE: order.get("side"),
            ATTR_PRICE: order.get("price"),
            ATTR_SIZE: order.get("size"),
            ATTR_ORDER_ID: order.get("order_id"),
            ATTR_ORDER_TYPE: order.get("order_type"),
            ATTR_TRIGGER_PRICE: order.get("trigger_price"),
            ATTR_REDUCE_ONLY: order.get("reduce_only"),
            ATTR_FILLED: order.get("filled"),
            ATTR_REMAINING: order.get("remaining"),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        return self._get_order() is not None

    def _get_order(self) -> dict[str, Any] | None:
        """Get order data for this order ID."""
        if self.coordinator.data is None:
            return None

        for order in self.coordinator.data.open_orders:
            if order.get("order_id") == self._order_id:
                return order

        return None


class HyperliquidVaultSensor(
    CoordinatorEntity[HyperliquidDataUpdateCoordinator], SensorEntity
):
    """Representation of a Hyperliquid vault deposit sensor."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = CURRENCY_USD
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: HyperliquidDataUpdateCoordinator,
        wallet_address: str,
        vault_address: str,
        vault_name: str,
    ) -> None:
        """Initialize the vault sensor."""
        super().__init__(coordinator)
        self._wallet_address = wallet_address
        self._vault_address = vault_address
        self._vault_name = vault_name
        short_address = f"{wallet_address[:6]}...{wallet_address[-4:]}"

        self._attr_unique_id = f"{wallet_address}_vault_{vault_address}"
        self._attr_name = f"Vault {vault_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, wallet_address)},
            name=f"Hyperliquid {short_address}",
            manufacturer="Hyperliquid",
            model="Perpetuals Account",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the equity value of the vault deposit."""
        vault = self._get_vault()
        if vault is None:
            return None
        return vault.get(ATTR_EQUITY)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional vault attributes."""
        vault = self._get_vault()
        if vault is None:
            return None

        return {
            ATTR_VAULT_NAME: vault.get("vault_name"),
            ATTR_VAULT_ADDRESS: vault.get("vault_address"),
            ATTR_PNL: vault.get("pnl"),
            ATTR_ROI: vault.get("roi"),
            ATTR_DEPOSIT_VALUE: vault.get("deposit_value"),
            ATTR_APR: vault.get("apr"),
            ATTR_LEADER_ADDRESS: vault.get("leader_address"),
            ATTR_LEADER_FRACTION: vault.get("leader_fraction"),
            ATTR_LEADER_EQUITY: vault.get("leader_equity"),
            ATTR_LEADER_COMMISSION: vault.get("leader_commission"),
            ATTR_VAULT_TOTAL_VALUE: vault.get("vault_total_value"),
            ATTR_IS_CLOSED: vault.get("is_closed"),
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        return self._get_vault() is not None

    def _get_vault(self) -> dict[str, Any] | None:
        """Get vault data for this vault address."""
        if self.coordinator.data is None:
            return None

        for vault in self.coordinator.data.vaults:
            if vault.get("vault_address") == self._vault_address:
                return vault

        return None
