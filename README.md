# 面试复盘 · interview-review

[下载最新版安装包](https://github.com/xingmou123/interview-review/releases/latest/download/interview-review.zip) · [版本发布与说明](https://github.com/xingmou123/interview-review/releases/latest)

点评已经发生的面试，保留原题、原答、自评和顺序，在对应题目后给出自然、具体的建议。适用于中文嵌入式技术面试和求职沟通。

以真实面试交流为尺度：回答是否抓住重点，面试官能否听懂。答得够用就写“没问题”；确实有缺口，再解释该补什么。不逐字挑无关例外，不重复整句原答，也不把每题都写成一套分析和替换话术。

完整规则见 [SKILL.md](SKILL.md)，点评尺度的具体例子见 [校准案例](references/review-calibration.md)。

需要方案判断时，讲清原理、直接影响方案成立的条件及必要取舍；问测试方法时给出相关工况的条件、操作、预期结果和判断依据，不固定套满所有异常类别。简单确认题保持简短，需要重新组织回答时才给能直接说出口的参考回答，不给每题套固定栏目或自动加学习计划。精简只删重复、套话和无关细节，关键原因、条件和步骤仍要讲清。

## 安装

首次使用建议下载上面的 `interview-review.zip`。解压后把其中整个 `interview-review` 文件夹放到 Codex 的 `skills` 目录，保留 `agents/`、`references/` 和 `scripts/`，不要只复制 `SKILL.md`。

- Windows 默认目录：`%USERPROFILE%\.codex\skills\interview-review`
- macOS / Linux 默认目录：`~/.codex/skills/interview-review`
- 设置了 `CODEX_HOME` 时：放到该目录的 `skills/interview-review` 下

已有同名 Skill 时，先保存自己的修改并备份旧目录，再替换或合并。安装后在新聊天使用 `$interview-review`；尚未识别时重启 Codex，再打开新聊天。

在 [版本发布页](https://github.com/xingmou123/interview-review/releases/latest) 的 Assets 中也能下载安装包及 SHA256 校验文件。若使用 GitHub 自动生成的 Source code ZIP，解压目录可能带分支或版本后缀，安装前把含 `SKILL.md` 的目录改名为 `interview-review`。

也可从仓库安装，取得的是仓库当前已提交版本：

Windows PowerShell：

```powershell
git clone https://github.com/xingmou123/interview-review.git "$env:USERPROFILE\.codex\skills\interview-review"
```

macOS / Linux：

```bash
git clone https://github.com/xingmou123/interview-review.git ~/.codex/skills/interview-review
```

## 使用

将面试记录粘贴进对话，或附上可读取的文件：

```text
$interview-review
复盘这份面试记录。保留原题、原答、自评和顺序，每题后补建议。
按真实面试交流的尺度判断，答得够用就写没问题。
有问题直接讲清缺什么，不重复引用原答，不逐字挑无关例外。
```

普通文字复盘只需面试记录，无需 Python、飞书工具或其他 Skill。可补充简历、项目手稿、代码和岗位要求，帮助判断技术方案及回答重点；没有这些材料也能完成能确定的复盘，个人职责和项目结果只依据已确认内容。

对空回答提供本题该准备的关键点；反问环节评价学员的问题，不把面试官介绍的设备或工作内容当成学员经历。用户已删短、改成没问题或清空的建议，未被本轮明确要求重改时按最新内容保留，不从旧稿自动恢复。

有音视频时由当前环境的媒体工具分析。仅有转写或只处理部分片段时，会说明覆盖范围；本包不附带语音识别服务。

若希望写回飞书，在请求里明确说明：

```text
$interview-review
逐题复盘这份飞书面试记录，把建议补回原文档，每题后用紫色区分。
保留原题、原答、自评和已有修改。
```

飞书写回需要自己的 `lark-cli`、登录身份和文档权限；有 `lark-doc` Skill 时可配合读取。发布脚本使用 Python 3.9+ 标准库，无需安装第三方 Python 包。本仓库不包含飞书工具或账号配置，没有工具或权限时先交付本地复盘，并说明尚未同步。

写回规则见 [飞书交付](references/feishu-delivery.md)，补丁格式和命令见 [正文检查与发布](references/publish-check.md)。脚本检查仅覆盖格式和已知句式，作者仍需逐题复核；离线测试通过不等于已完成真实飞书写回。

较大幅度的文字改稿可配合 `humanizer-zh`；它是可选辅助，本仓库不附带该 Skill。普通逐题点评使用本仓库的完整写作规则即可。

## 更新

通过 ZIP 安装的版本，下载最新安装包，保存自己的改动并备份旧目录后，再替换或合并更新。

通过 Git 安装的版本，可以在保留并处理好自己的本地修改后执行：

```powershell
git -C "$env:USERPROFILE\.codex\skills\interview-review" pull --ff-only
```

macOS / Linux 使用对应的 `~/.codex/skills/interview-review` 路径。更新后在新任务里调用，以便读取最新规则。

## 验证范围

`v2026.10.18` 在此基础上合并重复要求，补清同题分段判断、精简保留关键问题和按题控制深度的尺度，保留 DRM 与断电恢复完整案例。完成结构、相对链接、实际差异及安装包文件一致性核验，沿用的 17 项离线检查通过；整理后的规则也用于一份真实复盘的指定范围复查与局部飞书写回。本轮未重新开展两版同题匿名独立比较，旧版的独立试用记录仍归属于旧版。

`v2026.10.14` 版本完成了完整 8 题匿名独立试用、3 个缺少材料或工具的情境、17 项离线检查，以及安装包解压和文件一致性核验。原题、原答、自评、顺序与用户清空的建议均得到保留。

这些检查覆盖 Skill 规则、文字复盘和本地发布脚本；真实音视频分析、在线飞书写回与设备实测由各自工具和具体任务另行验证。

## 提交试用反馈

在 [Issues](https://github.com/xingmou123/interview-review/issues) 中提供具体例子：原题、原答、生成的建议，以及你认为应怎样点评。引用材料时去掉姓名和私人文档地址。

尤其欢迎反馈：回答已经够用却被硬挑问题、建议空泛或解释不到位、反复引用导致语气机械，以及误改原文或认错发言人的情况。

## 持续维护

本仓库直接维护可安装的 Skill，不另放一套需要手动同步的正文。

- `SKILL.md`：适用范围、点评规则和交付要求。
- `agents/openai.yaml`：显示名称和调用信息。
- `references/review-calibration.md`：不含身份信息的校准案例。
- `references/audio-review.md`：有录音或视频时的核对方式与覆盖范围。
- `references/feishu-delivery.md`、`references/publish-check.md`：飞书局部写回、正文检查及结果核验。
- `scripts/review_gate.py`、`scripts/test_review_gate.py`：正文检查和发布入口、离线测试。

改动应来自具体使用反馈。优先修正判断标准，避免因一次案例增加一条普遍禁令。规则修改时检查校准案例是否仍一致；只有案例有助于区分点评好坏时才补充。

维护者在原位置修改并核对差异；本机修改不等于远端发布。需要分发时按明确的发布要求提交、推送并生成安装包，使用者再更新。
