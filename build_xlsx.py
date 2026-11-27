# -*- coding: utf-8 -*-
"""合并子代理生成的 JSON 题目文件 -> 考试宝可导入的 Excel 题库。

- 校验：题量、题型、选项数、答案字母合法性、多选答案 2~3 个且升序、判断题 A/B、
  题干去重、答案字母与选项数一致。
- 输出：单工作表 xlsx，表头采用考试宝"批量导入"官方 Excel 模板列名。
"""
import json
import os
import re
import sys

QUESTIONS_DIR = r"D:\ProjectCode\death-note\questions"
OUT_XLSX = r"D:\ProjectCode\death-note\前端开发岗位考试题库_1100题.xlsx"

CHAPTERS = ["ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "ch10", "ch11"]
CHAPTER_NAMES = {
    "ch01": "考点1：HTML与语义化标记",
    "ch02": "考点2：CSS基础与布局",
    "ch03": "考点3：JavaScript语言核心",
    "ch04": "考点4：ES6+与异步编程",
    "ch05": "考点5：DOM、BOM与事件",
    "ch06": "考点6：浏览器原理与网络基础",
    "ch07": "考点7：HTTP与数据交互",
    "ch08": "考点8：Vue框架",
    "ch10": "考点10：前端工程化、构建与性能优化",
    "ch11": "考点11：前端安全与跨端技术",
}

TYPE_FILES = [("single_a", "single", 33), ("single_b", "single", 33),
              ("multi", "multiple", 22), ("judge", "judge", 22)]

HEADER = [
    "所属题库", "题型", "是否转义题干", "题干", "标签", "题目分数", "题目难度",
    "过期时间", "是否转义试题解析", "试题解析", "语言属性", "是否绝密", "答案",
    "是否转义选项", "选项A", "选项B", "选项C", "选项D", "选项E", "选项F", "选项G",
]

TYPE_LABEL = {"single": "单选题", "multiple": "多选题", "judge": "判断题"}
TYPE_SCORE = {"single": 2, "multiple": 3, "judge": 1}


def normalize(text):
    return re.sub(r"\s+", "", text or "")


def safe_option(o):
    """考试宝会把纯数字选项转成 xx.0，纯数字选项加反引号包裹为代码字面量。"""
    if isinstance(o, str) and o.strip().isdigit():
        return "`" + o.strip() + "`"
    return o


def main():
    problems = []
    rows = []
    seen = set()
    stats = {
        "single": 0, "multiple": 0, "judge": 0,
        "single_ans": {"A": 0, "B": 0, "C": 0, "D": 0},
        "judge_ans": {"A": 0, "B": 0},
        "multi_ans_len": {},
        "difficulty": {},
        "per_chapter": {ch: {"single": 0, "multiple": 0, "judge": 0} for ch in CHAPTERS},
    }

    for ch in CHAPTERS:
        for suffix, qtype, expected in TYPE_FILES:
            fp = os.path.join(QUESTIONS_DIR, f"{ch}_{suffix}.json")
            if not os.path.exists(fp):
                problems.append(f"缺少文件: {fp}")
                continue
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                problems.append(f"{fp} 不是JSON数组"); continue
            if len(data) != expected:
                problems.append(f"{fp} 题数 {len(data)} != {expected}")
            for i, q in enumerate(data):
                if not isinstance(q, dict):
                    problems.append(f"{fp}[{i}] 不是对象"); continue
                qtext = q.get("question", "")
                nq = normalize(qtext)
                if not nq:
                    problems.append(f"{fp}[{i}] 题干为空")
                if nq in seen:
                    problems.append(f"重复题干: {qtext[:50]}...")
                seen.add(nq)

                t = q.get("type")
                if t != qtype:
                    problems.append(f"{fp}[{i}] type={t} 与文件名不符")
                opts = q.get("options") or []
                ans = q.get("answer", "")
                ana = q.get("analysis", "")
                if not ana:
                    problems.append(f"{fp}[{i}] 解析为空")
                diff = q.get("difficulty")
                stats["difficulty"][diff] = stats["difficulty"].get(diff, 0) + 1

                if t == "judge":
                    if opts != ["正确", "错误"]:
                        problems.append(f"{fp}[{i}] 判断题选项应为[正确,错误]: {opts}")
                    if ans not in ("A", "B"):
                        problems.append(f"{fp}[{i}] 判断题答案应为A/B: {ans}")
                    stats["judge"] += 1
                    stats["judge_ans"][ans] += 1
                    optA, optB = "正确", "错误"
                    opts_out = ["正确", "错误"]
                else:
                    if len(opts) != 4:
                        problems.append(f"{fp}[{i}] 选择项数应为4: {len(opts)}")
                    letters = [chr(65 + j) for j in range(len(opts))]
                    if t == "single":
                        if ans not in letters:
                            problems.append(f"{fp}[{i}] 单选答案非法: {ans}")
                        stats["single"] += 1
                        stats["single_ans"][ans] = stats["single_ans"].get(ans, 0) + 1
                    else:
                        al = "".join(sorted(set(ans))) if ans else ""
                        if not (2 <= len(al) <= 3 and set(al) <= set(letters)):
                            problems.append(f"{fp}[{i}] 多选答案非法: {ans}")
                        if ans != al:
                            problems.append(f"{fp}[{i}] 多选答案未升序/重复: {ans}")
                        stats["multiple"] += 1
                        stats["multi_ans_len"][len(al)] = stats["multi_ans_len"].get(len(al), 0) + 1
                    opts_out = opts

                chapter = q.get("chapter") or CHAPTER_NAMES[ch]
                tag = q.get("tag", "")
                rows.append([
                    "前端开发岗位考试题库",  # 所属题库
                    TYPE_LABEL[t],          # 题型
                    "否",                   # 是否转义题干
                    qtext,                  # 题干
                    tag,                    # 标签
                    TYPE_SCORE[t],          # 题目分数
                    diff,                   # 题目难度
                    "",                     # 过期时间
                    "否",                   # 是否转义试题解析
                    ana,                    # 试题解析
                    1,                      # 语言属性(中文)
                    "否",                   # 是否绝密
                    ans,                    # 答案
                    "否",                   # 是否转义选项
                    *(safe_option(o) for o in opts_out),  # 选项A..D
                    "", "", "",             # 选项E/F/G
                ])
                stats["per_chapter"][ch][t] += 1

    # 统计多选答案字母候选数量
    if problems:
        print("!! 校验发现问题（前 40 条）：")
        for p in problems[:40]:
            print(" -", p)
        print(f"共 {len(problems)} 个问题，中止生成 Excel。")
        sys.exit(1)

    total = stats["single"] + stats["multiple"] + stats["judge"]
    print(f"合计题目: {total}（单选 {stats['single']} / 多选 {stats['multiple']} / 判断 {stats['judge']}）")
    print("单选答案分布:", stats["single_ans"])
    print("判断答案分布:", stats["judge_ans"])
    print("多选答案长度分布:", stats["multi_ans_len"])
    print("难度分布(1~5):", stats["difficulty"])
    for ch in CHAPTERS:
        c = stats["per_chapter"][ch]
        print(f"  {ch} {CHAPTER_NAMES[ch]}: 单选{c['single']} 多选{c['multiple']} 判断{c['judge']}")

    # 写入 Excel
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "题库"
    ws.append(HEADER)
    hfill = PatternFill("solid", fgColor="4472C4")
    hfont = Font(bold=True, color="FFFFFF")
    for c in ws[1]:
        c.fill = hfill
        c.font = hfont
        c.alignment = Alignment(vertical="center")
    for r in rows:
        ws.append(r)
    widths = [20, 10, 12, 60, 12, 10, 10, 12, 14, 50, 10, 10, 10, 12, 30, 30, 30, 30, 12, 12, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:U{ws.max_row}"
    wb.save(OUT_XLSX)
    print("已写入:", OUT_XLSX, "行数(含表头):", ws.max_row)


if __name__ == "__main__":
    main()