#!/usr/bin/env python3
"""
命运双鉴 · 主流程编排器
完整的八字+紫微命理报告生成流水线，包含异常处理和自动清理。

用法:
  python pipeline.py <年> <月> <日> <时> <性别>
  python pipeline.py <年> <月> <日> <时> <性别> --keep-temp  # 保留中间文件（调试用）
  python pipeline.py <年> <月> <日> <时> <性别> --skip-cleanup # 不清理（LLM 调用时用此标志自行清理）
"""
import os
import sys
import json
import subprocess
import traceback
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)

# ── 输入校验 ──

def validate_input(y: int, m: int, d: int, h: int, sex: str) -> list:
    """校验输入参数，返回错误列表。空列表表示通过。"""
    errors = []

    # 年份
    if y < 1900 or y > 2100:
        errors.append(f'年份 {y} 超出精确计算范围（1900-2100），农历转换和节气计算可能不准确')

    # 月份
    if m < 1 or m > 12:
        errors.append(f'月份 {m} 不合法，应为 1-12')
        return errors  # 月份不对就没必要继续检查日期

    # 日期
    days_in_month = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
                     7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    max_d = days_in_month.get(m, 31)
    if d < 1 or d > max_d:
        errors.append(f'日期 {d} 不合法，{m} 月最多 {max_d} 天')

    # 小时
    if h < 0 or h > 23:
        errors.append(f'小时 {h} 不合法，应为 0-23')

    # 性别
    if sex not in ('男', '女'):
        errors.append(f'性别 "{sex}" 不合法，应为「男」或「女」')

    return errors


def validate_lunar_edge_case(y: int, m: int, d: int) -> list:
    """检查农历闰月等边界情况，返回警告列表"""
    warnings = []

    # 闰月检测：查找同年是否有两个相同的农历月
    # 这里用启发式检测——如果日期在春节前，年份要减一
    from data_bundle import compute_bazi, compute_ziwei
    try:
        bz = compute_bazi(y, m, d, 12, '男')  # 临时计算，只取农历信息
        zw = compute_ziwei(y, m, d, 12, '男')
        lunar_str = zw.get('输入', {}).get('农历', '')
        if '闰' in lunar_str:
            warnings.append(f'检测到农历闰月：{lunar_str}，计算结果可能需人工复核')
    except Exception:
        pass  # 边界情况检测失败不影响主流程

    return warnings


# ── 步骤执行 ──

def run_step(cmd: list, description: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """运行一个步骤，统一异常处理"""
    try:
        result = subprocess.run(
            cmd,
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace',
        )
        if result.returncode != 0:
            print(f'❌ {description} 失败 (退出码 {result.returncode})')
            if result.stderr:
                print(f'   stderr: {result.stderr.strip()[:500]}')
            if result.stdout:
                print(f'   stdout: {result.stdout.strip()[:500]}')
        return result
    except subprocess.TimeoutExpired:
        print(f'❌ {description} 超时（{timeout}秒），请检查计算引擎')
        raise
    except FileNotFoundError:
        print(f'❌ {description} 找不到命令: {cmd[0]}')
        raise
    except Exception as e:
        print(f'❌ {description} 异常: {e}')
        raise


def generate_data(y: int, m: int, d: int, h: int, sex: str) -> dict:
    """第1阶段：生成数据包 + HTML 框架 + 风格配置"""
    print('━' * 50)
    print('📊 阶段 1/4: 生成命理数据...')

    # 1a. 运行主生成器
    result = run_step(
        ['python', 'generate_report.py', str(y), str(m), str(d), str(h), sex],
        '命理数据生成'
    )
    if result.returncode != 0:
        raise RuntimeError('命理数据生成失败')

    reading_path = os.path.join(ROOT, 'reading.json')
    frame_path = os.path.join(ROOT, 'frame.html')

    if not os.path.isfile(reading_path):
        raise FileNotFoundError(f'reading.json 未生成: {reading_path}')
    if not os.path.isfile(frame_path):
        raise FileNotFoundError(f'frame.html 未生成: {frame_path}')

    # 1b. 生成风格随机化配置
    print('🎨 生成写作风格配置...')
    run_step(
        ['python', 'randomizer.py', os.path.join(ROOT, 'style_config.json')],
        '风格随机化'
    )

    # 统计占位符
    import re
    with open(frame_path, 'r', encoding='utf-8') as f:
        ph_count = len(set(re.findall(r'(?<!\{)\{(\w+)\}(?!\})', f.read())))

    reading_size = os.path.getsize(reading_path)
    frame_size = os.path.getsize(frame_path)

    print(f'   reading.json: {reading_size:,} 字节')
    print(f'   frame.html:   {frame_size:,} 字节')
    print(f'   占位符:       {ph_count} 个')
    print(f'   style_config.json: 已生成')

    return {
        'reading_path': reading_path,
        'frame_path': frame_path,
        'placeholder_count': ph_count,
    }


def assemble_report(date_str: str, sex: str) -> str:
    """第3阶段：组装 + 验证（在 LLM 生成 analysis.json 之后调用）"""
    print('━' * 50)
    print('🔧 阶段 3/4: 组装 HTML 报告...')

    frame_path = os.path.join(ROOT, 'frame.html')
    analysis_path = os.path.join(ROOT, 'analysis.json')
    out_name = f'命运双鉴_{date_str}_{sex}.html'
    out_path = os.path.join(ROOT, out_name)

    if not os.path.isfile(analysis_path):
        raise FileNotFoundError(f'analysis.json 不存在: {analysis_path}\n'
                                f'请先运行分析脚本 gen_analysis_*.py 生成 analysis.json')

    # 先验证 analysis.json
    from validator import validate_analysis_json
    passed, errors, warnings = validate_analysis_json(analysis_path)
    if errors:
        print(f'⚠️  analysis.json 存在问题:')
        for e in errors:
            print(f'   • {e}')
    if warnings:
        for w in warnings:
            print(f'   ⚠ {w}')

    # 组装
    result = run_step(
        ['python', 'assemble.py', frame_path, analysis_path, out_path],
        'HTML 组装'
    )
    if result.returncode != 0:
        raise RuntimeError('HTML 组装失败')

    # 验证输出
    from validator import check_placeholders_in_html
    ok, remaining, total = check_placeholders_in_html(out_path)
    if not ok:
        print(f'❌ HTML 中仍有 {len(remaining)} 个未替换占位符!')
        print(f'   {remaining}')
        raise RuntimeError(f'占位符替换不完整: {remaining}')

    print(f'✅ 最终报告: {out_path}')
    print(f'   {os.path.getsize(out_path) / 1024:.0f} KB')
    print(f'   占位符全部替换 ✓')
    return out_path


def cleanup(date_str: str, sex: str):
    """第4阶段：清理所有中间文件"""
    print('━' * 50)
    print('🧹 阶段 4/4: 清理中间文件...')

    to_remove = [
        os.path.join(ROOT, 'reading.json'),
        os.path.join(ROOT, 'frame.html'),
        os.path.join(ROOT, 'analysis.json'),
        os.path.join(ROOT, 'style_config.json'),
    ]

    # 清理分析脚本
    import glob
    script_pattern = os.path.join(BASE, f'gen_analysis_*_*.py')
    for f in glob.glob(script_pattern):
        to_remove.append(f)

    removed = 0
    for f in to_remove:
        if os.path.isfile(f):
            try:
                os.remove(f)
                print(f'   🗑  {os.path.basename(f)}')
                removed += 1
            except OSError as e:
                print(f'   ⚠  无法删除 {os.path.basename(f)}: {e}')

    if removed == 0:
        print('   (无中间文件需要清理)')
    else:
        print(f'   清理完成，共删除 {removed} 个中间文件')


# ── 主入口 ──

def print_usage():
    print("命运双鉴 · 八字 × 紫微斗数 —— 完整流水线")
    print()
    print("用法: python pipeline.py <年> <月> <日> <时> <性别> [选项]")
    print()
    print("示例:")
    print("  python pipeline.py 2006 4 10 1 男")
    print("  python pipeline.py 2006 4 10 1 男 --keep-temp")
    print()
    print("选项:")
    print("  --keep-temp    保留中间文件（调试用）")
    print("  --skip-cleanup 不清理中间文件（LLM 调用时自行管理）")
    print()
    print("流水线阶段:")
    print("  1. 输入校验 → 数据生成 (reading.json + frame.html + style_config.json)")
    print("  2. LLM 分析（需人工/AI介入，生成 analysis.json）")
    print("  3. 组装 HTML → 占位符验证")
    print("  4. 清理中间文件")
    print()
    print("注意: 阶段 2 需要 Claude 读取 reading.json + style_config.json，")
    print("      编写分析脚本并运行，生成 analysis.json。")


def main():
    if len(sys.argv) < 6:
        print_usage()
        sys.exit(1)

    try:
        y, m, d, h = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        sex = sys.argv[5]
    except ValueError:
        print('❌ 年、月、日、时必须为整数')
        print_usage()
        sys.exit(1)

    keep_temp = '--keep-temp' in sys.argv or '--skip-cleanup' in sys.argv
    skip_cleanup = '--skip-cleanup' in sys.argv

    # ═══ 阶段 0: 输入校验 ═══
    print('━' * 50)
    print('🔍 输入校验...')

    errors = validate_input(y, m, d, h, sex)
    if errors:
        print(f'❌ 输入不合法:')
        for e in errors:
            print(f'   • {e}')
        sys.exit(1)

    warnings = validate_lunar_edge_case(y, m, d)
    if warnings:
        for w in warnings:
            print(f'   ⚠ {w}')

    print(f'✅ 输入: {y}年{m}月{d}日 {h}时 · {sex}命')

    try:
        # ═══ 阶段 1: 生成数据 ═══
        generate_data(y, m, d, h, sex)

        # ═══ 阶段 2: 提示 LLM 介入 ═══
        print('━' * 50)
        print('🤖 阶段 2/4: 等待 LLM 分析...')
        print(f'   📖 请阅读: {os.path.join(ROOT, "reading.json")}')
        print(f'   🎨 风格提示: {os.path.join(ROOT, "style_config.json")}')
        print(f'   ✍️  创建分析脚本: scripts/gen_analysis_<{y:04d}{m:02d}{d:02d}>_<{sex}>.py')
        print(f'   ▶️  运行脚本生成 analysis.json')
        print()
        print(f'   完成后运行: python assemble.py frame.html analysis.json 命运双鉴_{y:04d}{m:02d}{d:02d}_{sex}.html')

        # 如果 LLM 已经生成了 analysis.json，继续
        analysis_path = os.path.join(ROOT, 'analysis.json')
        if os.path.isfile(analysis_path):
            date_str = f'{y:04d}{m:02d}{d:02d}'
            assemble_report(date_str, sex)

            # ═══ 阶段 4: 清理 ═══
            if not skip_cleanup:
                cleanup(date_str, sex)
            else:
                print('⏭️  跳过清理（--skip-cleanup）')
        else:
            print()
            print('⏸️  流水线暂停，等待 analysis.json 生成后继续...')
            print(f'   手动继续: python assemble.py frame.html analysis.json 命运双鉴_{y:04d}{m:02d}{d:02d}_{sex}.html')

    except KeyboardInterrupt:
        print('\n⚠️  用户中断')
        sys.exit(130)
    except Exception as e:
        print(f'\n❌ 流水线失败: {e}')
        traceback.print_exc()

        # 失败时也尝试清理（保留中间文件以便调试）
        if keep_temp:
            print(f'\n💡 中间文件已保留在 {ROOT}（--keep-temp）')
        elif not skip_cleanup:
            print(f'\n🧹 清理中间文件...')
            try:
                # 只清理数据文件，保留可能成功的 HTML
                for f in ['reading.json', 'frame.html', 'style_config.json']:
                    fp = os.path.join(ROOT, f)
                    if os.path.isfile(fp):
                        os.remove(fp)
                        print(f'   🗑 {f}')
            except Exception:
                pass

        sys.exit(1)


if __name__ == '__main__':
    main()
