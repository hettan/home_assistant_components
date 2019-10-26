""""
tradfri_swith:
    id: kitchen_ikea_switch
    entities:
        - light.living_room_floor
        - light.living_room_floor_cabinet
        - light.living_room_wall_cabinet
    up_button:
        hold:
            entity_id: light.living_room_floor
            interval: 0.1
            behavior:
                dim:
                    percent: 10
        click:
            entity_id: selected_entity
            
            behavior: toggle
            behavior: on
            behavior: off
            
            behavior: select_entity_left
            behavior_data:
                notify_entity_id: media_player.living_room_speaker

            behavior: select_entity_right

"""

"""
TODO 
1. Seems like power button procudes a short click first then after ˜1s sends a hold which is
different from the rest... 
2. Temporary volume queuing logic
3. Cleanup split to files
4. Tweak configuration. Current stucture requires too much config. Could have some preset maybe?

Summary: It is ready to be uploaded to the real system

-----------

import voluptuous as vol

import homeassistant.helpers.config_validation as cv

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
      vol.Required(CONF_TEXT): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)
"""

import time
import logging
import asyncio
import json
from contextlib import suppress

from .button import Button
from .constants import *

_LOGGER = logging.getLogger(__name__)


# button_binding_example = {
#             'hold' : brightness up / brigtness down / alternate_brightness
#             'click' : toggle, set_scene
#             'double-click': toogle, set_scene
# }

# button_binding = {
#     'hold': {'interval': 50, 'call': service_call},
#     'hold_alternate': {'interval': 50, 'call': service_call},
#     'click': service_call,
#     'double-click': service_call
# }

def create_component_state(component_config):
    component_state = {}
    entities = component_config.get('entities')
    if not entities:
        entities = []
    component_state['entities'] = entities
    component_state['selected_entity_index'] = len(entities) - 1
    return component_state

def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""

    component_config = config.get('tradfri_switch.deconz')
    if (not component_config):
        print('Tradfri switch deconz component not configured. Please configure it if you want it to work.')

    print('config\n %s' % json.dumps(component_config, indent=4))
    component_state = create_component_state(component_config)
    print('component_state\n %s' % json.dumps(component_state, indent=4))
    buttons = {
        1 : Button(hass, 'middle_button', component_config, component_state),
        2 : Button(hass, 'up_button', component_config, component_state),
        3 : Button(hass, 'down_button', component_config, component_state),
        4 : Button(hass, 'left_button', component_config, component_state),
        5 : Button(hass, 'right_button', component_config, component_state)
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