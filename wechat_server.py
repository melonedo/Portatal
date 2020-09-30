
from fastapi import FastAPI
from hashlib import sha1
import json
from fastapi.responses import PlainTextResponse

app = FastAPI()

with open("data/secrets.json") as f:
    secrets = json.load(f)

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




