import base64  # 解压那坨位图用的（嗯确实是解压因为a85编码比直接写hex还短这何尝不是一种压缩
import re  # 过滤用的
from collections.abc import Iterable
from enum import IntEnum, StrEnum
from functools import cache
from itertools import chain, pairwise
from typing import cast, overload
from unicodedata import normalize
from warnings import warn


class Initial(IntEnum):
    missing = 0
    unspec = 0x0001
    nul = 0x0002
    H = 0x0003  # Hhm Hhng
    R = 0x0004  # Rri
    b = 0x0005
    c = 0x0006
    ch = 0x0007
    d = 0x0008
    f = 0x0009
    g = 0x000A
    h = 0x000B
    j = 0x000C
    k = 0x000D
    l = 0x000E
    m = 0x000F
    n = 0x0010
    p = 0x0011
    q = 0x0012
    r = 0x0013
    s = 0x0014
    sh = 0x0015
    t = 0x0016
    w = 0x0017
    x = 0x0018
    y = 0x0019
    z = 0x001A
    zh = 0x001B
    M = 0x001C  # Mm Mn Mng


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
    hm = 0x0D00
    hng = 0x0E00
    i = 0x0F00  # [i] ji qi xi
    ia = 0x1000
    ian = 0x1100
    iang = 0x1200
    iao = 0x1300
    ieh = 0x1400
    ien = 0x1500
    ii = 0x1600  # [z]/[ɿ] zi ci si
    ieng = 0x1700
    iong = 0x1800
    iou = 0x1900
    ng = 0x1A00  # [ŋ̊]
    o = 0x1B00
    ong = 0x1C00
    ou = 0x1D00
    ri = 0x1E00  # [ʅ] zhi chi shi [ʐ]/[ʅ] ri
    u = 0x1F00
    ua = 0x2000
    uai = 0x2100
    uan = 0x2200
    uang = 0x2300
    uei = 0x2400
    uen = 0x2500
    ueng = 0x2600
    uo = 0x2700
    v = 0x2800
    van = 0x2900
    veh = 0x2A00
    ven = 0x2B00
    m = 0x2C00
    n = 0x2D00
    eh = 0x2E00  # ê


class Tone(IntEnum):
    missing = 0
    unspec = 0x0020
    nul = 0x0040
    t1 = 0x0060
    t2 = 0x0080
    t3 = 0x00A0
    t4 = 0x00C0
    t5 = 0x00E0


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
            if i & ~0x3FFF:
                raise ValueError("int中存在无效的位。使用整数初始化时仅接受高2位为0的uint16。")
            try:
                self.initial = Initial(i & 0x001F)
                self.final = Final(i & 0x3F00)
                self.tone = Tone(i & 0x00E0)
            except ValueError:
                raise ValueError("无效的uint16。")

    def __int__(self):
        return self.initial | self.final | self.tone

    def __repr__(self):
        return f"<{self.initial.name}·{self.final.name}·{self.tone.name.removeprefix("t")}{"" if self.is_valid() else "(N/E)"}>"

    @cache
    def to_str(self, tone_style: ToneStyle = ToneStyle.ABOVE, NO_INCOMPAT_WARNING: bool = False) -> str:
        match self.initial:
            case Initial.missing | Initial.unspec | Initial.nul:
                initial_str = ""
            case Initial.R:
                initial_str = "r"
            case Initial.H:
                initial_str = "h"
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

    __hash__ = __int__

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


TOKENS = {
    "iang": [0x1200],
    "iāng": [0x1260],  # 江
    "iáng": [0x1280],  # 凉
    "iǎng": [0x12A0],  # 抢
    "iàng": [0x12C0],  # 呛
    "iong": [0x1800],
    "iōng": [0x1860],  # 凶
    "ióng": [0x1880],  # 穷
    "iǒng": [0x18A0],  # 涌
    "iòng": [0x18C0],  # 用
    "uang": [0x2300],
    "uāng": [0x2360],  # 光
    "uáng": [0x2380],  # 狂
    "uǎng": [0x23A0],  # 广
    "uàng": [0x23C0],  # 旷
    "ueng": [0x2600],
    "uēng": [0x2660],  # 翁
    "uéng": [0x2680],  # 不存在，然而拒绝解析有违直觉，因而保留，下同
    "uěng": [0x26A0],  # 塕
    "uèng": [0x26C0],  # 瓮
    "juan": [0x290C],
    "juān": [0x296C],  # 捐
    "juán": [0x298C],  # 不存在
    "juǎn": [0x29AC],  # 卷
    "juàn": [0x29CC],  # 倦
    "quan": [0x2912],
    "quān": [0x2972],  # 圈
    "quán": [0x2992],  # 全
    "quǎn": [0x29B2],  # 犬
    "quàn": [0x29D2],  # 劝
    "xuan": [0x2918],
    "xuān": [0x2978],  # 宣
    "xuán": [0x2998],  # 悬
    "xuǎn": [0x29B8],  # 选
    "xuàn": [0x29D8],  # 炫
    "yang": [0x1219],
    "yāng": [0x1279],  # 央
    "yáng": [0x1299],  # 阳
    "yǎng": [0x12B9],  # 养
    "yàng": [0x12D9],  # 样
    "ying": [0x1719],
    "yīng": [0x1779],  # 英
    "yíng": [0x1799],  # 赢
    "yǐng": [0x17B9],  # 影
    "yìng": [0x17D9],  # 映
    "yong": [0x1819],
    "yōng": [0x1879],  # 拥
    "yóng": [0x1899],  # 颙
    "yǒng": [0x18B9],  # 泳
    "yòng": [0x18D9],  # 用
    "wang": [0x2317],
    "wāng": [0x2377],  # 汪
    "wáng": [0x2397],  # 王
    "wǎng": [0x23B7],  # 网
    "wàng": [0x23D7],  # 忘
    "weng": [0x2617],
    "wēng": [0x2677],  # 翁
    "wéng": [0x2697],  # 不存在
    "wěng": [0x26B7],  # 塕
    "wèng": [0x26D7],  # 瓮
    "yuan": [0x2919],
    "yuān": [0x2979],  # 冤
    "yuán": [0x2999],  # 圆
    "yuǎn": [0x29B9],  # 远
    "yuàn": [0x29D9],  # 怨
    "ang": [0x0602, 0x0600],
    "āng": [0x0662, 0x0660],  # 刚 肮
    "áng": [0x0682, 0x0680],  # 扛 昂
    "ǎng": [0x06A2, 0x06A0],  # 莽 䇦
    "àng": [0x06C2, 0x06C0],  # 抗 盎
    "eng": [0x0B02, 0x0B00],
    "ēng": [0x0B62, 0x0B60],  # 庚 鞥
    "éng": [0x0B82, 0x0B80],  # 横 不存在
    "ěng": [0x0BA2, 0x0BA0],  # 冷 不存在
    "èng": [0x0BC2, 0x0BC0],  # 赠 不存在
    "ian": [0x1100],
    "iān": [0x1160],  # 先
    "ián": [0x1180],  # 咸
    "iǎn": [0x11A0],  # 显
    "iàn": [0x11C0],  # 现
    "iao": [0x1300],
    "iāo": [0x1360],  # 交
    "iáo": [0x1380],  # 嚼
    "iǎo": [0x13A0],  # 缴
    "iào": [0x13C0],  # 叫
    "ing": [0x1700],
    "īng": [0x1760],  # 星
    "íng": [0x1780],  # 形
    "ǐng": [0x17A0],  # 醒
    "ìng": [0x17C0],  # 幸
    "ong": [0x1C00],
    "ōng": [0x1C60],  # 东
    "óng": [0x1C80],  # 龙
    "ǒng": [0x1CA0],  # 拢
    "òng": [0x1CC0],  # 冻
    "uai": [0x2100],
    "uāi": [0x2160],  # 乖
    "uái": [0x2180],  # 淮
    "uǎi": [0x21A0],  # 拐
    "uài": [0x21C0],  # 坏
    "uan": [0x2200],
    "uān": [0x2260],  # 欢
    "uán": [0x2280],  # 环
    "uǎn": [0x22A0],  # 缓
    "uàn": [0x22C0],  # 换
    "van": [0x2900],
    "vān": [0x2960],  # 捐
    "ván": [0x2980],  # 全
    "vǎn": [0x29A0],  # 犬
    "vàn": [0x29C0],  # 倦
    "üan": [0x2900],
    "üān": [0x2960],
    "üán": [0x2980],
    "üǎn": [0x29A0],
    "üàn": [0x29C0],
    "hng": [0x0EE3],  # 哼
    "zhi": [0x1E1B],  # [ʅ]
    "zhī": [0x1E7B],  # 支
    "zhí": [0x1E9B],  # 直
    "zhǐ": [0x1EBB],  # 纸
    "zhì": [0x1EDB],  # 至
    "chi": [0x1E07],  # [ʅ]
    "chī": [0x1E67],  # 吃
    "chí": [0x1E87],  # 持
    "chǐ": [0x1EA7],  # 尺
    "chì": [0x1EC7],  # 赤
    "shi": [0x1E15],  # [ʅ]
    "shī": [0x1E75],  # 诗
    "shí": [0x1E95],  # 石
    "shǐ": [0x1EB5],  # 史
    "shì": [0x1ED5],  # 事
    "jue": [0x2A0C],
    "juē": [0x2A6C],  # 撅
    "jué": [0x2A8C],  # 绝
    "juě": [0x2AAC],  # 蹶
    "juè": [0x2ACC],  # 倔
    "que": [0x2A12],
    "quē": [0x2A72],  # 缺
    "qué": [0x2A92],  # 瘸
    "quě": [0x2AB2],  # 不存在
    "què": [0x2AD2],  # 雀
    "xue": [0x2A18],
    "xuē": [0x2A78],  # 薛
    "xué": [0x2A98],  # 学
    "xuě": [0x2AB8],  # 雪
    "xuè": [0x2AD8],  # 谑
    "jun": [0x2B0C],
    "jūn": [0x2B6C],  # 君
    "jún": [0x2B8C],  # 不存在
    "jǔn": [0x2BAC],  # 𢉦（RD广军）
    "jùn": [0x2BCC],  # 郡
    "qun": [0x2B12],
    "qūn": [0x2B72],  # 逡
    "qún": [0x2B92],  # 群
    "qǔn": [0x2BB2],  # 䊎
    "qùn": [0x2BD2],  # 不存在
    "xun": [0x2B18],
    "xūn": [0x2B78],  # 勋
    "xún": [0x2B98],  # 寻
    "xǔn": [0x2BB8],  # 不存在
    "xùn": [0x2BD8],  # 巽
    "yao": [0x1319],
    "yāo": [0x1379],  # 邀
    "yáo": [0x1399],  # 摇
    "yǎo": [0x13B9],  # 咬
    "yào": [0x13D9],  # 药
    "you": [0x1919],
    "yōu": [0x1979],  # 优
    "yóu": [0x1999],  # 游
    "yǒu": [0x19B9],  # 有
    "yòu": [0x19D9],  # 右
    "yan": [0x1119],
    "yān": [0x1179],  # 烟
    "yán": [0x1199],  # 盐
    "yǎn": [0x11B9],  # 眼
    "yàn": [0x11D9],  # 验
    "yin": [0x1519],
    "yīn": [0x1579],  # 阴
    "yín": [0x1599],  # 银
    "yǐn": [0x15B9],  # 饮
    "yìn": [0x15D9],  # 印
    "wai": [0x2117],
    "wāi": [0x2177],  # 歪
    "wái": [0x2197],  # 不存在
    "wǎi": [0x21B7],  # 𨂿
    "wài": [0x21D7],  # 外
    "wei": [0x2417],
    "wēi": [0x2477],  # 威
    "wéi": [0x2497],  # 维
    "wěi": [0x24B7],  # 尾
    "wèi": [0x24D7],  # 味
    "wan": [0x2217],
    "wān": [0x2277],  # 弯
    "wán": [0x2297],  # 完
    "wǎn": [0x22B7],  # 碗
    "wàn": [0x22D7],  # 万
    "wen": [0x2517],
    "wēn": [0x2577],  # 温
    "wén": [0x2597],  # 文
    "wěn": [0x25B7],  # 稳
    "wèn": [0x25D7],  # 问
    "yue": [0x2A19],
    "yuē": [0x2A79],  # 约
    "yué": [0x2A99],  # 块（音yué义不详，但字统有记载因而算进来了）
    "yuě": [0x2AB9],  # 哕
    "yuè": [0x2AD9],  # 月
    "yun": [0x2B19],
    "yūn": [0x2B79],  # 晕
    "yún": [0x2B99],  # 云
    "yǔn": [0x2BB9],  # 允
    "yùn": [0x2BD9],  # 韵
    "zi": [0x161A],
    "zī": [0x167A],  # 兹
    "zí": [0x169A],  # 不存在
    "zǐ": [0x16BA],  # 紫
    "zì": [0x16DA],  # 字
    "ci": [0x1606],
    "cī": [0x1666],  # 呲
    "cí": [0x1686],  # 词
    "cǐ": [0x16A6],  # 此
    "cì": [0x16C6],  # 次
    "si": [0x1614],
    "sī": [0x1674],  # 丝
    "sí": [0x1694],  # 不存在
    "sǐ": [0x16B4],  # 死
    "sì": [0x16D4],  # 四
    "ri": [0x1E04, 0x1E00],  # [ʐ]/[ʅ]
    "rī": [0x1E64, 0x1E60],  # 痴 不存在
    "rí": [0x1E84, 0x1E80],  # 迟 不存在
    "rǐ": [0x1EA4, 0x1EA0],  # 齿 不存在
    "rì": [0x1EC4, 0x1EC0],  # 斥 日
    "hm": [0x0DE3],
    "ai": [0x0402, 0x0400],
    "āi": [0x0462, 0x0460],  # 该 挨
    "ái": [0x0482, 0x0480],  # 孩 皑
    "ǎi": [0x04A2, 0x04A0],  # 改 矮
    "ài": [0x04C2, 0x04C0],  # 骇 爱
    "an": [0x0502, 0x0500],
    "ān": [0x0562, 0x0560],  # 潘 安
    "án": [0x0582, 0x0580],  # 盘 儑
    "ǎn": [0x05A2, 0x05A0],  # 懒 俺
    "àn": [0x05C2, 0x05C0],  # 烂 暗
    "ao": [0x0702, 0x0700],
    "āo": [0x0762, 0x0760],  # 高 凹
    "áo": [0x0782, 0x0780],  # 豪 熬
    "ǎo": [0x07A2, 0x07A0],  # 好 拗
    "ào": [0x07C2, 0x07C0],  # 告 傲
    "ei": [0x0902, 0x0900],
    "ēi": [0x0962, 0x0960],  # 飞 不存在（欸等字在eh）
    "éi": [0x0982, 0x0980],  # 肥 不存在
    "ěi": [0x09A2, 0x09A0],  # 匪 不存在
    "èi": [0x09C2, 0x09C0],  # 费 不存在
    "en": [0x0A02, 0x0A00],
    "ēn": [0x0A62, 0x0A60],  # 奔 恩
    "én": [0x0A82, 0x0A80],  # 盆 不存在
    "ěn": [0x0AA2, 0x0AA0],  # 本 不存在
    "èn": [0x0AC2, 0x0AC0],  # 笨 摁
    "er": [0x0C02, 0x0C00],
    "ēr": [0x0C62, 0x0C60],  # 不存在 不存在
    "ér": [0x0C82, 0x0C80],  # 不存在 儿
    "ěr": [0x0CA2, 0x0CA0],  # 不存在 尔
    "èr": [0x0CC2, 0x0CC0],  # 不存在 佴
    "ia": [0x1000],
    "iā": [0x1060],  # 家
    "iá": [0x1080],  # 夹
    "iǎ": [0x10A0],  # 贾
    "ià": [0x10C0],  # 架
    "ie": [0x1400],
    "iē": [0x1460],  # 街
    "ié": [0x1480],  # 截
    "iě": [0x14A0],  # 解
    "iè": [0x14C0],  # 借
    "ii": [0x1600],  # [z]/[ɿ]
    "in": [0x1500],
    "īn": [0x1560],  # 侵
    "ín": [0x1580],  # 琴
    "ǐn": [0x15A0],  # 寝
    "ìn": [0x15C0],  # 沁
    "iu": [0x1900],
    "iū": [0x1960],  # 秋
    "iú": [0x1980],  # 求
    "iǔ": [0x19A0],  # 朽
    "iù": [0x19C0],  # 锈
    "ng": [0x1A1C],  # [ŋ̊]，仅见于唔、嗯二字
    "n̄g": [0x1A7C],  # 然而还是为了不违反直觉，在这插一个n1g
    "ńg": [0x1A9C],
    "ňg": [0x1ABC],
    "ǹg": [0x1ADC],  # n+macron没有单字符表示，且n1g不存在，
    "ou": [0x1D02, 0x1D00],
    "ōu": [0x1D62, 0x1D60],  # 沟 欧
    "óu": [0x1D82, 0x1D80],  # 楼 吽
    "ǒu": [0x1DA2, 0x1DA0],  # 篓 偶
    "òu": [0x1DC2, 0x1DC0],  # 够 沤
    "ua": [0x2000],
    "uā": [0x2060],  # 花
    "uá": [0x2080],  # 滑
    "uǎ": [0x20A0],  # 垮
    "uà": [0x20C0],  # 跨
    "ui": [0x2400],
    "uī": [0x2460],  # 灰
    "uí": [0x2480],  # 回
    "uǐ": [0x24A0],  # 毁
    "uì": [0x24C0],  # 会
    "un": [0x2500],
    "ūn": [0x2560],  # 昆
    "ún": [0x2580],  # 仑
    "ǔn": [0x25A0],  # 捆
    "ùn": [0x25C0],  # 论
    "uo": [0x2700],
    "uō": [0x2760],  # 锅
    "uó": [0x2780],  # 活
    "uǒ": [0x27A0],  # 火
    "uò": [0x27C0],  # 过
    "ve": [0x2A00],
    "vē": [0x2A60],  # 薛
    "vé": [0x2A80],  # 学
    "vě": [0x2AA0],  # 雪
    "vè": [0x2AC0],  # 谑
    "üe": [0x2A00],
    "üē": [0x2A60],
    "üé": [0x2A80],
    "üě": [0x2AA0],
    "üè": [0x2AC0],
    "vn": [0x2B00],
    "ün": [0x2B00],
    "ǖn": [0x2B60],  # 逡
    "ǘn": [0x2B80],  # 群
    "ǚn": [0x2BA0],  # 允
    "ǜn": [0x2BC0],  # 孕
    "ju": [0x280C],
    "jū": [0x286C],  # 居
    "jú": [0x288C],  # 局
    "jǔ": [0x28AC],  # 举
    "jù": [0x28CC],  # 句
    "qu": [0x2812],
    "qū": [0x2872],  # 区
    "qú": [0x2892],  # 渠
    "qǔ": [0x28B2],  # 取
    "qù": [0x28D2],  # 去
    "xu": [0x2818],
    "xū": [0x2878],  # 需
    "xú": [0x2898],  # 徐
    "xǔ": [0x28B8],  # 许
    "xù": [0x28D8],  # 序
    "yi": [0x0F19],
    "yī": [0x0F79],  # 一
    "yí": [0x0F99],  # 疑
    "yǐ": [0x0FB9],  # 以
    "yì": [0x0FD9],  # 忆
    "ya": [0x1019],
    "yā": [0x1079],  # 压
    "yá": [0x1099],  # 牙
    "yǎ": [0x10B9],  # 雅
    "yà": [0x10D9],  # 亚
    "ye": [0x1419],
    "yē": [0x1479],  # 噎
    "yé": [0x1499],  # 爷
    "yě": [0x14B9],  # 野
    "yè": [0x14D9],  # 页
    "wu": [0x1F17],
    "wū": [0x1F77],  # 屋
    "wú": [0x1F97],  # 无
    "wǔ": [0x1FB7],  # 舞
    "wù": [0x1FD7],  # 物
    "wa": [0x2017],
    "wā": [0x2077],  # 洼
    "wá": [0x2097],  # 娃
    "wǎ": [0x20B7],  # 瓦
    "wà": [0x20D7],  # 袜
    "wo": [0x2717],
    "wō": [0x2777],  # 窝
    "wó": [0x2797],  # 不存在
    "wǒ": [0x27B7],  # 我
    "wò": [0x27D7],  # 卧
    "yu": [0x2819],
    "yū": [0x2879],  # 淤
    "yú": [0x2899],  # 于
    "yǔ": [0x28B9],  # 与
    "yù": [0x28D9],  # 玉
    "zh": [0x001B],
    "ch": [0x0007],
    "sh": [0x0015],
    "ê": [0x2E00],
    "ê̄": [0x2E60],
    "ế": [0x2E80],
    "ê̌": [0x2EA0],
    "ề": [0x2EC0],  # U+1EC1 一、二、三声没有结合形式，只能用组合字符；四声有结合形式
    "a": [0x0302, 0x0300],
    "ā": [0x0362, 0x0360],  # 妈 啊
    "á": [0x0382, 0x0380],  # 麻 啊
    "ǎ": [0x03A2, 0x03A0],  # 马 啊
    "à": [0x03C2, 0x03C0],  # 骂 啊
    "e": [0x0802, 0x0800],
    "ē": [0x0862, 0x0860],  # 歌 婀
    "é": [0x0882, 0x0880],  # 隔 俄
    "ě": [0x08A2, 0x08A0],  # 舸 𫫇
    "è": [0x08C2, 0x08C0],  # 各 恶
    "i": [0x0F00],  # [i]
    "ī": [0x0F60],  # 机
    "í": [0x0F80],  # 急
    "ǐ": [0x0FA0],  # 挤
    "ì": [0x0FC0],  # 记
    "o": [0x1B02, 0x1B00],  # 咯、哦
    "ō": [0x1B62, 0x1B60],  # 此四音是否统合到uo尚有待商榷，暂定为不统合
    "ó": [0x1B82, 0x1B80],
    "ǒ": [0x1BA2, 0x1BA0],
    "ò": [0x1BC2, 0x1BC0],
    "u": [0x1F00],
    "ū": [0x1F60],  # 孤
    "ú": [0x1F80],  # 湖
    "ǔ": [0x1FA0],  # 虎
    "ù": [0x1FC0],  # 固
    "v": [0x2800],
    "ü": [0x2800],
    "ǖ": [0x2860],  # 屈
    "ǘ": [0x2880],  # 渠
    "ǚ": [0x28A0],  # 取
    "ǜ": [0x28C0],  # 去
    "b": [0x0005],
    "p": [0x0011],
    "m": [0x000F],  # 也可为韵母m[m̥]，仅见于呒、呣二字
    "f": [0x0009],
    "d": [0x0008],
    "t": [0x0016],
    "n": [0x0010],  # 也可为韵母n[n̥]/[ɰ̃]，仅见于唔、嗯二字
    "l": [0x000E],
    "g": [0x000A],
    "h": [0x000B],
    "j": [0x000C],
    "k": [0x000D],
    "q": [0x0012],
    "x": [0x0018],
    "r": [0x0013],
    "z": [0x001A],
    "c": [0x0006],
    "s": [0x0014],
    "y": [0x0019],  # 伪声母y
    "w": [0x0017],  # 伪声母w
    "1": [0x0060],
    "2": [0x0080],
    "3": [0x00A0],
    "4": [0x00C0],
    "5": [0x00E0],  # 轻声
    "̄": [0x0060],  # ISO 7098:2015 7.1节
    "́": [0x0080],
    "̌": [0x00A0],
    "̀": [0x00C0],
    # 以下按需启用
    # "?": [0x0001, 0x0100, 0x0020],
    # ".": [0x0121],  # 通配
    # "*": [0x0001, 0x0100],  # 声母韵母通配
    # "0": [0x0020],  # 声调通配
    # "/": [0x0002],  # 零声母
    # "&": [0x0004],  # 伪声母R
    "n̄": [0x2D7C],  # 多字符，不存在
    "ń": [0x2D9C],
    "ň": [0x2DBC],
    "ǹ": [0x2DDC],
    "n1": [0x2D7C],  # 不存在
    "n2": [0x2D9C],
    "n3": [0x2DBC],
    "n4": [0x2DDC],
    "m̄": [0x2C7C],  # 多字符，不存在
    "ḿ": [0x2C9C],  # 只有ḿ有单字符表示
    "m̌": [0x2CBC],  # 多字符，不存在
    "m̀": [0x2CDC],  # 多字符
    "m1": [0x2C7C],  # 不存在
    "m2": [0x2C9C],
    "m3": [0x2CBC],  # 不存在
    "m4": [0x2CDC],
}
VALID_CHARS = set(chain.from_iterable(TOKENS.keys()))
VALID_CHARS_RE_DEFAULT = re.compile(f"[{re.escape("".join(VALID_CHARS))}]*")
VALID_SYLLABLES = base64.a85decode(
    b'q>2-6l15_oq>2-6q=>R.a`&4$zzzH&EXE3V!^_H2AQ`H2AQ`84!jfzzzq<K"&Z18e8q>238q>238#Qb,0zzzq>238Z2,(5q>238q>238i(sa^zzzH2AQ`H1DjUH2AWbH2AWb!"],3zzz@64l!@7pq0+U\\VY0j>\\$6$X"DzzzadNb@Ja`pGamf?2RIC1X#S6t9zzz\\Z6,@YbMO,WJ_5gl2(ei+<UXbzzzq7@[M\\FLO<kkPJdq"#O/#Tsrazzzz!<<*"!<<*"!<<*"!<<*"zzzzzzz!WW3#zzzzzzz!WW3#zzz8G(:08G(:08G(:08G(:05S1a3zzz!(=X\'!!L+<5SV$7!!L+<!!IfPzzz8ArmU5k*/$8G(:08G(:0#R!Enzzz!!L+<#Z/>;!*$c7#ZSV?!"aY\\zzz8@6bE!4:,R8G(:0aRmj[!(9W`zzz8G(:089E5Z8CZ#e8G(:0!&T3+zzz#aE.*!:[f)#kYq58<gpj#[kFJzzz&-)h6&-)h6&-)h6&-)h6!!!-&zzz8<hL%!:\\A98G(:08G(:0!&QtAzzz!!L+<!!\'h8!!L(;!!L+<zzzz5ZGQ"!*$c7!-H$W!-H$W!!IfPzzzz!!!!%!!!!%!!!!%zzzz$(ueKM4ahK$(q7u$(q7u$*\\p[zzzE#TPp0N&YdE*F([GZtpc!!*-%zzzn[fbCZ18e7nbX@0EVgdZ!>$(Jzzz+92ZK+92ZK+92ZK,QJ)O+92ZKzzzpmXAJq"m5Wq"m5Wq"m5WW08t:zzz+:BS!!!=DF+:0Ft+:BRt!!",Azzz+9<kl+9DNC+:0Ft+:BS!!!48CzzzE!nc10N\'Y-?s>MkE)Sq&zzzz+:BS!+:94k+:BS!+:BS!!!<3$zzzE!nK)+:::5E!ni3E!ni3&-=6\\zzzE#LP80N\'Y,E#UtC:g6*c!!j\\Izzz!!",Az!!",A!!",AzzzzE"b>9:fAD;:fB1OE*GL.5SF8&zzz!!L+<!*$c7!*$c7!*$c7!!L+<zzz!!L+<!!\'h8!!L+<!!L+<!!!$"zzz!!L+<!!L+<!#33K!*$c7zzzz!!L+<!!\'h8!!IiQ!!L(;!!%NLzzz!!!!%!!!!%z!!!!%zzzzz!!!!%!!!!%!!!!%zzzz!<<*"!<<*"!<<*"!<'
)
# 请自行忽略这个雷霆大位图，0人知道为什么我要把位图直接就内联到代码里
CHRMAP = str.maketrans("ˉˊˇˋ", "̄́̌̀")


@cache
def _check_syllable_valid(i: int) -> bool:
    def _check_full(val: int) -> bool:
        off = val - 866
        return (0 <= off < 11105) and bool(VALID_SYLLABLES[(off >> 3)] & (1 << (off & 7)))

    initial = i & 0x001F
    final = i & 0x3F00
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


def _check_input_valid(s: str, VRE: re.Pattern[str] | str = VALID_CHARS_RE_DEFAULT) -> bool:
    return bool(re.fullmatch(VRE, s))


def __parse(s: str, stack: list[Syllable], force_initial: bool = True, force_valid_syllable: bool = False) -> list[Syllable] | None:
    # 我知道DFS还不剪枝会导致这个函数性能极差而且有爆递归风险，但是我无能优化了
    if not s:
        return stack
    valid_heads = [s[:n] for n in range(min(4, len(s)), 0, -1) if s[:n] in TOKENS]
    if not valid_heads:
        return None

    dont_try_again: set[Syllable] = set()

    for head in valid_heads:
        next_force_initial = not (
            (head[-1] not in TOKENS) or (not any(((r & 0x001F) and (r & 0x001F) != Initial.nul) for r in TOKENS[head[-1]]))
        )  # 当前head末位字符不能做声母，那没必要再设置声母回退了。
        # 不回退但是也不能直接continue（那样会导致更短的head先被尝试然后抢了），只能扔到dont_try_again里防止冗余计算
        # 虽然但是很明显这块是把原来的for in [True,False]展开了。嘛虽然更长了但至少缩进少了而且效率或许可能会高一点？

        for role in (Syllable(v) for v in TOKENS[head]):
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
                if ret_stack := __parse(
                    s=s[len(head) :],
                    stack=next_new_stack,
                    force_initial=next_force_initial and start_new_syll,
                    force_valid_syllable=force_valid_syllable,
                ):  # 不新开音节就不检测声母
                    return ret_stack

    for head in valid_heads:
        for role in (Syllable(v) for v in TOKENS[head]):
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
                if ret_stack := __parse(s[len(head) :], next_new_stack, False, force_valid_syllable):
                    return ret_stack
    return None


_recompile = cache(re.compile)


def parse(s: str, sep: str = "' -", default_tone_neutral=False, force_valid_syllable=False, missing_as_nul: bool = False) -> list[Syllable]:
    s = normalize("NFKC", s).lower().translate(CHRMAP)
    if not _check_input_valid(s, _recompile(f"[{re.escape("".join(VALID_CHARS|set(sep)))}]*")):
        raise ValueError("无效的输入字符")

    ret = [
        __parse(s=seg, stack=[Syllable()], force_initial=False, force_valid_syllable=force_valid_syllable)
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
def parse_single(s: str, force_valid_syllable=False) -> Syllable:
    s = normalize("NFKC", s).lower().translate(CHRMAP)
    if not _check_input_valid(s):
        raise ValueError("无效的输入字符")

    ret = __parse(s=s, stack=[Syllable()], force_initial=False, force_valid_syllable=force_valid_syllable)

    if ret and not ret[-1]:
        del ret[-1]

    if not ret or len(ret) != 1:
        raise ValueError(f"无法解析 {s}")

    rets = ret[0]

    rets.initial = rets.initial or Initial.nul
    rets.final = rets.final or Final.nul
    rets.tone = rets.tone or Tone.t5

    return rets


def syllables_to_str(sylls: Iterable[Syllable], sep: str = "'") -> str:
    ret = []
    for prev, curr in pairwise(filter(None, sylls)):
        if not ret:
            ret.append(str(prev))
        if curr.need_sep(prev):
            ret.append(sep)
        ret.append(str(curr))
    return "".join(ret)


__all__ = ["Initial", "Final", "Tone", "Syllable", "parse_single", "syllables_to_str", "parse"]
