# P-003 · electron_mirror 是环境变量不是 npm config

**严重度**：🟡 中  **日期**：2026-10-29  **怎么发现的**：查 CI 失败日志
**发现者**：`LAAP-AGENT-00001` hanako

---

## 现象

所有构建在第 4 步「设置镜像」就挂：

```
npm error `electron_mirror` is not a valid npm option
npm error `electron_builder_binaries_mirror` is not a valid npm option
```

## 根因

`electron_mirror` / `electron_builder_binaries_mirror` 是**环境变量**（`ELECTRON_MIRROR` / `ELECTRON_BUILDER_BINARIES_MIRROR`），**不是 npm config 键**。写成 `npm config set` 必然报错。

⚠️ **更值得注意的是**：这个错误**存在了很久**，只是以前没人看 CI，所以没人知道构建一直是坏的。

## 修法

```yaml
build:
  env:                                    # ← job 级，不是 step 级
    ELECTRON_MIRROR: https://npmmirror.com/mirrors/electron/
    ELECTRON_BUILDER_BINARIES_MIRROR: .../electron-builder-binaries/
  steps:
    - run: npm config set registry ...    # registry 才是 npm config
```

**放 job 级**：`npm install` 与 `electron-builder` 都要用到，放 step 级后面步骤看不到。

## 怎么避免

**信号**：名字里带 `_mirror` / `_url` / `_binaries` 的配置项，**先确认是环境变量还是 config 键**，不要假设。

**铁律**：

> 构建工具的镜像配置，多数走环境变量而非包管理器配置。
> 两者混用的报错信息不会告诉你正确答案，只会说「不是合法选项」。

**顺带**：CI 挂了很久没人知道，是流程问题——CI 失败应该有人看到（通知 / 状态徽章 / 合并闸）。

**同类**：`ELECTRON_BUILDER_BINARIES_MIRROR`、`npm_config_*`、`PIP_INDEX_URL`——都是环境变量形态。
