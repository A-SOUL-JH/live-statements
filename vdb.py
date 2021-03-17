from pymongo import MongoClient


class VDB():
    client = MongoClient()
    db = client['free']
    living_dbs = {}
    
    @classmethod
    def migrate(cls, to):
        for collection in db.list_collection_names():
            client[to][collection].insert_many(db[collection].find({},{'_id':0}))

    @classmethod
    def set_db(cls, rid):
        VDB.living_dbs[rid] = VDB.client[str(rid)]

    @classmethod
    def remove_db(cls, rid):
        if VDB.living_dbs.get(rid, None):
            del VDB.living_dbs[rid]

    @classmethod
    def get_db(cls, rid):
        return VDB.living_dbs.get(rid, VDB.db)

    async def insert(self, rid, msg):
        collection = VDB.get_db(rid)[msg[0]]
        data = msg[1]
        if collection.database.name == 'free':
            data.update({'roomid': rid})
        collection.insert_one(data)

    async def update(self, rid, msg, cond):
        collection = VDB.get_db(rid)[msg[0]]
        data = msg[1]
        collection.update(cond, data)

    @classmethod
    def find(self, rid, cname, *args):
        print(rid, cname, *args)
        return VDB.get_db(rid)[cname].find(*args)