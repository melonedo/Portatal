
from fastapi import FastAPI, WebSocketDisconnect, WebSocket, Request
from hashlib import sha1
import json
from fastapi.responses import PlainTextResponse
from wechat_xml import dict_to_xml, xml_to_dict
from aiohttp import ClientSession

app = FastAPI()

with open("data/secrets.json") as f:
    secrets = json.load(f)

ip = None


@app.get("/wechat")
async def verify_wechat(signature: str, timestamp: str, nonce: str, echostr: str):
    # print(signature, timestamp, nonce, sep='\n')
    params = ''.join(sorted([secrets['Token'], timestamp, nonce]))
    hashcode = sha1(params.encode('utf-8')).hexdigest()
    if hashcode == signature:
        print("认证成功")
        return PlainTextResponse(echostr)
    else:
        print("认证失败")
        return PlainTextResponse("")


@app.websocket("/piconnect")
async def websocket_endpoint(ws: WebSocket):
    global ip
    if ip:
        await ws.close()
        return
    await ws.accept()
    ip = f"http://{ws.client.host}:4321/"

    print(f"{ip} connected")
    try:
        while True:
            # Not much to do
            await ws.receive_text()

    except WebSocketDisconnect:
        print(f"{ip} disconnected")
        ip = None
        await ws.close()


@app.post("/wechat")
async def receive_msg(req: Request):
    body = xml_to_dict(await req.body().decode('utf-8'))
    if body['MsgType'] != 'TEXT':
        return PlainTextResponse("success")
    text = body['Content']
    if not text.startswith('电费'):
        return PlainTextResponse("success")
    async with ClientSession() as s:
        resp = await s.get(ip + "electricity", params=text[2:])
        elec = await resp.json()
        if elec['success']:
            content = f"{elec['name']}剩余{elec['type']}: {elec['num']}{elec['unit']}"
        else:
            content = f"查询失败: {elec['error']}"
    resp={
        'ToUserName': body['FromUserName'],
        'FromUserName': body['ToUserName'],
        'CreateTime': int(body['CreateTime']),
        'MsgType': 'TEXT',
        'Content': content,
    }
    return PlainTextResponse(dict_to_xml(resp))
