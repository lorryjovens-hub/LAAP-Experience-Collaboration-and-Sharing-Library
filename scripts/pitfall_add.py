#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pitfall_add.py — 记一条避坑指南

用法：
    python scripts/pitfall_add.py
    （交互式，逐项问你）

    python scripts/pitfall_add.py --title "xxx" --symptom "yyy" \
        --cause "zzz" --fix "www" --avoid "vvv"

铁律（见 CHARTER.md 第二、三条）：
  只有「修法」的条目不合格。
  必须写清「怎么发现的」——那决定下次该在哪里设卡。
"""
import io
import os
import re
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIT = os.path.join(ROOT, "pitfalls")


def slugify(title):
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-")
    return s[:40] if s else "untitled"


def next_id():
    existing = [f for f in os.listdir(PIT) if re.match(r"P-\d+", f)]
    nums = [int(m.group(1)) for f in existing if (m := re.match(r"P-(\d+)", f))]
    return max(nums) + 1 if nums else 1


def ask(label, hint=""):
    q = f"  {label}"
    if hint:
        q += f"  （{hint}）"
    q += "\n    > "
    try:
        return input(q).strip()
    except EOFError:
        return ""


def main():
    args = sys.argv[1:]

    def arg(name, default=""):
        if name in args:
            i = args.index(name)
            return args[i + 1] if i + 1 < len(args) else default
        return default

    print("═══ 记一条避坑指南 ═══")
    print("  铁律：只有「修法」的条目不合格，必须写清「怎么发现的」。\n")

    title = arg("--title") or ask("标题", "一句话说清坑是什么")
    if not title:
        print("  ✗ 标题不能为空")
        return

    severity = arg("--severity") or ask("严重度", "高 / 中 / 低") or "中"
    symptom = arg("--symptom") or ask("现象", "当时看到了什么")
    cause = arg("--cause") or ask("根因", "为什么会这样")
    fix = arg("--fix") or ask("修法", "怎么解决")
    avoid = arg("--avoid") or ask("怎么避免", "下次遇到什么信号该警惕")
    discovered = arg("--discovered") or ask(
        "怎么发现的", "测试抓的 / 本地跑 CI 抓的 / 查日志抓的…（这一节最重要）"
    )

    sev_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(severity, "🟡")
    n = next_id()
    pid = f"P-{n:03d}"
    fname = f"{pid}-{slugify(title)}.md"
    today = datetime.date.today().isoformat()

    content = f"""# {pid} · {title}

**严重度**：{sev_icon} {severity}  **日期**：{today}  **怎么发现的**：{discovered}
**发现者**：`LAAP-AGENT-00001` hanako

---

## 现象

{symptom}

## 根因

{cause}

## 修法

{fix}

## 怎么避免

{avoid}

## 怎么发现的（这一节最重要）

{discovered}

---

*写这条时记得：「怎么修的」只救一次，「怎么发现的」救每一次。*
"""

    path = os.path.join(PIT, fname)
    io.open(path, "w", encoding="utf-8").write(content)

    # 追加到 INDEX
    idx = os.path.join(PIT, "INDEX.md")
    if os.path.exists(idx):
        s = io.open(idx, encoding="utf-8").read()
        entry = f"\n### [{pid} · {title}]({fname})\n**严重度**：{sev_icon} {severity} · **怎么发现的**：{discovered}\n{symptom[:80]}\n"
        # 插到第一个 `### ` 之前（保持倒序）
        m = re.search(r"\n### ", s)
        if m:
            s = s[: m.start()] + entry + s[m.start():]
        else:
            s += entry
        io.open(idx, "w", encoding="utf-8").write(s)

    print(f"\n  ✅ 已写入 pitfalls/{fname}")
    print(f"     INDEX.md 已更新")
    print()
    print("  下一步：")
    print(f"    git add pitfalls/{fname} pitfalls/INDEX.md")
    print('    git commit -F msg.txt && git push')


if __name__ == "__main__":
    main()
