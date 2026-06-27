#!/usr/bin/env python3
"""
命运双鉴 · 输出验证器
用法: python validator.py <analysis.json> [frame.html]
检查 analysis.json 结构完整性、占位符替换情况、HTML 格式正确性
"""
import json
import os
import re
import sys
from typing import Tuple, List, Set

# 71 个必需的占位符 key
REQUIRED_KEYS: Set[str] = {
    f'BAZI_CARD_{i}' for i in range(6)
} | {
    f'BAZI_ANALYSIS_{i}' for i in range(7)
} | {
    f'DAYUN_DETAIL_{i}' for i in range(8)
} | {
    f'ZIWEI_CARD_{i}' for i in range(6)
} | {
    f'PALACE_{i}' for i in range(12)
} | {
    'SIHUA_DETAIL_LU', 'SIHUA_DETAIL_QUAN', 'SIHUA_DETAIL_KE', 'SIHUA_DETAIL_JI'
} | {
    f'DAXIAN_DETAIL_{i}' for i in range(12)
} | {
    'CROSS_REF_ROWS', 'VERDICT_CARDS'
} | {
    f'NARRATIVE_{i}' for i in range(8)
} | {
    f'ACTION_{i}' for i in range(6)
}

# 最小字数要求（防止空内容）
MIN_LENGTHS = {
    'BAZI_CARD': 60,
    'BAZI_ANALYSIS': 80,
    'DAYUN_DETAIL': 30,
    'ZIWEI_CARD': 60,
    'PALACE': 50,
    'SIHUA_DETAIL': 50,
    'DAXIAN_DETAIL': 20,
    'CROSS_REF_ROWS': 200,
    'VERDICT_CARDS': 300,
    'NARRATIVE': 150,
    'ACTION': 40,
}


def validate_analysis_json(filepath: str) -> Tuple[bool, List[str], List[str]]:
    """
    验证 analysis.json 的结构完整性
    返回: (通过, 错误列表, 警告列表)
    """
    errors = []
    warnings = []

    # ── 文件存在性 ──
    if not os.path.isfile(filepath):
        return False, [f'文件不存在: {filepath}'], []

    # ── JSON 解析 ──
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f'JSON 解析失败: {e}'], []
    except Exception as e:
        return False, [f'读取文件失败: {e}'], []

    if not isinstance(data, dict):
        return False, [f'analysis.json 应为 JSON 对象，实际为 {type(data).__name__}'], []

    # ── 必填 key 检查 ──
    existing_keys = set(data.keys())
    missing_keys = REQUIRED_KEYS - existing_keys
    extra_keys = existing_keys - REQUIRED_KEYS

    if missing_keys:
        errors.append(f'缺少 {len(missing_keys)} 个必填占位符: {sorted(missing_keys)}')
    if extra_keys:
        warnings.append(f'发现 {len(extra_keys)} 个多余 key: {sorted(extra_keys)}')

    # ── 空值检查 ──
    empty_keys = [k for k, v in data.items() if v is None or (isinstance(v, str) and v.strip() == '')]
    if empty_keys:
        errors.append(f'{len(empty_keys)} 个占位符值为空: {sorted(empty_keys)}')

    # ── 最小字数检查 ──
    for key, value in data.items():
        if not isinstance(value, str):
            continue
        # 找到匹配的前缀
        for prefix, min_len in MIN_LENGTHS.items():
            if key.startswith(prefix):
                actual_len = len(value.strip())
                if actual_len < min_len:
                    warnings.append(f'{key} 内容过短（{actual_len} 字 < 建议 {min_len} 字）')
                break

    return len(errors) == 0, errors, warnings


def check_placeholders_in_html(html_path: str) -> Tuple[bool, List[str], int]:
    """
    检查 HTML 文件中的残留占位符
    返回: (通过, 残留占位符列表, 总数)
    """
    if not os.path.isfile(html_path):
        return False, [f'HTML 文件不存在: {html_path}'], 0

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 查找 {XXX} 格式的占位符（排除 CSS 中的 {{}}）
    placeholders = set(re.findall(r'(?<!\{)\{(\w+)\}(?!\})', html))

    # 过滤掉非占位符的变量（如 CSS 中用到的合法变量名）
    # 我们的占位符都以特定前缀开头
    valid_prefixes = ('BAZI_', 'ZIWEI_', 'DAYUN_', 'PALACE_', 'SIHUA_', 'DAXIAN_',
                      'CROSS_REF', 'VERDICT_CARDS', 'NARRATIVE_', 'ACTION_')
    remaining = {p for p in placeholders if any(p.startswith(vp) for vp in valid_prefixes)}

    return len(remaining) == 0, sorted(remaining), len(placeholders)


def print_report(passed: bool, errors: List[str], warnings: List[str]):
    """打印验证报告"""
    if passed and not warnings:
        print('✅ 验证通过：analysis.json 结构完整')
        return

    if errors:
        print(f'❌ 发现 {len(errors)} 个错误:')
        for e in errors:
            print(f'   • {e}')
    if warnings:
        print(f'⚠️  发现 {len(warnings)} 个警告:')
        for w in warnings:
            print(f'   • {w}')
    if passed:
        print('✅ 基本验证通过（有警告但不影响生成）')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python validator.py <analysis.json> [frame.html|output.html]")
        print("      验证 analysis.json 结构完整性")
        print("      如果提供 HTML 文件，同时检查占位符替换情况")
        sys.exit(1)

    json_path = sys.argv[1]
    passed, errors, warnings = validate_analysis_json(json_path)
    print_report(passed, errors, warnings)

    if len(sys.argv) > 2:
        html_path = sys.argv[2]
        ok, remaining, total = check_placeholders_in_html(html_path)
        if remaining:
            print(f'\n❌ HTML 中仍有 {len(remaining)} 个未替换占位符: {remaining}')
        else:
            print(f'\n✅ HTML 占位符全部替换完成（共 {total} 处检查）')

    sys.exit(0 if passed else 1)
