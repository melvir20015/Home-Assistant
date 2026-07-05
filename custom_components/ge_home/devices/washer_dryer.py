import logging
from typing import List

from homeassistant.helpers.entity import Entity
from gehomesdk import ErdCode, ErdApplianceType

from .washer import WasherApi
from .dryer import DryerApi
from ..entities import GeErdSensor, GeErdBinarySensor

_LOGGER = logging.getLogger(__name__)


def _erd_code(name: str):
    return getattr(ErdCode, name, None)


class WasherDryerApi(WasherApi, DryerApi):
    """API class for washer/dryer objects"""
    APPLIANCE_TYPE = ErdApplianceType.COMBINATION_WASHER_DRYER
    # Washer/dryer combos such as PFQ97 report model-specific laundry ERDs.
    # Do not force-register generic laundry ERDs here; get_all_entities() only
    # creates entities after has_erd_code() confirms the SDK knows or caches them.
    REGISTER_WITHOUT_KNOWN_PROPERTIES = set()

    def _add_if_supported(
        self,
        entities: List[Entity],
        skipped_erds: List[str],
        entity_cls,
        erd_code,
        **kwargs,
    ) -> bool:
        if erd_code is None:
            return False
        if self.has_erd_code(erd_code):
            entities.append(entity_cls(self, erd_code, **kwargs))
            return True
        skipped_erds.append(str(erd_code))
        return False

    def get_all_entities(self) -> List[Entity]:
        base_entities = self.get_base_entities()
        common_entities = []
        skipped_erds = []

        self._add_if_supported(common_entities, skipped_erds, GeErdSensor, ErdCode.LAUNDRY_MACHINE_STATE)
        self._add_if_supported(common_entities, skipped_erds, GeErdSensor, ErdCode.LAUNDRY_CYCLE)
        self._add_if_supported(common_entities, skipped_erds, GeErdSensor, ErdCode.LAUNDRY_SUB_CYCLE)
        self._add_if_supported(common_entities, skipped_erds, GeErdSensor, ErdCode.LAUNDRY_TIME_REMAINING)
        self._add_if_supported(common_entities, skipped_erds, GeErdSensor, ErdCode.LAUNDRY_DELAY_TIME_REMAINING)

        combo_door_status = _erd_code("LAUNDRY_COMBO_DOOR_STATUS")
        if not self._add_if_supported(common_entities, skipped_erds, GeErdBinarySensor, combo_door_status):
            self._add_if_supported(common_entities, skipped_erds, GeErdBinarySensor, ErdCode.LAUNDRY_DOOR)

        self._add_if_supported(common_entities, skipped_erds, GeErdBinarySensor, ErdCode.LAUNDRY_REMOTE_STATUS)
        self._add_if_supported(
            common_entities,
            skipped_erds,
            GeErdSensor,
            _erd_code("LAUNDRY_COMBO_WASHER_TIME_REMAINING"),
        )
        self._add_if_supported(
            common_entities,
            skipped_erds,
            GeErdSensor,
            _erd_code("LAUNDRY_COMBO_DRYER_TIME_REMAINING"),
        )

        washer_entities = self.get_washer_entities()
        dryer_entities = self.get_dryer_entities()

        entities = base_entities + common_entities + washer_entities + dryer_entities
        built_erds = [str(getattr(entity, "erd_code", None)) for entity in common_entities + washer_entities + dryer_entities]
        _LOGGER.warning(
            "GE_HOME_LAUNDRY_DIAG WasherDryerApi supported_entities serial_or_mac=%s mac_addr=%s added_erds=%s omitted_erds=%s",
            self.serial_or_mac,
            self.mac_addr,
            built_erds,
            skipped_erds or "none",
        )
        return entities
