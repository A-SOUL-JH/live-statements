from bilibili_api.live import LiveDanmaku, get_room_info
from bilibili_api import utils
from datetime import datetime
from figure import ASFigure
from vdb import VDB


class LiveDanmu(LiveDanmaku):
    def __init__(self, room_display_id: int, debug: bool = False, use_wss: bool = True, should_reconnect: bool = True
                 , verify: utils.Verify = None):
        super().__init__(room_display_id, debug, use_wss, should_reconnect, verify)
        self.start_time = None
        self.end_time = None
        self.live_flag = False

    def _remove_event_handler(self, event_name):
        if event in self._LiveDanmaku__event_handlers:
            self._LiveDanmaku__event_handlers[event_name] = []

    def live_on(self):
        VDB.set_db(self.room_display_id)
        self.live_flag = True
        self.start_time = int(datetime.now().timestamp())

    def live_off(self):
        self.live_flag = False
        room_info = get_room_info(self.room_display_id)
        self.title = room_info['room_info']['title']
        self.end_time = int(datetime.now().timestamp())
        try:
            ASFigure(self).paint()
        except Exception as e:
            print(e)

    def reset_time(self):
        self.start_time = None
        self.end_time = None