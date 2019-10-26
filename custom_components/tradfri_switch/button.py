from threading import Timer
import logging

from .service_calls import service_call_mapper

_LOGGER = logging.getLogger(__name__)

# TODO: Use async_track_time_interval for hold updates
class Button:
    def __init__(self, hass, name, config, component_state):
        self.hass = hass
        self.name = name
        self.timer = None
        self.hold_call = None
        self.click_call = None

        data = config.get(name)
        if not data:
            # Button not configured
            self.log_debug("Not setup")
            return 

        self.log_debug("Data %s" % data)
        self.hold_call = self.create_behaviour_call(hass, data.get('hold'), component_state)
        if self.hold_call:
            self.hold_interval = data.get('hold').get('interval')
            if not self.hold_interval:
                self.hold_interval = 0.1 # Default to 100ms
        
        self.click_call = self.create_behaviour_call(hass, data.get('click'), component_state)

        if self.hold_call:
            self.log_debug('Setup hold')
        if self.click_call:
            self.log_debug('Setup click')

        # self.light_id = 'light.living_room_floor'
        # self._reverse_brightness = False
        # self.timer = None

    def create_behaviour_call(self, hass, data, component_state):
        if not data: return # Not configured
        
        entity_id = data.get('entity_id')
        # if not entity_id:
        #     self.log_debug('No entity_id set on button')
        #     return None

        behavior = data.get('behavior')
        if not behavior:
            self.log_debug('No behavior set on button')
            return None

        behavior_service_call = service_call_mapper[behavior]
        if not behavior_service_call:
            self.log_debug('Invalid behavior %s specified' % behavior)
            return None
        
        def call():
            resolved_entity_id = entity_id
            if resolved_entity_id == 'all_entities':
                entities = component_state['entities']
                if len(entities) == 0:
                    print('no entities specified, could not perform bevavior')
                    return
                # Perform behavior on all entities
                for e in component_state['entities']:
                    behavior_service_call(hass, e, data.get('behavior_data'), component_state)
                return

            elif resolved_entity_id == 'selected_entity':
                selected_entity_index = component_state['selected_entity_index']
                entities = component_state['entities']
                if selected_entity_index == -1:
                    print('no entity selected, could not perform behavior')
                    return
                elif selected_entity_index == len(entities):
                    # Perform behavior on all entities
                    for e in component_state['entities']:
                        behavior_service_call(hass, e, data.get('behavior_data'), component_state)
                    return
                    
                resolved_entity_id = entities[selected_entity_index]

            behavior_data = data.get('behavior_data')
            if not behavior_data:
                behavior_data = {}
            behavior_service_call(hass, resolved_entity_id, behavior_data, component_state)

        return call

    def handle_key_event(self, event_code):
        self.log_debug('event_code: %d' % event_code)
        key_event = event_code % 1000
        if key_event == 1:
            self.handle_button_hold()
        elif key_event == 2:
            self.handle_button_short_click()
        elif key_event == 3:
            self.handle_button_long_click()
        else:
            _LOGGER.info('Button %s: Unhandled key event %d from event code %d' % name, key_event, event_code)

    def handle_button_hold(self):
        self.log_debug('hold 1')
        # self.brightness = 0
        if not self.hold_call: return # Nothing to do
        self.log_debug('hold 2')

        if self.hold_stop(): return
        self.log_debug('hold 3')

        # self.timer = Timer(DIM_UPDATE_INTERVAL_MS, self.dim_update, args=[], kwargs={})

        # self.timer = Timer(self.hold_interval, self.hold_call, args=[], kwargs={})
        # self.timer.start()
        self.hold_update()

    def handle_button_short_click(self):
        self.log_debug('short click')
        if self.hold_stop(): return

        # TODO: don't do click directly but wait for a small delay to wait for double click
        if self.click_call != None:
            self.click_call()

    def handle_button_long_click(self):
        self.log_debug('long click')
        if self.hold_stop(): return

    def hold_update(self):
        self.hold_call()

        self.timer = Timer(self.hold_interval, self.hold_update, args=[], kwargs={})
        self.timer.start()

    # def set_brightness(self, value):
    #     self.log_debug('Brightness %d' % value)

    #     self.brightness = value
    #     service_data = {
    #         'entity_id': self.light_id,
    #         'brightness_pct': self.brightness
    #     }
    #     self.log_debug('before call %s' % service_data)

    #     self.hass.services.call('light', 'turn_on', service_data, False)
    #     self.log_debug('after call')

    # def get_brightness(self):
    #     return self.brightness

    def hold_stop(self):
        if self.timer == None: return False
        self.log_debug('hold stop')

        if self.timer.isAlive:
            self.timer.cancel()
        
        self.timer = None
        return True

    def dim_update(self):
        self.timer = Timer(hold.interval, self.hold_update, args=[], kwargs={})
        self.timer.start()

    def log_debug(self, msg):
        print('Button %s: %s' % (self.name, msg))