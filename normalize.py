from functools import lru_cache
import re

CN_TO_AR_TRANS = str.maketrans("一二三四五六七八九", "123456789")
CN_NUM_PATTERN = r"[一二三四五六七八九十]{1,3}"


@lru_cache(maxsize=None)
def cn_num_to_arabic(cn_num: re.Match) -> str:
    "cn_num是100以内的中文数字，将其转换为对应的阿拉伯数字"
    # assert re.fullmatch(CN_NUM_PATTERN) is not None
    ara_num = cn_num[0].translate(CN_TO_AR_TRANS)

    if len(ara_num) == 1:  # 1-10
        if ara_num == "十":
            return "10"
        else:
            return ara_num
    elif len(ara_num) == 2 and ara_num[0] == "十":  # 11-19
        return "1" + ara_num[1]
    elif len(ara_num) == 2 and ara_num[1] == "十":  # 20, 30, ..., 90
        return ara_num[0] + "0"
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
    name = re.sub(r"(?!\d)0+(\d+)", r"\1", name)
    name = name.replace("博士生", "博士")
    name = re.sub(r"号?(楼|公寓)$", "", name)
    name = re.sub("号楼", "号", name)
    return name
