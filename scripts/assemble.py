#!/usr/bin/env python3
"""
命运双鉴 · 组装器（增强版）
用法: python assemble.py <frame.html> <analysis.json> [输出路径]
将 Claude 生成的分析文本注入 HTML 框架，生成最终报告。
自动验证 analysis.json 结构完整性和占位符替换情况。
"""
import sys
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))


def assemble(frame_path: str, analysis_path: str, output_path: str, strict: bool = True) -> dict:
    """
    组装最终 HTML
    strict=True: 占位符未完全替换时报错退出
    返回统计信息
    """
    # ── 读取框架 ──
    if not os.path.isfile(frame_path):
        raise FileNotFoundError(f'框架文件不存在: {frame_path}')
    with open(frame_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # ── 读取分析 ──
    if not os.path.isfile(analysis_path):
        raise FileNotFoundError(f'分析文件不存在: {analysis_path}')
    try:
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f'analysis.json 格式错误: {e}')

    if not isinstance(analysis, dict):
        raise TypeError(f'analysis.json 应为对象，实际为 {type(analysis).__name__}')

    # ── 导入验证器进行预检 ──
    from validator import validate_analysis_json, REQUIRED_KEYS
    passed, errors, warnings = validate_analysis_json(analysis_path)
    if errors:
        print(f'⚠️  analysis.json 预检发现问题:')
        for e in errors:
            print(f'   ❌ {e}')
        if strict:
            raise ValueError('analysis.json 验证失败，请修复后重试')
    if warnings:
        for w in warnings:
            print(f'   ⚠ {w}')

    # ── 占位符替换 ──
    replaced = 0
    missing = []
    empty_vals = []

    for key in REQUIRED_KEYS:
        placeholder = '{' + key + '}'
        if placeholder not in html:
            missing.append(key)
            continue
        value = analysis.get(key, '')
        if value is None:
            value = ''
        value_str = str(value)
        if not value_str.strip():
            empty_vals.append(key)
        html = html.replace(placeholder, value_str)
        replaced += 1

    # ── 替换额外的非标准 key ──
    for key, value in analysis.items():
        if key not in REQUIRED_KEYS:
            placeholder = '{' + key + '}'
            if placeholder in html:
                html = html.replace(placeholder, str(value))
                replaced += 1

    # ── 检查残留占位符 ──
    remaining = set(re.findall(r'(?<!\{)\{(\w+)\}(?!\})', html))
    # 过滤：不是我们占位符前缀的不算
    valid_prefixes = ('BAZI_', 'ZIWEI_', 'DAYUN_', 'PALACE_', 'SIHUA_', 'DAXIAN_',
                      'CROSS_REF', 'VERDICT_CARDS', 'NARRATIVE_', 'ACTION_')
    residual_placeholders = {p for p in remaining if any(p.startswith(vp) for vp in valid_prefixes)}

    # ── 输出 ──
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    report = {
        'output': output_path,
        'replaced': replaced,
        'missing': missing,
        'empty_values': empty_vals,
        'residual': sorted(residual_placeholders),
        'size_kb': os.path.getsize(output_path) / 1024,
    }

    # ── 打印报告 ──
    print(f'✅ 已生成: {os.path.basename(output_path)}')
    print(f'   替换: {replaced}/{len(REQUIRED_KEYS)} 个占位符')
    if missing:
        print(f'   ❌ 缺失: {len(missing)} 个 — {missing}')
    if empty_vals:
        print(f'   ⚠ 空值: {len(empty_vals)} 个 — {empty_vals}')
    if residual_placeholders:
        print(f'   ❌ 残留: {len(residual_placeholders)} 个 — {sorted(residual_placeholders)}')
    print(f'   大小: {report["size_kb"]:.0f} KB')

    if strict and (missing or residual_placeholders):
        raise RuntimeError(
            f'占位符未完全替换: 缺失 {len(missing)}, 残留 {len(residual_placeholders)}'
        )

    return report


def main():
    if len(sys.argv) < 3:
        print("用法: python assemble.py <frame.html> <analysis.json> [输出路径] [--loose]")
        print("示例: python assemble.py frame.html analysis.json ../命运双鉴_20060410_男.html")
        print()
        print("选项:")
        print("  --loose  宽松模式：占位符未完全替换不报错（调试用）")
        sys.exit(1)

    frame_path = sys.argv[1]
    analysis_path = sys.argv[2]

    if len(sys.argv) > 3 and not sys.argv[3].startswith('--'):
        out_path = sys.argv[3]
    else:
        out_path = os.path.join(os.path.dirname(BASE), '..', '命运双鉴_output.html')

    strict = '--loose' not in sys.argv

    try:
        assemble(frame_path, analysis_path, out_path, strict=strict)
    except Exception as e:
        print(f'\n❌ 组装失败: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
