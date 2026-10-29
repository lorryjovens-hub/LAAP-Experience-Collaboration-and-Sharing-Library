#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kb_search.py — 共享知识库检索

用法：
    python scripts/kb_search.py "支付 回调 验签"
    python scripts/kb_search.py "electron 构建" --dir pitfalls
    python scripts/kb_search.py "误报" --top 5

设计：
  不用向量（这个库是小规模、高价值的，全文检索就够）。
  关键在「优先显示判断」——标题/铁律/怎么避免 的权重高于正文，
  因为未来能用上的正是那部分。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEARCH_DIRS = ["pitfalls", "consensus", "principles", "skills", "domains"]

# 权重：越靠前越是「判断」而非「描述」
WEIGHTED = [
    ("# ", 5.0),            # 标题
    ("**铁律", 4.0),         # 铁律
    ("## 怎么避免", 4.0),     # 怎么避免
    ("## 根因", 3.0),
    ("## 修法", 3.0),
    ("**信号", 3.0),
    ("**严重度", 2.0),
]


def tokenize(q):
    """把查询切成关键词（支持中英混合，按空白与标点切）"""
    return [t for t in re.split(r"[\s,，。、/|]+", q.strip()) if t]


def score_file(path, tokens):
    try:
        text = io.open(path, encoding="utf-8").read()
    except Exception:
        return 0, []
    lines = text.split("\n")
    total = 0.0
    hits = []
    for tok in tokens:
        tl = tok.lower()
        for i, line in enumerate(lines):
            if tl in line.lower():
                w = 1.0
                for prefix, weight in WEIGHTED:
                    if line.lstrip().startswith(prefix):
                        w = weight
                        break
                total += w
                hits.append((i + 1, line.strip()[:100]))
                if len(hits) > 6:
                    break
    return total, hits


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__)
        return

    query = args[0]
    top = 8
    only = None
    if "--top" in args:
        top = int(args[args.index("--top") + 1])
    if "--dir" in args:
        only = args[args.index("--dir") + 1]

    tokens = tokenize(query)
    if not tokens:
        print("  查询为空")
        return

    results = []
    dirs = [only] if only else SEARCH_DIRS
    for d in dirs:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for fn in os.listdir(base):
            if not fn.endswith(".md") or fn.upper() == "INDEX.MD":
                continue
            p = os.path.join(base, fn)
            score, hits = score_file(p, tokens)
            if score > 0:
                results.append((score, d, fn, hits))

    results.sort(key=lambda x: -x[0])

    print("═══ 知识库检索 ═══")
    print(f"  查询: {query}")
    print(f"  关键词: {' / '.join(tokens)}")
    print()

    if not results:
        print("  ✗ 没有匹配。")
        print()
        print("  两种可能：")
        print("    ① 真的没踩过这个坑 —— 那你踩到时请写进来（scripts/pitfall_add.py）")
        print("    ② 关键词不同 —— 换个说法，或用 --dir 指定目录")
        return

    print(f"  找到 {len(results)} 个条目（按相关度）：\n")
    for score, d, fn, hits in results[:top]:
        title = ""
        try:
            first = io.open(os.path.join(ROOT, d, fn), encoding="utf-8").readline().strip()
            title = first.lstrip("# ")
        except Exception:
            pass
        print(f"  ★ {d}/{fn}   (相关度 {score:.0f})")
        if title:
            print(f"    {title}")
        for ln, snippet in hits[:3]:
            print(f"      L{ln}: {snippet}")
        print()

    print("  提示：优先看「怎么避免」「铁律」两节——那是未来能用上的部分。")


if __name__ == "__main__":
    main()
