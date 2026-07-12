import logging
from typing import List

from homeassistant.helpers.entity import Entity
from gehomesdk.erd import ErdCode, ErdApplianceType

from .base import ApplianceApi
from ..entities import GeWacClimate, GeErdSensor, GeErdBinarySensor, GeErdSwitch, ErdOnOffBoolConverter

_LOGGER = logging.getLogger(__name__)


def _get_optional_erd(*erd_names: str):
    for erd_name in erd_names:
        erd = getattr(ErdCode, erd_name, None)
        if erd is not None:
            return erd

    _LOGGER.debug(
        "ERD WAC demand response no disponible en gehomesdk; "
        "omitiendo sensor opcional y continuando con el A/C. ERD buscados: %s",
        ", ".join(erd_names),
    )
    return None


class WacApi(ApplianceApi):
    """API class for Window AC objects"""
    APPLIANCE_TYPE = ErdApplianceType.AIR_CONDITIONER

    def get_all_entities(self) -> List[Entity]:
        base_entities = super().get_all_entities()

        wac_entities = [
            GeWacClimate(self),
            GeErdSensor(self, ErdCode.AC_TARGET_TEMPERATURE),
            GeErdSensor(self, ErdCode.AC_AMBIENT_TEMPERATURE),
            GeErdSensor(self, ErdCode.AC_FAN_SETTING, icon_override="mdi:fan"),
            GeErdSensor(self, ErdCode.AC_OPERATION_MODE),
            GeErdSwitch(self, ErdCode.AC_POWER_STATUS, bool_converter=ErdOnOffBoolConverter(), icon_on_override="mdi:power-on", icon_off_override="mdi:power-off"),
            GeErdBinarySensor(self, ErdCode.AC_FILTER_STATUS, device_class_override="problem"),
        ]

        demand_response_sensors = [
            (("WAC_DEMAND_RESPONSE_STATE", "RESOURCE_DEMAND_RESPONSE_STATE"), {}),
            (("WAC_DEMAND_RESPONSE_POWER",), {"uom_override": "kW", "register_without_property_cache": True}),
            (
                ("RESOURCE_DSM_POWER_USAGE", "DSM_POWER_USAGE", "WAC_POWER_USAGE"),
                {
                    "erd_override": "WAC_DEMAND_RESPONSE_POWER",
                    "uom_override": "kW",
                    "value_attr": "instantaneous_power_w",
                    "value_scale": 0.001,
                    "register_without_property_cache": True,
                },
            ),
        ]

        for erd_names, sensor_kwargs in demand_response_sensors:
            demand_response_erd = _get_optional_erd(*erd_names)
            if demand_response_erd is not None:
                _LOGGER.info(
                    "Adding optional WAC demand response sensor for %s using ERD %s",
                    self.appliance.mac_addr,
                    getattr(demand_response_erd, "name", demand_response_erd),
                )
                wac_entities.append(GeErdSensor(self, demand_response_erd, **sensor_kwargs))

        entities = base_entities + wac_entities
        return entities
