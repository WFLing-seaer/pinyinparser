from __future__ import annotations  # 兼容一下3.14-

import base64  # 解压那坨位图用的（嗯确实是解压因为a85编码比直接写hex还短这何尝不是一种压缩
import re  # 过滤用的
from collections.abc import Iterable
from enum import IntEnum, StrEnum
from functools import cache
from itertools import chain
from typing import NamedTuple, cast, overload
from unicodedata import normalize
from warnings import warn

# 0x8000为声母变体选择位，0x6000为韵母变体选择位。0x0600不完全是介音，还有一些其他变体的借位，但总体上来说和介音差不多


class Initial(IntEnum):
    missing = 0
    unspec = 0x0001
    nul = 0x0002
    b = 0x0003
    c = 0x0004
    d = 0x0005
    f = 0x0006
    g = 0x0007
    h = 0x0008
    j = 0x0009
    k = 0x000A
    l = 0x000B
    m = 0x000C
    n = 0x000D
    p = 0x000E
    q = 0x000F
    r = 0x0010
    s = 0x0011
    t = 0x0012
    w = 0x0013  # 注意y w不是nul的变体
    x = 0x0014
    y = 0x0015
    z = 0x0016

    ch = 0x8004  # 变体选择位的意义在于，可以通过屏蔽变体选择位来实现“首字母”或者“通配”之类的概念，比如ch屏蔽了0x8000就变成c，下同
    sh = 0x8011
    zh = 0x8016
    H = 0x8008  # Hhm Hhng
    R = 0x8010  # Rri
    M = 0x800C  # Mm
    N = 0x800D  # Nn Nng


class Final(IntEnum):
    missing = 0
    unspec = 0x0100
    nul = 0x0200
    a = 0x0300
    ai = 0x0400
    an = 0x0500
    ang = 0x0600
    ao = 0x0700
    e = 0x0800
    ei = 0x0900
    en = 0x0A00
    eng = 0x0B00
    er = 0x0C00
    i = 0x0D00  # [i] ji qi xi
    ong = 0x0E00
    ou = 0x0F00
    u = 0x1000
    uo = 0x1100
    veh = 0x1200
    o = 0x1400
    v = 0x1500
    ieng = 0x1600
    ng = 0x1700  # [ŋ̊]
    m = 0x2200
    n = 0x4200
    hm = 0x6200  # 此三视为nul的变体
    hng = 0x3700  # ng的变体
    eh = 0x2900  # ê，兼容性地视为变体。理论上兼容变体还可以有hng=eng ng=en这两组，但是这两组从音位上就说不通，因此不予采用
    ii = 0x2D00  # [z]/[ɿ] zi ci si
    ri = 0x4D00  # [ʅ] zhi chi shi [ʐ]/[ʅ] ri
    ia = 0x2300
    ian = 0x2500
    iang = 0x2600
    iao = 0x2700
    ieh = 0x2800
    ien = 0x2A00
    iong = 0x2E00
    iou = 0x2F00
    ua = 0x4300
    uai = 0x4400
    uan = 0x4500
    uang = 0x4600
    uei = 0x4900
    uen = 0x4A00
    ueng = 0x4B00
    van = 0x6500
    ven = 0x6A00


class Tone(IntEnum):  # 可以进行一些bithack，比如&0x00C0=0x0080匹配新韵平声之类的
    missing = 0
    unspec = 0x0020
    nul = 0x0040
    t5 = 0x0060
    t1 = 0x0080
    t2 = 0x00A0
    t3 = 0x00C0
    t4 = 0x00E0


FINAL2STR = {
    Final.ii: "i",
    Final.ri: "i",
    Final.iou: "iu",
    Final.uei: "ui",
    Final.ien: "in",
    Final.uen: "un",
    Final.v: "ü",
    Final.veh: "üe",
    Final.van: "üan",
    Final.ven: "ün",
    Final.eh: "ê",
    Final.ieh: "ie",
    Final.ieng: "ing",
}
TONE2STR = {
    Tone.t1: "1",
    Tone.t2: "2",
    Tone.t3: "3",
    Tone.t4: "4",
    Tone.t5: "5",
}
FINAL2TONED = {
    Tone.t1: {"a": "ā", "e": "ē", "i": "ī", "o": "ō", "u": "ū", "ü": "ǖ", "ê": "ê̄", "m": "m̄", "n": "n̄"},
    Tone.t2: {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "ü": "ǘ", "ê": "ế", "m": "ḿ", "n": "ń"},
    Tone.t3: {"a": "ǎ", "e": "ě", "i": "ǐ", "o": "ǒ", "u": "ǔ", "ü": "ǚ", "ê": "ê̌", "m": "m̌", "n": "ň"},
    Tone.t4: {"a": "à", "e": "è", "i": "ì", "o": "ò", "u": "ù", "ü": "ǜ", "ê": "ề", "m": "m̀", "n": "ǹ"},
}
SYLLMAP_Y = {
    Final.ia: "ya",
    Final.ieh: "ye",
    Final.iao: "yao",
    Final.iou: "you",
    Final.ian: "yan",
    Final.ien: "yin",
    Final.iang: "yang",
    Final.ieng: "ying",
    Final.iong: "yong",
    Final.v: "yu",
    Final.veh: "yue",
    Final.van: "yuan",
    Final.ven: "yun",
}
SYLLMAP_W = {
    Final.ua: "wa",
    Final.uo: "wo",
    Final.uai: "wai",
    Final.uei: "wei",
    Final.uan: "wan",
    Final.uen: "wen",
    Final.uang: "wang",
    Final.ueng: "weng",
}
SYLL1SEP: set[Final] = {
    Final.m,
    Final.n,
    Final.ng,
    Final.an,
    Final.ang,
    Final.en,
    Final.eng,
    Final.er,
    Final.hm,
    Final.hng,
    Final.i,
    Final.ri,
    Final.ii,
    Final.ian,
    Final.iang,
    Final.ien,
    Final.ieng,
    Final.iong,
    Final.ong,
    Final.uan,
    Final.uang,
    Final.uen,
    Final.ueng,
    Final.van,
    Final.ven,
}
SYLL2SEP: set[Final] = {Final.m, Final.n, Final.ng, Final.eh}
SYLLSEP: dict[Final, set[Final]] = {
    Final.a: {Final.o, Final.ong, Final.ou},
    Final.ia: {Final.o, Final.ong, Final.ou},
    Final.u: {Final.a, Final.ai, Final.an, Final.ang, Final.ao, Final.eng, Final.o, Final.ong, Final.ou},
    Final.v: {Final.an, Final.ang, Final.e, Final.ei, Final.en, Final.eng, Final.er, Final.o},
}


class ToneStyle(StrEnum):
    ABOVE = "above"
    RIGHT = "right"
    AFTER = "after"


class IncompatibleWarning(UserWarning):
    pass


class _SyllMeta(type):
    def __getattr__(self, name):
        try:
            return parse_single(name)
        except ValueError:
            raise AttributeError(name)


class Syllable(metaclass=_SyllMeta):
    @overload
    def __init__(self, i: Initial = ..., f: Final = ..., t: Tone = ...): ...

    @overload
    def __init__(self, i: int): ...

    @overload
    def __init__(self, i: str): ...

    def __init__(self, i: int | Initial | str = Initial.missing, f: Final = Final.missing, t: Tone = Tone.missing):
        if isinstance(i, str):
            if (f is not Final.missing) or (t is not Tone.missing):
                raise ValueError("不能同时使用字符串初始化和声韵调初始化。")
            sp = parse_single(i)
            self.initial = sp.initial
            self.final = sp.final
            self.tone = sp.tone
        elif isinstance(i, Initial):
            self.initial = i
            self.final = f
            self.tone = t
        else:
            if (f is not Final.missing) or (t is not Tone.missing):
                raise ValueError("不能同时使用uint16初始化和声韵调初始化。")
            if i & ~0xFFFF:
                raise ValueError("int中存在无效的位。使用整数初始化时仅接受uint16。")
            try:
                self.initial = Initial(i & 0x801F)
                self.final = Final(i & 0x7F00)
                self.tone = Tone(i & 0x00E0)
            except ValueError as e:
                raise ValueError("无效的uint16。") from e

    def __index__(self):
        return self.initial | self.final | self.tone

    def __repr__(self):
        return f"<{self.initial.name}·{self.final.name}·{self.tone.name.removeprefix("t")}{"" if self.is_valid() else "(N/E)"}>"

    @cache
    def to_str(self, tone_style: ToneStyle = ToneStyle.ABOVE, NO_INCOMPAT_WARNING: bool = False) -> str:
        match self.initial:
            case Initial.missing | Initial.unspec | Initial.nul:
                initial_str = ""
            case Initial.H:
                initial_str = "h"
            case Initial.M | Initial.N:
                initial_str = ""
            case _:
                initial_str = self.initial.name

        if self.final in (Final.missing, Final.unspec, Final.nul):
            final_str = ""
        else:
            final_str = FINAL2STR.get(self.final, self.final.name)

        match self.initial:
            case Initial.y:
                base_str = SYLLMAP_Y.get(self.final, f"y{final_str}")
            case Initial.w:
                base_str = SYLLMAP_W.get(self.final, f"w{final_str}")
            case Initial.j | Initial.q | Initial.x:
                base_str = initial_str + final_str.replace("ü", "u")
            case Initial.R if self.final == Final.ri:
                base_str = "ri"
            case Initial.H if self.final in (Final.hm, Final.hng):
                base_str = final_str
            case Initial.M if self.final in (Final.m, Final.n, Final.ng):
                base_str = final_str
            case _:
                base_str = initial_str + final_str

        if not base_str:
            return ""

        if tone_style == ToneStyle.AFTER:
            return base_str + TONE2STR.get(self.tone, "")

        if self.tone in (Tone.missing, Tone.unspec, Tone.nul):
            return base_str

        if tone_style == ToneStyle.ABOVE and self.tone == Tone.t5:
            return base_str

        toned = FINAL2TONED.get(self.tone, {})

        for v in ["a", "ê", "e", "o"]:
            if (pos := base_str.find(v)) != -1:
                break
        else:
            for pos in range(len(base_str) - 1, -1, -1):
                if base_str[pos] in {"i", "u", "ü"}:
                    break
            else:
                for v in ["n", "m"]:
                    if (pos := base_str.find(v)) != -1:
                        break
                else:
                    return base_str

        if tone_style == ToneStyle.ABOVE:
            if base_str[pos] in toned:
                return f"{base_str[:pos]}{toned[base_str[pos]]}{base_str[pos+1:]}"
            return base_str
        elif tone_style == ToneStyle.RIGHT:
            if not NO_INCOMPAT_WARNING:
                warn(
                    "注意：使用RIGHT（数字附标）模式产出的拼音字符串并不通用，且不再能被本解析器解析。如果你明确知道你在做什么，可以传入NO_INCOMPAT_WARNING=True以关闭此警告。",
                    IncompatibleWarning,
                )
            return f"{base_str[:pos+1]}{TONE2STR.get(self.tone, '')}{base_str[pos+1:]}"

        return base_str

    def __str__(self):
        return self.to_str()

    def __bool__(self):
        return bool(self.initial or self.final or self.tone)

    def __eq__(self, other):
        return self.initial == other.initial and self.final == other.final and self.tone == other.tone

    __hash__ = __index__

    def is_complete(self):
        return bool(self.initial and self.final and self.tone)

    def need_sep(self, prev: Syllable) -> bool:
        if self.initial and (self.initial not in {Initial.nul, Initial.unspec, Initial.M}):
            return False  # 有有效声母隔着则必不需要

        if prev.final in SYLL1SEP or self.final in SYLL2SEP:
            return True

        return prev.final in SYLLSEP and self.final in SYLLSEP[prev.final]

    def is_valid(self):
        return _check_syllable_valid(int(self))

    def copy(self):
        return Syllable(self.initial, self.final, self.tone)

    def _mreject(self, other: Syllable, check_initial: bool = False):
        return bool(
            (self.initial and other.initial)
            or (self.tone and other.tone)
            or ((self.final or self.tone) and (other.initial or other.final))
            or (
                check_initial
                and (self.final or other.final or ((self.initial or other.initial) and (self.tone or other.tone)))
                and ((self.initial == Initial.nul) or (not self.initial))
                and ((other.initial == Initial.nul) or (not other.initial))
            )
        )
        # 化简自(s1 and o1)or(s2 and o2)or(s3 and o3)or(s2 and o1)or(s3 and o1)or(s3 and o2)or(check_initial and(s1 or o1 or s2 or o2)and(s2 or o2 or s3 or o3)and((self.initial==Initial.nul)or(not s1))and((other.initial==Initial.nul)or(not o1)))
        # 其中s1=self.initial!=Initial.missing s2=self.final!=Final.missing s3=self.tone!=Tone.missing o1=other.initial!=Initial.missing o2=other.final!=Final.missing o3=other.tone!=Tone.missing

    def _merge(self, other: Syllable):
        if other.initial != Initial.missing:
            self.initial = other.initial
        if other.final != Final.missing:
            self.final = other.final
        if other.tone != Tone.missing:
            self.tone = other.tone


class TOKENS(NamedTuple):
    NE = {  # noqa: RUF012 这个怎么不会自动检测NamedTuple……以及github上似乎一堆issue没修了，唉谁知道呢
        "uéng": [0x4BA0],
        "juán": [0x65A9],
        "wéng": [0x4BB3],
        "quě": [0x12CF],
        "jún": [0x6AA9],
        "qùn": [0x6AEF],
        "xǔn": [0x6AD4],
        "wái": [0x44B3],
        "zí": [0x2DB6],
        "sí": [0x2DB1],
        "ēr": [0x0C82, 0x0C80],
        "n̄g": [0x978D],  # n+macron没有单字符表示
        "wó": [0x11B3],
        "rī": [0x4D80],
        "rí": [0x4DA0],
        "rǐ": [0x4DC0],
    }
    EXT = {  # noqa: RUF012
        "ń": [0xC2AD],
        "ň": [0xC2CD],
        "ǹ": [0xC2ED],
        "n2": [0xC2AD],
        "n3": [0xC2CD],
        "n4": [0xC2ED],
        "ḿ": [0xA2AC],  # 只有ḿ有单字符表示
        "m̀": [0xA2EC],  # 多字符
        "m2": [0xA2AC],
        "m4": [0xA2EC],
        "hm": [0xE268],  # 噷
        "hng": [0xB768],  # 哼
        "ng": [0x970D],  # [ŋ̊]，仅见于唔、嗯二字
        "ńg": [0x97AD],
        "ňg": [0x97CD],
        "ǹg": [0x97ED],
    }
    EXT_NE = {  # noqa: RUF012
        "n̄": [0xC28D],  # 多字符
        "n1": [0xC28D],
        "m̄": [0xA28C],  # 多字符
        "m̌": [0xA2CC],  # 多字符
        "m1": [0xA28C],
        "m3": [0xA2CC],
    }
    EXT2 = {  # 按需启用 # noqa: RUF012
        "?": [0x0001, 0x0100, 0x0020],  # 通配
        ".": [0x0121],
        "*": [0x0001, 0x0100],  # 声母韵母通配
        "0": [0x0020],  # 声调通配
        "/": [0x0002],  # 零声母
        "&": [0x0004],  # 伪声母R
        "ri": [0xCD10, 0x4D00],  # [ʐ]/[ʅ]
        "rī": [0xCD90, 0x4D80],  # 痴 不存在
        "rí": [0xCDB0, 0x4DA0],  # 迟 不存在
        "rǐ": [0xCDD0, 0x4DC0],  # 齿 不存在
        "rì": [0xCDF0, 0x4DE0],  # 斥 日
        "ii": [0x2D00],  # [z]/[ɿ]
    }
    BASIC = {  # noqa: RUF012
        "iang": [0x2600],
        "iāng": [0x2680],  # 江
        "iáng": [0x26A0],  # 凉
        "iǎng": [0x26C0],  # 抢
        "iàng": [0x26E0],  # 呛
        "iong": [0x2E00],
        "iōng": [0x2E80],  # 凶
        "ióng": [0x2EA0],  # 穷
        "iǒng": [0x2EC0],  # 涌
        "iòng": [0x2EE0],  # 用
        "uang": [0x4600],
        "uāng": [0x4680],  # 光
        "uáng": [0x46A0],  # 狂
        "uǎng": [0x46C0],  # 广
        "uàng": [0x46E0],  # 旷
        "ueng": [0x4B00],
        "uēng": [0x4B80],  # 翁
        "uěng": [0x4BC0],  # 塕
        "uèng": [0x4BE0],  # 瓮
        "juan": [0x6509],
        "juān": [0x6589],  # 捐
        "juǎn": [0x65C9],  # 卷
        "juàn": [0x65E9],  # 倦
        "quan": [0x650F],
        "quān": [0x658F],  # 圈
        "quán": [0x65AF],  # 全
        "quǎn": [0x65CF],  # 犬
        "quàn": [0x65EF],  # 劝
        "xuan": [0x6514],
        "xuān": [0x6594],  # 宣
        "xuán": [0x65B4],  # 悬
        "xuǎn": [0x65D4],  # 选
        "xuàn": [0x65F4],  # 炫
        "yang": [0x2615],
        "yāng": [0x2695],  # 央
        "yáng": [0x26B5],  # 阳
        "yǎng": [0x26D5],  # 养
        "yàng": [0x26F5],  # 样
        "ying": [0x1615],
        "yīng": [0x1695],  # 英
        "yíng": [0x16B5],  # 赢
        "yǐng": [0x16D5],  # 影
        "yìng": [0x16F5],  # 映
        "yong": [0x2E15],
        "yōng": [0x2E95],  # 拥
        "yóng": [0x2EB5],  # 颙
        "yǒng": [0x2ED5],  # 泳
        "yòng": [0x2EF5],  # 用
        "wang": [0x4613],
        "wāng": [0x4693],  # 汪
        "wáng": [0x46B3],  # 王
        "wǎng": [0x46D3],  # 网
        "wàng": [0x46F3],  # 忘
        "weng": [0x4B13],
        "wēng": [0x4B93],  # 翁
        "wěng": [0x4BD3],  # 塕
        "wèng": [0x4BF3],  # 瓮
        "yuan": [0x6515],
        "yuān": [0x6595],  # 冤
        "yuán": [0x65B5],  # 圆
        "yuǎn": [0x65D5],  # 远
        "yuàn": [0x65F5],  # 怨
        "ang": [0x0602, 0x0600],
        "āng": [0x0682, 0x0680],  # 刚 肮
        "áng": [0x06A2, 0x06A0],  # 扛 昂
        "ǎng": [0x06C2, 0x06C0],  # 莽 䇦
        "àng": [0x06E2, 0x06E0],  # 抗 盎
        "eng": [0x0B02, 0x0B00],
        "ēng": [0x0B82, 0x0B80],  # 庚 鞥
        "éng": [0x0BA2, 0x0BA0],  # 横 不存在
        "ěng": [0x0BC2, 0x0BC0],  # 冷 不存在
        "èng": [0x0BE2, 0x0BE0],  # 赠 不存在
        "ian": [0x2500],
        "iān": [0x2580],  # 先
        "ián": [0x25A0],  # 咸
        "iǎn": [0x25C0],  # 显
        "iàn": [0x25E0],  # 现
        "iao": [0x2700],
        "iāo": [0x2780],  # 交
        "iáo": [0x27A0],  # 嚼
        "iǎo": [0x27C0],  # 缴
        "iào": [0x27E0],  # 叫
        "ing": [0x1600],
        "īng": [0x1680],  # 星
        "íng": [0x16A0],  # 形
        "ǐng": [0x16C0],  # 醒
        "ìng": [0x16E0],  # 幸
        "ong": [0x0E00],
        "ōng": [0x0E80],  # 东
        "óng": [0x0EA0],  # 龙
        "ǒng": [0x0EC0],  # 拢
        "òng": [0x0EE0],  # 冻
        "uai": [0x4400],
        "uāi": [0x4480],  # 乖
        "uái": [0x44A0],  # 淮
        "uǎi": [0x44C0],  # 拐
        "uài": [0x44E0],  # 坏
        "uan": [0x4500],
        "uān": [0x4580],  # 欢
        "uán": [0x45A0],  # 环
        "uǎn": [0x45C0],  # 缓
        "uàn": [0x45E0],  # 换
        "van": [0x6500],
        "vān": [0x6580],  # 捐
        "ván": [0x65A0],  # 全
        "vǎn": [0x65C0],  # 犬
        "vàn": [0x65E0],  # 倦
        "üan": [0x6500],
        "üān": [0x6580],
        "üán": [0x65A0],
        "üǎn": [0x65C0],
        "üàn": [0x65E0],
        "zhi": [0xCD16],  # [ʅ]
        "zhī": [0xCD96],  # 支
        "zhí": [0xCDB6],  # 直
        "zhǐ": [0xCDD6],  # 纸
        "zhì": [0xCDF6],  # 至
        "chi": [0xCD04],  # [ʅ]
        "chī": [0xCD84],  # 吃
        "chí": [0xCDA4],  # 持
        "chǐ": [0xCDC4],  # 尺
        "chì": [0xCDE4],  # 赤
        "shi": [0xCD11],  # [ʅ]
        "shī": [0xCD91],  # 诗
        "shí": [0xCDB1],  # 石
        "shǐ": [0xCDD1],  # 史
        "shì": [0xCDF1],  # 事
        "jue": [0x1209],
        "juē": [0x1289],  # 撅
        "jué": [0x12A9],  # 绝
        "juě": [0x12C9],  # 蹶
        "juè": [0x12E9],  # 倔
        "que": [0x120F],
        "quē": [0x128F],  # 缺
        "qué": [0x12AF],  # 瘸
        "què": [0x12EF],  # 雀
        "xue": [0x1214],
        "xuē": [0x1294],  # 薛
        "xué": [0x12B4],  # 学
        "xuě": [0x12D4],  # 雪
        "xuè": [0x12F4],  # 谑
        "jun": [0x6A09],
        "jūn": [0x6A89],  # 君
        "jǔn": [0x6AC9],  # 𢉦（RD广军）
        "jùn": [0x6AE9],  # 郡
        "qun": [0x6A0F],
        "qūn": [0x6A8F],  # 逡
        "qún": [0x6AAF],  # 群
        "qǔn": [0x6ACF],  # 䊎
        "xun": [0x6A14],
        "xūn": [0x6A94],  # 勋
        "xún": [0x6AB4],  # 寻
        "xùn": [0x6AF4],  # 巽
        "yao": [0x2715],
        "yāo": [0x2795],  # 邀
        "yáo": [0x27B5],  # 摇
        "yǎo": [0x27D5],  # 咬
        "yào": [0x27F5],  # 药
        "you": [0x2F15],
        "yōu": [0x2F95],  # 优
        "yóu": [0x2FB5],  # 游
        "yǒu": [0x2FD5],  # 有
        "yòu": [0x2FF5],  # 右
        "yan": [0x2515],
        "yān": [0x2595],  # 烟
        "yán": [0x25B5],  # 盐
        "yǎn": [0x25D5],  # 眼
        "yàn": [0x25F5],  # 验
        "yin": [0x2A15],
        "yīn": [0x2A95],  # 阴
        "yín": [0x2AB5],  # 银
        "yǐn": [0x2AD5],  # 饮
        "yìn": [0x2AF5],  # 印
        "wai": [0x4413],
        "wāi": [0x4493],  # 歪
        "wǎi": [0x44D3],  # 𨂿
        "wài": [0x44F3],  # 外
        "wei": [0x4913],
        "wēi": [0x4993],  # 威
        "wéi": [0x49B3],  # 维
        "wěi": [0x49D3],  # 尾
        "wèi": [0x49F3],  # 味
        "wan": [0x4513],
        "wān": [0x4593],  # 弯
        "wán": [0x45B3],  # 完
        "wǎn": [0x45D3],  # 碗
        "wàn": [0x45F3],  # 万
        "wen": [0x4A13],
        "wēn": [0x4A93],  # 温
        "wén": [0x4AB3],  # 文
        "wěn": [0x4AD3],  # 稳
        "wèn": [0x4AF3],  # 问
        "yue": [0x1215],
        "yuē": [0x1295],  # 约
        "yué": [0x12B5],  # 块（音yué义不详，但字统有记载因而算进来了）
        "yuě": [0x12D5],  # 哕
        "yuè": [0x12F5],  # 月
        "yun": [0x6A15],
        "yūn": [0x6A95],  # 晕
        "yún": [0x6AB5],  # 云
        "yǔn": [0x6AD5],  # 允
        "yùn": [0x6AF5],  # 韵
        "zi": [0x2D16],
        "zī": [0x2D96],  # 兹
        "zǐ": [0x2DD6],  # 紫
        "zì": [0x2DF6],  # 字
        "ci": [0x2D04],
        "cī": [0x2D84],  # 呲
        "cí": [0x2DA4],  # 词
        "cǐ": [0x2DC4],  # 此
        "cì": [0x2DE4],  # 次
        "si": [0x2D11],
        "sī": [0x2D91],  # 丝
        "sǐ": [0x2DD1],  # 死
        "sì": [0x2DF1],  # 四
        "ri": [0xCD10, 0x4D00],  # [ʐ]/[ʅ]
        "rì": [0xCDF0, 0x4DE0],  # 日
        "ai": [0x0402, 0x0400],
        "āi": [0x0482, 0x0480],  # 该 挨
        "ái": [0x04A2, 0x04A0],  # 孩 皑
        "ǎi": [0x04C2, 0x04C0],  # 改 矮
        "ài": [0x04E2, 0x04E0],  # 骇 爱
        "an": [0x0502, 0x0500],
        "ān": [0x0582, 0x0580],  # 潘 安
        "án": [0x05A2, 0x05A0],  # 盘 儑
        "ǎn": [0x05C2, 0x05C0],  # 懒 俺
        "àn": [0x05E2, 0x05E0],  # 烂 暗
        "ao": [0x0702, 0x0700],
        "āo": [0x0782, 0x0780],  # 高 凹
        "áo": [0x07A2, 0x07A0],  # 豪 熬
        "ǎo": [0x07C2, 0x07C0],  # 好 拗
        "ào": [0x07E2, 0x07E0],  # 告 傲
        "ei": [0x0902, 0x0900],
        "ēi": [0x0982, 0x0980],  # 飞 不存在（欸等字在eh）
        "éi": [0x09A2, 0x09A0],  # 肥 不存在
        "ěi": [0x09C2, 0x09C0],  # 匪 不存在
        "èi": [0x09E2, 0x09E0],  # 费 不存在
        "en": [0x0A02, 0x0A00],
        "ēn": [0x0A82, 0x0A80],  # 奔 恩
        "én": [0x0AA2, 0x0AA0],  # 盆 不存在
        "ěn": [0x0AC2, 0x0AC0],  # 本 不存在
        "èn": [0x0AE2, 0x0AE0],  # 笨 摁
        "er": [0x0C02, 0x0C00],
        "ér": [0x0CA2, 0x0CA0],  # 不存在 儿
        "ěr": [0x0CC2, 0x0CC0],  # 不存在 尔
        "èr": [0x0CE2, 0x0CE0],  # 不存在 佴
        "ia": [0x2300],
        "iā": [0x2380],  # 家
        "iá": [0x23A0],  # 夹
        "iǎ": [0x23C0],  # 贾
        "ià": [0x23E0],  # 架
        "ie": [0x2800],
        "iē": [0x2880],  # 街
        "ié": [0x28A0],  # 截
        "iě": [0x28C0],  # 解
        "iè": [0x28E0],  # 借
        "in": [0x2A00],
        "īn": [0x2A80],  # 侵
        "ín": [0x2AA0],  # 琴
        "ǐn": [0x2AC0],  # 寝
        "ìn": [0x2AE0],  # 沁
        "iu": [0x2F00],
        "iū": [0x2F80],  # 秋
        "iú": [0x2FA0],  # 求
        "iǔ": [0x2FC0],  # 朽
        "iù": [0x2FE0],  # 锈
        "ou": [0x0F02, 0x0F00],
        "ōu": [0x0F82, 0x0F80],  # 沟 欧
        "óu": [0x0FA2, 0x0FA0],  # 楼 吽
        "ǒu": [0x0FC2, 0x0FC0],  # 篓 偶
        "òu": [0x0FE2, 0x0FE0],  # 够 沤
        "ua": [0x4300],
        "uā": [0x4380],  # 花
        "uá": [0x43A0],  # 滑
        "uǎ": [0x43C0],  # 垮
        "uà": [0x43E0],  # 跨
        "ui": [0x4900],
        "uī": [0x4980],  # 灰
        "uí": [0x49A0],  # 回
        "uǐ": [0x49C0],  # 毁
        "uì": [0x49E0],  # 会
        "un": [0x4A00],
        "ūn": [0x4A80],  # 昆
        "ún": [0x4AA0],  # 仑
        "ǔn": [0x4AC0],  # 捆
        "ùn": [0x4AE0],  # 论
        "uo": [0x1100],
        "uō": [0x1180],  # 锅
        "uó": [0x11A0],  # 活
        "uǒ": [0x11C0],  # 火
        "uò": [0x11E0],  # 过
        "ve": [0x1200],
        "vē": [0x1280],  # 薛
        "vé": [0x12A0],  # 学
        "vě": [0x12C0],  # 雪
        "vè": [0x12E0],  # 谑
        "üe": [0x1200],
        "üē": [0x1280],
        "üé": [0x12A0],
        "üě": [0x12C0],
        "üè": [0x12E0],
        "vn": [0x6A00],
        "ün": [0x6A00],
        "ǖn": [0x6A80],  # 逡
        "ǘn": [0x6AA0],  # 群
        "ǚn": [0x6AC0],  # 允
        "ǜn": [0x6AE0],  # 孕
        "ju": [0x1509],
        "jū": [0x1589],  # 居
        "jú": [0x15A9],  # 局
        "jǔ": [0x15C9],  # 举
        "jù": [0x15E9],  # 句
        "qu": [0x150F],
        "qū": [0x158F],  # 区
        "qú": [0x15AF],  # 渠
        "qǔ": [0x15CF],  # 取
        "qù": [0x15EF],  # 去
        "xu": [0x1514],
        "xū": [0x1594],  # 需
        "xú": [0x15B4],  # 徐
        "xǔ": [0x15D4],  # 许
        "xù": [0x15F4],  # 序
        "yi": [0x0D15],
        "yī": [0x0D95],  # 一
        "yí": [0x0DB5],  # 疑
        "yǐ": [0x0DD5],  # 以
        "yì": [0x0DF5],  # 忆
        "ya": [0x2315],
        "yā": [0x2395],  # 压
        "yá": [0x23B5],  # 牙
        "yǎ": [0x23D5],  # 雅
        "yà": [0x23F5],  # 亚
        "ye": [0x2815],
        "yē": [0x2895],  # 噎
        "yé": [0x28B5],  # 爷
        "yě": [0x28D5],  # 野
        "yè": [0x28F5],  # 页
        "wu": [0x1013],
        "wū": [0x1093],  # 屋
        "wú": [0x10B3],  # 无
        "wǔ": [0x10D3],  # 舞
        "wù": [0x10F3],  # 物
        "wa": [0x4313],
        "wā": [0x4393],  # 洼
        "wá": [0x43B3],  # 娃
        "wǎ": [0x43D3],  # 瓦
        "wà": [0x43F3],  # 袜
        "wo": [0x1113],
        "wō": [0x1193],  # 窝
        "wǒ": [0x11D3],  # 我
        "wò": [0x11F3],  # 卧
        "yu": [0x1515],
        "yū": [0x1595],  # 淤
        "yú": [0x15B5],  # 于
        "yǔ": [0x15D5],  # 与
        "yù": [0x15F5],  # 玉
        "zh": [0x8016],
        "ch": [0x8004],
        "sh": [0x8011],
        "ê": [0x2900],
        "ê̄": [0x2980],
        "ế": [0x29A0],
        "ê̌": [0x29C0],
        "ề": [0x29E0],  # U+1EC1 一、二、三声没有结合形式，只能用组合字符；四声有结合形式
        "a": [0x0302, 0x0300],
        "ā": [0x0382, 0x0380],  # 妈 啊
        "á": [0x03A2, 0x03A0],  # 麻 啊
        "ǎ": [0x03C2, 0x03C0],  # 马 啊
        "à": [0x03E2, 0x03E0],  # 骂 啊
        "e": [0x0802, 0x0800],
        "ē": [0x0882, 0x0880],  # 歌 婀
        "é": [0x08A2, 0x08A0],  # 隔 俄
        "ě": [0x08C2, 0x08C0],  # 舸 𫫇
        "è": [0x08E2, 0x08E0],  # 各 恶
        "i": [0x0D00],  # [i]
        "ī": [0x0D80],  # 机
        "í": [0x0DA0],  # 急
        "ǐ": [0x0DC0],  # 挤
        "ì": [0x0DE0],  # 记
        "o": [0x1402, 0x1400],  # 咯、哦
        "ō": [0x1482, 0x1480],  # 此四音是否统合到uo尚有待商榷，暂定为不统合
        "ó": [0x14A2, 0x14A0],
        "ǒ": [0x14C2, 0x14C0],
        "ò": [0x14E2, 0x14E0],
        "u": [0x1000],
        "ū": [0x1080],  # 孤
        "ú": [0x10A0],  # 湖
        "ǔ": [0x10C0],  # 虎
        "ù": [0x10E0],  # 固
        "v": [0x1500],
        "ü": [0x1500],
        "ǖ": [0x1580],  # 屈
        "ǘ": [0x15A0],  # 渠
        "ǚ": [0x15C0],  # 取
        "ǜ": [0x15E0],  # 去
        "b": [0x0003],
        "p": [0x000E],
        "m": [0x000C],  # 也可为韵母m[m̥]，仅见于呒、呣二字
        "f": [0x0006],
        "d": [0x0005],
        "t": [0x0012],
        "n": [0x000D],  # 也可为韵母n[n̥]/[ɰ̃]，仅见于唔、嗯二字
        "l": [0x000B],
        "g": [0x0007],
        "h": [0x0008],
        "j": [0x0009],
        "k": [0x000A],
        "q": [0x000F],
        "x": [0x0014],
        "r": [0x0010],
        "z": [0x0016],
        "c": [0x0004],
        "s": [0x0011],
        "y": [0x0015],  # 伪声母y
        "w": [0x0013],  # 伪声母w
        "1": [0x0080],
        "2": [0x00A0],
        "3": [0x00C0],
        "4": [0x00E0],
        "5": [0x0060],  # 轻声
        "̄": [0x0080],  # ISO 7098:2015 7.1节
        "́": [0x00A0],
        "̌": [0x00C0],
        "̀": [0x00E0],
    }


VALID_SYLLABLES = base64.a85decode(
    b')iaq!J"I;QHQEb!J"I;QJ"@5Pzzz8dGFtDikV37ih[2Dk@UADk@UAzzz6@]UIJ"7/O<F-7;J):h<J):h<zzz(eOc.J):h<<F5b,J):h<J):h<zzz!!3-#Dk@UA:L4V5Dr2-,Dr2-,zzz.1[!jBnlZgBh8j9@6jknA]kYczzz!Wi?%>8%#;&KVJ`4!"A%(ENPVzzz!!Ei5GEi^>FAr5?F3tO!HX@<azzz!X&N(J(G84<aGe,3Zen5IbkY:zzz!<<*"z!<<*"!<<*"!<<*"zzz#U0ZWMEVILMEVILMEVILMEVILzzz+@$J<Cr6hb7*5N1Cs*CjDT`Ulzzz!<N9%I?tNG<F,\\+IGYV:D;Pp*zzzE`)u>IZkEFIbte=Ibte=Ibte=zzzBS$cqCk<<#Cs!=iCl/l+Cs*IlzzzzJ057#J057#J-$,ZJ1:s-zzzzzzzzzzz!u;.B!u)"@\',1EH!u(_8!u(_8zzzJ057#J057#J1:s-J1:s-J1:s-zzzJ0kC!MD>V@!\'UhlMEVILMEVILzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzJ,fiTJ1(g+J057#La!6-J057#zzzzzzzzzzzJfk0rMDu%F#X/[tMEVILMEVILzzz!!3E+J057#!\\+TYJ1:s-Jgq0/zzzJ-Z;YMDbnDJ2Ri:MEVILRQ_/\\zzzJ-H8ZMEVILMCo><ME21HMEVILzzzz!<<*"!<<*"!<<*"!<<*"zzz!XoJ;Jhd`7!\'UekJj\'SCMD>S?zzzzzzzzzzzzzzzzzzz!.YU\\"Fq$`"Fq$`"Fq$`"Fq$`zzzzJ057#!$D[MJ,fuXJ057#zzzJ,fiTLaif5J1:s-J1_61J1_61zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz!!!\'#?i^</?pFbn+9;ND?i^</zzz5QCic+92HC5QCca+9;ND?i^</zzzzCk36"6qRO]BZh%hCs!Ckzzz?iU0,?i^</5QLod?i^</?i^</zzzzzzzzzzzzzzzzzzz6i[i"Ck36"5f"*6Cr$bbCr$bbzzz!!*-$9S3uY6qS*mCr6ndCs*Ilzzzz!!!\'#z!!!\'#!!!\'#zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz!$D7AJ057#!$D[MJ057#J057#zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz!!!9)J057#!$D[MJ05*tJ,fuXzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz!.YU\\"Fq$`"Fq$`"Fq$`"Fq$`zzzz"Fq$`"98u5"Fq$`"Fq$`zzzz"Fq$`"Fq$`"Fq$`"Fq$`zzz"Fq$`"Fq$`"98E%"Fq$`"Fq$`zzz!!!Q1"Fq$`"Fq$`"Fq$`"Fq$`zzz!!!Q1"Fq$`"Fq$`"Fq$`"Fq$`zzzzz!.Y%Lz!!!Q1zzz"98E%"Fq$`"Fq$`"Fq$`"Fq$`zzz!.Y%L"Fq$`"FpIP"Fq$`"Fq$`zzzzzzzzzzzzzzzzzzzz"98u5"98E%"98u5"98u5zzz!.Y%L"Fq$`"Fq$`"Fq$`"Fq$`zzz"98E%"Fq$`"Fq$`"Fq$`"Fq$`zzz!!!Q1"Fq$`!.YU\\z"Fq$`zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz!!iQ)!!iQ)!!iQ)zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz!!E9%!!E9%z!!E9%zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz5QCcazzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz!!iQ)!!iQ)!!iQ)zzzz"Fq$`z"Fq$`"FpIPzzzz"Fq$`"98E%"Fq$`"Fq$`zzzz"Fq$`"98u5"98u5"Fq$`zzzz"Fq$`"98E%"Fq$`"Fq$`zzzzzzzzzzzzzzzzzzz!.Y%L"98u5"FpIP"Fq$`"Fq$`zzzz"98u5"98E%"Fq$`!.YU\\zzzzzzzzzzzzzzzzzzz"Fq$`"Fq$`"Fq$`"Fq$`"MbQKzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz5Q'
)
# 请自行忽略这个雷霆大位图，0人知道为什么我要把位图直接就内联到代码里
CHRMAP = str.maketrans("ˉˊˇˋ", "̄́̌̀")


@cache
def _check_syllable_valid(i: int) -> bool:
    def _check_full(val: int) -> bool:
        off = val - 866
        return (0 <= off < 57095) and bool(VALID_SYLLABLES[(off >> 3)] & (1 << (off & 7)))

    initial = i & 0x801F
    final = i & 0x7F00
    tone = i & 0x00E0

    i_empty = initial in (Initial.unspec, Initial.missing)
    f_empty = final in (Final.unspec, Final.missing)
    t_empty = tone in (Tone.unspec, Tone.missing)

    filled = (not i_empty) + (not f_empty) + (not t_empty)

    if filled <= 1:
        return True
    elif filled == 2:
        if i_empty:
            for x in Initial:
                if x not in (Initial.unspec, Initial.missing) and _check_full(x | final | tone):
                    return True
        elif f_empty:
            for x in Final:
                if x not in (Final.unspec, Final.missing) and _check_full(initial | x | tone):
                    return True
        elif t_empty:
            for x in Tone:
                if x not in (Tone.unspec, Tone.missing) and _check_full(initial | final | x):
                    return True
        return False
    else:
        return _check_full(i)


_recompile = cache(re.compile)


class Parser:
    def __init__(
        self, tokens: dict[str, list[int]] = TOKENS.BASIC | TOKENS.NE | TOKENS.EXT | TOKENS.EXT_NE, sep: str = "' -"
    ):  # 默认行为是解析不存在的token，避免有违直觉。例如wai2之类的，按照规则或者按照直觉都应该是合法音节，但是其并不存在。
        self.TOKENS = tokens
        self.VALID_CHARS = set(chain.from_iterable(tokens.keys()))
        self.VALID_CHARS_RE_DEFAULT = re.compile(f"[{re.escape("".join(self.VALID_CHARS))}]*")
        self.default_sep = sep

    def __check_input_valid(self, s: str, VRE: re.Pattern[str] | str | None = None) -> bool:
        if VRE is None:
            VRE = self.VALID_CHARS_RE_DEFAULT
        return bool(re.fullmatch(VRE, s))

    def __parse(self, s: str, stack: list[Syllable], force_initial: bool = True, force_valid_syllable: bool = False) -> list[Syllable] | None:
        # 我知道DFS还不剪枝会导致这个函数性能极差而且有爆递归风险，但是我无能优化了
        if not s:
            return None if (force_valid_syllable and (not stack[-1].is_valid())) else stack
        valid_heads = [s[:n] for n in range(min(4, len(s)), 0, -1) if s[:n] in self.TOKENS]
        if not valid_heads:
            return None

        dont_try_again: set[Syllable] = set()

        for head in valid_heads:
            next_force_initial = not (
                (head[-1] not in self.TOKENS) or (not any(((r & 0x001F) and (r & 0x001F) != Initial.nul) for r in self.TOKENS[head[-1]]))
            )  # 当前head末位字符不能做声母，那没必要再设置声母回退了。
            # 不回退但是也不能直接continue（那样会导致更短的head先被尝试然后抢了），只能扔到dont_try_again里防止冗余计算
            # 虽然但是很明显这块是把原来的for in [True,False]展开了。嘛虽然更长了但至少缩进少了而且效率或许可能会高一点？

            for role in (Syllable(v) for v in self.TOKENS[head]):
                if stack[-1]._mreject(role, force_initial):
                    continue

                current_stack = stack.copy()
                current_stack[-1] = current_stack[-1].copy()
                current_stack[-1]._merge(role)

                for start_new_syll in [True] if role.tone else [False, True]:  # 声调后必须新开音节
                    if force_valid_syllable and start_new_syll and (not current_stack[-1].is_valid()):
                        continue
                    if not next_force_initial:
                        dont_try_again.add(role)
                    next_new_stack = current_stack.copy()
                    if start_new_syll:
                        next_new_stack.append(Syllable())
                    if ret_stack := self.__parse(
                        s=s[len(head) :],
                        stack=next_new_stack,
                        force_initial=next_force_initial and start_new_syll,
                        force_valid_syllable=force_valid_syllable,
                    ):  # 不新开音节就不检测声母
                        return ret_stack

        for head in valid_heads:
            for role in (Syllable(v) for v in self.TOKENS[head]):
                if role in dont_try_again:
                    continue

                if stack[-1]._mreject(role, force_initial):
                    continue

                current_stack = stack.copy()
                current_stack[-1] = current_stack[-1].copy()
                current_stack[-1]._merge(role)

                for start_new_syll in [True] if role.tone else [False, True]:
                    if force_valid_syllable and start_new_syll and (not current_stack[-1].is_valid()):
                        continue
                    next_new_stack = current_stack.copy()
                    if start_new_syll:
                        next_new_stack.append(Syllable())
                    if ret_stack := self.__parse(s[len(head) :], next_new_stack, False, force_valid_syllable):
                        return ret_stack
        return None

    def parse(
        self, s: str, sep: str | None = None, default_tone_neutral=False, force_valid_syllable=False, missing_as_nul: bool = False
    ) -> list[Syllable]:
        if sep is None:
            sep = self.default_sep

        s = normalize("NFKC", s).lower().translate(CHRMAP)
        if not self.__check_input_valid(s, _recompile(f"[{re.escape(''.join(self.VALID_CHARS|set(sep)))}]*")):
            raise ValueError("无效的输入字符")

        ret = [
            self.__parse(s=seg, stack=[Syllable()], force_initial=False, force_valid_syllable=force_valid_syllable)
            for seg in re.split(f"[{re.escape(sep)}]", s)
            if seg
        ]
        if not all(ret):
            raise ValueError(f"无法解析 {s}")

        ret = cast(list[list[Syllable]], ret)  # 沟槽的pylance不会用all收窄，怒哩

        for r in ret:
            if not r[-1]:
                del r[-1]

        retl = list(chain.from_iterable(ret))
        for syl in retl:
            if default_tone_neutral and syl.tone == Tone.missing:
                syl.tone = Tone.t5
            if missing_as_nul:
                syl.initial = syl.initial or Initial.nul
                syl.final = syl.final or Final.nul
                syl.tone = syl.tone or Tone.nul

        return retl

    @cache
    def parse_single(self, s: str, force_valid_syllable=False) -> Syllable:
        s = normalize("NFKC", s).lower().translate(CHRMAP)
        if not self.__check_input_valid(s):
            raise ValueError("无效的输入字符")

        ret = self.__parse(s=s, stack=[Syllable()], force_initial=False, force_valid_syllable=force_valid_syllable)

        if ret and not ret[-1]:
            del ret[-1]

        if not ret or len(ret) != 1:
            raise ValueError(f"无法解析 {s}")

        rets = ret[0]

        rets.initial = rets.initial or Initial.nul
        rets.final = rets.final or Final.nul
        rets.tone = rets.tone or Tone.t5

        return rets

    def syllables_to_str(self, sylls: Iterable[Syllable], sep: str | None = None) -> str:
        if sep is None:
            sep = self.default_sep[0]

        itf = iter(filter(None, sylls))
        prev = next(itf, None)
        if prev is None:
            return ""
        ret: list[str] = [str(prev)]
        for curr in itf:
            if curr.need_sep(prev):
                ret.append(sep)
            ret.append(str(curr))
            prev = curr
        return "".join(ret)


_inst = Parser()
parse = _inst.parse
parse_single = _inst.parse_single
syllables_to_str = _inst.syllables_to_str


__all__ = ["Final", "Initial", "Parser", "Syllable", "Tone", "parse", "parse_single", "syllables_to_str"]
