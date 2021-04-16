from datetime import datetime
from collections import namedtuple
from vdb import VDB
from utils import get_live_start_time

Message = namedtuple('Message', [
    'DANMU_MSG',
    'INTERACT_WORD',
    'ENTRY_EFFECT',
    'SEND_GIFT',
    'COMBO_SEND',
    'SUPER_CHAT_MESSAGE_JPN',
    'SUPER_CHAT_MESSAGE',
    'ROOM_REAL_TIME_MESSAGE_UPDATE',
    'GUARD_BUY',
    'USER_TOAST_MSG'
])

RID = 'room_display_id'

class WsMessage():
    def __init__(self, msg):
        self.msg_type = msg.get('type', None)
        self.rid = msg.get(RID, None)
        try:
            self.data = getattr(self, '_process_'+self.msg_type.lower())(msg)
        except Exception as e:
            print(e)
            print(msg)
            self.data = None
    
    def _process_send_gift(self, msg):
        data = msg['data']['data']
        return [
            'gift', {
                'time': data['timestamp'],
                'type': data['coin_type'],
                'coin': data['total_coin'],
                'gift_name': data['giftName'],
                'num': data['num'],
                'uid': data['uid'],
                'uname': data['uname'],
                'medal': [data['medal_info']['medal_level'], data['medal_info']['medal_name']]
            }
        ]

    def _process_super_chat_message(self, msg):
        data = msg['data']['data']
        medal_info = data['medal_info']
        return [
            'superchat', {
                'time': data['ts'],
                'price': data['price'],
                'text': data['message'],
                'uid': data['uid'],
                'uname': data['user_info']['uname'],
                'medal': [medal_info['medal_level'], medal_info['medal_name']] if medal_info else [0, ''],
                'level': data['user_info']['user_level']
            }
        ]

    def _process_user_toast_msg(self, msg):
        data = msg['data']['data']
        return [
            'guard', {
                'time': data['start_time'],
                'price': data['price'],
                'num': data['num'],
                'unit': data['unit'],
                'uid': data['uid'],
                'uname': data['username']
            }
        ]

    def _process_danmu_msg(self, msg):
        info = msg['data']['info']
        return [
            'danmu', {
                'time': info[0][4],
                'text': info[1],
                'uid': info[2][0],
                'uname': info[2][1],
                'medal': info[3][:2] if info[3] else [0, ''],
                'level': info[4][0]
            }
        ]

    def _process_interact_word(self, msg):
        data = msg['data']['data']
        return [
            'entry', {
                'time': data['timestamp'],
                'uid': data['uid'],
                'uname': data['uname'],
                'medal': [data['fans_medal']['medal_level'], data['fans_medal']['medal_name']],
            }
        ]

    def _process_guard_entry(self, msg):
        data = msg['data']['data']
        return [
            'entry_guard', {
                'uid': data['uid']
            }
        ]
    
    def _process_view(self, msg):
        rid = msg[RID]
        return [
            'view', {'value': msg['data'], 'time': int(datetime.now().timestamp())}
        ]

    def _process_room_real_time_message_update(self, msg):
        data = msg['data']['data']
        return [
            'fans', {
                'time': int(datetime.now().timestamp()),
                'fans': data['fans'],
                'fans_club': data['fans_club']
            }
        ]
    
    def _process_live(self, msg):
        print('_process_live...')
        print(msg)
        ts = get_live_start_time(msg)
        msg['data'].update(dict(finished=False, start_time=ts, _id=ts))
        return ['live_info', msg['data']]

    def _process_preparing(self, msg):
        print('_process_preparing...')
        print(msg)
        data = msg['data']
        #VDB.get_db(rid)['live_info'].find_one_and_update({'finished': False, 'roomid': self.rid, '_id': {'$type': 16}}
        #                , {'$set':{'finished': True, 'end_time': int(datetime.now().timestamp()),}}, sort=[('_id', -1)])
        return ['live_info', {'finished': True, 'end_time': int(datetime.now().timestamp()),}, {'finished': False, '_id': msg['_id']}]

    def get_message_type(self):
        return self.msg_type

    async def save_to_db(self, rid):
        if not self.data:
            return
        await VDB().insert(rid, self.data)
    