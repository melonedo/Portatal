import asyncio
from collections import namedtuple
import json
import aiohttp
from bs4 import BeautifulSoup, Tag
from normalize import normalize_name
import re
from pathlib import Path


URL = "http://202.120.163.129:88"


def extract_form(soup: BeautifulSoup, form_id="form1"):
    form = {}
    for i in soup.find(id=form_id).find_all("input"):  # type: ignore
        if "value" in i.attrs:
            form[i["name"]] = i["value"]
    return form


async def post_form(s: aiohttp.ClientSession, form: dict):
    async with s.post(URL, data=form, raise_for_status=True) as r:
        text = await r.text()
    soup = BeautifulSoup(text, "lxml")
    form = extract_form(soup)
    return soup, form


KEYS = ["drlouming", "drceng", "dr_ceng", "drfangjian"]


async def fetch_data(s: aiohttp.ClientSession, i: int, form: dict, entry: dict):
    soup, form = await post_form(s, form)
    options = soup.find(id=KEYS[i])
    entry["state"] = form["__VIEWSTATE"]
    assert isinstance(options, Tag)
    for o in options.find_all("option"):
        k, v = o.get_text().strip(), o["value"]
        if not v:
            continue
        assert k
        entry[k] = dict(value=v)
        if i + 1 < len(KEYS):
            # print(k)
            await fetch_data(s, i + 1, {**form, KEYS[i]: v}, entry[k])


Room = namedtuple("Room", "state, name, campus, building, floor, room")


def normalize_building_name(building: str, campus_id: str):
    if campus_id in ["3", "4"]:
        building = "彰武" + building
    elif campus_id == "11":
        building = "沪西" + building
    elif campus_id in ["7", "9"]:
        building = "友园" + building.removeprefix("友园")
    building = normalize_name(building)
    return building


def preprocess(data) -> dict[str, dict[str, Room]]:
    "Convert to format result[building][room] => Room(...)"
    result = dict()
    for campus in data.values():
        if not isinstance(campus, dict):
            continue
        for building_name, building in campus.items():
            if not isinstance(building, dict):
                continue
            building_name = normalize_building_name(building_name, campus["value"])
            d = result[building_name] = dict()
            for floor in building.values():
                if not isinstance(floor, dict):
                    continue
                for room_name, room in floor.items():
                    if not isinstance(room, dict):
                        continue
                    m = re.search(r"([a-zA-Z0-9-]+)$", room_name)
                    if not m:
                        continue
                    room_id = m.group(1)
                    if building_name in ["友园17", "友园18"]:
                        # 12034 -> 1234
                        room_id = room_id[:2] + room_id[3:]
                    assert len(room_id) < 3 or room_id not in d
                    if re.fullmatch(r"\d+", room_name):
                        name = building_name + "-" + room_name
                    else:
                        name = room_name
                    d[room_id] = Room(
                        state=floor["state"],
                        name=name,
                        campus=campus["value"],
                        building=building["value"],
                        floor=floor["value"],
                        room=room["value"],
                    )
    return result


async def query(s: aiohttp.ClientSession, room: Room):
    form = {
        "__VIEWSTATE": room.state,
        "__VIEWSTATEGENERATOR": "CA0B0334",
        "radio": "usedR",
        "drfangjian": room.room,
        "ImageButton1.x": 51,
        "ImageButton1.y": 37,
    }
    # Must use unsafe cookie jar to accept cookies without domain name
    assert s.cookie_jar._unsafe  # type: ignore
    async with s.post(URL, data=form) as r:
        text = await r.text()
    pattern = r"(剩余电量|剩余金额).+?([+-]?\d+\.?\d*).*?([元度])"
    m = re.search(pattern, text)
    if not m:
        raise ValueError("Failed to parse http://202.120.163.129:88/default.aspx")
    return m.group(1, 2, 3)


class InvalidRoomNameError(ValueError):
    pass


def split_building_room(room_name: str):
    m = re.fullmatch(r"\s*(\d+)\s*[-—]\s*([-—\d]+)", room_name)
    if m:
        return "友园" + m.group(1), m.group(2)
    m = re.fullmatch(r"\s*(\S+?)\s*(\d+(-\d)?)\s*", room_name)
    if m:
        return m.group(1, 2)
    raise InvalidRoomNameError(f"Failed to parse: {room_name}")


def parse_room(room_name: str, database: dict[str, dict[str, Room]]):
    building_name, room_name = split_building_room(room_name)
    building_name = normalize_name(building_name)
    # 友园17/18
    if len(room_name) > 4:
        room_name = re.sub("[-—]", "", normalize_name(room_name))
        room_name = room_name[:2] + room_name[3:]

    if building_name in database:
        building = database[building_name]
    else:
        raise InvalidRoomNameError(f"Failed to interpret building name {building_name}")

    room = building.get(room_name)
    if not room:
        raise InvalidRoomNameError(f"Failed to interpret room name {room_name}")
    return room


async def load_database():
    p = Path("data/database.json")
    if not p.parent.exists():
        raise RuntimeError("Directory `data` does not exist")
    if not p.exists():
        print("Creating `data/database.json`")
        database = {}
        async with aiohttp.ClientSession() as s:
            await fetch_data(s, 0, {}, database)
        with p.open("wt", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)
    else:
        with p.open("rb") as f:
            database = json.load(f)
    return preprocess(database)


DATABASE = None
sema = asyncio.Semaphore()


async def query_electricity(room_name: str):
    global DATABASE
    async with sema:
        if not DATABASE:
            DATABASE = await load_database()
    room = parse_room(room_name, DATABASE)
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as s:
        result = await query(s, room)
    return room.name, result


async def main():
    names = "17-1-2-021;16-1122;西南一1022;8—404;20- 533;13-543;博士3号楼1303;\
        西南11 216;西北三139;西南二539-1;彰武三1406;彰武8 1413;\
        12-711"
    for r in await asyncio.gather(*map(query_electricity, names.split(";"))):
        print(r)


if __name__ == "__main__":
    asyncio.run(main())
