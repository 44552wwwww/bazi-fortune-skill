#!/usr/bin/env python3
"""
命运双鉴 · 统一生成器（LLM 驱动版）
用法: python generate_report.py <年> <月> <日> <时> <性别>
输出: reading.json（供 LLM 阅读的数据包）+ frame.html（带占位符的HTML框架）+ style_config.json（写作风格提示）

工作流:
  1. python generate_report.py → reading.json + frame.html + style_config.json
  2. LLM 读取 reading.json + style_config.json，生成个性化分析 → analysis.json
  3. python assemble.py frame.html analysis.json → 最终 HTML（自动验证占位符）
"""
import sys, os, json, re, io

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from bazi_calculator import compute_bazi
from ziwei_calculator import compute_ziwei
from data_bundle import build_bundle
from html_frame import build_frame

# 修复被计算器模块覆盖的 stdout
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def generate(y, m, d, h, sex):
    """生成数据包和 HTML 框架"""
    bz = compute_bazi(y, m, d, h, sex)
    zw = compute_ziwei(y, m, d, h, sex)

    # 输出目录（skill 根目录）
    out_dir = os.path.dirname(BASE)

    # Step 1: 生成数据包
    bundle = build_bundle(bz, zw)
    reading_path = os.path.join(out_dir, 'reading.json')
    with open(reading_path, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    # Step 2: 生成 HTML 框架
    frame = build_frame(bz, zw)
    frame_path = os.path.join(out_dir, 'frame.html')
    with open(frame_path, 'w', encoding='utf-8') as f:
        f.write(frame)

    # 占位符统计
    placeholders = set(re.findall(r'\{(\w+)\}', frame))

    # Step 3: 生成风格随机化配置
    try:
        from randomizer import generate_config
        style_config = generate_config()
        style_path = os.path.join(out_dir, 'style_config.json')
        with open(style_path, 'w', encoding='utf-8') as f:
            json.dump(style_config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'⚠️  风格配置生成失败（非致命）: {e}')
        style_path = None

    return {
        'reading': reading_path,
        'frame': frame_path,
        'style_config': style_path,
        'placeholders': sorted(placeholders),
        'bz': bz,
        'zw': zw,
    }


if __name__ == '__main__':
    if len(sys.argv) < 6:
        print("用法: python generate_report.py <年> <月> <日> <时> <性别>")
        print("示例: python generate_report.py 2006 4 10 1 男")
        print()
        print("新工作流（LLM 驱动）:")
        print("  1. python generate_report.py → reading.json + frame.html")
        print("  2. LLM 读取 reading.json → 生成 analysis.json")
        print("  3. python assemble.py frame.html analysis.json → 最终 HTML")
        sys.exit(1)

    try:
        y, m, d, h = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        sex = sys.argv[5]
        if sex not in ('男', '女'):
            print("性别请输入「男」或「女」")
            sys.exit(1)
        if y < 1900 or y > 2100:
            print(f'⚠️  警告：{y}年超出精确计算范围(1900-2100)，农历转换和节气计算可能不够准确。')
        if m < 1 or m > 12 or d < 1 or d > 31 or h < 0 or h > 23:
            print("日期或时间不合法，请检查输入。")
            sys.exit(1)

        result = generate(y, m, d, h, sex)

        r_size = len(open(result["reading"], "r", encoding="utf-8").read())
        f_size = len(open(result["frame"], "r", encoding="utf-8").read())
        print(f'✅ 数据包: {result["reading"]}')
        print(f'   ({r_size} 字符)')
        print(f'✅ 框架:   {result["frame"]}')
        print(f'   ({f_size} 字符, {len(result["placeholders"])} 个占位符)')
        if result.get("style_config"):
            print(f'✅ 风格:   {result["style_config"]}')
        print()
        print('📋 下一步: 将 reading.json + style_config.json 交给 LLM 进行个性化分析，生成 analysis.json')
        print('   然后运行: python assemble.py frame.html analysis.json <输出路径>')
    except Exception as e:
        print(f'❌ 生成失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
