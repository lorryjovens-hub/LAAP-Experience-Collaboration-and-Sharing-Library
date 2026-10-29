#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
task_prep.py — 任务准备：路由 skill + 查知识库坑

**为什么要有这个**（DEV_CHARTER 第十六条）：

  route.py 只回答「有什么工具」，不回答「这事我踩过坑吗」。
  两者都要查——用错工具是慢，重复踩坑是蠢。

用法：
    python task_prep.py "给 billing.cjs 补支付回调测试"
    python task_prep.py "electron 打包" --no-skills     # 只查坑
    python task_prep.py "排版公众号" --no-kb           # 只路由

输出：
    ① 该用什么 skill（语义路由）
    ② 这事踩过什么坑（内部库 + 社区库）
    ③ 有没有相关共识（可执行判断）

铁律：**动手前先跑这个**。查到坑 = 省下一次踩坑的时间。
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROUTER = os.path.dirname(HERE)
D = os.path.dirname

# 知识库位置（内部库优先，社区库兜底）
KB_INTERNAL = r"C:\Users\user\Desktop\OH-WorkSpace\Laaper-Team-Shared-Collaboration-Knowledge-Base"
KB_COMMUNITY = r"C:\Users\user\Desktop\OH-WorkSpace\LAAP-Experience-Collaboration-and-Sharing-Library"

# skill-router 位置（多个候选，本机布局不固定）
ROUTE_PY_CANDIDATES = [
    os.path.join(HERE, "route.py"),
    r"D:\LAAP\skills\skill-router\scripts\route.py",
    os.path.join(SKILL_ROUTER, "scripts", "route.py"),
    os.path.join(os.path.expanduser("~"), ".pi", "agent", "skills", "skill-router", "scripts", "route.py"),
]

WEIGHTED = [
    ("# ", 5.0),
    ("**铁律", 4.0),
    ("## 怎么避免", 4.0),
    ("## 根因", 3.0),
    ("## 修法", 3.0),
    ("**信号", 3.0),
]


def tokenize(q):
    return [t for t in re.split(r"[\s,，。、/|()（）]+", q.strip()) if len(t) > 1]


def search_kb(query, top=4):
    """在两个知识库里搜，返回 (来源, 文件, 分数, 命中行)"""
    tokens = tokenize(query)
    if not tokens:
        return []
    out = []
    for label, root in (("内部库", KB_INTERNAL), ("社区库", KB_COMMUNITY)):
        for sub in ("pitfalls", "consensus", "principles", "experience"):
            base = os.path.join(root, sub)
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
                    score, hits = 0.0, []
                    for tok in tokens:
                        tl = tok.lower()
                        for i, line in enumerate(text.split("\n")):
                            if tl in line.lower():
                                w = 1.0
                                for prefix, weight in WEIGHTED:
                                    if line.lstrip().startswith(prefix):
                                        w = weight
                                        break
                                score += w
                                if len(hits) < 2:
                                    hits.append(line.strip()[:88])
                                break
                    if score > 0:
                        rel = os.path.relpath(p, root).replace("\\", "/")
                        out.append((score, label, sub, rel, hits))
    out.sort(key=lambda x: -x[0])
    return out[:top]


def route_skills(query):
    """调 skill-router 的 route.py"""
    script = next((p for p in ROUTE_PY_CANDIDATES if os.path.exists(p)), None)
    if not script:
        return None
    try:
        r = subprocess.run(
            [sys.executable, script, query],
            capture_output=True, text=True, timeout=180,
            cwd=os.path.dirname(script),
        )
        return (r.stdout or "").strip()
    except Exception as e:
        return f"(路由失败: {e})"


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__)
        return

    query = args[0]
    do_skills = "--no-skills" not in args
    do_kb = "--no-kb" not in args

    print("═" * 62)
    print(f"  任务准备：{query}")
    print("═" * 62)

    # ① skill 路由
    if do_skills:
        print("\n【① 该用什么工具】")
        out = route_skills(query)
        if out:
            # 只显示前 5 个候选
            lines = out.split("\n")
            shown = 0
            for ln in lines:
                if re.match(r"^\d\.\d+", ln) or re.match(r"^\s+\S", ln):
                    print("  " + ln[:100])
                    shown += 1
                    if shown > 12:
                        print("  …")
                        break
                elif ln.strip():
                    print("  " + ln[:100])
        else:
            print("  (skill-router 不可用)")

    # ② 知识库查坑
    if do_kb:
        print("\n【② 这事踩过什么坑 / 有什么共识】")
        hits = search_kb(query)
        if hits:
            for score, label, sub, rel, lines in hits:
                tag = {"pitfalls": "🔴 坑", "consensus": "📌 共识",
                       "principles": "⭐ 原则", "experience": "💡 经验"}.get(sub, sub)
                print(f"  {tag} [{label}] {rel}  (相关度 {score:.0f})")
                for l in lines:
                    print(f"        {l}")
            print()
            print("  ⚠ 动手前先读这几条——查到坑 = 省下一次踩坑的时间。")
        else:
            print("  ✗ 没有匹配。")
            print()
            print("  两种可能：")
            print("    ① 真没踩过 → 你踩到时请写进来（scripts/pitfall_add.py）")
            print("    ② 关键词不同 → 换个说法再查一次")

    print("\n" + "═" * 62)


if __name__ == "__main__":
    main()
