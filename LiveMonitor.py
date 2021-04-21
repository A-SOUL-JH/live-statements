from bilibili_api.live import connect_all_LiveDanmaku, get_room_info
from datetime import datetime
from live import WsMessage
from ASDanmuMaster import LiveDanmu
from vdb import VDB
from settings import DEFAULT_LISTEN_EVENTS, LISTEN_ROOMS
from utils import gen_msg
import asyncio
import traceback
import sys
import requests


class LiveMonitor():
    def __init__(self, rids=LISTEN_ROOMS, events=DEFAULT_LISTEN_EVENTS):
        self.rooms = [LiveDanmu(rid) for rid in rids]
        self.tasks = []
        for room in self.rooms:
            room.add_event_handler('LIVE', room.start_record)
            room.add_event_handler('PREPARING', room.stop_record)
            for event_name in events:
                room.add_event_handler(event_name, room.record)

    def __init_room(self, room):
        data = get_room_info(room.room_display_id)
        rinfo = data['room_info']
        if rinfo['live_status'] == 1:
            start_time = rinfo['live_start_time']
            live_key = rinfo['up_session']
            rid = rinfo['short_id'] if rinfo['short_id'] else rinfo['room_id']
            msg = gen_msg(rid, 'LIVE', **dict(start_time=start_time, live_key=live_key, full=False))
            asyncio.create_task(room.start_record(msg))

    async def run(self):
        for room in self.rooms:
            self.__init_room(room)
        for i in range(120):
            print('monitor running...')
            try:
                self.tasks = [asyncio.create_task(room.listen()) for room in self.rooms]
                await asyncio.gather(*self.tasks)
            except requests.exceptions.ConnectionError as err:
                print(datetime.now().strftime('%Y%m%d %H:%M:%S'), err)
                print('------------------------------>')                
            except Exception as e:
                print(datetime.now())
            finally:
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                traceback.print_exception(exc_type, exc_value, exc_traceback_obj)
                for room in self.rooms:
                    if room.get_connect_status():
                        room.disconnect() 
                for task in asyncio.all_tasks():
                    if task in self.tasks and not task.done():
                        task.cancel()
            await asyncio.sleep(5)
            print('error occurred. now reconnecting...')
            


if __name__ == "__main__":
    monitor = LiveMonitor(LISTEN_ROOMS+[510, 6562109, 4138602])
    asyncio.run(monitor.run())