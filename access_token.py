# 获取和管理access_token

import aiohttp
import aiofiles
import asyncio
import json
import time

token = ""
expire = 0
lock = asyncio.Lock()

with open("data/secrets.json") as f:
    secrets = json.load(f)

async def query_access_token():
    "向服务器查询access token"
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": secrets["AppId"],
        "secret": secrets["AppSecret"]
    }
    resp = await aiohttp.get(url, params=params)
    data = await resp.json()
    return data

async def get_access_token():
    "若未过期则返回原来的access token，否则获取新的token"
    global token, expire
    async with lock:
        if time.time() > expire:
            data = await query_access_token()
            async with aiofiles.open("token.json", "wt") as f:
                await f.write(json.dumps(data))
            assert 'access_token' in data and 'expires_in' in data
            token = data['access_token']
            expire = time.time() + data['expires_in']
        return token
