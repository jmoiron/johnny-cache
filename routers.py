# routers for johnny's tests
class MultiSyncedRouter(object):
    def db_for_read(self, *args, **kwargs): return None
    def db_for_write(self, *args, **kwargs): return None
    def allow_relation(self, *args, **kwargs): return None
    def allow_sync_db(self, db, model):
        return True
