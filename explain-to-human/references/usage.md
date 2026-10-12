# 调用与安装边界

四个同级目录：`explain-to-human`、`plan-explanation`、`write-explanation`、`audit-explanation`。共享材料位于第一个目录；不要只复制子技能而遗漏它。

在 Codex 输入示例：

- `$explain-to-human 解释……；我懂……，卡在……。`
- `$plan-explanation 根据这些材料规划怎样回答……，只给简短内容规格。`
- `$write-explanation 按这份规格写……，保留这些步骤和条件。`
- `$audit-explanation 检查下面讲解，指出有原文依据的主要缺陷并作最小修订。`
- `$explain-to-human 只改这句，让对象和关系更清楚：……`

普通请求也允许被自动选择，但**允许不等于保证触发**。显式调用入口后，它规定选材→写作→检查与定点修复的顺序；局部任务可缩短执行路径，简单事实直接作答。技能不会常驻拦截所有会话，也不会自动更改系统提示、AGENTS.md 或其他技能。

当前 [Codex 官方文档](https://learn.chatgpt.com/docs/build-skills) 列出的用户级安装目录为 `~/.agents/skills/`，项目级目录为项目中的 `.agents/skills/`。把四个技能目录一起放入目标位置，保持同级并保留各自的配套文件。Codex 会自动发现技能变化；若尚未出现，重启 Codex 后再显式调用。其他运行环境按其实际安装说明确定位置。

机械检查只在已有 JSON 交接记录时需要：`python3 <audit-explanation目录>/scripts/lint_explanation.py record.json --strict`。不需要为正常聊天运行脚本或生成 JSON。
