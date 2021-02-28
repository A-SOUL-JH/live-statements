from bilibili_api.live import connect_all_LiveDanmaku, get_room_info
from datetime import datetime
from live import WsMessage
from ASDanmuMaster import LiveDanmu
from vdb import VDB
from settings import DEFAULT_LISTEN_EVENTS, LISTEN_ROOMS
from figure import ASFigure
import asyncio


class LiveMonitor():
    def __init__(self, rids):
        self.rooms = [LiveDanmu(rid) for rid in rids]
        for room in self.rooms:
            room.add_event_handler('LIVE', self.start_record(room))
            room.add_event_handler('PREPARING', self.stop_record(room))
            for event_name in DEFAULT_LISTEN_EVENTS:
                room.add_event_handler(event_name, self.record(room))

    def record(self, room):
        """普通直播事件处理程序"""
        async def process(msg):
            asyncio.create_task(WsMessage(msg).save_to_db(room.room_display_id))
        return process

    def start_record(self, room):
        """直播开始事件处理程序"""
        async def register(msg):
            room.start_time = int(datetime.now().timestamp())
            asyncio.create_task(WsMessage(msg).save_to_db(room.room_display_id))
        return register

    def stop_record(self, room):
        """直播结束事件处理程序"""
        def close(msg):
            room_info = get_room_info(room.room_display_id)
            room.title = room_info['room_info']['title']
            # room.start_time = room_info['room_info']['live_start_time']
            room.end_time = int(datetime.now().timestamp())
            try:
                ASFigure(room).paint()
            except Exception as e:
                print(e)
            WsMessage(msg)
            room.reset_time()            
        return close

    def run(self):
        for room in self.rooms:
            if get_room_info(room.room_display_id)['room_info']['live_status'] == 1:
                VDB.set_db(room.room_display_id)
        connect_all_LiveDanmaku(*self.rooms)


if __name__ == "__main__":
    monitor = LiveMonitor(LISTEN_ROOMS)
    monitor.run()