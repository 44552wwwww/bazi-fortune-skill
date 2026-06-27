#!/usr/bin/env python3
"""
命运双鉴 · 数据打包器
用法: python data_bundle.py <年> <月> <日> <时> <性别> [输出路径]
输出: 按领域组织的 reading.json，供 Claude 阅读分析
"""
import sys, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from bazi_calculator import compute_bazi
from ziwei_calculator import compute_ziwei


def build_bundle(bz, zw):
    """将两个计算器的输出合并为按领域组织的 JSON"""
    p = bz['四柱']
    ss = bz['十神标注']
    wx = bz['五行分布']
    yong = bz['用神分析']
    dy = bz['大运']
    sex = bz['输入']['性别']
    gongs = zw['十二宫']

    # 辅助：找紫微宫位
    def find_gong(name):
        for g in gongs:
            if g['宫名'] == name:
                return g
        return None

    def gong_summary(g):
        if not g:
            return {"宫位": "?", "干支": "?", "地支": "?", "主星": [], "辅星": [], "四化": [],
                    "三方四正": [], "大限": "", "status": "data_missing"}
        def safe_get(d, key, default=''):
            val = d.get(key, default)
            if val is None:
                return default
            return val
        return {
            "宫位": safe_get(g, '宫名', '?'),
            "干支": safe_get(g, '干支', '?'),
            "地支": safe_get(g, '地支', '?'),
            "主星": [f'{s.get("星名","?")}({s.get("庙旺","?")})' for s in safe_get(g, '主星', [])] if g.get('主星') else [],
            "辅星": [f'{s.get("星名","?")}({s.get("类型","?")})' for s in safe_get(g, '辅星', [])] if g.get('辅星') else [],
            "四化": [s.get('化星', '?') for s in safe_get(g, '四化', [])] if g.get('四化') else [],
            "三方四正": safe_get(g, '三方四正', []),
            "大限": safe_get(g, '大限', ''),
            "isEmpty": len(g.get('主星', [])) == 0,
        }

    cs = [v['天干十神'] for v in ss.values()]
    target = '正官' if sex == '女' else '正财'
    tn = '夫星' if sex == '女' else '妻星'
    has_target = target in cs

    # 配偶宫
    ri_zhi = p['日柱']['地支']
    sp_state = '普通'
    if ri_zhi in ['午', '子']:
        sp_state = '羊刃（个性强、主导欲强）'
    elif ri_zhi in ['卯', '酉']:
        sp_state = '桃花（配偶外貌好或异性缘旺）'

    # 五行过旺/偏弱
    over = [f'{w}({c})' for w, c in wx.items() if c >= 7]
    under = [f'{w}({c})' for w, c in wx.items() if c <= 1]

    # 八字大运
    dy_list = []
    for d in dy['大运列表']:
        is_y = d['天干五行'] in yong['用神']
        is_j = d['天干五行'] in yong['忌神']
        tag = '用神运' if is_y else ('忌神运' if is_j else '平运')
        dy_list.append({
            "年龄段": d['年龄段'],
            "干支": d['干支'],
            "天干": d['天干'],
            "地支": d['地支'],
            "天干五行": d['天干五行'],
            "地支五行": d['地支五行'],
            "纳音": d['纳音'],
            "用忌": tag
        })

    # 紫微大限
    dx_list = []
    for d in zw['大限']['大限列表']:
        g = find_gong(d['宫位'])
        dx_list.append({
            "年龄段": d['年龄段'],
            "宫位": d['宫位'],
            "地支": d['地支'],
            "主星": [s['星名'] for s in g['主星']] if g and g['主星'] else [],
            "吉星数": sum(1 for s in g['辅星'] if s['类型'] == '吉') if g else 0,
            "煞星数": sum(1 for s in g['辅星'] if s['类型'] == '煞') if g else 0,
            "四化": [s['化星'] for s in g['四化']] if g else [],
        })

    # 四化飞星
    sihua_detail = {}
    for hn, sn in zw['四化'].items():
        gn = next((g['宫名'] for g in gongs if any(s['化星'] == hn for s in g['四化'])), '?')
        g = find_gong(gn)
        sihua_detail[hn] = {
            "星曜": sn,
            "所在宫": gn,
            "宫位干支": g['干支'] if g else '?',
            "宫内主星": [s['星名'] for s in g['主星']] if g and g['主星'] else [],
            "宫内辅星": [s['星名'] for s in g['辅星']] if g and g['辅星'] else [],
        }

    bundle = {
        "input": {
            "公历": bz['输入']['公历'],
            "农历": zw['输入']['农历'],
            "性别": sex,
            "生肖": p['年柱']['生肖'],
            "时辰": zw['输入']['时辰'],
        },

        "persona": {
            "八字": {
                "四柱": bz['八字'],
                "日主": bz['日主']['天干'],
                "日主五行": bz['日主']['五行'],
                "日主阴阳": bz['日主']['阴阳'],
                "身强身弱": yong['身强身弱'],
                "力量占比": yong['日主力量占比'],
                "节气": bz['节气'],
            },
            "紫微": {
                "命宫": zw['命宫'],
                "命宫干支": find_gong('命宫')['干支'] if find_gong('命宫') else '?',
                "身宫": zw['身宫'],
                "五行局": zw['五行局'],
                "紫微星在": zw['紫微星在'],
                "命身同宫": zw['命宫'] == zw['身宫'],
            }
        },

        "wuxing": {
            "分布": wx,
            "用神": yong['用神'],
            "忌神": yong['忌神'],
            "调候需求": yong.get('调候需求'),
            "过旺": over,
            "偏弱": under,
        },

        "relationships": {
            "八字": {
                "配偶星": f'{target}({tn})',
                "配偶星状态": '透干有气' if has_target else '不透干偏弱',
                "配偶宫": ri_zhi,
                "配偶宫状态": sp_state,
                "十神分布": [f'{ss[c]["天干十神"]}({c})' for c in ['年柱', '月柱', '日柱', '时柱']],
                "日柱纳音": p['日柱']['纳音'],
                "官杀混杂": '正官' in cs and '七杀' in cs,
                "伤官见官": '伤官' in cs and '正官' in cs,
            },
            "紫微": gong_summary(find_gong('夫妻宫')),
        },

        "career_wealth": {
            "八字": {
                "财星": '透干' if ('正财' in cs or '偏财' in cs) else '不显',
                "正财位置": [c for c in ['年柱', '月柱', '日柱', '时柱'] if '正财' in ss[c]['天干十神']],
                "偏财位置": [c for c in ['年柱', '月柱', '日柱', '时柱'] if '偏财' in ss[c]['天干十神']],
                "食神": '有' if '食神' in cs else '无',
                "伤官": '有' if '伤官' in cs else '无',
                "劫财": '有' if '劫财' in cs else '无',
                "正印": '有' if '正印' in cs else '无',
                "偏印": '有' if '偏印' in cs else '无',
                "七杀": '有' if '七杀' in cs else '无',
            },
            "紫微": {
                "财帛宫": gong_summary(find_gong('财帛宫')),
                "官禄宫": gong_summary(find_gong('官禄宫')),
            }
        },

        "health": {
            "五行关联": {f'{w}({c})': _organ_for_wuxing(w) for w, c in wx.items()},
            "紫微疾厄宫": gong_summary(find_gong('疾厄宫')),
        },

        "fortune": {
            "八字大运": {
                "起运年龄": dy['起运年龄'],
                "排法": dy['排法'],
                "大运": dy_list,
            },
            "紫微大限": {
                "排法": zw['大限']['排法'],
                "大限": dx_list,
            }
        },

        "structures": {
            "地支关系": bz['地支关系']['冲突列表'],
            "四化飞星": sihua_detail,
        },

        "all_palaces": [gong_summary(g) for g in gongs],
    }

    return bundle


def _organ_for_wuxing(w):
    m = {'木': '肝胆、筋骨、神经系统', '火': '心血管、血压、眼睛、炎症',
         '土': '脾胃、消化、肌肉', '金': '肺、呼吸道、皮肤、大肠',
         '水': '肾、膀胱、泌尿、腰膝'}
    return m.get(w, '')


def main():
    if len(sys.argv) < 6:
        print("用法: python data_bundle.py <年> <月> <日> <时> <性别> [输出路径]")
        print("示例: python data_bundle.py 2006 4 10 1 男")
        sys.exit(1)

    y, m, d, h = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    sex = sys.argv[5]
    out_path = sys.argv[6] if len(sys.argv) > 6 else os.path.join(os.path.dirname(BASE), 'reading.json')

    bz = compute_bazi(y, m, d, h, sex)
    zw = compute_ziwei(y, m, d, h, sex)
    bundle = build_bundle(bz, zw)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    print(f'✅ 数据包已生成: {out_path}')
    print(f'   包含 {len(json.dumps(bundle, ensure_ascii=False))} 字符的结构化命理数据')


if __name__ == '__main__':
    main()
