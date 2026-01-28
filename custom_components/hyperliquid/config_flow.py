"""Config flow for Hyperliquid integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_UPDATE_INTERVAL,
    CONF_WALLET_ADDRESS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

WALLET_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")


def validate_wallet_address(address: str) -> bool:
    """Validate Ethereum wallet address format."""
    return bool(WALLET_ADDRESS_REGEX.match(address))


class HyperliquidConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hyperliquid."""

    VERSION = 1

    @staticmethod
    def _test_api_connection(wallet_address: str) -> dict:
        """Test API connection (runs in executor)."""
        from hyperliquid.info import Info

        info = Info(skip_ws=True)
        return info.user_state(wallet_address)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            wallet_address = user_input[CONF_WALLET_ADDRESS].strip().lower()

            # Validate wallet address format
            if not validate_wallet_address(wallet_address):
                errors["base"] = "invalid_wallet_address"
            else:
                # Check if already configured
                await self.async_set_unique_id(wallet_address)
                self._abort_if_unique_id_configured()

                try:
                    # Test API connection - lazy import, run in executor to avoid blocking
                    await self.hass.async_add_executor_job(
                        self._test_api_connection, wallet_address
                    )
                except Exception as err:
                    _LOGGER.error("Failed to connect to Hyperliquid API: %s", err)
                    errors["base"] = "cannot_connect"
                else:
                    # Create short title from wallet address
                    short_address = f"{wallet_address[:6]}...{wallet_address[-4:]}"

                    return self.async_create_entry(
                        title=f"Hyperliquid ({short_address})",
                        data={
                            CONF_WALLET_ADDRESS: wallet_address,
                        },
                        options={
                            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_WALLET_ADDRESS): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry,
    ) -> HyperliquidOptionsFlowHandler:
        """Get the options flow for this handler."""
        return HyperliquidOptionsFlowHandler(config_entry)


class HyperliquidOptionsFlowHandler(OptionsFlow):
    """Handle Hyperliquid options."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                    ),
                }
            ),
        )
