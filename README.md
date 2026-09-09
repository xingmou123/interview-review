# 面试复盘 · interview-review

点评已经发生的面试，保留原题、原答、自评和顺序，在对应题目后给出自然、具体的建议。适用于中文嵌入式技术面试和求职沟通。

以真实面试交流为尺度：回答是否抓住重点，面试官能否听懂。答得够用就写“没问题”；确实有缺口，再解释该补什么。不逐字挑无关例外，不重复整句原答，也不把每题都写成一套分析和替换话术。

完整规则见 [SKILL.md](SKILL.md)，点评尺度的具体例子见 [校准案例](references/review-calibration.md)。

## 安装

Windows PowerShell：

```powershell
git clone https://github.com/xingmou123/interview-review.git "$env:USERPROFILE\.codex\skills\interview-review"
```

macOS / Linux：

```bash
git clone https://github.com/xingmou123/interview-review.git ~/.codex/skills/interview-review
```

如果设置了 `CODEX_HOME`，将仓库放到该目录的 `skills/interview-review` 下。安装目录已有同名旧版时，先保留自己的修改，再备份旧文件夹或合并更新。

也可以下载仓库 ZIP，解压后将包含 `SKILL.md` 的目录命名为 `interview-review`，放进 skills 目录。

安装后打开一个新任务，使用 `$interview-review` 调用；若尚未识别，重启 Codex 后再打开任务。

## 使用

将面试记录粘贴进对话，或附上可读取的文件：

```text
$interview-review
复盘这份面试记录。保留原题、原答、自评和顺序，每题后补建议。
按真实面试交流的尺度判断，答得够用就写没问题。
有问题直接讲清缺什么，不重复引用原答，不逐字挑无关例外。
```

若希望写回飞书，在请求里明确说明：

```text
$interview-review
逐题复盘这份飞书面试记录，把建议补回原文档，每题后用紫色区分。
保留原题、原答、自评和已有修改。
```

飞书读写需要自己的 `lark-cli`、`lark-doc` Skill 和文档权限，本仓库不包含飞书工具或账号配置。暂时没有飞书工具时，可以先粘贴正文进行复盘。

较大幅度的文字改稿可配合 `humanizer-zh`；它是可选辅助，本仓库不附带该 Skill。普通逐题点评使用本仓库的完整写作规则即可。

## 更新

通过 Git 安装的版本，可以在保留并处理好自己的本地修改后执行：

```powershell
git -C "$env:USERPROFILE\.codex\skills\interview-review" pull --ff-only
```

macOS / Linux 使用对应的 `~/.codex/skills/interview-review` 路径。更新后在新任务里调用，以便读取最新规则。

## 提交试用反馈

在 [Issues](https://github.com/xingmou123/interview-review/issues) 中提供具体例子：原题、原答、生成的建议，以及你认为应怎样点评。引用材料时去掉姓名和私人文档地址。

尤其欢迎反馈：回答已经够用却被硬挑问题、建议空泛或解释不到位、反复引用导致语气机械，以及误改原文或认错发言人的情况。

## 持续维护

本仓库直接维护可安装的 Skill，不另放一套需要手动同步的正文。

- `SKILL.md`：适用范围、点评规则和交付要求。
- `agents/openai.yaml`：显示名称和调用信息。
- `references/review-calibration.md`：不含身份信息的校准案例。

改动应来自具体使用反馈。优先修正判断标准，避免因一次案例增加一条普遍禁令。规则修改时检查校准案例是否仍一致；只有案例有助于区分点评好坏时才补充。

维护者在此仓库修改、检查差异后提交并推送，使用者通过 `git pull --ff-only` 更新。
