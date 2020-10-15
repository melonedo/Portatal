# 树莓派主动联系服务器以提供查询电费服务

import asyncio
import aiohttp
from electricity import query_electricity

url = 'http://172.81.215.215/piconnect'

async def main():
    async with aiohttp.ClientSession() as s:
        while True:
            try:
                async with s.ws_connect(url) as ws:
                    while True:
                        print("Websocket connected.")
                        await ws.receive_str()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(repr(e))
            print("Websocket disconnected, retry in 5 mins.")
            await asyncio.sleep(300)
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
