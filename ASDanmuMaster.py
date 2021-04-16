from bilibili_api.live import LiveDanmaku, get_room_info
from bilibili_api import utils
from datetime import datetime
from figure import ASFigure
from live import WsMessage
from utils import get_live_start_time
from vdb import VDB
import asyncio

import socket
import requests

class LiveDanmu(LiveDanmaku):
    def __init__(self, room_display_id: int, debug: bool = False, use_wss: bool = True, should_reconnect: bool = True
                 , verify: utils.Verify = None):
        super().__init__(room_display_id, debug, use_wss, should_reconnect, verify)
        self.start_time = None
        self.end_time = None
        self.live_flag = False
        self.__err_flag = 0

    async def listen(self):
        while True:
            self.__err_flag = 0
            try:
                await self.connect(True)
            except socket.gaierror as err:
                print(self.room_display_id, end=': ')            
                print(err)
                self.__err_flag = 1
                await asyncio.sleep(1)
            except requests.exceptions.ConnectionError as err:
                print(self.room_display_id, end=': ')
                print(err)
                self.__err_flag = 1
                await asyncio.sleep(1)
            finally:
                self.disconnect()
                if not self.__err_flag:
                    return self.__err_flag

    def _remove_event_handler(self, event_name):
        if event_name in self._LiveDanmaku__event_handlers:
            self._LiveDanmaku__event_handlers[event_name] = []

    async def record(self, msg):
        """普通直播事件处理程序"""
        await VDB().insert(WsMessage(msg))

    async def start_record(self, msg):
        """直播开始事件处理程序"""
        if not self.live_flag:
            await self.live_on(msg)

    async def stop_record(self, msg):
        """直播结束事件处理程序"""
        self.live_off(msg)

    async def live_on(self, msg):
        self.live_flag = True
        VDB.set_db(self.room_display_id)
        self.start_time = get_live_start_time(msg)
        await VDB().insert(WsMessage(msg))

    def live_off(self, msg):
        self.live_flag = False
        self.end_time = int(datetime.now().timestamp())
        VDB().update(WsMessage({**msg, '_id': self.start_time}))
        room_info = get_room_info(self.room_display_id)
        self.title = room_info['room_info']['title']        
        try:
            ASFigure(self).paint()
        except Exception as e:
            print(e)
        self.reset_time()
        VDB.remove_db(self.room_display_id)

    def reset_time(self):
        self.start_time = None
        self.end_time = None