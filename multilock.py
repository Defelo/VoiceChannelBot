import asyncio


class MultiLock:
    def __init__(self):
        self.locks = {}
        self.requests = {}

    async def acquire(self, key):
        lock = self.locks.setdefault(key, asyncio.Lock())
        self.requests[key] = self.requests.get(key, 0) + 1
        await lock.acquire()

    def release(self, key):
        assert key in self.locks
        lock = self.locks[key]
        lock.release()
        self.requests[key] -= 1
        if not self.requests[key]:
            self.locks.pop(key)
            self.requests.pop(key)
