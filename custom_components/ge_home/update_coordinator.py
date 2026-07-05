"""Data update coordinator for GE Home Appliances"""

import asyncio
import async_timeout
import logging
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, List

logging.getLogger('slixmpp.stringprep').setLevel(logging.ERROR)

from gehomesdk import (
    EVENT_APPLIANCE_INITIAL_UPDATE,
    EVENT_APPLIANCE_UPDATE_RECEIVED,
    EVENT_CONNECTED,
    EVENT_DISCONNECTED,
    EVENT_GOT_APPLIANCE_LIST,
    ErdCodeType,
    GeAppliance,
    GeWebsocketClient,
)
from gehomesdk import GeAuthFailedError, GeGeneralServerError, GeNotAuthenticatedError
from .exceptions import HaAuthError, HaCannotConnect

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_REGION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.ssl import get_default_context 
from .const import (
    DOMAIN,
    EVENT_ALL_APPLIANCES_READY,
    UPDATE_INTERVAL,
    MIN_RETRY_DELAY,
    MAX_RETRY_DELAY,
    RETRY_OFFLINE_COUNT,
    ASYNC_TIMEOUT,
    INITIAL_READY_TIMEOUT,
)
from .devices import ApplianceApi, get_appliance_api_type

PLATFORMS = [
    "binary_sensor", 
    "sensor", 
    "switch", 
    "water_heater", 
    "select", 
    "climate", 
    "light", 
    "button", 
    "number",
    "humidifier"
]
_LOGGER = logging.getLogger(__name__)
_DIAGNOSTIC_MACS = {"AZ312796N"}


class GeHomeUpdateCoordinator(DataUpdateCoordinator):
    """Define a wrapper class to update GE Home data."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Set up the GeHomeUpdateCoordinator class."""
        super().__init__(hass, _LOGGER, name=DOMAIN)

        self._config_entry = config_entry
        self._username = config_entry.data[CONF_USERNAME]
        self._password = config_entry.data[CONF_PASSWORD]
        self._region = config_entry.data[CONF_REGION]
        self._appliance_apis = {}  # type: Dict[str, ApplianceApi]
        self._signal_remove_callbacks = [] # type: List[Callable]
        self._retry_count = 0
        self._initial_ready_handle = None
        self._laundry_unavailable_warnings = set()

        self._reset_initialization()

    def _reset_initialization(self):
        self.client = None  # type: Optional[GeWebsocketClient]

        # Mark all appliances as not initialized yet
        for a in self.appliance_apis.values():
            a.appliance.initialized = False

        # Some record keeping to let us know when we can start generating entities
        if self._initial_ready_handle:
            self._initial_ready_handle.cancel()
            self._initial_ready_handle = None
        self._got_roster = False
        self._init_done = False

    def create_ge_client(
        self, event_loop: Optional[asyncio.AbstractEventLoop]
    ) -> GeWebsocketClient:
        """
        Create a new GeClient object with some helpful callbacks.

        :param event_loop: Event loop
        :return: GeWebsocketClient
        """
        client = GeWebsocketClient(
            self._username,
            self._password,
            self._region,
            event_loop=event_loop,
            ssl_context=get_default_context()
        )
        client.add_event_handler(EVENT_APPLIANCE_INITIAL_UPDATE, self.on_device_initial_update)
        client.add_event_handler(EVENT_APPLIANCE_UPDATE_RECEIVED, self.on_device_update)
        client.add_event_handler(EVENT_GOT_APPLIANCE_LIST, self.on_appliance_list)
        client.add_event_handler(EVENT_DISCONNECTED, self.on_disconnect)
        client.add_event_handler(EVENT_CONNECTED, self.on_connect)
        return client

    @property
    def appliances(self) -> Iterable[GeAppliance]:
        return (
                    appliance for appliance in self.client.appliances.values() 
                    if self._is_appliance_valid(appliance)
        )

    @property
    def appliance_apis(self) -> Dict[str, ApplianceApi]:
        return self._appliance_apis

    @property
    def signal_ready(self) -> str:
        """Event specific per entry to signal readiness"""
        return f"{DOMAIN}-ready-{self._config_entry.entry_id}"

    @property
    def initialized(self) -> bool:
        return self._init_done 

    @property
    def online(self) -> bool:
        """
        Indicates whether the services is online. If it's retried several times, it's assumed
        that it's offline for some reason
        """
        return self.connected or self._retry_count <= RETRY_OFFLINE_COUNT

    @property
    def connected(self) -> bool:
        """
        Indicates whether the coordinator is connected
        """
        return self.client and self.client.connected

    def _get_appliance_api(self, appliance: GeAppliance) -> ApplianceApi:
        self._dump_appliance(appliance)
        api_type = get_appliance_api_type(appliance.appliance_type)
        _LOGGER.debug(
            "GE Home appliance api selection: mac_addr=%s, appliance_type=%s, available=%s, initialized=%s, api_class=%s",
            appliance.mac_addr,
            appliance.appliance_type,
            appliance.available,
            appliance.initialized,
            api_type.__name__,
        )
        return api_type(self, appliance)

    def regenerate_appliance_apis(self):
        """Regenerate the appliance_apis dictionary, adding elements as necessary."""
        if not self.client:
            return

        for appliance in self.client.appliances.values():
            self._maybe_add_appliance_api(appliance)

    def _maybe_add_appliance_api(self, appliance: GeAppliance) -> bool:
        """Add an appliance API when the appliance is valid and initialized."""
        mac_addr = appliance.mac_addr

        if not self._is_appliance_valid(appliance):
            _LOGGER.debug(
                "Skipping appliance api for invalid appliance %s: available=%s, initialized=%s, appliance_type=%s, coordinator_online=%s",
                mac_addr,
                appliance.available,
                appliance.initialized,
                appliance.appliance_type,
                self.online,
            )
            return False

        if not appliance.initialized:
            _LOGGER.debug(
                "Skipping appliance api for appliance %s (%s): appliance is in roster but not initialized; available=%s, coordinator_online=%s",
                mac_addr,
                appliance.appliance_type,
                appliance.available,
                self.online,
            )
            return False

        if mac_addr not in self.appliance_apis:
            _LOGGER.info(
                "Adding appliance api for appliance %s (%s): appliance initialized",
                mac_addr,
                appliance.appliance_type,
            )
            api = self._get_appliance_api(appliance)
            api.build_entities_list()
            self.appliance_apis[mac_addr] = api
        else:
            # if we already have the API, switch out its appliance reference for this one
            api = self.appliance_apis[mac_addr]
            _LOGGER.debug(
                "GE Home appliance api already exists: mac_addr=%s, appliance_type=%s, available=%s, initialized=%s, api_class=%s, incoming_appliance_id=%s, current_api_appliance_id=%s",
                mac_addr,
                appliance.appliance_type,
                appliance.available,
                appliance.initialized,
                type(api).__name__,
                id(appliance),
                id(api.appliance),
            )
            api.appliance = appliance
            _LOGGER.debug(
                "GE Home replaced appliance reference for existing api: mac_addr=%s, api_class=%s, new_appliance_id=%s",
                appliance.mac_addr,
                type(api).__name__,
                id(appliance),
            )
        return True

    def add_signal_remove_callback(self, cb: Callable):
        self._signal_remove_callbacks.append(cb)

    async def get_client(self) -> GeWebsocketClient:
        """Get a new GE Websocket client."""
        if self.client:
            try:
                self.client.clear_event_handlers()
                await self.client.disconnect()
            except Exception as err:
                _LOGGER.warning(f"exception while disconnecting client {err}")
            finally:
                self._reset_initialization()

        self.client = self.create_ge_client(event_loop=self.hass.loop)
        return self.client

    async def async_setup(self):
        """Setup a new coordinator"""
        _LOGGER.debug("Setting up coordinator")

        await self.hass.config_entries.async_forward_entry_setups(
            self._config_entry, PLATFORMS
        )

        try:
            await self.async_start_client()
        except (GeNotAuthenticatedError, GeAuthFailedError):
            raise HaAuthError("Authentication failure")
        except GeGeneralServerError:
            raise HaCannotConnect("Cannot connect (server error)")
        except Exception:
            raise HaCannotConnect("Unknown connection failure")

        return True

    async def async_start_client(self):
        """Start a new GeClient in the HASS event loop."""
        try:
            _LOGGER.debug("Creating and starting client")
            await self.get_client()
            await self.async_begin_session()
        except:
            _LOGGER.debug("could not start the client")
            self.client = None
            raise

    async def async_begin_session(self):
        """Begins the ge_home session."""
        _LOGGER.debug("Beginning session")
        session = async_get_clientsession(self.hass)
        await self.client.async_get_credentials(session)
        fut = asyncio.ensure_future(self.client.async_run_client(), loop=self.hass.loop)
        _LOGGER.debug("Client running")
        return fut

    async def async_reset(self):
        """Resets the coordinator."""
        _LOGGER.debug("resetting the coordinator")
        entry = self._config_entry
        
        # remove all the callbacks for this coordinator
        for c in self._signal_remove_callbacks:
            c()
        self._signal_remove_callbacks.clear()

        if self._initial_ready_handle:
            self._initial_ready_handle.cancel()
            self._initial_ready_handle = None

        unload_ok = await self.hass.config_entries.async_unload_platforms(
            self._config_entry, PLATFORMS
        )
        return unload_ok

    async def _kill_client(self):
        """Kill the client.  Leaving this in for testing purposes."""
        await asyncio.sleep(30)
        _LOGGER.critical("Killing the connection.  Popcorn time.")
        await self.client.disconnect()

    @callback
    def reconnect(self, log=False) -> None:
        """Prepare to reconnect ge_home session."""
        if log:
            _LOGGER.info("Will try to reconnect to ge_home service")
        self.hass.loop.create_task(self.async_reconnect())

    async def async_reconnect(self) -> None:
        """Try to reconnect ge_home session."""
        self._retry_count += 1
        _LOGGER.info(
            f"attempting to reconnect to ge_home service (attempt {self._retry_count})"
        )

        try:
            with async_timeout.timeout(ASYNC_TIMEOUT):
                await self.async_start_client()
        except Exception as err:
            _LOGGER.warning(f"could not reconnect: {err}, will retry in {self._get_retry_delay()} seconds")
            self.hass.loop.call_later(self._get_retry_delay(), self.reconnect)
            _LOGGER.debug("forcing a state refresh while disconnected")
            try:
                await self._refresh_ha_state()
            except Exception as err:
                _LOGGER.debug(f"error refreshing state: {err}")

    @callback
    def shutdown(self, event) -> None:
        """Close the connection on shutdown.
        Used as an argument to EventBus.async_listen_once.
        """
        _LOGGER.info("ge_home shutting down")
        if self.client:
            self.client.clear_event_handlers()
            self.hass.loop.create_task(self.client.disconnect())

    async def on_device_update(self, data: Tuple[GeAppliance, Dict[ErdCodeType, Any]]):
        """Let HA know there's new state."""
        self.last_update_success = True
        appliance, _ = data

        self._dump_appliance(appliance)
        
        if not self._is_appliance_valid(appliance):
            _LOGGER.debug(f"on_device_update: skipping invalid appliance {appliance.mac_addr}")
            return

        try:
            api = self.appliance_apis[appliance.mac_addr]
            _LOGGER.debug(
                "GE Home device update: mac_addr=%s, appliance_type=%s, available=%s, initialized=%s, existing_api=%s, api_class=%s, incoming_appliance_id=%s, api_appliance_id=%s",
                appliance.mac_addr,
                appliance.appliance_type,
                appliance.available,
                appliance.initialized,
                True,
                type(api).__name__,
                id(appliance),
                id(api.appliance),
            )
            api.appliance = appliance
        except KeyError:
            api_type = get_appliance_api_type(appliance.appliance_type)
            _LOGGER.info(
                "Received update for appliance %s before discovery completed; adding it now",
                appliance.mac_addr,
            )
            _LOGGER.debug(
                "GE Home device update: mac_addr=%s, appliance_type=%s, available=%s, initialized=%s, existing_api=%s, api_class=%s",
                appliance.mac_addr,
                appliance.appliance_type,
                appliance.available,
                appliance.initialized,
                False,
                api_type.__name__,
            )
            self._maybe_add_appliance_api(appliance)
            await self.async_maybe_trigger_all_ready()
            api = self.appliance_apis.get(appliance.mac_addr)
            if api is None:
                return

        if self._is_laundry_appliance(appliance) and not appliance.available and api.entities:
            warning_key = (appliance.mac_addr, appliance.available, appliance.initialized)
            if warning_key not in self._laundry_unavailable_warnings:
                self._laundry_unavailable_warnings.add(warning_key)
                _LOGGER.warning(
                    "GE Home laundry appliance %s (%s) has %s registered entities but SDK reports available=False; entities will remain unavailable until the SDK/coordinator reports availability",
                    appliance.mac_addr,
                    appliance.appliance_type,
                    len(api.entities),
                )

        self._update_entity_state(api.entities)

    async def _refresh_ha_state(self):
        entities = [
            entity for api in self.appliance_apis.values() for entity in api.entities
        ]

        self._update_entity_state(entities)

    def _update_entity_state(self, entities: List[Entity]):
        from .entities import GeEntity
        for entity in entities:
            # if this is a GeEntity, check if it's been added
            #if not, don't try to refresh this entity
            if isinstance(entity, GeEntity):
                gee: GeEntity = entity
                if not gee.added:
                    _LOGGER.debug(f"Entity {entity} ({entity.unique_id}, {entity.entity_id}) not yet added, skipping update...")
                    continue
            if entity.enabled:
                try:
                    _LOGGER.debug(f"Refreshing state for {entity} ({entity.unique_id}, {entity.entity_id}")
                    entity.async_write_ha_state()
                except:
                    _LOGGER.warning(f"Could not refresh state for {entity} ({entity.unique_id}, {entity.entity_id}", exc_info=1)

    @property
    def all_appliances_updated(self) -> bool:
        """True if all discovered appliances with a type have had an initial update."""
        appliances = list(self.appliances)
        pending = [
            a.mac_addr for a in appliances
            if not a.initialized and a.mac_addr not in self.appliance_apis
        ]
        if pending:
            _LOGGER.debug(
                "GE Home waiting for initial appliance updates: pending=%s, discovered_apis=%s",
                pending,
                list(self.appliance_apis),
            )
        return bool(appliances) and not pending

    async def on_appliance_list(self, _):
        """When we get an appliance list, mark it and maybe trigger all ready."""
        _LOGGER.debug("Got roster update")
        self.last_update_success = True
        if not self._got_roster:
            self._got_roster = True
            roster_count = len(self.client.appliances) if self.client else 0
            _LOGGER.info("GE Home appliance roster received with %s appliance(s)", roster_count)
            if self.client:
                for appliance in self.client.appliances.values():
                    appliance_valid = self._is_appliance_valid(appliance)
                    _LOGGER.debug(
                        "GE Home roster appliance: mac_addr=%s, appliance_type=%s, available=%s, initialized=%s, valid=%s",
                        appliance.mac_addr,
                        appliance.appliance_type,
                        appliance.available,
                        appliance.initialized,
                        appliance_valid,
                    )
                    if appliance_valid:
                        _LOGGER.debug(
                            "GE Home appliance %s (%s) is in roster but not initialized; waiting for initial update",
                            appliance.mac_addr,
                            appliance.appliance_type,
                        )
                    else:
                        _LOGGER.debug(
                            "GE Home appliance %s is invalid from roster: available=%s, initialized=%s, appliance_type=%s",
                            appliance.mac_addr,
                            appliance.available,
                            appliance.initialized,
                            appliance.appliance_type,
                        )
            self._schedule_initial_ready_check()
            await self.async_maybe_trigger_all_ready()

    async def on_device_initial_update(self, appliance: GeAppliance):
        self._dump_appliance(appliance)
        property_cache = getattr(appliance, "_property_cache", {})
        _LOGGER.debug(
            "GE Home initial update details: mac_addr=%s, appliance_type=%s, available=%s, initialized=%s, known_properties_count=%s, property_cache_count=%s",
            appliance.mac_addr,
            appliance.appliance_type,
            appliance.available,
            appliance.initialized,
            len(appliance.known_properties),
            len(property_cache),
        )

        if not self._is_appliance_valid(appliance):
            _LOGGER.debug(f"on_device_initial_update: skipping invalid appliance {appliance.mac_addr}")
            return

        """When an appliance first becomes ready, let the system know and schedule periodic updates."""
        _LOGGER.info("GE Home initial update received for appliance %s", appliance.mac_addr)
        self.last_update_success = True
        self._maybe_add_appliance_api(appliance)
        await self.async_maybe_trigger_all_ready()
        _LOGGER.debug(f"Requesting updates for {appliance.mac_addr}")
        while self.connected:
            await asyncio.sleep(UPDATE_INTERVAL)
            if self.connected and self.client.available:
                await appliance.async_request_update()

        _LOGGER.debug(f"No longer requesting updates for {appliance.mac_addr}")

    async def on_disconnect(self, _):
        """Handle disconnection."""
        _LOGGER.debug(f"Disconnected. Attempting to reconnect in {MIN_RETRY_DELAY} seconds")
        self.last_update_success = False
        self.hass.loop.call_later(MIN_RETRY_DELAY, self.reconnect, True)

    async def on_connect(self, _):
        """Set state upon connection."""
        self.last_update_success = True
        self._retry_count = 0

    async def async_maybe_trigger_all_ready(self):
        """See if we're all ready to go, and if so, let the games begin."""
        if self._init_done:
            # Been here, done this
            return
        if self._got_roster and self.all_appliances_updated:
            _LOGGER.info(
                "GE Home initialization complete; publishing %s appliance API(s)",
                len(self.appliance_apis),
            )
            self._init_done = True
            if self._initial_ready_handle:
                self._initial_ready_handle.cancel()
                self._initial_ready_handle = None
            await self.client.async_event(EVENT_ALL_APPLIANCES_READY, None)
            async_dispatcher_send(
                self.hass,
                self.signal_ready,
                list(self.appliance_apis.values()))

    def _schedule_initial_ready_check(self) -> None:
        """Schedule a guarded check for slow SmartHQ initial updates."""
        if self._init_done or self._initial_ready_handle:
            return
        self._initial_ready_handle = self.hass.loop.call_later(
            INITIAL_READY_TIMEOUT, self._check_initial_ready_timeout
        )

    @callback
    def _check_initial_ready_timeout(self) -> None:
        """Recover from a partial startup where roster arrived but initial data did not."""
        self._initial_ready_handle = None
        if self._init_done:
            return

        appliances = list(self.appliances)
        pending = [a.mac_addr for a in appliances if not a.initialized]
        _LOGGER.warning(
            "GE Home initial data still pending after %s seconds; pending=%s, discovered_apis=%s. Reconnecting with backoff.",
            INITIAL_READY_TIMEOUT,
            pending or "none",
            len(self.appliance_apis),
        )
        self.regenerate_appliance_apis()
        self.reconnect(log=True)

    def _get_retry_delay(self) -> int:
        delay = MIN_RETRY_DELAY * 2 ** (self._retry_count - 1)
        return min(delay, MAX_RETRY_DELAY)

    def _is_appliance_valid(self, appliance: GeAppliance) -> bool:
        """Return True when an appliance is discoverable by type.

        Availability is intentionally not part of discovery validity. The entity
        availability path still uses ApplianceApi.available, which combines the
        SDK appliance availability with coordinator connectivity.
        """
        return bool(appliance.appliance_type)

    def _is_laundry_appliance(self, appliance: GeAppliance) -> bool:
        appliance_type = getattr(appliance, "appliance_type", None)
        appliance_type_name = getattr(appliance_type, "name", str(appliance_type))
        return any(part in appliance_type_name.upper() for part in ("WASHER", "DRYER", "LAUNDRY"))

    def _dump_appliance(self, appliance: GeAppliance) -> None:
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return

        import pprint
        try:
            _LOGGER.debug(f"--- COMPREHENSIVE DUMP FOR APPLIANCE: {appliance.mac_addr} ---")
            appliance_data = {}            
            # dir() gets all attrs, including properties and methods
            for attr_name in dir(appliance):
                # skip "magic" methods and "private" attributes to reduce noise
                if attr_name.startswith('_'):
                    continue                
                try:
                    value = getattr(appliance, attr_name)
                    # for now skip methods - we only want data
                    if callable(value):
                        continue
                    appliance_data[attr_name] = value
                except Exception:
                    # some props might fail if called out of context
                    appliance_data[attr_name] = "Error: Could not read attribute"
            _LOGGER.debug(pprint.pformat(appliance_data))
            _LOGGER.debug("--- END OF COMPREHENSIVE DUMP ---")
        except Exception as e:
            _LOGGER.error(f"Could not dump appliance {appliance}: {e}")
