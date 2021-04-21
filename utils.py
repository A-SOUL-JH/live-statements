from datetime import datetime

def gen_msg(rid, cmd, **msgs):
    return {'room_display_id': rid, 'type': cmd, 'data': {'cmd': cmd, **msgs}}

def get_live_start_time(msg):
    ssk = msg['data'].get('sub_session_key', None)
    return int(ssk.split(':')[1]) if ssk else msg['data'].get('start_time', int(datetime.now().timestamp()))