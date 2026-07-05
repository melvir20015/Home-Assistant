import asyncio
import logging
from typing import Dict, List, Optional, Set

from gehomesdk import GeAppliance
from gehomesdk.erd import ErdCode, ErdCodeType, ErdApplianceType

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_DIAGNOSTIC_MACS = {"AZ312796N"}
_LAUNDRY_DIAGNOSTIC_TYPE_PARTS = ("WASHER", "DRYER", "COMBINATION_WASHER_DRYER", "LAUNDRY")
_DIAGNOSTIC_ERD_NAMES = {
    "LAUNDRY_MACHINE_STATE",
    "LAUNDRY_CYCLE",
    "LAUNDRY_SUB_CYCLE",
    "LAUNDRY_TIME_REMAINING",
    "LAUNDRY_DELAY_TIME_REMAINING",
    "LAUNDRY_DOOR",
    "LAUNDRY_REMOTE_STATUS",
    "LAUNDRY_WASHER_SMART_DISPENSE_TANK_STATUS",
    "LAUNDRY_DRYER_EXTENDED_TUMBLE_OPTION_SELECTION",
}


def _is_laundry_diagnostic_target(api) -> bool:
    try:
        if api.mac_addr in _DIAGNOSTIC_MACS or api.serial_or_mac in _DIAGNOSTIC_MACS:
            return True
    except Exception:
        pass

    try:
        appliance_type_name = getattr(
            api.appliance.appliance_type, "name", str(api.appliance.appliance_type or "")
        ).upper()
        if any(part in appliance_type_name for part in _LAUNDRY_DIAGNOSTIC_TYPE_PARTS):
            return True
    except Exception:
        pass

    try:
        model_number = api.model_number
        serial_number = api.serial_number
    except Exception:
        model_number = serial_number = None
    return any("PFQ97" in str(value).upper() for value in (model_number, serial_number) if value)


def _laundry_erd_sample(values) -> List[str]:
    try:
        return [
            str(value)
            for value in values
            if "LAUNDRY_" in str(value).upper()
        ][:20]
    except Exception:
        return []


class ApplianceApi:
    """
    API class to represent a single physical device.

    Since a physical device can have many entities, we"ll pool common elements here
    """
    APPLIANCE_TYPE = None  # type: Optional[ErdApplianceType]
    REGISTER_WITHOUT_KNOWN_PROPERTIES = set()  # type: Set[ErdCodeType]

    def __init__(self, coordinator: DataUpdateCoordinator, appliance: GeAppliance):
        if not appliance.initialized:
            raise RuntimeError("Appliance not ready")
        self._appliance = appliance
        self._loop = appliance.client.loop
        self._hass = coordinator.hass
        self.coordinator = coordinator
        self.initial_update = False
        self._entities = {}  # type: Optional[Dict[str, Entity]]
        self._last_availability_diagnostic = None

    @property
    def hass(self) -> HomeAssistant:
        return self._hass

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        if self._loop is None:
            self._loop = self._appliance.client.loop
        return self._loop

    @property
    def appliance(self) -> GeAppliance:
        return self._appliance

    @appliance.setter
    def appliance(self, value: GeAppliance):
        self._appliance = value

    @property
    def available(self) -> bool:
        #Note - online will be there since we're using the GE coordinator
        #Didn't want to deal with the circular references to get the type hints
        #working.
        appliance_available = self.appliance.available
        coordinator_online = self.coordinator.online
        available = appliance_available and coordinator_online
        if not available:
            diagnostic_state = (appliance_available, coordinator_online)
            if diagnostic_state != self._last_availability_diagnostic:
                self._last_availability_diagnostic = diagnostic_state
                if _is_laundry_diagnostic_target(self):
                    _LOGGER.warning(
                        "GE_HOME_LAUNDRY_DIAG entity_unavailable mac_addr=%s serial_or_mac=%s appliance_type=%s appliance_available=%s coordinator_online=%s",
                        self.mac_addr,
                        self.serial_or_mac,
                        self.appliance.appliance_type,
                        appliance_available,
                        coordinator_online,
                    )
                else:
                    _LOGGER.debug(
                        "GE Home appliance availability false: mac_addr=%s, serial_or_mac=%s, appliance_type=%s, appliance_available=%s, coordinator_online=%s",
                        self.mac_addr,
                        self.serial_or_mac,
                        self.appliance.appliance_type,
                        appliance_available,
                        coordinator_online,
                    )
        else:
            self._last_availability_diagnostic = (appliance_available, coordinator_online)
        return available

    @property
    def serial_number(self) -> str:
        return self.appliance.get_erd_value(ErdCode.SERIAL_NUMBER)

    @property
    def mac_addr(self) -> str:
        return self.appliance.mac_addr

    @property
    def serial_or_mac(self) -> str:
        def is_zero(val: str) -> bool:
            try:
                intVal = int(val)
                return intVal == 0
            except:
                return False
    
        if (self.serial_number and not 
            self.serial_number.isspace() and not 
            is_zero(self.serial_number)):
            return self.serial_number
        return self.mac_addr

    @property
    def model_number(self) -> str:
        return self.appliance.get_erd_value(ErdCode.MODEL_NUMBER)

    @property
    def sw_version(self) -> str:
        appVer = self.try_get_erd_value(ErdCode.APPLIANCE_SW_VERSION)
        wifiVer = self.try_get_erd_value(ErdCode.WIFI_MODULE_SW_VERSION)

        return 'Appliance=' + str(appVer or 'Unknown') + '/Wifi=' + str(wifiVer or 'Unknown')

    @property
    def name(self) -> str:
        appliance_type = self.appliance.appliance_type
        if appliance_type is None or appliance_type == ErdApplianceType.UNKNOWN:
            appliance_type = "Appliance"
        else:
            appliance_type = appliance_type.name.replace("_", " ").title()
        return f"GE {appliance_type} {self.serial_or_mac}"

    @property
    def device_info(self) -> Dict:
        """Device info dictionary."""

        return {
            "identifiers": {(DOMAIN, self.serial_or_mac)},
            "name": self.name,
            "manufacturer": "GE",
            "model": self.model_number,
            "sw_version": self.sw_version
        }

    @property
    def entities(self) -> List[Entity]:
        return list(self._entities.values())

    def get_all_entities(self) -> List[Entity]:
        """Create Entities for this device."""
        return self.get_base_entities()

    def get_base_entities(self) -> List[Entity]:
        """Create base entities (i.e. common between all appliances)."""
        from ..entities import GeErdSensor, GeErdSwitch
        entities = [
            GeErdSensor(self, ErdCode.CLOCK_TIME),
            GeErdSwitch(self, ErdCode.SABBATH_MODE),
        ]
        return entities        

    def build_entities_list(self) -> None:
        """Build the entities list, adding anything new."""
        from ..entities import GeErdEntity, GeErdButton, GeErdSensor

        known_properties = self.appliance.known_properties
        property_cache = getattr(self.appliance, "_property_cache", {})
        register_without_known_properties = {
            self.appliance.translate_erd_code(erd_code)
            for erd_code in self.REGISTER_WITHOUT_KNOWN_PROPERTIES
        }
        entities = []
        omitted_entities = []

        if _is_laundry_diagnostic_target(self):
            diagnostic_known_properties = sorted(str(prop) for prop in known_properties)
            diagnostic_property_cache = sorted(str(prop) for prop in property_cache)
            _LOGGER.debug(
                "GE Home build entities start: serial_or_mac=%s, mac_addr=%s, api_class=%s, known_properties_count=%s, property_cache_count=%s, relevant_known_properties=%s, relevant_property_cache=%s",
                self.serial_or_mac,
                self.mac_addr,
                type(self).__name__,
                len(known_properties),
                len(property_cache),
                [prop for prop in diagnostic_known_properties if any(name in prop for name in _DIAGNOSTIC_ERD_NAMES)],
                [prop for prop in diagnostic_property_cache if any(name in prop for name in _DIAGNOSTIC_ERD_NAMES)],
            )

        for entity in self.get_all_entities():
            if not isinstance(entity, GeErdEntity) or isinstance(entity, GeErdButton):
                entities.append(entity)
                continue

            if entity.erd_code in known_properties:
                entities.append(entity)
                continue

            if (
                entity.erd_code in register_without_known_properties
                and entity.erd_code in property_cache
            ):
                _LOGGER.debug(
                    "Registering %s for %s because allowed ERD %s exists in the property cache",
                    entity.unique_id,
                    self.serial_or_mac,
                    entity.erd_code,
                )
                entities.append(entity)
                continue

            if (
                entity.erd_code in register_without_known_properties
                or (
                    isinstance(entity, GeErdSensor)
                    and entity.register_without_property_cache
                )
            ):
                _LOGGER.debug(
                    "Registering %s for %s even though ERD %s is absent from known properties",
                    entity.unique_id,
                    self.serial_or_mac,
                    entity.erd_code,
                )
                entities.append(entity)
                continue

            omitted_entities.append((entity.unique_id, str(entity.erd_code)))

        entity_diagnostics = [(entity.unique_id, str(getattr(entity, "erd_code", None))) for entity in entities]
        _LOGGER.debug(
            "GE Home build entities complete: serial_or_mac=%s, mac_addr=%s, api_class=%s, entity_count=%s",
            self.serial_or_mac,
            self.mac_addr,
            type(self).__name__,
            len(entities),
        )

        if _is_laundry_diagnostic_target(self):
            laundry_entity_erds = _laundry_erd_sample(
                getattr(entity, "erd_code", None) for entity in entities
            )
            _LOGGER.warning(
                "GE_HOME_LAUNDRY_DIAG entities_built mac_addr=%s serial_or_mac=%s api_class=%s entity_count=%s laundry_entity_erds=%s",
                self.mac_addr,
                self.serial_or_mac,
                type(self).__name__,
                len(entities),
                laundry_entity_erds or "none",
            )
            _LOGGER.debug(
                "GE Home build entities detail: serial_or_mac=%s, mac_addr=%s, api_class=%s, entities=%s, omitted_entities=%s",
                self.serial_or_mac,
                self.mac_addr,
                type(self).__name__,
                entity_diagnostics,
                omitted_entities,
            )

        for entity in entities:
            if entity.unique_id not in self._entities:
                self._entities[entity.unique_id] = entity

    def try_get_erd_value(self, code: ErdCodeType):
        try:
            return self.appliance.get_erd_value(code)
        except:
            return None
    
    def has_erd_code(self, code: ErdCodeType):
        try:
            self.appliance.get_erd_value(code)
            return True
        except:
            return False
