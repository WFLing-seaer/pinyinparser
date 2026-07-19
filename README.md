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

**以下内容** [![IIIA-5](https://img.shields.io/badge/IIIA-5-4D6BFE)](https://github.com/ErSanSan233/IIIA)

## pinyinparser.py 使用说明

`pinyinparser` 是一个强大且高精度的汉语拼音解析与生成库。它不仅支持将拼音字符串解析为结构化的“声母+韵母+声调”对象，还能将对象重新格式化为不同风格的拼音字符串。
该模块对拼音的音位学进行了较深度的建模（如区分 `i` 的不同音位变体、处理 `y/w` 伪声母等），因此在使用时有部分不符合直觉的设计，请务必阅读**注意事项**。

---
## 🚀 基本使用
### 1. 解析拼音字符串
使用 `parse()` 方法将拼音字符串解析为 `Syllable` 对象列表。默认支持空格、单引号 `'` 和连字符 `-` 作为音节分隔符。
```python
from pinyinparser import parse, Syllable, ToneStyle, syllables_to_str

# 解析连续拼音（解析器会自动尝试切分）
syllables = parse("xian")  # 可能解析为 xi'an 或 xian，取决于合法性
print(syllables)
# 推荐使用分隔符消除歧义
syllables = parse("xi'an")
for s in syllables:
    print(f"声母: {s.initial.name}, 韵母: {s.final.name}, 声调: {s.tone.name}")
```
### 2. 构建与解析单个音节
可以直接通过字符串构造 `Syllable`，或使用 `parse_single`。
```python
# 直接通过字符串构造
syl = Syllable("zhōng")
print(syl)  # <zh·ong·1>
# 使用类属性直接获取（利用了元类 _SyllMeta 的 __getattr__）
syl2 = Syllable.zhong1
print(syl2.initial, syl2.final, syl2.tone)
```
### 3. 拼音对象转字符串
使用 `syllables_to_str()` 或 `Syllable.to_str()` 将对象转回字符串。支持三种声调风格：
```python
syl = Syllable("zhōng")
# 默认：声调在元音上方
print(syl.to_str())  # "zhōng"
# 声调数字在韵母后
print(syl.to_str(ToneStyle.RIGHT))  # "zho1ng" (注意：此格式不可逆！)
# 声调数字在音节末尾
print(syl.to_str(ToneStyle.AFTER))  # "zhong1"
# 批量转换并自动添加分隔符
syllables = parse("xi'an")
print(syllables_to_str(syllables))  # "xi'ān"
```
---
## ⚠️ 注意事项与反直觉设计（重要！）
本库为了严格贴合语音学和底层位运算设计，存在多处与日常直觉不符的逻辑，使用时请特别注意：
### 1. `y` 和 `w` 是“伪声母”
在《汉语拼音方案》中，`y` 和 `w` 是起隔音作用的零声母标记。但在本库中，**`y` 和 `w` 被视作正式的声母**。
* 直觉：`yan` 的声母为空（零声母），韵母为 `ian`。
* 本库：`yan` 的声母为 `Initial.y`，韵母为 `Final.ian`。
* 同理，`wu` 的声母为 `Initial.w`，韵母为 `Final.u`。
### 2. `i` 并不总是 `Final.i`
受舌尖元音影响，拼音中的 `i` 在解析时会被映射为不同的底层韵母：
* `zi, ci, si` 中的 `i` 解析为 **`Final.ii`**（[ɿ]）
* `zhi, chi, shi, ri` 中的 `i` 解析为 **`Final.ri`**（[ʅ]）
* `bi, pi, mi` 等常规发音解析为 **`Final.i`**
* **注意**：在 `j, q, x` 后面的 `i`（如 `ji`）依然是 `Final.i`，但在转出字符串时，若搭配 `ü`（如 `ju`），底层韵母其实是 `Final.v`，转字符串时规则会自动把 `ü` 替换为 `u`。
### 3. 缺失声调 与 轻声(t5) 的区别
本库严格区分“没有标注声调”和“轻声”：
* 如果输入 `zhong`（不带声调），解析出的声调是 `Tone.missing`，而不是轻声 `t5`。
* 如果要默认将未标调音节视为轻声，需在 `parse` 时传入 `default_tone_neutral=True`。
### 4. `ToneStyle.RIGHT` 是单向不可逆的
使用 `ToneStyle.RIGHT`（如 `zho1ng`）生成的拼音字符串**无法被本解析器重新解析**。因为数字插在字母中间破坏了正则与Token的匹配逻辑。调用时会抛出 `IncompatibleWarning`，若你明确知道后果，可传 `NO_INCOMPAT_WARNING=True` 关闭警告。
### 5. “不存在”的拼音也会被解析（除非强制校验）
解析器默认只做文法切分，不检验音节在普通话中是否真实存在。例如 `wai2` 在词典中不存在，但符合拼写规则，默认仍能解析成功。
* 若要强制只生成真实存在的音节，请使用 `parse(s, force_valid_syllable=True)`。内部会通过一个巨大的 Base85 位图（`VALID_SYLLABLES`）进行校验。
### 6. 声母变体选择位（高级用法）
声母枚举值不是简单的递增。例如：
* `c = 0x0004`
* `ch = 0x8004`
这里 `0x8000` 是变体选择位。如果你需要做模糊匹配（比如让 `ch` 匹配 `c` 开头的所有音），可以通过位运算 `initial & 0x001F` 屏蔽高位，实现“通配首字母”的功能。`zh, sh, H, R, M, N` 同理。
### 7. 特殊叹词的韵母
像 `hm` (噷)、`hng` (哼)、`m` (呣)、`n` (嗯) 等特殊音节：
* `hm` 被视为声母 `Initial.H` + 韵母 `Final.hm`。
* `m` 单独作音节时，被视为声母 `Initial.M` + 韵母 `Final.m`。
* 这与普通零声母（如 `an`）的处理逻辑完全不同。
### 8. `ü` 与 `v` 的输入输出
* 输入时，`ü` 和 `v` 均可被接受（如 `nv` 和 `nü` 等价）。
* 内部统一存储为 `Final.v`（或其衍生如 `Final.veh`, `Final.van`）。
* 输出时，`FINAL2STR` 映射表会自动将其转为标准的 `ü`（在 j/q/x 后会自动脱帽变 u）。
### 9. DFS解析性能问题
作者在源码中坦诚指出，`__parse` 方法使用了不带剪枝的深度优先搜索（DFS），在处理长且无分隔符的极端字符串时，可能存在性能瓶颈或爆递归风险。**推荐在处理用户输入时，尽量要求带分隔符，或对输入长度做限制。**

