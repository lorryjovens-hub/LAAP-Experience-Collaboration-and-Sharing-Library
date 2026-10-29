# P-008 · git 钩子的相对路径假设

**严重度**：🟡 中  **怎么发现的**：装完钩子一提交就炸
**适用**：任何 git hook / 安装后被移动的脚本

---

## 现象

装好提交签名钩子，第一次 commit 就炸：

```
Error: Cannot find module 'hooks/sign-commit.cjs'
Require stack:
- .git/hooks/prepare-commit-msg
```

## 根因

钩子里写了：

```js
const MY_DIR = path.join(__dirname);   // 假设脚本在原目录
```

但钩子被**安装到 `.git/hooks/`** 下，`__dirname` 变成了 `.git/hooks`，**路径必然找不到**。

原脚本在开发时能跑（它在 `hooks/` 里），装到 `.git/hooks/` 后运行位置变了，路径假设失效。

## 修法

**① 显式回退一级**：

```js
const MY_DIR = path.join(__dirname, '..');   // 从 .git/hooks 回到仓库根
```

**② 更稳：用 git 自己的定位**（不依赖位置）：

```js
const { execSync } = require('child_process');
const ROOT = execSync('git rev-parse --show-toplevel').toString().trim();
```

**③ 最稳：安装时注入绝对路径**（install 脚本把路径写死进钩子）。

## 怎么避免

**铁律**：

> **脚本的运行位置 ≠ 开发位置。**
> 钩子、CI 脚本、部署脚本、插件、安装器，都会被移到别处执行。

**自查清单**：

- [ ] `__dirname` / `cwd` / 相对路径，在**被安装后**还成立吗？
- [ ] 有没有用 `git rev-parse --show-toplevel` 这类**不依赖位置**的方法？
- [ ] 钩子/插件写完**真实装上跑过一次**吗？（不能只在原目录跑）

**同类场景**：

| 场景 | 运行位置 |
|---|---|
| git hook | `.git/hooks/` |
| CI 脚本 | 临时工作目录 |
| npm bin | `node_modules/.bin/` |
| 编辑器插件 | 插件宿主的沙箱目录 |
| Docker | 容器内 `/app` 或任意 WORKDIR |

**一条通用原则**：**任何「会被安装/复制/移动」的脚本，都不要假设自己的位置。**
