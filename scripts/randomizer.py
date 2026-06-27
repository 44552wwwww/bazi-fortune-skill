#!/usr/bin/env python3
"""
命运双鉴 · 风格随机化器
每次为分析脚本注入不同的写作风格参数，从程序层面防止模板化。
输出 style_config.json 供 LLM 读取。

用法:
  python randomizer.py [输出路径]   # 生成随机风格配置
  python randomizer.py --seed 42    # 指定种子（调试用）
"""
import json
import os
import random
import sys
from datetime import datetime, timezone, timedelta

# 北京时间
CST = timezone(timedelta(hours=8))


def _seeded_random():
    """用当前时间戳 + 进程 ID 生成真随机种子"""
    ts = datetime.now(CST).timestamp()
    pid = os.getpid()
    # 混合多个熵源
    seed = int(ts * 1_000_000) ^ (pid << 8) ^ (os.getpid() * 2654435761)
    random.seed(seed)
    return seed


# ── 风格维度池 ──

TONE_POOL = [
    {"name": "典雅沉稳", "hint": "用词讲究、句式工整，适当引用古籍典故，像一位博学的老先生在娓娓道来"},
    {"name": "平实直白", "hint": "语言朴素直接，少用修辞，注重逻辑推导，像一位理性的科学工作者在分析数据"},
    {"name": "温润细腻", "hint": "措辞柔和，多用比喻和意象，像一位体贴的长者在关心后辈的人生"},
    {"name": "犀利透彻", "hint": "观点鲜明，不绕弯子，一针见血指出问题，像一位严厉但公正的导师"},
    {"name": "诗意灵动", "hint": "多用自然意象和韵律感强的短句，像一位诗人在解读命运的诗篇"},
    {"name": "通俗亲和", "hint": "接地气的大白话，多用生活化比喻，像一位邻家大哥在聊天"},
]

STRUCTURE_POOL = [
    {"name": "总分总", "hint": "先给出总体定论 → 分层展开论证 → 回归总结升华"},
    {"name": "由果溯因", "hint": "先抛出最显著的人生表现 → 再倒推命理根源是什么"},
    {"name": "时空推进", "hint": "从早年大运讲到晚年大运，像讲述一个完整的人生故事"},
    {"name": "核心突围", "hint": "全篇围绕命盘最突出的那个矛盾展开，所有分析为这一个主题服务"},
    {"name": "对比交织", "hint": "八字和紫微交替穿插，每分析一个维度就两边对照，形成对话感"},
]

METAPHOR_DOMAIN_POOL = [
    ["自然山水", "江河、山峰、风雨、日月、森林、岩石"],
    ["建筑营造", "基石、梁柱、门窗、庭院、桥梁、灯塔"],
    ["植物生长", "根系、枝干、开花、结果、四季荣枯"],
    ["音乐韵律", "主旋律、和声、节奏、高潮、休止符"],
    ["行军打仗", "攻守、进退、补给、先锋、殿后、合围"],
    ["烹饪调味", "火候、主料、辅料、咸淡、收汁、回甘"],
    ["书画笔墨", "骨架、气韵、留白、浓淡、起承转合"],
    ["星辰宇宙", "轨道、引力、光芒、暗物质、星座连线"],
]

OPENING_POOL = [
    "这个命盘最让我注意的，是{feature}。",
    "拿到这个八字的第一眼，我就被{feature}吸引了。",
    "如果要给这个命盘画一幅肖像，它的底色是{feature}。",
    "这个命格的气质，可以用一个词概括：{feature}。",
    "翻开这个星盘，一个鲜明的主题跳了出来——{feature}。",
    "这不是一个平平无奇的命盘。它最特别的地方在{feature}。",
    "在分析这个命盘之前，先说结论：{feature}。",
    "让我从这个命盘最关键的一个点说起——{feature}。",
]

TRANSITION_POOL = [
    "接下来看", "下面再看", "换一个角度", "从另一个维度看",
    "再看", "不止如此，", "更有意思的是，", "值得注意的是，",
    "现在把视线转向", "翻到星盘的另一面，", "如果说前面是果，那这里是因——",
    "八字之外，紫微怎么看？", "两套体系在这里出现了有趣的——",
]

PARAGRAPH_STYLE_POOL = [
    {"style": "短句快节奏", "hint": "多用短句，一段不超过 4 行，节奏明快"},
    {"style": "长篇舒展", "hint": "每段充分展开，娓娓道来，不急于收束"},
    {"style": "混合节奏", "hint": "先短句点题，再长段展开，一张一弛"},
]

EMPHASIS_POOL = [
    {"style": "数据先行", "hint": "先列出具体的命盘数据，再给出解读"},
    {"style": "结论先行", "hint": "每段开头先给出核心判断，再展开理由"},
    {"style": "问题驱动", "hint": "用设问句开头，自问自答"},
]


def generate_config() -> dict:
    """生成一次随机的风格配置"""
    _seeded_random()

    tone = random.choice(TONE_POOL)
    structure = random.choice(STRUCTURE_POOL)
    metaphor = random.choice(METAPHOR_DOMAIN_POOL)
    opening = random.choice(OPENING_POOL)
    transitions = random.sample(TRANSITION_POOL, k=min(4, len(TRANSITION_POOL)))
    paragraph = random.choice(PARAGRAPH_STYLE_POOL)
    emphasis = random.choice(EMPHASIS_POOL)

    # 避开的比喻域（从池中再抽两个，确保跟当前选中的不同）
    avoid_pool = [m[0] for m in METAPHOR_DOMAIN_POOL if m[0] != metaphor[0]]
    avoid_metaphors = random.sample(avoid_pool, k=min(2, len(avoid_pool)))

    return {
        "_meta": {
            "generated_at": datetime.now(CST).isoformat(timespec='seconds'),
            "purpose": "本次分析的写作风格参数——LLM 请参照这些设定生成分析文字",
            "note": "每次生成的风格参数完全不同，确保每篇报告气质独特",
        },
        "tone": tone,
        "structure": structure,
        "metaphor_domain": {
            "use": metaphor[0],
            "examples": metaphor[1],
            "avoid": avoid_metaphors,
        },
        "opening": {
            "template": opening,
            "hint": "使用时将 {feature} 替换为命盘最突出的特征",
        },
        "transitions": transitions,
        "paragraph": paragraph,
        "emphasis": emphasis,
        "hard_rules": [
            "不使用上一个命盘用过的核心比喻",
            "不复制之前任何报告的段落结构",
            "每次选择不同的开篇角度",
            "八字和紫微的叙述顺序不固定——根据数据强度灵活调整",
            "交叉验证表是报告的核心价值——最后一列必须解释'为什么'",
        ],
    }


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))

    if '--seed' in sys.argv:
        idx = sys.argv.index('--seed')
        random.seed(int(sys.argv[idx + 1]))

    config = generate_config()

    out_path = os.path.join(os.path.dirname(out_dir), 'style_config.json')
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        out_path = sys.argv[1]

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f'🎨 风格配置已生成: {out_path}')
    print(f'   语调: {config["tone"]["name"]}')
    print(f'   结构: {config["structure"]["name"]}')
    print(f'   比喻域: {config["metaphor_domain"]["use"]}')
    print(f'   段落: {config["paragraph"]["style"]}')
    print(f'   强调: {config["emphasis"]["style"]}')


if __name__ == '__main__':
    main()
