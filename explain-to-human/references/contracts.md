# 任务、讲解单元与缺陷的数据约定

仅在跨阶段交接、批量转换或机械检查时使用完整记录。普通对话只保留足够的简短规格，不为格式而生成大表。记录是内容约束、证据与修订结果，不含隐含思考过程。原始研究材料保持独立，正文可通过来源定位回去。

## 任务记录 task

| 字段 | 含义 |
| --- | --- |
| question | 本轮具体问题，一句话即可 |
| constraints | 用户明确的语言、篇幅、格式、修改范围等限制 |
| additions | 新增的概念、方法、结论或已有概念间的新关系 |
| prerequisites | 理解这些内容必须用到的前提；在单元中安排位置 |
| understood | 用户明确表示已理解的内容及原话证据；不得从“提过”推定 |
| confused | 用户明确表示不懂的内容及原话证据 |
| must_preserve | 不能删的公式、步骤、条件、证据及来源定位（若有） |
| feedback | 可选：用户原话、涉及位置、具体修正规则、后续是否复现；不是全局用户画像 |

`understood`、`confused` 的每项为 `{content, evidence}`。不知道就留空数组，不能虚构用户反馈。可把不影响正确性的未知列为下一步需确认事项；不能据它写出确定结论。

## 讲解单元 units

一个单元回答一个问题；不等于一段。依赖必须位于该单元之前。

| 字段 | 含义 |
| --- | --- |
| id / question / claim | 唯一标识、该单元回答的问题、主张（未知可明确写未知） |
| selected_by | `answer`、`prerequisite`、`misuse-risk` 中至少一个 |
| selection_basis | 一句内容对应说明；前提注明服务的单元，边界注明限制的结论 |
| depends_on | 已排在前面的单元 ID；无依赖则空数组 |
| must_keep | 该单元必须保留的定义、理由、中间步骤、条件、输入输出／分支 |
| evidence_ids | 全局 sources 中的 ID；自己推导可为空，但须标明推导条件 |
| gap | 尚缺什么；没有则空字符串 |

写作阶段追加：

| 字段 | 含义 |
| --- | --- |
| text | 此单元实际要展示的完整文本 |
| entry | 数组，每项 `{text, step_ids}`：入口原文及其对应正式步骤 ID |
| steps | 数组，每项 `{id, text, uses_symbols, source_ids}`：实际出现的定义、等式理由、操作、条件或证据句 |

`entry.text` 和 `steps.text` 都应是 `unit.text` 中实际存在的连续片段，避免只登记一个不存在的段落。一个正式步骤可对应多个入口句；一个入口句可对应多个步骤。无需把每个连接词、算术符号和自然段都登记。若新增重要关系没有入口，语义审核仍必须发现；脚本不会自动判断什么算重要关系。

每步的符号引用只指已登记的关键数学对象，不是全文公式解析。全局 `symbols` 每项 `{id, notation, meaning, scope, defined_in}`：符号写法、含义、范围／条件、定义所在步骤 ID；首次引用不得早于定义（同一步定义并使用可行）。符号在前文已定义仍需可追溯位置；来源是读者已明确掌握的通用记号时，无须登记为本轮新符号。

## 来源 sources

每项 `{id, locator, status, support_scope}`。`locator` 可是用户提供摘录的具体句／表、文件与页码、可访问 URL；`status` 为 `provided`、`verified` 或 `unverified`。`support_scope` 写来源支持哪些对象、条件、指标与结论，不能只写“可信”。每个正文事实与其证据保留映射；推导与示意要明确标注，不能伪装成外部来源。

机械检查只检查来源 ID 有无登记，不核验网页、文献或 support_scope 的真实性。未核实来源不自动使条件解释无效，但不能承载已证实的关键结论；由语义检查按实际影响判断。

## 缺陷 defects

每项必填：`id`、`location`、`requirement`、`evidence`、`impact`、`severity`、`repair`、`status`。

- `location`：单元／段落／步骤或相邻步骤之间。
- `requirement`：具体违反的表达、正确性或证据要求。
- `evidence`：原文短引；漏项引用缺口两端。没有材料时不能虚构引文。
- `impact`：为什么会导致错误、误用或无法继续理解／实现。
- `severity`：`blocker`、`major`、`minor`，按实际影响排序。
- `repair`：最小可执行修复，必要时指出返回哪个技能。
- `status`：`open`、`repaired`、`unverified`。后者表示需要外部证据，不能算已经修好。

用户要求审核时可用自然语言呈现这些要素；用户只要正文时不展示缺陷表。默认一轮检查、定点修复和一轮复核；复核记录修了什么、还有什么未知，不给无证据的“清晰度分数”。

## JSON 顶层与机械边界

完整 JSON 使用 `version: 1`，`phase: "plan"` 或 `"draft"`，以及 `task`、`sources`、`units`；draft 另有 `symbols`，`defects` 可省略。plan 不需要 text／entry／steps／symbols。task 的数组即使为空也保留，以区分“未登记”和“明确暂无”。

运行 `python3 <audit-explanation目录>/scripts/lint_explanation.py record.json [--strict]`。退出码：0 为结构通过，1 为结构错误（或 strict 下已登记主要缺陷未修），2 为无法读入 JSON。重复文本只产生提醒。错误输出也采用位置、要求、依据、影响和修复建议。

机械检查不代替人工／模型语义审核，不验证数学、选材和理解；它检查的是记录的一致性。真实理解需要真实交流反馈，不是脚本生成的成绩。
