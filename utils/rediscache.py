
class Redis:
    
    tracker = {}

    @staticmethod
    def read(id, field=None):
        if field:
                return Redis.tracker.get(id,{}).get(field, None)
        else :
                val = Redis.tracker.get(id, None)
                print(f"Return val from read is {val}")
                return val
        
    @staticmethod
    def write(id, field):
        print(f"id recvd is {id}")
        Redis.tracker[id] = field
        print(f"Tracker is {Redis.tracker}")

    @staticmethod
    def update(id, k, v):
        Redis.tracker[id][k] = v