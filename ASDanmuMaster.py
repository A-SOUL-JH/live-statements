from bilibili_api.live import LiveDanmaku
from bilibili_api import utils


class LiveDanmu(LiveDanmaku):
    def __init__(self, room_display_id: int, debug: bool = False, use_wss: bool = True, should_reconnect: bool = True
                 , verify: utils.Verify = None):
        super().__init__(room_display_id, debug, use_wss, should_reconnect, verify)
        self.start_time = None
        self.end_time = None

    def _remove_event_handler(self, event_name):
        if event in self._LiveDanmaku__event_handlers:
            self._LiveDanmaku__event_handlers[event_name] = []

    def reset_time(self):
        self.start_time = None
        self.end_time = None