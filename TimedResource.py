
from time import time
import asyncio
import json
from os.path import isfile

class AsyncTimedResource(object):
    """以异步方式管理会随时间而过期的资源。
    距离上次调用经历超过timeout秒后会调用一次acquire_fn，然后把内容保存到file_name中。
    acquire_fn应返回可用json序列化的对象。
    """

    def __init__(self, acquire_fn, timeout, file_name):
        self.acquire_fn = acquire_fn
        self.timeout = timeout
        self.file_name = file_name
        
        self.time = 0
        self.lock = asyncio.Lock()
        self.data = None

        self.restore()
    
    async def get(self):
        async with self.lock:
            if time() - self.time < self.timeout:
                return self.data
            self.data = await self.acquire_fn()
            self.time  = time()
            data = {
                'time': self.time,
                'data': self.data
            }
            with open(self.file_name, 'wt', encoding='utf-8') as f:
                json.dump(data, f)
        return self.data
    
    def restore(self):
        "从文件中获得已经保存的内容。若文件不存在或内容错误则当作无事发生。"
        if not isfile(self.file_name):
            return
        with open(self.file_name, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        if 'data' in data and 'time' in data:
            self.data = data['data']
            self.time = data['time']


async def test():
    num = 0
    async def counter():
        nonlocal num
        num += 1
        return num
    resource = AsyncTimedResource(counter, 10, "data/test_async_timed_resouce.json")
    num = await resource.get()
    print("按回车键以获取数字，每10s更新一次（若关闭程序且已过期则重新计数）。num:", num)
    while True:
        try:
            input()
        except KeyboardInterrupt:
            print('')
            break
        n = await resource.get()
        print("Time passed:", time() - resource.time,", num:", n, end='')

if __name__ == "__main__":
    asyncio.run(test())
