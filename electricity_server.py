# 在内网用树莓派挂一个电费api

from fastapi import FastAPI, status
from electricity import query_electricity, InvalidRoomNameError
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/electricity")
async def elec_api(room: str):
    resp = {}
    try:
        name, result = await query_electricity(room)
        # print(result)
        resp['success'] = True
        resp['type'] = result[0]
        resp['number'] = result[1]
        resp['unit'] = result[2]
        resp['name'] = name
    except InvalidRoomNameError as e:
        resp['success'] = False
        resp['error'] = repr(e)
    except Exception as e:
        resp['success'] = False
        resp['error'] = str(e)
    
    return resp

