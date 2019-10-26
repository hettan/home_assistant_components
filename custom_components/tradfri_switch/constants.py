import time

DOMAIN = 'tradfri_switch'
STATE_NAME = '%s.component' % (DOMAIN)
DEPENDENCIES = []
DIM_UPDATE_INTERVAL_MS = 0.1
DIM_UPDATE_AMOUNT_PERCENT = 5 

current_milli_time = lambda: int(round(time.time() * 1000))