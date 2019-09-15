""""
tradfri_swith:
    id: kitchen_ikea_switch
    middle:
        hold:
            entity_id: light.living_room_floor
            behaviour: dim
                percent: 10
            interval: 0.1
        click:
            entity_id: light.living_room_floor
            behaviour: toggle
            behaviour: on
            behaviour: off

"""

import time
import logging
import asyncio
from contextlib import suppress
from threading import Timer

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'tradfri_switch'
DEPENDENCIES = []
DIM_UPDATE_INTERVAL_MS = 0.1
DIM_UPDATE_AMOUNT_PERCENT = 5 

current_milli_time = lambda: int(round(time.time() * 1000))

# button_binding_example = {
#             'hold' : brightness up / brigtness down
#             'hold_alternate': brightness up / brigtness down
#             'click' : toggle, set_scene
#             'double-click': toogle, set_scene
# }

service_call = {
    'service': 'light.turn_on',
    'data': {
        'entity_id': 'light.living_room_floor',
        'brightness_pct': '+10'
    }
}

service_call_data = {
    'change_brigthness': {
        'alternate': False, #TODO
        'percent': 10
    }
}


def dim_service_call(hass, entity_id, data):
    # TODO: Validate data
    brightness = hass.states.get("%s.attributes.brightness_pct" % entity_id)
    percent = data['percent']
    
    # Check if there is brighness change possible
    if percent > 0 and brightness == 100: return
    if percent < 0 and brightness == 0: return
    
    service_data = {
        'entity_id': entity_id,
        'brightness_pct': brightness + percent
    }
    hass.services.call('light', 'turn_on', service_data)
    print("brighness %s" % brightness + percent)

def toggle_service_call(hass, entity_id, data):
    state = hass.states.get("%s.state" % entity_id)
    if state == 'on':
        turn_on_light(hass, entity_id)
    else:
        turn_off_light(hass, entity_id)


def turn_on_light(hass, entity_id):
    service_data = {
        'entity_id': entity_id
    }
    hass.services.call('light', 'turn_on', service_call_data)
    print("turn on")

def turn_off_light(hass, entity_id):
    service_data = {
        'entity_id': entity_id
    }
    hass.services.call('light', 'turn_off', service_call_data)
    print("turn off")

def turn_on_service_call(hass, entity_id, data):
    turn_on_light(hass, entity_id)
    
def turn_off_service_call(hass, entity_id, data):
    turn_off_light(hass, entity_id)

service_call_mapper = {
    'dim': dim_service_call,
    'toggle': toggle_service_call,
    'on': turn_on_service_call,
    'off': turn_off_service_call
}

button_binding = {
    'hold': {'interval': 50, 'call': service_call},
    'hold_alternate': {'interval': 50, 'call': service_call},
    'click': service_call,
    'double-click': service_call
}

def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""

    buttons = {
        1 : Button(hass, 'middle', config),
        2 : Button(hass, 'up', config),
        3 : Button(hass, 'bottom', config),
        4 : Button(hass, 'left', config),
        5 : Button(hass, 'right', config)
    }

    def handle_event(event):
        data = event.data
        print('Got event data: %s' % data)

        # buttons[1].set_brightness(1)

        if data['id'] == 'kitchen_ikea_switch':
            event_code = data['event']
            key_id = event_code // 1000
            button = buttons[key_id]
            # if not button: return # Should never happen
            button.handle_key_event(event_code)

    # Listen for when my_cool_event is fired
    hass.bus.listen('deconz_event', handle_event)
    return True

# TODO: Use async_track_time_interval for hold updates
class Button:
    def __init__(self, hass, name, config):
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

        self.hold_call = self.create_behaviour_call(data['hold'])
        if self.hold_call:
            self.hold_interval = data['hold']['interval']
            if not self.hold_interval:
                self.hold_interval = 0.1 # Default to 100ms
        
        self.click_call = self.create_behaviour_call(data['click'])

        if self.hold_call:
            log_debug('Setup hold')
        if self.click_call:
            log_debug('Setup click')

        # self.light_id = 'light.living_room_floor'
        # self._reverse_brightness = False
        # self.timer = None

    def create_behaviour_call(self, hass, data):
        if not data: return # Not configured
        
        entity_id = data['entity_id']
        if not entity_id:
            self.log_debug('No entity_id set on button')
            return None

        behavior = ['behavior']
        if not behavior:
            self.log_debug('No behavior set on button')
            return None

        behavior_service_call = service_call_mapper[behavior]
        if not behavior_service_call:
            self.log_debug('Invalid behavior %s specified' % behavior)
            return None

        return lambda x: behavior_service_call(hass, entity_id, data)

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
        self.log_debug('hold')
        # self.brightness = 0
        if not self.hold_call: return # Nothing to do

        if self.hold_stop(): return
        # self.timer = Timer(DIM_UPDATE_INTERVAL_MS, self.dim_update, args=[], kwargs={})

        # self.timer = Timer(self.hold_interval, self.hold_call, args=[], kwargs={})
        # self.timer.start()
        self.hold_update()

    def handle_button_short_click(self):
        self.log_debug('short click')
        if self.hold_stop(): return

        # TODO: don't do click directly but wait for a small delay to wait for double click
        if self.click_call != None:
            click_call()

    def handle_button_long_click(self):
        self.log_debug('long click')
        if self.hold_stop(): return

    def hold_update(self):
        self.hold_call()

        self.timer = Timer(hold.interval, self.hold_update, args=[], kwargs={})
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
        # if self._reverse_brightness:
        #     self.set_brightness(max(0, self.brightness - DIM_UPDATE_AMOUNT_PERCENT))
        # else:
        #     self.set_brightness(min(100, self.brightness + DIM_UPDATE_AMOUNT_PERCENT))

        # self.timer = Timer(DIM_UPDATE_INTERVAL_MS, self.dim_update, args=[], kwargs={})
        self.timer = Timer(hold.interval, self.hold_update, args=[], kwargs={})
        self.timer.start()

    def log_debug(self, msg):
        print('Button %s: %s' % (self.name, msg))


# class Button2:

#     def __init__(self, hass, name):
#         self.hass = hass
#         self.name = name
#         self._hold_task = None
#         self._reverse_brightness = False
#         self.light_id = 'light.living_room_floor'

#     async def handle_key_event(self, event_code):
#         self.log_debug('event_code: %d' % event_code)
#         key_event = event_code % 1000
#         if key_event == 1:
#             await self.handle_button_hold()
#         elif key_event == 2:
#             await self.handle_button_short_click()
#         elif key_event == 3:
#             await self.handle_button_long_click()
#         else:
#             _LOGGER.info('Button %s: Unhandled key event %d from event code %d' % name, key_event, event_code)

#     async def handle_button_hold(self):
#         self.log_debug('hold')
#         if await self.hold_stop(): return
        
#         self.hold_start = current_milli_time()
#         self.brightness = 0
#         self._hold_task = self.hass.async_create_task(self._run_hold_task())

#     async def handle_button_short_click(self):
#         self.set_brightness(1)
#         self.log_debug('short click')
#         if await self.hold_stop(): return

#     async def handle_button_long_click(self):
#         self.log_debug('long click')
#         if await self.hold_stop(): return

#     async def hold_stop(self):
#         if self._hold_task == None: return False
#         self.log_debug('hold stop')
#         self._hold_task.cancel()
#         self._hold_task = None
#         return True

#     async def _run_hold_task(self):
#         while True:
#             self.dim_update()
#             await asyncio.sleep(DIM_UPDATE_INTERVAL_MS)
        
#     def dim_update(self):
#         if self._reverse_brightness:
#             self.set_brightness(max(0, self.brightness - DIM_UPDATE_AMOUNT_PERCENT))
#         else:
#             self.set_brightness(min(100, self.brightness + DIM_UPDATE_AMOUNT_PERCENT))
    
#     def set_brightness(self, value):
#         self.log_debug('Brightness %d' % value)

#         self.brightness = value
#         service_data = {
#             'entity_id': self.light_id,
#             'brightness_pct': self.brightness
#         }
#         self.hass.services.async_call('light', 'turn_on', service_data, False)

#     def get_brightness(self):
#         return self.brightness

#     def log_debug(self, msg):
#         print('Button %s: %s' % (self.name, msg))

class RepeatTimer(Timer):

    def run(self):
        while not self.finished.is_set():
            self.finished.wait(self.interval)
            self.function(*self.args, **self.kwargs)

        self.finished.set()