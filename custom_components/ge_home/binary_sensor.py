"""GE Home Sensor Entities"""
import logging
from typing import Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .devices import ApplianceApi
from .entities import GeErdBinarySensor
from .update_coordinator import GeHomeUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable):
    """GE Home binary sensors."""

    _LOGGER.debug('Adding GE Binary Sensor Entities')
    coordinator: GeHomeUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    registry = er.async_get(hass)

    def _is_laundry_diagnostic_entity(entity) -> bool:
        values = []
        for attr_name in ("unique_id", "entity_id", "name"):
            try:
                values.append(getattr(entity, attr_name, None))
            except Exception:
                continue
        api = getattr(entity, "api", None)
        if api is not None:
            for attr_name in ("serial_or_mac", "serial_number", "mac_addr"):
                try:
                    values.append(getattr(api, attr_name, None))
                except Exception:
                    continue
        erd_code = getattr(entity, "erd_code", None)
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

    @callback
    def async_devices_discovered(apis: list[ApplianceApi]):
        _LOGGER.debug(f'Found {len(apis):d} appliance APIs')
        for api in apis:
            api_entities = list(getattr(api, "entities", []))
            api_platform_entities = [entity for entity in api_entities if isinstance(entity, GeErdBinarySensor) and not isinstance(entity, SwitchEntity)]
            api_laundry_entities = [entity for entity in api_entities if _is_laundry_diagnostic_entity(entity)]
            if api_laundry_entities:
                _LOGGER.debug(
                    "GE_HOME_LAUNDRY_STATE_DIAG platform_api_summary platform=binary_sensor.py api_class=%s total_entities=%s platform_entities=%s laundry_entities=%s",
                    type(api).__name__,
                    len(api_entities),
                    len(api_platform_entities),
                    len(api_laundry_entities),
                )

        platform_entities = [
            entity
            for api in apis
            for entity in api.entities
            if isinstance(entity, GeErdBinarySensor) and not isinstance(entity, SwitchEntity)
        ]

        entities = []
        seen_unique_ids = set()
        for entity in platform_entities:
            unique_id = getattr(entity, "unique_id", None)
            entity_id = getattr(entity, "entity_id", None)
            is_registered = registry.async_is_registered(entity_id) if entity_id else False
            if _is_laundry_diagnostic_entity(entity):
                _LOGGER.debug(
                    "GE_HOME_LAUNDRY_STATE_DIAG platform_discovery platform=binary_sensor.py unique_id=%s entity_id=%s class=%s registered_by_entity_id=%s",
                    unique_id,
                    entity_id,
                    type(entity).__name__,
                    is_registered,
                )
            if unique_id is not None and unique_id in seen_unique_ids:
                if _is_laundry_diagnostic_entity(entity):
                    _LOGGER.debug(
                        "GE_HOME_LAUNDRY_STATE_DIAG platform_discovery_duplicate_unique_id platform=binary_sensor.py unique_id=%s entity_id=%s class=%s",
                        unique_id,
                        entity_id,
                        type(entity).__name__,
                    )
                continue
            if unique_id is not None:
                seen_unique_ids.add(unique_id)
            entities.append(entity)

        laundry_count = sum(1 for entity in platform_entities if _is_laundry_diagnostic_entity(entity))
        _LOGGER.info('Found %d GE Home binary sensors (%d laundry diagnostics); adding by unique_id', len(entities), laundry_count)
        async_add_entities(entities)

    #if we're already initialized at this point, call device
    #discovery directly, otherwise add a callback based on the
    #ready signal
    if coordinator.initialized:
        async_devices_discovered(coordinator.appliance_apis.values())
    else:    
        # add the ready signal and register the remove callback
        coordinator.add_signal_remove_callback(
            async_dispatcher_connect(hass, coordinator.signal_ready, async_devices_discovered))
