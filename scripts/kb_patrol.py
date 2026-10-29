#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kb_patrol.py — 知识库定期巡检：找出过时/可疑/待升格的条目

用法：
    python scripts/kb_patrol.py              # 全量巡检，输出报告
    python scripts/kb_patrol.py --days 90    # 只看 90 天前的
    python scripts/kb_patrol.py --json       # 机器可读输出（接 CI 用）
    python scripts/kb_patrol.py --stale-only # 只输出过时可疑项

【为什么要巡检】（CHARTER 第六条 / SECURITY.md 第六节）
  Lorry 2026-10-29 要求：「对于过时的经验和技能要修改更新」。
  但没人会记得主动去翻旧条目 —— 所以要有机器定期提醒。

【巡检四类】
  ① 过时可疑   超过 N 天未更新，且涉及快速演进领域（工具/版本/API）
  ② 待升格     只有「是什么」没有「为什么」的条目
  ③ 疑似重复   标题/关键词高度相似的条目
  ④ 待交叉     提到具体工具但没链接到对应 pitfalls 的条目

【重要】
  巡检**只提醒，不自动删改**。
  标记过时比删除更安全 —— 「曾经以为是这样，后来发现不是」本身是知识。
"""
import io
import os
import re
import sys
import json
import datetime
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["pitfalls", "consensus", "principles", "skills", "domains", "experience"]

# 快速演进领域的关键词 —— 命中则「过时风险」更高
FAST_MOVING = [
    "electron", "npm", "node", "react", "vue", "vite", "webpack",
    "api", "sdk", "版本", "version", "beta", "alpha", "deprecated",
    "云", "cloud", "aws", "阿里云", "cloudflare", "docker", "k8s",
    "llm", "gpt", "claude", "deepseek", "模型",
]

# 「是什么」而没有「为什么」的信号
SHALLOW_SIGNALS = ["注意", "小心", "记得", "应该", "要记得", "别忘了"]
DEEP_SIGNALS = ["根因", "因为", "所以", "为什么", "理由", "怎么发现", "信号", "铁律"]


def parse_date_from_content(text, mtime):
    """优先从内容里找日期，找不到用文件修改时间"""
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return datetime.date.fromtimestamp(mtime)


def iter_entries():
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _, fns in os.walk(base):
            for fn in fns:
                if not fn.endswith(".md") or fn.upper() == "INDEX.MD":
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    text = io.open(p, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                rel = os.path.relpath(p, ROOT).replace("\\", "/")
                yield rel, text, os.path.getmtime(p)


def main():
    args = sys.argv[1:]
    days = 180
    if "--days" in args:
        try:
            days = int(args[args.index("--days") + 1])
        except Exception:
            pass
    as_json = "--json" in args
    stale_only = "--stale-only" in args

    today = datetime.date.today()
    stale_cutoff = today - datetime.timedelta(days=days)

    stale, shallow, dup_candidates, no_link = [], [], [], []
    total = 0
    titles = {}

    for rel, text, mtime in iter_entries():
        total += 1
        d = parse_date_from_content(text, mtime)
        age_days = (today - d).days

        # ① 过时可疑：超期 + 涉及快速演进领域
        hits = [k for k in FAST_MOVING if k.lower() in text.lower()]
        if d < stale_cutoff and hits:
            stale.append({
                "path": rel, "date": d.isoformat(), "age_days": age_days,
                "fast_moving": sorted(set(hits))[:5],
            })

        # ② 待升格：只有浅层信号，没有深层信号
        shallow_n = sum(1 for s in SHALLOW_SIGNALS if s in text)
        deep_n = sum(1 for s in DEEP_SIGNALS if s in text)
        if shallow_n > 0 and deep_n == 0 and len(text) < 600:
            shallow.append({"path": rel, "shallow_hits": shallow_n})

        # ③ 疑似重复：标题真正相似（用字符集 Jaccard，不是暴力归一）
        first = text.strip().split("\n")[0] if text.strip() else rel
        title = re.sub(r"^[#\s]+", "", first)[:40]
        # 用 2-gram 字符集做相似度，而不是把所有符号剥光（剥光会让万物碰撞）
        def grams(s):
            s = re.sub(r"[\s\W]+", "", s.lower())
            return set(s[i:i + 2] for i in range(len(s) - 1)) or {s[:1]}
        g = grams(title)
        matched = False
        for prev_rel, prev_g in list(titles.items())[:400]:
            inter = len(g & prev_g)
            union = len(g | prev_g) or 1
            if inter / union > 0.72:            # Jaccard > 0.72 才算疑似重复
                dup_candidates.append({"a": prev_rel, "b": rel, "sim": round(inter / union, 2)})
                matched = True
                break
        if not matched:
            titles[rel] = g

        # ④ 待交叉：提到具体工具但没链接到 pitfalls
        if "pitfalls/" not in text and re.search(r"(electron|npm|git|PowerShell|D1|Cloudflare)", text, re.I):
            no_link.append(rel)

    report = {
        "patrol_date": today.isoformat(),
        "stale_threshold_days": days,
        "total_entries": total,
        "stale_suspects": stale,
        "shallow_entries": shallow,
        "duplicate_candidates": dup_candidates,
        "unlinked_tool_refs": no_link[:20],
    }

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("═" * 62)
    print(f"  知识库巡检报告 · {today.isoformat()}")
    print(f"  扫描 {total} 条 · 过时阈值 {days} 天")
    print("═" * 62)

    def section(title, items, render):
        if stale_only and title != "① 过时可疑":
            return
        print(f"\n【{title}】 {len(items)} 项")
        if not items:
            print("  ✓ 无")
            return
        for it in items[:12]:
            render(it)
        if len(items) > 12:
            print(f"  … 另有 {len(items) - 12} 项")

    section("① 过时可疑（超期 + 涉及快速演进领域）", stale,
            lambda x: print(f"  ⚠ {x['path']}\n      {x['age_days']} 天前 · 涉及 {', '.join(x['fast_moving'])}"))

    section("② 待升格（只有「是什么」没有「为什么」）", shallow,
            lambda x: print(f"  ↑ {x['path']}"))

    section("③ 疑似重复", dup_candidates,
            lambda x: print(f"  ≈ {x['a']}\n    ↔ {x['b']}"))

    section("④ 待交叉（提到工具但没链接 pitfalls）", no_link,
            lambda x: print(f"  → {x}"))

    print("\n" + "─" * 62)
    print("  处理建议：")
    print("    · 过时可疑 → 标记「⚠️ 已过时」+ 加「新做法」，不删除")
    print("    · 待升格   → 补「根因 / 怎么发现的 / 信号」三节")
    print("    · 疑似重复 → 合并，保留信息更全的那条")
    print("    · 待交叉   → 加「见 pitfalls/P-xxx」交叉引用")
    print()
    print("  ⚠ 巡检只提醒，不自动删改。")
    print("    标记过时比删除更安全 ——「曾经以为是这样，后来发现不是」本身是知识。")
    print("─" * 62)

    # 退出码：有可疑项时非零（可接 CI 告警）
    sys.exit(1 if (stale or shallow) else 0)


if __name__ == "__main__":
    main()
