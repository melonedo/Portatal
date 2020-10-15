
from fastapi import FastAPI, WebSocketDisconnect, WebSocket
from hashlib import sha1
import json
from fastapi.responses import PlainTextResponse

app = FastAPI()

with open("data/secrets.json") as f:
    secrets = json.load(f)

ip = None

@app.get("/wechat")
async def verify_wechat(signature: str, timestamp: str, nonce: str, echostr: str):
    #print(signature, timestamp, nonce, sep='\n')
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
