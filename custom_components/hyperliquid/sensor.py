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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_APR,
    ATTR_COIN,
    ATTR_DEPOSIT_VALUE,
    ATTR_ENTRY_PRICE,
    ATTR_EQUITY,
    ATTR_IS_CLOSED,
    ATTR_LEADER_ADDRESS,
    ATTR_LEADER_COMMISSION,
    ATTR_LEADER_EQUITY,
    ATTR_LEADER_FRACTION,
    ATTR_LEVERAGE,
    ATTR_LIQUIDATION_PRICE,
    ATTR_MARGIN_USED,
    ATTR_MARK_PRICE,
    ATTR_PNL,
    ATTR_POSITION_VALUE,
    ATTR_RETURN_ON_EQUITY,
    ATTR_ROI,
    ATTR_SIDE,
    ATTR_SIZE,
    ATTR_UNREALIZED_PNL,
    ATTR_VAULT_ADDRESS,
    ATTR_VAULT_NAME,
    ATTR_VAULT_TOTAL_VALUE,
    CONF_WALLET_ADDRESS,
    CURRENCY_USD,
    DOMAIN,
    SENSOR_ACCOUNT_VALUE,
    SENSOR_MARGIN_USED,
    SENSOR_TOTAL_VAULT_EQUITY,
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
        translation_key=SENSOR_ACCOUNT_VALUE,
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.account_value,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_UNREALIZED_PNL,
        translation_key=SENSOR_UNREALIZED_PNL,
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.unrealized_pnl,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_MARGIN_USED,
        translation_key=SENSOR_MARGIN_USED,
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.margin_used,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_WITHDRAWABLE,
        translation_key=SENSOR_WITHDRAWABLE,
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.withdrawable,
    ),
    HyperliquidSensorEntityDescription(
        key=SENSOR_TOTAL_VAULT_EQUITY,
        translation_key=SENSOR_TOTAL_VAULT_EQUITY,
        native_unit_of_measurement=CURRENCY_USD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data: data.total_vault_equity,
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

    # Add position sensors for each open position
    if coordinator.data:
        for position in coordinator.data.positions:
            entities.append(
                HyperliquidPositionSensor(
                    coordinator=coordinator,
                    wallet_address=wallet_address,
                    coin=position["coin"],
                )
            )

        # Add vault sensors for each vault deposit
        for vault in coordinator.data.vaults:
            entities.append(
                HyperliquidVaultSensor(
                    coordinator=coordinator,
                    wallet_address=wallet_address,
                    vault_address=vault["vault_address"],
                    vault_name=vault["vault_name"],
                )
            )

    async_add_entities(entities)

    # Set up listener to add/remove position and vault sensors dynamically
    @callback
    def async_update_entities() -> None:
        """Handle position and vault changes."""
        if not coordinator.data:
            return

        new_entities = []

        # Handle positions
        current_coins = {pos["coin"] for pos in coordinator.data.positions}
        existing_positions = hass.data[DOMAIN].get(f"{entry.entry_id}_position_entities", {})
        existing_coins = set(existing_positions.keys())

        for coin in current_coins - existing_coins:
            entity = HyperliquidPositionSensor(
                coordinator=coordinator,
                wallet_address=wallet_address,
                coin=coin,
            )
            new_entities.append(entity)
            existing_positions[coin] = entity

        hass.data[DOMAIN][f"{entry.entry_id}_position_entities"] = existing_positions

        # Handle vaults
        current_vaults = {v["vault_address"] for v in coordinator.data.vaults}
        existing_vaults = hass.data[DOMAIN].get(f"{entry.entry_id}_vault_entities", {})
        existing_vault_addrs = set(existing_vaults.keys())

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

        hass.data[DOMAIN][f"{entry.entry_id}_vault_entities"] = existing_vaults

        if new_entities:
            async_add_entities(new_entities)

    # Initialize entity tracking
    hass.data[DOMAIN][f"{entry.entry_id}_position_entities"] = {
        pos["coin"]: None for pos in (coordinator.data.positions if coordinator.data else [])
    }
    hass.data[DOMAIN][f"{entry.entry_id}_vault_entities"] = {
        v["vault_address"]: None for v in (coordinator.data.vaults if coordinator.data else [])
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
    _attr_has_entity_name = True

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

        self._attr_unique_id = f"{wallet_address}_{description.key}"
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


class HyperliquidPositionSensor(
    CoordinatorEntity[HyperliquidDataUpdateCoordinator], SensorEntity
):
    """Representation of a Hyperliquid position sensor."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = CURRENCY_USD
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
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

        return {
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
