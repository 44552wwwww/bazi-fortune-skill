#!/usr/bin/env python3
"""
命运双鉴 · HTML 框架生成器
用法: python html_frame.py <年> <月> <日> <时> <性别> [输出路径]
输出: 带 {{PLACEHOLDER}} 标记的完整 HTML 框架
"""
import sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from bazi_calculator import compute_bazi, GAN_WX, ZHI_WX
from ziwei_calculator import compute_ziwei


def wx_dot(wx):
    c = {'木': '4ade80', '火': 'f97316', '土': 'a78b5a', '金': 'e2e8a0', '水': '38bdf8'}.get(wx, '888')
    return f'<span class="wx-d" style="background:#{c}"></span>{wx}'


def bazi_chart(bz):
    """四柱表格 - 纯数据渲染"""
    p = bz['四柱']
    ss = bz['十神标注']
    chart = '<table class="bzt"><tr><th></th><th>年柱</th><th>月柱</th><th>日柱</th><th>时柱</th></tr>'
    for rn in ["天干", "地支", "纳音", "十二长生"]:
        chart += f'<tr><td class="lbl">{rn}</td>'
        for col in ["年柱", "月柱", "日柱", "时柱"]:
            if rn == "天干":
                dm = ' day-master' if col == "日柱" else ''
                chart += f'<td class="gz{dm}">{p[col]["天干"]} {wx_dot(p[col]["天干五行"])}<br><small>{ss[col]["天干十神"]}</small></td>'
            elif rn == "地支":
                chart += f'<td>{p[col]["地支"]} {wx_dot(p[col]["地支五行"])}<br><small>{"·".join(p[col]["藏干"])}</small></td>'
            elif rn == "纳音":
                chart += f'<td>{p[col]["纳音"]}</td>'
            else:
                chart += f'<td>{p[col]["日主十二长生在此"]}</td>'
        chart += '</tr>'
    chart += '</table>'
    return chart


def wuxing_bars(wx):
    """五行力量条 - 纯数据渲染"""
    wx_total = sum(wx.values())
    bar = '<div class="wx-bar">'
    for w, c in [("木", "4ade80"), ("火", "f97316"), ("土", "a78b5a"), ("金", "e2e8a0"), ("水", "38bdf8")]:
        pct = wx.get(w, 0) / wx_total * 100 if wx_total else 0
        if pct > 0:
            bar += f'<div style="width:{pct:.0f}%;background:#{c}"></div>'
    bar += '</div><div class="wx-lab">'
    for w in ["木", "火", "土", "金", "水"]:
        bar += f'<span>{wx_dot(w)} {wx.get(w, 0)} ({wx.get(w, 0) / wx_total * 100:.0f}%)</span> '
    bar += '</div>'
    return bar


def yongji_box(bz):
    """用神忌神 + 地支关系 - 纯数据渲染"""
    p = bz['四柱']
    yong = bz['用神分析']
    wuxing = bz['五行分布']
    wx_total = sum(wuxing.values())

    html = '<div class="box">'
    html += f'<p>日主<b>{bz["日主"]["天干"]}</b>（{bz["日主"]["五行"]}·{bz["日主"]["阴阳"]}）· <b>{yong["身强身弱"]}</b>（日主力量 {yong["日主力量占比"]}）</p>'
    html += f'<p>用神：<span class="green"><b>{"、".join(yong["用神"])}</b></span> | 忌神：<span class="red"><b>{"、".join(yong["忌神"])}</b></span></p>'
    if yong.get('调候需求'):
        html += f'<p>调候需求：{yong["调候需求"]}</p>'
    html += '</div>'

    cf = bz['地支关系']['冲突列表']
    if cf:
        html += '<div class="box">'
        for c in cf:
            html += f'<span class="red">[{c["关系"]}]</span> {c["涉及"]} · '
        html += '</div>'
    return html


def dayun_timeline(bz):
    """大运时间线 - 纯数据渲染"""
    dy = bz['大运']
    yong = bz['用神分析']['用神']
    ji = bz['用神分析']['忌神']

    html = f'<p style="color:#888;margin-bottom:12px"><b>{dy["起运年龄"]}岁起运 · {dy["排法"]}</b></p>'
    html += '<div class="dy-row">'
    for d in dy['大运列表']:
        is_y = d['天干五行'] in yong
        is_j = d['天干五行'] in ji
        cls = 'dy-y' if is_y else ('dy-j' if is_j else '')
        label = '用神' if is_y else ('忌神' if is_j else '平')
        lc = 'var(--gr)' if is_y else ('var(--r)' if is_j else '#888')
        html += f'<div class="dy-s {cls}"><div class="dy-a">{d["年龄段"]}</div><div class="dy-g">{d["干支"]}</div><div style="font-size:.65em;color:{lc}">{label}</div></div>'
    html += '</div>'

    # Dayun detail placeholders
    for i, d in enumerate(dy['大运列表']):
        is_y = d['天干五行'] in yong
        is_j = d['天干五行'] in ji
        lc = 'var(--gr)' if is_y else ('var(--r)' if is_j else '#888')
        html += f'<div style="padding:8px 0;border-bottom:1px solid var(--bd);color:#bbb;line-height:1.8"><b style="color:{lc}">{d["年龄段"]} · {d["干支"]}</b>（{d["天干五行"]}+{d["地支五行"]}）—— {{DAYUN_DETAIL_{i}}}</div>'
    return html


def ziwei_grid(zw):
    """紫微十二宫星盘网格 - 纯数据渲染"""
    gongs = zw['十二宫']
    gong_by_zhi = {g['地支']: g for g in gongs}
    order = ['巳', '午', '未', '申', '辰', None, None, '酉', '卯', None, None, '戌', '寅', '丑', '子', '亥']

    grid = '<div class="zw-grid">'
    for z in order:
        if z is None:
            grid += f'<div class="zw-c"><div class="zw-ctr">☯<br><small>命·{zw["命宫"]}<br>身·{zw["身宫"]}<br>{zw["五行局"]}<br>紫微在{zw["紫微星在"]}</small></div></div>'
        else:
            g = gong_by_zhi.get(z)
            if g:
                mjr = ''.join(
                    f'<span class="st-mjr{" mi" if s["庙旺"] == "庙旺" else ""}">{s["星名"]}</span>'
                    for s in g['主星'])
                aux = ''.join(
                    f'<span class="st-{"ji" if s["类型"] == "吉" else "sha" if s["类型"] == "煞" else "za"}">{s["星名"]}</span>'
                    for s in g['辅星'])
                si = ''.join(f'<span class="st-si">{s["化星"]}</span>' for s in g['四化'])
                grid += f'<div class="zw-p{(" empty" if not g["主星"] else "")}"><div class="zw-pn">{g["宫名"]}<span class="zw-pz">{g["干支"]}</span></div><div class="zw-st">{mjr if mjr else "<span class=dim>(空)</span>"}</div><div class="zw-st">{aux}</div><div class="zw-st">{si}</div><div class="zw-dx">{g.get("大限", "")}</div></div>'
    grid += '</div>'
    return grid


def sihua_banner(zw):
    """四化飞星横幅 - 纯数据渲染"""
    gongs = zw['十二宫']
    sh = zw['四化']
    hua_cls = {'化禄': ('lu', '🟢'), '化权': ('quan', '🟣'), '化科': ('ke', '🔵'), '化忌': ('ji', '🔴')}

    html = '<div class="sh-ban">'
    for hn, sn in sh.items():
        cls, em = hua_cls.get(hn, ('', ''))
        gn = next((g['宫名'] for g in gongs if any(s['化星'] == hn for s in g['四化'])), '?')
        html += f'<div class="sh-c sh-{cls}"><div class="sh-l">{em} {hn}</div><div>{sn}</div><div class="dim" style="font-size:.7em">在{gn}</div></div>'
    html += '</div>'
    html += '<p style="color:#888;font-size:.85em;margin-top:12px">生年干决定四化——化禄为优势，化权为发力方向，化科为名声，化忌为人生课题。</p>'
    return html


def sihua_details(zw):
    """四化飞星详细分析 - 占位符"""
    gongs = zw['十二宫']
    sh = zw['四化']
    hua_cls = {'化禄': 'gr', '化权': 'p', '化科': 'b', '化忌': 'r'}
    hua_key = {'化禄': 'LU', '化权': 'QUAN', '化科': 'KE', '化忌': 'JI'}

    html = ''
    for hn, sn in sh.items():
        cls = hua_cls.get(hn, '')
        key = hua_key.get(hn, hn)
        gn = next((g['宫名'] for g in gongs if any(s['化星'] == hn for s in g['四化'])), '?')
        g = next((g for g in gongs if g['宫名'] == gn), None)
        g_ganzhi = g['干支'] if g else '?'

        em_icons = {'化禄': '🟢', '化权': '🟣', '化科': '🔵', '化忌': '🔴'}
        em = em_icons.get(hn, '')
        html += f'<div style="padding:12px 0;border-bottom:1px solid var(--bd)"><b style="color:var(--{cls})">{em} {hn} · {sn} 在 {gn}（{g_ganzhi}）</b><br><span style="color:#888;font-size:.85em">{{SIHUA_DETAIL_{key}}}</span></div>'
    return html


def daxian_list(zw):
    """大限列表 - 占位符"""
    html = f'<p style="color:#888;margin-bottom:10px"><b>{zw["大限"]["排法"]}</b>——每个大限主十年运势，宫位代表该阶段的人生重心</p>'
    for i, d in enumerate(zw['大限']['大限列表']):
        html += f'<div style="padding:10px 0;border-bottom:1px solid var(--bd);color:#bbb;line-height:1.9"><b style="color:var(--g)">{d["年龄段"]}</b> · {d["宫位"]}({d["地支"]}) · {{DAXIAN_DETAIL_{i}}}</div>'
    return html


# ══════════════════════════════════════════════════
# HTML_V2 模板 - 保留全部 CSS/JS 不变
# ══════════════════════════════════════════════════
HTML_V2 = r'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>命运双鉴 {date}</title>
<style>
:root{{--bg:#0f0f14;--card:#1a1a24;--c2:#222232;--t:#d4d4dc;--g:#c9a96e;--p:#8b5cf6;--r:#e85d75;--b:#60a5fa;--gr:#4ade80;--bd:#2a2a3a}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--t);font-family:'Segoe UI','Noto Sans SC','Microsoft YaHei',sans-serif;line-height:1.7;min-height:100vh}}
.top-nav{{display:flex;background:#12121a;border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:100}}
.nav-btn{{flex:1;padding:16px 10px;background:none;border:none;color:#777;cursor:pointer;font-size:1em;transition:all .25s;border-bottom:2px solid transparent;font-family:inherit;text-align:center}}
.nav-btn:hover{{color:#aaa}}.nav-btn.on{{color:var(--g);border-bottom-color:var(--g);background:rgba(201,169,110,.04)}}
.nav-btn .sub{{font-size:.65em;display:block;color:#555;margin-top:2px}}.nav-btn.on .sub{{color:var(--g)}}
.panel{{display:none}}.panel.on{{display:block}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px 20px 60px}}
.hdr{{text-align:center;padding:36px 20px;margin-bottom:28px;background:linear-gradient(135deg,rgba(201,169,110,.06),rgba(139,92,246,.06));border:1px solid var(--bd);border-radius:18px}}
.hdr h1{{font-size:2em;background:linear-gradient(135deg,var(--g),#e2c98a,var(--p));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px}}
.hdr .sub{{color:#888;font-size:.9em}}.hdr .meta{{display:inline-block;margin-top:12px;padding:6px 18px;background:var(--card);border:1px solid var(--bd);border-radius:20px;color:#888;font-size:.82em}}
.badges{{display:flex;justify-content:center;gap:12px;margin-top:14px;flex-wrap:wrap}}
.badge{{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:5px 12px;font-size:.82em}}
.badge span{{color:var(--g);font-weight:600}}
.mod{{margin-bottom:12px}}
.mod-hd{{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:16px 20px;cursor:pointer;display:flex;align-items:center;gap:10px;transition:all .25s}}
.mod-hd:hover{{border-color:var(--g)}}
.mod-icon{{font-size:1.2em}}.mod-hd span{{font-size:.95em;color:#ddd;flex:1}}
.mod-arr{{color:#666;transition:transform .3s;font-size:.8em}}.mod-hd.open .mod-arr{{transform:rotate(180deg)}}
.mod-bd{{max-height:0;overflow:hidden;transition:max-height .5s ease;background:var(--card);border-radius:0 0 12px 12px}}
.mod-bd.open{{max-height:20000px;padding:16px 20px;border:1px solid var(--bd);border-top:0}}
.sum{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:8px}}
.vc{{background:var(--c2);border:1px solid var(--bd);border-radius:14px;padding:22px 18px;transition:all .25s}}
.vc:hover{{border-color:var(--g);transform:translateY(-2px)}}
.vc-icon{{font-size:1.6em;margin-bottom:4px}}.vc h3{{font-size:.95em;color:#bbb;margin-bottom:4px}}
.vc .big{{font-size:1.2em;font-weight:700;margin:6px 0 8px}}
.big.good{{color:var(--gr)}}.big.warn{{color:var(--r)}}.big.ok{{color:var(--g)}}
.vc .detail{{color:#999;font-size:.8em;line-height:1.6}}.vc .detail em{{color:#ccc;font-style:normal;font-weight:600}}
.tg{{display:inline-block;padding:2px 8px;border-radius:5px;font-size:.7em;margin:2px}}
.tag-good{{background:rgba(74,222,128,.1);color:var(--gr);border:1px solid rgba(74,222,128,.2)}}
.tag-bad{{background:rgba(232,93,117,.1);color:var(--r);border:1px solid rgba(232,93,117,.2)}}
.tag-tip{{background:rgba(96,165,250,.08);color:var(--b);border:1px solid rgba(96,165,250,.2)}}
.bzt{{width:100%;border-collapse:collapse;border-radius:12px;overflow:hidden;margin-bottom:8px}}
.bzt th{{background:#2F5496;color:#fff;padding:12px;font-size:.85em}}
.bzt td{{padding:12px;background:var(--c2);border:1px solid var(--bd);text-align:center;font-size:.85em}}
.bzt .day-master{{color:var(--g);font-weight:700;font-size:1.05em}}.bzt .lbl{{color:#888;font-size:.78em}}
.wx-d{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:3px}}
.wx-bar{{height:18px;border-radius:9px;display:flex;overflow:hidden;margin-bottom:6px}}
.wx-lab{{display:flex;gap:14px;flex-wrap:wrap;font-size:.78em;color:#888;margin-bottom:12px}}
.box{{background:var(--c2);border:1px solid var(--bd);border-radius:10px;padding:14px;margin:8px 0}}
.green{{color:var(--gr)}}.red{{color:var(--r)}}.dim{{color:#666}}
.dy-row{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}}
.dy-s{{flex:1;min-width:85px;background:var(--c2);border:1px solid var(--bd);border-radius:8px;padding:10px;text-align:center;transition:all .25s}}
.dy-s:hover{{border-color:var(--g)}}.dy-s.dy-y{{border-color:rgba(74,222,128,.3)}}.dy-s.dy-j{{border-color:rgba(232,93,117,.3)}}
.dy-a{{font-size:.62em;color:#666}}.dy-g{{font-size:.95em;color:var(--g);font-weight:600;margin:2px 0}}
.zw-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin-bottom:12px}}
.zw-p,.zw-c{{background:var(--c2);border:1px solid var(--bd);border-radius:10px;padding:10px;min-height:90px;font-size:.8em}}
.zw-p.empty{{opacity:.5}}.zw-ctr{{text-align:center;color:var(--g);font-size:.85em;font-weight:700;line-height:1.8}}
.zw-pn{{font-size:.7em;color:var(--g);font-weight:700;margin-bottom:3px}}.zw-pz{{float:right;color:#666;font-size:.65em}}
.zw-st{{display:flex;flex-wrap:wrap;gap:1px;margin:2px 0}}
.st-mjr{{display:inline-block;padding:1px 4px;border-radius:3px;font-size:.65em;color:var(--g);background:rgba(201,169,110,.1)}}.st-mjr.mi{{color:#f59e0b}}
.st-ji{{font-size:.62em;color:var(--gr)}}.st-sha{{font-size:.62em;color:var(--r)}}.st-za{{font-size:.62em;color:#a78bfa}}
.st-si{{font-size:.62em;color:var(--b);font-weight:700}}.zw-dx{{font-size:.6em;color:#666;margin-top:2px}}
.sh-ban{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}}
.sh-c{{flex:1;min-width:140px;border-radius:10px;padding:12px;text-align:center;border:1px solid var(--bd)}}
.sh-lu{{background:rgba(74,222,128,.05);border-color:rgba(74,222,128,.2)}}
.sh-quan{{background:rgba(139,92,246,.05);border-color:rgba(139,92,246,.2)}}
.sh-ke{{background:rgba(96,165,250,.05);border-color:rgba(96,165,250,.2)}}
.sh-ji{{background:rgba(232,93,117,.05);border-color:rgba(232,93,117,.2)}}
.sh-l{{font-size:1em;font-weight:700}}
.xref-wrap{{overflow-x:auto;margin-bottom:12px}}
.xref-table{{width:100%;border-collapse:separate;border-spacing:0;border-radius:12px;overflow:hidden;font-size:.82em}}
.xref-table th{{background:#2F5496;color:#fff;padding:10px;font-size:.82em}}
.xref-table td{{padding:10px;background:var(--c2);border-bottom:1px solid var(--bd);vertical-align:top;line-height:1.5}}
.xref-table tr td:first-child{{font-weight:700;color:var(--g);text-align:center;font-size:.95em}}
.agree{{color:var(--gr);font-weight:600}}.conflict{{color:var(--r);font-weight:600}}.unique{{color:var(--b);font-weight:600}}
.actions{{background:linear-gradient(135deg,rgba(201,169,110,.06),rgba(139,92,246,.06));border:1px solid var(--bd);border-radius:16px;padding:28px 24px;margin-top:24px}}
.actions h3{{margin-bottom:16px}}
.act-list{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
.act-item{{background:var(--c2);border-radius:10px;padding:14px 12px;border-left:3px solid var(--g);font-size:.82em;line-height:1.6}}
.act-item .num{{display:inline-block;width:20px;height:20px;border-radius:50%;background:var(--g);color:#1a1a24;text-align:center;line-height:20px;font-size:.7em;font-weight:700;margin-right:6px}}
.act-item em{{color:#ddd;font-style:normal;font-weight:600}}
.nar h3{{color:var(--g);font-size:1em;margin:16px 0 6px;padding-bottom:4px;border-bottom:1px solid var(--bd)}}
.nar p{{color:#bbb;font-size:.84em;margin:4px 0;line-height:1.8}}
.nar b{{color:#ddd}}
.sub-tabs{{display:flex;gap:4px;margin-bottom:24px;flex-wrap:wrap}}
.sub-btn{{padding:10px 18px;border:1px solid var(--bd);background:var(--card);color:#999;cursor:pointer;border-radius:10px 10px 0 0;transition:all .25s;font-size:.9em;font-family:inherit}}
.sub-btn:hover{{color:#fff;background:#2a2a3e}}
.sub-btn.on{{background:var(--c2);color:var(--g);border-bottom-color:var(--c2)}}
.sub-panel{{display:none}}.sub-panel.on{{display:block}}
.footer{{text-align:center;color:#555;font-size:.75em;margin:30px 0 10px;line-height:1.8}}
@media(max-width:768px){{.sum{{grid-template-columns:repeat(2,1fr)}}.act-list{{grid-template-columns:1fr}}.zw-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:480px){{.sum{{grid-template-columns:1fr}}.nav-btn{{font-size:.8em;padding:12px 6px}}}}
</style></head><body>
<div class="top-nav">
  <button class="nav-btn on" onclick="sw('bazi')">八字命盘<span class="sub">子平术</span></button>
  <button class="nav-btn" onclick="sw('ziwei')">紫微斗数<span class="sub">星盘分析</span></button>
  <button class="nav-btn" onclick="sw('dual')">双鉴总结<span class="sub">交叉验证</span></button>
</div>

<div id="tb-bazi" class="panel on"><div class="wrap">
<div class="hdr"><h1>八字命盘 · 子平术</h1><div class="sub">Ba Zi · Four Pillars of Destiny</div><div class="meta" style="font-size:1.1em;color:var(--g);font-weight:700">{bz_date} · {bz_sex}命 · {bz_year}年 · 日主{bz_rigan}({bz_riwx}) · {bz_sq}</div></div>
<div class="sub-tabs"><button class="sub-btn on" onclick="swSub('bazi',0,event)">💬 白话总结</button><button class="sub-btn" onclick="swSub('bazi',1,event)">📊 排盘数据</button><button class="sub-btn" onclick="swSub('bazi',2,event)">📋 命理分析</button><button class="sub-btn" onclick="swSub('bazi',3,event)">⏳ 大运走势</button></div>
<div class="sub-panel on"><div class="sum">
{{BAZI_CARD_0}}
{{BAZI_CARD_1}}
{{BAZI_CARD_2}}
{{BAZI_CARD_3}}
{{BAZI_CARD_4}}
{{BAZI_CARD_5}}
</div></div>
<div class="sub-panel">
{bz_chart}
{wx_bars}
{yj_box}
</div>
<div class="sub-panel">
{{BAZI_ANALYSIS_0}}
{{BAZI_ANALYSIS_1}}
{{BAZI_ANALYSIS_2}}
{{BAZI_ANALYSIS_3}}
{{BAZI_ANALYSIS_4}}
{{BAZI_ANALYSIS_5}}
{{BAZI_ANALYSIS_6}}
</div>
<div class="sub-panel">
{dy_timeline}
</div>
<div class="footer">⚠ 命理仅为传统民俗文化参考</div></div></div>

<div id="tb-ziwei" class="panel"><div class="wrap">
<div class="hdr"><h1>紫微斗数 · 星盘命理</h1><div class="sub">Zi Wei Dou Shu · Star Chart</div><div class="meta" style="font-size:1.1em;color:var(--g);font-weight:700">{zw_date} · {zw_sex}命 · {zw_year}年 · 命宫{zw_ming} · 身宫{zw_shen} · {zw_wxj}</div></div>
<div class="sub-tabs"><button class="sub-btn on" onclick="swSub('ziwei',0,event)">💬 白话总结</button><button class="sub-btn" onclick="swSub('ziwei',1,event)">🌟 星盘总览</button><button class="sub-btn" onclick="swSub('ziwei',2,event)">📋 命理分析</button><button class="sub-btn" onclick="swSub('ziwei',3,event)">🔄 四化飞星</button><button class="sub-btn" onclick="swSub('ziwei',4,event)">⏳ 大限走势</button></div>
<div class="sub-panel on"><div class="sum">
{{ZIWEI_CARD_0}}
{{ZIWEI_CARD_1}}
{{ZIWEI_CARD_2}}
{{ZIWEI_CARD_3}}
{{ZIWEI_CARD_4}}
{{ZIWEI_CARD_5}}
</div></div>
<div class="sub-panel">
{sh_banner}
{zw_grid}
</div>
<div class="sub-panel">
{{PALACE_0}}
{{PALACE_1}}
{{PALACE_2}}
{{PALACE_3}}
{{PALACE_4}}
{{PALACE_5}}
{{PALACE_6}}
{{PALACE_7}}
{{PALACE_8}}
{{PALACE_9}}
{{PALACE_10}}
{{PALACE_11}}
</div>
<div class="sub-panel">
{sh_details}
</div>
<div class="sub-panel">
{dx_list}
</div>
<div class="footer">⚠ 命理仅为传统民俗文化参考</div></div></div>

<div id="tb-dual" class="panel"><div class="wrap"><div class="hdr"><h1>命运双鉴 · 综合交叉验证</h1><div class="sub">八字 × 紫微斗数 —— 两套独立命理体系互相印证</div></div>
<h2 style="color:var(--g);margin-bottom:12px;font-size:1.1em">📊 七维交叉验证表</h2>
<div class="xref-wrap"><table class="xref-table"><tr><th></th><th>八字</th><th>紫微</th><th>一致性</th></tr>
{{CROSS_REF_ROWS}}
</table></div>
<h2 style="color:var(--g);margin:24px 0 12px;font-size:1.1em">🎯 综合定论</h2>
<div class="sum">
{{VERDICT_CARDS}}
</div>
<h2 style="color:var(--g);margin:24px 0 12px;font-size:1.1em">📝 详细命理分析</h2>
<div class="nar">
{{NARRATIVE_0}}
{{NARRATIVE_1}}
{{NARRATIVE_2}}
{{NARRATIVE_3}}
{{NARRATIVE_4}}
{{NARRATIVE_5}}
{{NARRATIVE_6}}
{{NARRATIVE_7}}
</div>
<div class="actions"><h3 style="color:var(--g);">📋 行动建议</h3><div class="act-list">
{{ACTION_0}}
{{ACTION_1}}
{{ACTION_2}}
{{ACTION_3}}
{{ACTION_4}}
{{ACTION_5}}
</div></div>
<div class="footer">⚠ 命理仅为传统民俗文化参考</div></div></div>

<script>
function sw(n){{document.querySelectorAll('.nav-btn').forEach(function(b){{b.classList.remove('on')}});document.querySelectorAll('.panel').forEach(function(p){{p.classList.remove('on')}});document.getElementById('tb-'+n).classList.add('on');event.target.classList.add('on')}}
function swSub(tab,idx,ev){{var p=document.getElementById('tb-'+tab);var btns=p.querySelectorAll('.sub-btn');var pns=p.querySelectorAll('.sub-panel');btns.forEach(function(b){{b.classList.remove('on')}});pns.forEach(function(p){{p.classList.remove('on')}});btns[idx].classList.add('on');pns[idx].classList.add('on')}}
</script>
</body></html>'''


def build_frame(bz, zw):
    """生成带占位符的完整 HTML"""
    y, m, d = [int(x) for x in bz['输入']['公历'].replace('年', ' ').replace('月', ' ').replace('日', ' ').split()[:3]]

    # 提取元数据
    bz_date = bz['输入']['公历']
    bz_sex = bz['输入']['性别']
    bz_year = bz['四柱']['年柱']['干支']
    bz_rigan = bz['日主']['天干']
    bz_riwx = bz['日主']['五行']
    bz_sq = bz['用神分析']['身强身弱']
    zw_date = zw['输入']['公历']
    zw_sex = zw['输入']['性别']
    zw_year = zw['年干支']
    zw_ming = zw['命宫']
    zw_shen = zw['身宫']
    zw_wxj = zw['五行局']

    html = HTML_V2.format(
        date=f'{y}.{m}.{d}',
        bz_date=bz_date, bz_sex=bz_sex, bz_year=bz_year,
        bz_rigan=bz_rigan, bz_riwx=bz_riwx, bz_sq=bz_sq,
        zw_date=zw_date, zw_sex=zw_sex, zw_year=zw_year,
        zw_ming=zw_ming, zw_shen=zw_shen, zw_wxj=zw_wxj,
        bz_chart=bazi_chart(bz),
        wx_bars=wuxing_bars(bz['五行分布']),
        yj_box=yongji_box(bz),
        dy_timeline=dayun_timeline(bz),
        sh_banner=sihua_banner(zw),
        zw_grid=ziwei_grid(zw),
        sh_details=sihua_details(zw),
        dx_list=daxian_list(zw),
    )
    return html


def main():
    if len(sys.argv) < 6:
        print("用法: python html_frame.py <年> <月> <日> <时> <性别> [输出路径]")
        print("示例: python html_frame.py 2006 4 10 1 男")
        sys.exit(1)

    y, m, d, h = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    sex = sys.argv[5]
    out_path = sys.argv[6] if len(sys.argv) > 6 else os.path.join(os.path.dirname(BASE), 'frame.html')

    bz = compute_bazi(y, m, d, h, sex)
    zw = compute_ziwei(y, m, d, h, sex)
    frame = build_frame(bz, zw)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(frame)

    # 统计占位符
    import re
    placeholders = set(re.findall(r'\{(\w+)\}', frame))
    print(f'✅ HTML 框架已生成: {out_path}')
    print(f'   大小: {len(frame)} 字符')
    print(f'   占位符数量: {len(placeholders)}')
    print(f'   占位符列表: {sorted(placeholders)}')


if __name__ == '__main__':
    main()
