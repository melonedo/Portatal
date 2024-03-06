import requests
import re
from base64 import b64encode
from Crypto.Cipher import DES
import json
from parse_room import parse_room, InvalidRoomNameError
from urllib.parse import quote

with open("data/secrets.json") as f:
    secrets = json.load(f)
user = secrets['StudentId']
passwd = secrets['Password']

with open("data/buildings_tongxinyun.json", encoding='utf-8') as f:
    room_lib = json.load(f)


def enc_passwd(user, pwd):
    key = user[:8].ljust(8, '\0').encode()
    cipher = DES.new(key, DES.MODE_CBC, iv=key)
    pad = 8 - len(pwd) % 8
    pwd += pad * chr(pad)
    return b64encode(cipher.encrypt(pwd.encode())).decode()


def login(user, passwd) -> requests.Session:
    sess = requests.Session()
    resp = sess.post('https://txb.tongji.edu.cn/openaccess/user/login', json={
        'eid': '',
        'userName': user,
        'password': enc_passwd(user, passwd),
        'appClientId': '38881',
        'deviceId': '?',
        'deviceType': '?',
    }).json()
    if not resp['success']:
        raise RuntimeError("登陆失败")
    token = resp['data']['token']
    # print(f'获取到 Opentoken: {token}')
    sess.headers['Opentoken'] = token
    resp = sess.post('https://txb.tongji.edu.cn/gateway/ticket/terminal/lappAccess', data={
        'appId': '200019',
        'deviceType': '1',
    }).json()
    if not resp['success']:
        raise RuntimeError("获取 App 数据失败")
    # print(f"校园钱包2.0: {resp['data']['url']}")
    ticket = re.findall('ticket=([\w\d]*)', resp['data']['url'])[0]
    # print(f'获取到ticket: {ticket}')
    resp = sess.post('https://tjpay.tongji.edu.cn:8080/user/login', data={
        'ticket': ticket,
    })
    if resp.json()['msg'] != 'success':
        raise RuntimeError("认证失败")
    userid = resp.json()['data']['userId']
    sess.headers['Authorization'] = resp.headers['Authorization']
    # print(f'认证成功 Authorization: {resp.headers["Authorization"]}')
    return sess, userid


def get_lib(sess):
    with sess.get("https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms/firstSchools") as resp:
        schools = resp.json()['data']['appList']
    for s in schools:
        with sess.get(f"https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms/secondSchools?aid={s['aid']}") as resp:
            s['areas'] = resp.json()['data']['areatab']
            account = resp.json()['data']['account']
        for a in s['areas']:
            with sess.get(f"https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms/buildings?account={account}&aid={s['aid']}&area={a['area']}") as resp:
                a['buildings'] = resp.json()['data']['buildingtab']
            for b in a['buildings']:
                print(b)
                with sess.get(f"https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms/rooms", params={'area': a['area'], 'buildingId': b['buildingId']}) as resp:
                    b['rooms'] = resp.json()['data']

    # 把列表改成字典
    data = {}
    for s in data:
        data[s['name']] = s
        areas = s['areas']
        s['areas'] = {}
        for a in areas:
            s['areas'][a['areaName']] = a
            buildings = a['buildings']
            a['buildings'] = {}
            for b in buildings:
                a['buildings'][b['building']] = b
                rooms = b['rooms']
                b['rooms'] = {}
                for r in rooms:
                    b['rooms'][r['room']] = r['roomId']

    with open("data/buildings_tongxinyun.json", "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def get_room_data(room_name):
    room, std_name = parse_room(room_name)
    # print(room)
    area_map = {'四平路校区ISIMS': ('四平路校区', '本部电控1'),
                '彰武路校区SIMS': ('彰武校区', '航校校区'),
                '彰武路校区ISIMS': ('彰武校区', '航校校区1'),
                '嘉定校区SIMS': ('嘉定校区', '嘉定校区'),
                '嘉定校区ISIMS': ('嘉定校区', '嘉定校区1')}
    area_name = room[0]
    if area_name not in area_map:
        raise InvalidRoomNameError("暂不支持此校区：{area}")
    # print(area_map[area_name])
    school_name, area_name = area_map[area_name]
    school = room_lib[school_name]
    area = school['areas'][area_name]
    building = area['buildings'][room[1].strip()]
    rooms = building['rooms']
    m = re.search(r'\d+$', room[3])
    if not m:
        raise InvalidRoomNameError("房间名{room[3]}中不包含数字房间号")
    room_num = m[0]
    return {
        "area": area['area'],
        "areaName": area_name,
        "building": building['building'],
        "buildingId": building['buildingId'],
        "room": room_num,
        "roomId": rooms[room_num]
    }


def query_electricity(room_name):
    data = get_room_data(room_name)
    sess, userid = login(user, passwd)
    # get_data(sess)
    with sess.post(f"https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms?userId={userid}") as resp:
        pass
    resp = sess.get(
        f'https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms/list?userId={userid}').json()
    # for item in resp['data']:
    #     print(' '.join([item['areaName'], item['building'],
    #                     item['room'], str(item['remain'])]))

    # 添加
    form = data.copy()
    form['userId'] = userid
    form['isDefault'] = False
    nodelete = False
    with sess.post(f"https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms?userId={userid}", json=form) as resp:
        code = resp.json()['code']
        if code == 1 and resp.json()['msg'] == "该宿舍楼已绑定":
            nodelete = True
        else:
            assert code == 0
    # 查询
    with sess.get(f"https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms/list?userId={userid}") as resp:
        assert resp.json()['code'] == 0
        for item in resp.json()['data']:
            if item['areaName'] == data['areaName'] and item['room'] == data['room']:
                result = item['remain']
    # 删除
    if not nodelete:
        with sess.delete(f"https://tjpay.tongji.edu.cn:8080/user/merchant/elec/dorms/area/{data['area']}/room/{quote(data['room'])}/building/{quote(data['building'])}/userId/{userid}") as resp:
            assert resp.json()['code'] == 0
    return data['areaName'] + ' ' + data['building'] + data['room'], ("剩余电量", result, "度")


def main(room):
    sess, userid = login(user,passwd)
    get_lib(sess)
    query_electricity(room)

if __name__ == '__main__':
    # print(query_electricity('7-123'))
    print(query_electricity('14-636'))
