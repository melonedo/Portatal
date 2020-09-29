# 在内网用树莓派挂一个电费api

from fastapi import FastAPI, status
from electricity import query_electricity, InvalidRoomNameError
app = FastAPI()

@app.get("/electricity")
async def elec_api(room: str):
    resp = {}
    try:
        name, result = await query_electricity(room)
        print(result)
        resp['success'] = True
        resp['type'] = result[0]
        resp['number'] = result[1]
        resp['unit'] = result[2]
        resp['name'] = name
    except InvalidRoomNameError as e:
        resp['sucess'] = False
        resp['error'] = repr(e)
    except Exception as e:
        resp['sucess'] = False
        resp['error'] = str(e)
    
    return resp