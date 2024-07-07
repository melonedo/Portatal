# 在内网用树莓派挂一个电费api

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from electricity_viewstate import query_electricity, InvalidRoomNameError
from electricity_tongxinyun import query_electricity as query_electricity_tongxinyun
import threading

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Uncomment to use nyglzx API
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

lock = threading.Lock()
# @app.get("/electricity")
def elec_api_tongxinyun(room: str):
    resp = {}
    try:
        with lock:
            name, result = query_electricity_tongxinyun(room)
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
