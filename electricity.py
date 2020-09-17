import asyncio
import aiohttp
from bs4 import BeautifulSoup
import xml.dom.minidom as dom
import re

from parse_room import InvalidRoomNameError, parse_room, normalize_name


def getForm(soup: BeautifulSoup, form_id):
    form = {}
    for i in soup.find(id=form_id).find_all('input'):
        if 'value' in i.attrs:
            form[i['name']] = i['value']
    return form


url = 'http://202.120.163.129:88'


async def updateForm(session, form, soup: BeautifulSoup, key, value):
    "该网页每次选择了选项后都会提交一次表单，此函数提交原来的并获得新的表。"
    def normalized_equal(s):
        return normalize_name(s) == normalize_name(value)
    select = soup.find('select', id=key)
    opt = select.find('option', string=normalized_equal)
    if opt is None:
        raise InvalidRoomNameError(value)
    data = {key: opt['value']}

    form.update(data)
    async with session.post(url, data=form) as resp:
        text = await resp.text()
    soup = BeautifulSoup(text, 'lxml')
    new_form = getForm(soup, 'form1')
    form.update(new_form)
    return soup


async def get_left_electricity(data):
    "根据提供的房间数据访问能源管理中心以查询电费"
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as s:
        #从ip接收cookies需要unsafe的cookie jar
        async with s.get(url) as resp:
            text = await resp.text()
        soup = BeautifulSoup(text, 'lxml')
        form = getForm(soup, 'form1')

        keys = ['drlouming', 'drceng', 'dr_ceng', 'drfangjian']
        for k, v in zip(keys, data):
            soup = await updateForm(s, form, soup, k, v)

        form.update({
            'radio': 'usedR',
            'ImageButton1.x': 51,
            'ImageButton1.y': 37})
        async with s.post(url, data=form, raise_for_status=True) as resp:
            # 如果allow_redirects=False的话还得手动再转发一次
            # async with s.get(url+'/usedRecord1.aspx') as resp:
            text = await resp.text()
            try:
                pattern = r'(剩余电量|剩余金额).+?([+-]?\d+\.?\d*).*?([元度])'
                return re.search(pattern, text).group(1, 2, 3)
            except Exception as e:
                raise ValueError(e)


async def query_electricity(room_name):
    "解析房间名并在能源管理中心查询电费。"
    try:
        room = parse_room(room_name)
    except Exception as e:
        raise InvalidRoomNameError(e)
    elec = await get_left_electricity(room)
    room_arabic = list(map(normalize_name, room))
    if room_arabic[1] in room_arabic[3]:
        room_name = room[3].strip()
    else:
        room_name = room[1].strip() + room[3].strip()
    return room_name, elec


async def main():
    await query_electricity('西北三139')
    names = '西南一1023;8—404;20- 533;博士3号楼1303;西南11 216;西北三139;西南二539-1;彰武三1406;彰武8 1413'.split(';')
    for r in await asyncio.gather(*map(query_electricity, names)):
        print(r)


if __name__ == "__main__":
    print(asyncio.run(main()))
