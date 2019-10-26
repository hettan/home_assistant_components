import time
import logging

from .constants import *

_LOGGER = logging.getLogger(__name__)

_DEFAULT_NOTIFY_VOLUME_LEVEL = '0.3'

def _dim_service_call(hass, entity_id, data, component_state):
    # TODO: Validate data
    brightness_str = hass.states.get(entity_id).attributes.get('brightness')
    brightness = 0
    if brightness_str:
        brightness = int(brightness_str)

    percent_str = data['percent']
    percent = 10
    if percent_str:
        percent = int(percent_str)
    
    # Check if there is brighness change possible
    if percent > 0 and brightness == 255: return
    if percent < 0 and brightness == 0: return
    
    delta_brightness = percent / 100 * 255
    new_brightness = max(0, min(brightness + delta_brightness, 255))

    if new_brightness == 0:
        service_data = {
            'entity_id': entity_id
        }
        hass.services.call('light', 'turn_off', service_data)
        print("turn off light %s" % entity_id)
        return

    service_data = {
        'entity_id': entity_id,
        'brightness': new_brightness
    }
    hass.services.call('light', 'turn_on', service_data)
    print("brightness %s" % new_brightness)

def _toggle_service_call(hass, entity_id, data, component_state):
    state = hass.states.get("%s" % (entity_id))
    print('Entity %s has state %s' % (entity_id, state.state))
    if state.state == 'off':
        _turn_on_light(hass, entity_id)
    else:
        _turn_off_light(hass, entity_id)

def _turn_on_light(hass, entity_id):
    service_data = {
        'entity_id': entity_id
    }
    print('turn on %s' % (entity_id))
    hass.services.call('light', 'turn_on', service_data)

def _turn_off_light(hass, entity_id):
    service_data = {
        'entity_id': entity_id
    }
    print('turn off %s' % (entity_id))
    hass.services.call('light', 'turn_off', service_data)

def _turn_on_service_call(hass, entity_id, data, component_state):
    _turn_on_light(hass, entity_id)
    
def _turn_off_service_call(hass, entity_id, data, component_state):
    _turn_off_light(hass, entity_id)

# TODO: Do some smart queing logic to make selection call better. Currently we can still get
# inconistentcy how the temporary volume is set.
def _select_entity(hass, entity_id, data, component_state, reverse):
    entities = component_state['entities']
    if len(entities) == 0:
        print('Select entity called but no entities to select... No-op.')
        return

    selected_entity_index = component_state['selected_entity_index']
    next_index = 0
    # Allow for index to be == len(entities) where the last index will mean 'all_entities'
    if reverse:
        next_index = (selected_entity_index + 1) % (len(entities) + 1)
    else:
        next_index = (selected_entity_index - 1) % (len(entities) + 1)
    component_state['selected_entity_index'] = next_index

    selected_entity_name = 'All'
    if next_index < len(entities):
        selected_entity_state = hass.states.get(entities[next_index])
        selected_entity_name = None
        if not selected_entity_state:
            selected_entity_name = selected_entity_state.attributes.get('friendly_name') 
            print('Attributes: %s' % (selected_entity_state.attributes))
        if not selected_entity_name:
            # Fallback to a best effort entity name using the entity id
            selected_entity_name = entities[next_index].split('.')[1].replace('_', ' ')

    notification_entity_id = data.get('notify_entity_id')
    if notification_entity_id:
        notification_entity_state = hass.states.get(notification_entity_id)
        attrs = {}
        component_saved_state = hass.states.get(STATE_NAME)
        component_attrs = {}
        if component_saved_state:
            component_attrs = component_saved_state.attributes.copy()

        if notification_entity_state:
            if notification_entity_state.attributes:
                attrs = notification_entity_state.attributes.copy()
            
            temporary_set_volume = True
            if component_attrs.get('revert_volume_level'):
                notification_entity_volume_level = component_attrs.get('revert_volume_level')
                temporary_set_volume = False
            elif attrs.get('volume_level'):
                notification_entity_volume_level = attrs.get('volume_level')
            else:
                notification_entity_volume_level = '0.0'
        else:
            notification_entity_volume_level = '0.0'

        revert_volume_id = current_milli_time()
        component_attrs['revert_volume_id'] = revert_volume_id
        # Make sure the revert volume hasn't already been set
        if temporary_set_volume:
            component_attrs['revert_volume_level'] = notification_entity_volume_level
            notify_volume_level = data.get('notify_volume')
            if not notify_volume_level:
                notify_volume_level = _DEFAULT_NOTIFY_VOLUME_LEVEL

            # Temporary set a volume level
            hass.services.call('media_player', 'volume_set', {
                'entity_id': notification_entity_id,
                'volume_level': notify_volume_level
            })
        
        # Write down the volume to be reverted to the state such that it cab be used outside of this scope
        hass.states.set(STATE_NAME, '', component_attrs)

        hass.services.call('tts', 'google_say', {
            'entity_id': notification_entity_id,
            'message': selected_entity_name
        })

        print('Before wait: %s' % hass.states.get(notification_entity_id).attributes)
        print('Before wait: %s' % hass.states.get(STATE_NAME).attributes)

        # There is a small notification when changing the sound, so lets start waiting for 1s to make sure the
        # TTS is playing
        time.sleep(0.2)

        # Wait for TTS to finish
        attrs = hass.states.get(notification_entity_id).attributes
        print(attrs)
        wait_tts_duration = 5.0
        media_duration = attrs.get('media_duration')
        media_position = attrs.get('media_position')
        if media_duration != None and media_position != None:
            print('%d, %d' % (float(media_duration), float(media_position)))
            wait_tts_duration = max(float(media_duration) * (1 - float(media_position)), 0)
        print('Waiting for %ds' % (wait_tts_duration))
        time.sleep(wait_tts_duration + 0.5)

        # NOTE: That new clicks can happen before TTS is done, in that case we don't want to rever the volume
        #  in this call (but let the last click's call take care if it)

        notification_entity_state = hass.states.get(notification_entity_id)
        attrs = notification_entity_state.attributes.copy()
        media_position = float(attrs.get('media_position'))
        print('After wait: %s' % attrs)
        component_saved_state = hass.states.get(STATE_NAME)
        component_attrs = component_saved_state.attributes.copy()
        print('After wait: %s' % component_attrs)

        # Make sure another keypress was clicked (thus that keypress should revert the volume)
        if revert_volume_id == component_attrs.get('revert_volume_id'):
            # Revert to previous volume level
            hass.services.call('media_player', 'volume_set', {
                'entity_id': notification_entity_id,
                'volume_level': notification_entity_volume_level
            })
            component_attrs['revert_volume_level'] = None
            component_attrs['revert_volume_id'] = None
            hass.states.set(STATE_NAME, '', component_attrs)
            print('Reverting volume to %s' % notification_entity_volume_level)

    print('Changed to selected entity %s' % (selected_entity_name))

def _select_entity_left_service_call(hass, entity_id, data, component_state):
    _select_entity(hass, entity_id, data, component_state, True)

def _select_entity_right_service_call(hass, entity_id, data, component_state):
    _select_entity(hass, entity_id, data, component_state, False)

service_call_mapper = {
    'dim': _dim_service_call,
    'toggle': _toggle_service_call,
    'on': _turn_on_service_call,
    'off': _turn_off_service_call,
    'select_entity_left': _select_entity_left_service_call,
    'select_entity_right': _select_entity_right_service_call
}