[![PyPI - Version](https://img.shields.io/pypi/v/pinyinparser)](https://pypi.org/project/pinyinparser/)
[![Recommended - Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-forestgreen.svg)](https://www.python.org/downloads/)
[![Modded - Python 3.10+](https://img.shields.io/badge/python-3.10+-darkgoldenrod.svg)](https://www.python.org/downloads/)

# 这是一个拼音解析器。
更准确地说，针对符合**汉语拼音方案**的**汉语拼音**的解析器；

并可以扩展预设的**音位表示补充方案**或用户自定义的**其他类拼音方案**。

## 能做什么？

- 解析拼音，尤其适用于索引、高压存储、UGC查询，或者任何你对输入是一坨怎样的东西完全没信心的时候。
    - **如果你的输入已经非常整洁标准，那或许有其他更好的解析库适合你，例如[Pinyin Tokenizer](https://github.com/shibing624/pinyin-tokenizer)。**
    - 本库保证输出**标准化、规范化**；但是对于不符合设计意图的输入，**强行标准规范化可能导致奇怪的结果。**
        - 例如，压根不是拼音的`chinese`强行解析会变成`[<ch·ri·missing>,<n·e·missing>,<s·e·missing>]`
- 检验一个拼音是不是存在。
- 查拼音，尤其是查谐音/双声叠韵 etc.
- 把拼音解析成按音位的声韵调格式，便于存储与查询。
    - 每个音节仅占用**2B**(16b)，而只是“存储音节”的**理论最小值**就是**2B**(11b)。
    - 因此使用本库可以获取理论极限的内存效率以及与之相匹配的性能（不bitpack的情况下）。
- 也可以转换拼音的格式/风格（例如`guang1` `gua1ng` `guāng`）。
    - **但这不是主要功能。如果你的主要需求是这个，那你应该去看[kittell的同名库](https://github.com/kittell/pinyinparser)或是[pypinyin](https://github.com/mozillazg/python-pinyin)。**
- 拼音规范化/格式化。
  - 默认行为**不完全严格符合汉语拼音正词法**，而是使用了更保守的方案（在主观上可能混淆的时候额外断词）。
- _或者其他任何需要对 **“拼音”本身** 进行处理的场合_。

#### 以及……

- 将本库称作`PYthon-PinYinParser`，简称`PYPYP`（读作`pʰaɪpʰip̚`）。

## 不能做什么？

- 从汉字解析出来拼音。
    - **如果你的需求是汉字加拼音，那你应该去看[pypinyin](https://github.com/mozillazg/python-pinyin)。**
- 模糊解析。
- 所见即所得的解析。
    - 本解析器使用的是**音位**表示，解析结果很可能会**与你想象的**不同。
        - 例：`chi`→`<ch·ri·missing>`而不是`<ch·i·missing>`。
    - 如果你需要所见即所得，那么你应当自己处理转换，将音节转换为更“符合直觉”的表示。
- 通配y w 零声母。
    - 本库**将y w 零声母视为三个独立的声母，没有变体关系。** ~~其实是因为16bit塞不下。~~
- 支持儿化音（`-r`，如`huar`）。
    - **本库只能将`-r`尾解析为一个`<r·missing·missing>`。**
        - 一来**本库设计为处理未必完整的拼音**而不是保证完整的拼音（因而无法推断是-r尾还是r首字母），二来~~还是因为16bit塞不下。~~

## 怎么使用？

你应当询问AI。我的语言能力并不足以支持我进行非常详细的表述。

~~当然如果你懒得用AI的话，往下一点就可以看到我帮你问的……~~

## 支持什么版本？

3.12+，推荐3.14；3.10及以上需要删一些类型注解之类的东西再用；3.10以下不考虑支持，要用自己（或让AI）去改。

---

**以上内容** [![IIIA-0](https://img.shields.io/badge/IIIA-0-FAB689)](https://github.com/ErSanSan233/IIIA)

# AI写的readme

**以下内容** [![IIIA-5](https://img.shields.io/badge/IIIA-5-4D6BFE)](https://github.com/ErSanSan233/IIIA) **由DeepSeek生成**，有修改事实性错误

# pinyinparser

> 一个面向**汉语拼音方案**的拼音解析器，专注于音位级别的解析、存储与查询。  
> 支持将拼音字符串转换为紧凑的数值表示（每个音节仅占 2B），并提供了灵活的解析与格式化能力。

---

## 特性

- **音位级解析** – 严格按照汉语拼音方案（声母、韵母、声调）进行解析，而非“所见即所得”的拼写转换。  
- **紧凑存储** – 每个音节被编码为 `uint16`（2 字节），达到理论极限的内存效率，便于索引、高压存储和 UGC 查询。  
- **标准化输出** – 保证输出格式统一规范；支持转换为带声调符号、数字标调、或纯字母形式。  
- **灵活的分词** – 可自动处理音节边界，也可自定义分隔符，支持不完整输入（如缺失声母或声调）。  
- **扩展性** – 内置丰富的预定义音素表，并可扩展用户自定义的拼音方案。  

---

## 安装

```bash
pip install pinyinparser
```

Python 版本要求 **3.12+**（推荐 3.14）。若需在 3.10 / 3.11 上使用，可自行移除部分类型注解。

---

## 快速开始

```python
from pinyinparser import parse, parse_single, Syllable, Tone

# 解析单个音节
syl = parse_single("guang1")
print(syl)  # <g·uang·1>
print(syl.to_str())  # guāng
print(syl.to_str(ToneStyle.AFTER))  # guang1

# 解析一串拼音（自动处理分隔符）
sylls = parse("zhong1 guo2 ren2 min2")
for s in sylls:
    print(s)  # 每个音节对象

# 将音节列表还原为字符串（自动插入分隔符）
from pinyinparser import syllables_to_str

print(syllables_to_str(sylls, sep=" "))  # 'zhōngguórénmín'
```

---

## 核心概念

### 1. 音节的内部表示

每个音节用 `Syllable` 对象表示，包含三个枚举字段：

- `Initial` – 声母（包括零声母 `nul`、伪声母 `y/w`、特殊声母 `H/M/N/R` 等）
- `Final` – 韵母（包括 `ii`、`ri` 等特殊变体）
- `Tone` – 声调（`t1` ~ `t5`，`missing`/`unspec`/`nul` 用于不完整音节）

这些字段组合成 **一个 `uint16` 整数**（仅使用 16 位），可通过 `int(syl)` 或 `syl.__index__()` 获取。

### 2. 解析策略

- 解析器基于 **最长匹配** 的 DFS 回溯，优先尝试更长的 token（如 `zh` 优先于 `z`）。
- 支持不完整输入（如 `"ch"` 可解析为声母 `ch`，韵母和声调缺失）。
- 默认行为：**声调后自动切分音节**，其他情况下按规则合并。
- 对于明显非拼音的字符串（如 `"chinese"`），解析器会尽力拆分成音素片段（但结果可能无意义）。

### 3. 有效性校验

内置了 **所有合法音节（含声调）** 的位图，可通过 `syl.is_valid()` 快速判断该音节是否存在。  
解析时可通过 `force_valid_syllable=True` 强制只输出合法音节（若无法解析则抛出异常）。

---

## API 参考

### 主要函数

```python
parse(s: str, sep: str = "' -", default_tone_neutral=False, 
      force_valid_syllable=False, missing_as_nul=False) -> list[Syllable]
```

- `s` – 待解析的拼音字符串（可包含分隔符 `sep` 中的字符）。  
- `sep` – 分隔符集合，默认包含 `'`, ` `, `-`。  
- `default_tone_neutral` – 若音节无声调则自动设为轻声（`t5`）。  
- `force_valid_syllable` – 要求每个片段都必须是合法音节，否则抛出异常。  
- `missing_as_nul` – 将缺失的声母/韵母/声调填充为 `nul`（而非 `missing`）。

```python
parse_single(s: str, force_valid_syllable=False) -> Syllable
```

专用于解析单个音节，不允许包含分隔符。

```python
syllables_to_str(sylls: Iterable[Syllable], sep: str | None = None) -> str
```

将音节列表还原为字符串，自动在需要分隔的地方插入 `sep`（默认为 `'`）。

### 类 `Syllable`

主要属性：

- `initial`, `final`, `tone` – 枚举值。
- `to_str(tone_style: ToneStyle = ToneStyle.ABOVE, NO_INCOMPAT_WARNING=False) -> str`  
  输出拼音字符串：
  - `ToneStyle.ABOVE` – 带声调符号（默认，如 `guāng`）。
  - `ToneStyle.AFTER` – 数字标调（如 `guang1`）。
  - `ToneStyle.RIGHT` – 数字附标（如 `gua1ng`，不通用，会触发警告）。
- `is_complete()` – 声母、韵母、声调都不缺失。
- `is_valid()` – 是否为合法音节（基于位图校验）。
- `need_sep(prev: Syllable) -> bool` – 判断该音节前是否需要插入分隔符。

类方法：

- `Syllable(i: int | Initial | str, f: Final = ..., t: Tone = ...)` – 多种构造方式。

### 类 `Parser`

可自定义 token 表，一般直接使用模块级函数即可。若需扩展，可实例化：

```python
from pinyinparser import Parser

my_parser = Parser(tokens={...}, sep=" ")
```

---

## 注意事项

### 与同类库的区别

- **不是汉字转拼音**（请用 [pypinyin](https://github.com/mozillazg/python-pinyin)）。
- **不是分词器**（若输入本身整洁标准，请用 [Pinyin Tokenizer](https://github.com/shibing624/pinyin-tokenizer)）。
- **不是通用拼音转换器**（若只需转换格式，请用 [kittell/pinyinparser](https://github.com/kittell/pinyinparser) 或 pypinyin）。

### 设计取舍

- **音位优先**：`chi` 解析为 `ch·ri·missing`（韵母为 `ri` 而非 `i`），这是为了体现音位上的实际发音。
- **不处理 y/w 变体**：`y` 和 `w` 被视为独立声母，与零声母无变体关系（受限于编码空间）。
- **不支持儿化音**：`-r` 尾会被解析为单独的声母 `r`，无法合并为儿化韵母。
- **输入宽容性**：对于明显非拼音的字符串，解析结果可能“强行规范化”而变得奇怪。

### 性能提示

- 解析基于 DFS，对于长字符串或极端不合法输入可能较慢（但通常可接受）。
- 大量重复解析时，模块内部缓存了编译的正则和某些计算，可提升性能。

---

## 扩展与自定义

你可以通过继承或替换 `Parser` 的 `TOKENS` 字典来支持其他类拼音方案（如注音符号、其他罗马化方案）。  
`TOKENS` 的键为字符串子串，值为对应的 `uint16` 编码列表（允许多重映射）。

示例（添加自定义 token）：
```python
from pinyinparser import Parser, TOKENS

new_tokens = TOKENS.BASIC.copy()
new_tokens["my"] = [0x1234]  # 自定义韵母
parser = Parser(tokens=new_tokens)
```
