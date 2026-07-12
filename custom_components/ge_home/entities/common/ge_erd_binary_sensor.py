import logging
from typing import Optional

from homeassistant.components.binary_sensor import BinarySensorEntity

from gehomesdk import ErdCode, ErdCodeType, ErdCodeClass
from ...devices import ApplianceApi
from .ge_erd_entity import GeErdEntity

_LOGGER = logging.getLogger(__name__)


class GeErdBinarySensor(GeErdEntity, BinarySensorEntity):
    def __init__(self, api: ApplianceApi, erd_code: ErdCodeType, erd_override: str = None, icon_on_override: str = None, icon_off_override: str = None, device_class_override: str = None):
        super().__init__(api, erd_code, erd_override=erd_override, icon_override=icon_on_override, device_class_override=device_class_override)
        self._icon_on_override = icon_on_override
        self._icon_off_override = icon_off_override

    """GE Entity for binary sensors"""
    @property
    def is_on(self) -> Optional[bool]:
        """Return True if entity is on."""
        raw_value = None
        try:
            raw_value = self.appliance.get_erd_value(self.erd_code)
            result = self._laundry_combo_door_bytes_to_bool(raw_value)
            if self._is_laundry_diagnostic_target():
                _LOGGER.debug(
                    "GE_HOME_LAUNDRY_STATE_DIAG is_on unique_id=%s entity_id=%s erd_code=%s raw_value=%s final_value=%s",
                    getattr(self, "unique_id", None),
                    getattr(self, "entity_id", None),
                    getattr(self.erd_code, "name", self.erd_code),
                    raw_value,
                    result,
                )
            return result
        except KeyError:
            if self._is_laundry_diagnostic_target():
                _LOGGER.debug(
                    "GE_HOME_LAUNDRY_STATE_DIAG is_on_missing unique_id=%s entity_id=%s erd_code=%s raw_value=%s final_value=None",
                    getattr(self, "unique_id", None),
                    getattr(self, "entity_id", None),
                    getattr(self.erd_code, "name", self.erd_code),
                    raw_value,
                )
            return None

    def _laundry_combo_door_bytes_to_bool(self, raw_value) -> Optional[bool]:
        """Return door state for combo laundry byte payloads, or boolify fallback."""
        combo_door_status = getattr(ErdCode, "LAUNDRY_COMBO_DOOR_STATUS", None)
        if (
            combo_door_status is not None
            and self.erd_code == combo_door_status
            and isinstance(raw_value, (bytes, bytearray))
        ):
            return any(raw_value)
        return self._boolify(raw_value)

    def _get_icon(self):
        is_on = self.is_on
        if self._icon_on_override and is_on is True:
            return self._icon_on_override
        if self._icon_off_override and is_on is False:
            return self._icon_off_override

        if self._erd_code_class == ErdCodeClass.DOOR or self.device_class == "door":
            if is_on is None:
                return super()._get_icon()
            return "mdi:door-open" if is_on else "mdi:door-closed"

        return super()._get_icon()

    def _get_device_class(self) -> Optional[str]:
        if self._device_class_override:
            return self._device_class_override
        if self._erd_code_class == ErdCodeClass.DOOR:
            return "door"
        return None
