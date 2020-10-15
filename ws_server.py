from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import RedirectResponse
import asyncio

app = FastAPI()

ip = None

@app.get("/")
async def hello():
    return {"hello": "world!"}

@app.get("/pi/{more_path:path}")
async def forward(req: Request, more_path: str):
    return RedirectResponse(ip + more_path, 307, req.headers)

@app.websocket("/piconnect")
async def elec_ws(ws: WebSocket):
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
        print(f"{ip} diconnected")
        ip = None
        await ws.close()
