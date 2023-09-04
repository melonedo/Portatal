from functools import lru_cache
import re
import json


class InvalidRoomNameError(ValueError):
    pass


CN_TO_AR_TRANS = str.maketrans('一二三四五六七八九', '123456789')
CN_NUM_PATTERN = r'[一二三四五六七八九十]{1,3}'


@lru_cache(maxsize=None)
def cn_num_to_arabic(cn_num: re.Match) -> str:
    "cn_num是100以内的中文数字，将其转换为对应的阿拉伯数字"
    # assert re.fullmatch(CN_NUM_PATTERN) is not None
    ara_num = cn_num[0].translate(CN_TO_AR_TRANS)

    if len(ara_num) == 1:  # 1-10
        if ara_num == '十':
            return '10'
        else:
            return ara_num
    elif len(ara_num) == 2 and ara_num[0] == '十':  # 11-19
        return '1' + ara_num[1]
    elif len(ara_num) == 2 and ara_num[1] == '十':  # 20, 30, ..., 90
        return ara_num[0] + '0'
    elif len(ara_num) == 3:
        return ara_num[0] + ara_num[2]
    else:
        raise ValueError(f"InvalidChineseNumber: {cn_num}")


def chinese_number_to_arabic(name):
    return re.sub(CN_NUM_PATTERN, cn_num_to_arabic, name)


@lru_cache(maxsize=None)
def normalize_name(name: str) -> str:
    "把楼名做标准化处理"
    name = name.strip()
    name = chinese_number_to_arabic(name)
    name = re.sub(r'(?!\d)0+(\d+)', r'\1', name)
    name = name.replace("博士生", "博士")
    name = re.sub(r'号?(楼|公寓)$', '', name)
    name = re.sub('号楼', '号', name)
    return name


BUILDINGS_MAP_NORMALIZED = {}  # 初始化的部分在下面


YOUYUAN_SET = {*range(2, 11),  12, 16}
HAOLOU_SET = {13, 14, 15, 17, 18, 19, 20}


def preprocess_jiading(room_name):
    "把12-404格式的房间名改成对应楼名，如“友园12号楼404”"
    m = re.match(r'\s*(\d+)\s*[-—]\s*(\d+)', room_name)
    if m is None:
        return room_name
    building = int(m.group(1))
    room = m.group(2)
    if building in YOUYUAN_SET:
        return f"友园{building}号楼 {room}"
    if building in HAOLOU_SET:
        return f"{building}号楼 {room}"
    raise InvalidRoomNameError(f"无法解析嘉定{building}号楼")


@lru_cache(maxsize=None)
def parse_room(name: str):
    "解析房间号，返回电费查询所需的四个选项的名称。"
    # 先解析嘉定的房间
    name = preprocess_jiading(name)

    # 分离房间号和楼号
    m = re.fullmatch(r'\s*(\S+?)\s*(\d+(-\d)?)\s*', name)
    if m is None:
        raise InvalidRoomNameError(f"Invalid room name: {name}")
    building, room = m.group(1, 2)

    # 标准化
    building = normalize_name(building)

    data = BUILDINGS_MAP_NORMALIZED.get(building, None)
    if data is None:
        raise InvalidRoomNameError(f"Unrecognized building: {building}")

    if building == '西南1':
        # 特例
        raise InvalidRoomNameError("西南一号楼无法查询")
        floor_name = f"{room[0:2]}01-{room[0:2]}99"
    else:
        if '博士' in building or '彰武' in building:
            floor = room[:-2]
        else:
            floor = room[0]
        for name in data['include']:
            # 寻找最右的数字作为楼层
            m = re.search(r'(\d+)\D*$', chinese_number_to_arabic(name))
            if m is None:
                raise ValueError(f"{name}不包含楼层")
            if floor in m.group(1):
                floor_name = name
                break
        else:
            raise InvalidRoomNameError(f"Unrecognized room: {room}")

    belong = data['belong']
    raw_building = data['raw']
    if belong.endswith('ISIMS'):
        room_name = raw_building + room
    else:  # SIMS
        room_name = room

    raw_bd_nm = normalize_name(raw_building)
    room_name_nm = normalize_name(room_name)
    if raw_bd_nm in room_name_nm:
        std_name = room_name_nm
    else:
        std_name = raw_building + ' ' + room_name_nm
    if '彰武' in building:
        std_name = '彰武' + std_name
    std_name = std_name.replace(" ", "")
    std_name = re.sub(r"号楼?(?!公寓)", r"号楼", std_name)
    std_name = re.sub(r"^((?:19|20)号楼?|\d+号公寓)", r"友园\1", std_name)

    return (belong, raw_building, floor_name, room_name), std_name


with open('data/buildings.json', encoding='utf-8') as f:
    buildings_map = json.load(f)
for k, v in buildings_map['main'].items():
    v['raw'] = k
    BUILDINGS_MAP_NORMALIZED[normalize_name(k)] = v
for k, v in buildings_map['zhangwu'].items():
    v['raw'] = k
    BUILDINGS_MAP_NORMALIZED['彰武' + normalize_name(k)] = v


def test():
    test_nums = '西南十二号楼 十号楼 学五楼 二十 三十四个人'
    print(normalize_name(test_nums))
    import json
    print(json.dumps(BUILDINGS_MAP_NORMALIZED, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    test()
