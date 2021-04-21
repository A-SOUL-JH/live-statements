from pymongo import MongoClient
# from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

class VDB():
    # client = AsyncIOMotorClient()
    client = MongoClient()
    db = client['free']
    living_dbs = {}
    
    @classmethod
    def migrate(cls, to):
        for collection in db.list_collection_names():
            client[to][collection].insert_many(db[collection].find({},{'_id':0}))

    @classmethod
    def add_db(cls, rid):
        VDB.living_dbs[rid] = VDB.client[str(rid)]

    @classmethod
    def remove_db(cls, rid):
        if VDB.living_dbs.get(rid, None):
            del VDB.living_dbs[rid]

    @classmethod
    def get_db(cls, rid):
        return VDB.living_dbs.get(rid, VDB.db)

    async def insert(self, ws_msg):
        if not ws_msg:
            return
        cname, data, *cond = ws_msg.data
        collection = VDB.get_db(ws_msg.rid)[cname]
        if collection.database.name == 'free':
            data.update({'roomid': ws_msg.rid})
        collection.insert_one(data)

    def update(self, ws_msg):
        cname, data, *cond = ws_msg.data
        print(cond)
        collection = VDB.get_db(ws_msg.rid)[cname]
        res = collection.update(cond[0] if cond else dict(), {'$set': data})
        print('[update]', res)

    def find(self, rid, cname, *args):
        return VDB.client[str(rid)][cname].find(*args)