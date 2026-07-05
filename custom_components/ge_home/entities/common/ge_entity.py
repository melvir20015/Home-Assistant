from datetime import timedelta
import logging
from typing import Optional, Dict, Any

from gehomesdk import GeAppliance
from ...devices import ApplianceApi

_LOGGER = logging.getLogger(__name__)

class GeEntity:
    """Base class for all GE Entities"""
    should_poll = False

    def __init__(self, api: ApplianceApi):
        self._api = api
        self._added = False

    @property
    def unique_id(self) -> str:
        raise NotImplementedError

    @property
    def api(self) -> ApplianceApi:
        return self._api

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self.api.device_info

    @property
    def serial_number(self):
        return self.api.serial_number

    @property
    def available(self) -> bool:
        return self.api.available

    @property
    def appliance(self) -> GeAppliance:
        return self.api.appliance

    @property
    def mac_addr(self) -> str:
        return self.api.mac_addr

    @property
    def serial_or_mac(self) -> str:
        return self.api.serial_or_mac

    @property
    def name(self) -> Optional[str]:
        raise NotImplementedError

    @property
    def icon(self) -> Optional[str]:
        return self._get_icon()

    @property
    def device_class(self) -> Optional[str]:
        return self._get_device_class()    

    @property
    def added(self) -> bool:
        return self._added

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._added = True
        if self._is_laundry_diagnostic_target():
            _LOGGER.warning(
                "GE_HOME_LAUNDRY_STATE_DIAG added_to_hass unique_id=%s entity_id=%s class=%s",
                getattr(self, "unique_id", None),
                getattr(self, "entity_id", None),
                type(self).__name__,
            )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        self._added = False

    def _stringify(self, value: any, **kwargs) -> Optional[str]:
        if isinstance(value, timedelta):
            return str(value)[:-3] if value else ""
        if value is None:
            return None
        return self.appliance.stringify_erd_value(value, **kwargs)

    def _boolify(self, value: any) -> Optional[bool]:
        return self.appliance.boolify_erd_value(value)

    def _is_laundry_diagnostic_target(self) -> bool:
        """Return True for laundry entities involved in the temporary diagnostics."""
        values = []
        for attr_name in ("unique_id", "entity_id", "name", "serial_or_mac", "serial_number", "mac_addr"):
            try:
                values.append(getattr(self, attr_name, None))
            except Exception:
                continue
        erd_code = getattr(self, "erd_code", None)
        values.append(getattr(erd_code, "name", erd_code))

        normalized_values = [str(value).upper() for value in values if value]
        return any(
            "AZ312796N" in value
            or "02000047439D" in value
            or "LAUNDRY" in value
            or "WASHER" in value
            or "DRYER" in value
            for value in normalized_values
        )

    def _get_icon(self) -> Optional[str]:
        return None

    def _get_device_class(self) -> Optional[str]:
        return None
