# P-007 · PowerShell 内联脚本的编码/引号陷阱

**严重度**：🟡 中  **怎么发现的**：反复踩
**适用**：Windows + PowerShell 5.1/7 任何自动化脚本

---

## 现象（多个，容易误判为「玄学」）

1. **中文/特殊符号被搅乱**：here-string 里的中文在某些场景变乱码
2. **括号被当子表达式**：提交信息里的 `(xxx)` 被 PowerShell 解析报错
3. **内联 Python/Node 的引号被吃**：多层引号嵌套后解析错位
4. **`ConvertFrom-Json` 对带 BOM/注释的 JSON 报错**
5. **`Write-Output "═══"` 报「缺少 `)`」**——box-drawing 字符有时触发解析器问题

## 根因

PowerShell 的解析器**先解析再执行**：`$()`、`()`、`@'` 都是语法结构，不是纯文本。

多层嵌套时（PowerShell → 临时文件 → Python → JSON），某一层的引号会被上一层提前消费。**每一层都认为自己在处理字符串，实际上在处理语法。**

## 修法

**写文件，不要内联**：

```powershell
@'
# -*- coding: utf-8 -*-
import io
...
'@ | Out-File -Encoding utf8 "$env:TEMP\_task.py"
python "$env:TEMP\_task.py"
Remove-Item "$env:TEMP\_task.py" -Force
```

**提交信息用文件传**：

```powershell
$msg | Out-File -Encoding utf8 "_m.txt"
git commit -F "_m.txt"    # 而不是 git commit -m "$msg"
```

## 怎么避免

**铁律**：

> **超过 3 行的脚本，写成文件再执行。**
> 内联省下的几秒钟，会在引号地狱里加倍还回来。

**触发信号**（看到任一就直接写文件）：

- 要在 PowerShell 里嵌 Python / Node / JSON
- 提交信息含 `(` `)` `$` 或中文
- 字符串里有 box-drawing 字符（`═` `★` `✓`）
- 多层引号嵌套超过 2 层

**顺带**：`Out-File -Encoding utf8` 在 PS 5.1 会写 BOM，Python 读时用 `encoding="utf-8"` 通常没问题，但 JSON 解析器可能挑剔——需要无 BOM 时用 `[System.IO.File]::WriteAllText()`。
