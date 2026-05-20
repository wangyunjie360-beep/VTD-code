# OpenSCENARIO 项目中文使用说明

## 1. 现在项目算不算做完了

结论先说：

- 这个项目已经到了“可用”状态。
- 它已经具备：
  - 本地 OpenSCENARIO XML 知识库
  - MCP 服务
  - Codex skill
  - schema 校验
  - 报错解释
  - 结构化辅助信息
  - benchmark guidance 辅助包
- 但它目前不是“全自动一键生成 XML 的封闭系统”。

推荐理解方式：

- 大模型负责：理解需求、设计 XML、决定具体写法、决定修复方案
- MCP 负责：查规则、提供结构辅助、做 schema 校验、解释报错

也就是：

`LLM 主导，MCP 辅助`

## 2. 这个库现在能做什么

当前仓库里主要有两部分能力：

1. OpenX 资源包
   - `roads/`
   - `scenarios/`
   - `tools/`
   - `tests/`

2. OpenSCENARIO MCP + Codex skill
   - `src/openscenario_mcp/`
   - `skills/openscenario-xml-generator/`
   - `knowledge/structured/`
   - `benchmarks/`

MCP 当前主要提供这些能力：

- `retrieve_vtd_asset`
  当你要选择具体的 VTD 运行时资产、模型、信号、贴图或外部资源时，先查真实候选项
- `resolve_vtd_name`
  当你准备把名字写进 XML，且这个名字可能与 VTD 运行时资源或命名规则冲突时，再做名称解析
- `normalize_scenario_intent`
  当你希望先把自然语言需求稳定落成结构化场景意图时使用
- `build_generation_packet`
  当你希望一次性拿到 intent、schema plan、VTD plan、naming plan、validation plan 时使用
- `retrieve_schema_subgraph`
  当你需要的是场景级结构闭环，而不是单个 element 的 schema 记录时使用
- `recommend_vtd_candidates`
  当你想同时看 runtime 候选、国家偏好和名称解析结果时使用
- `retrieve_spec`
  通过自然语言查元素、属性、错误主题，并返回 `strategy_summary`
- `get_element_schema`
  返回某个元素的完整结构信息和 `strategy`
- `build_vtd_guidance`
  可选的 VTD 组合包，会把 `retrieve_vtd_asset` 与 `resolve_vtd_name` 的结果合并起来
- `validate_xml`
  用本地 schema 校验 XML
- `explain_validation_errors`
  返回报错解释和 `repair_strategy`
- `build_xml_guidance`
  把检索、schema、修复建议合并成一个 guidance 包
- `summarize_validation_repairs`
  当一个 XML 草稿同时出现多个校验错误时，把它们压缩成更适合局部修复的 repair batch
- `check_xml_intent_consistency`
  在 schema 通过之后，再把 XML 和原始 intent 做一致性核对

本地脚本还提供两个辅助入口：

- `scripts/build_guidance_packet.py`
  给任意 prompt 文件生成 `.guidance.json`
- `scripts/build_benchmark_guidance.py`
  给 benchmark prompt 生成 `.guidance.json`

## 3. 安装步骤

### 3.1 Python 依赖

建议使用本机当前约定的 Python 3.14。

在仓库根目录执行：

```powershell
py -3.14 -m pip install -e .
```

如果你只是想做基本检查，也可以跑：

```powershell
py -3.14 -m pytest -v -p no:cacheprovider
```

### 3.2 本地启动 MCP 服务

直接启动：

```powershell
py -3.14 -m openscenario_mcp
```

或者用稳定启动脚本：

```powershell
scripts\start_mcp_server.cmd
```

## 4. 如何让 Codex 发现这个 MCP

编辑：

```text
C:\Users\EDY\.codex\config.toml
```

加入：

```toml
[mcp_servers.openscenario]
command = "D:\\wyj\\OPenscenario\\scripts\\start_mcp_server.cmd"
```

保存后，重新打开一个新的 Codex 会话。

说明：

- 这个脚本会优先用 `py -3.14`
- 如果找不到 `py`，会回退到 `C:\Python314\python.exe`

## 5. 如何安装这个 skill

在仓库根目录执行：

```powershell
py -3.14 scripts/install_codex_skill.py
```

它会把项目里的 skill 安装到：

```text
C:\Users\EDY\.codex\skills\openscenario-xml-generator\SKILL.md
```

安装完以后，重新开一个新的 Codex 会话。

## 6. 如何在 Codex 里调用这个 skill

最简单的方法不是记命令，而是直接在对话里明确说：

```text
请使用 openscenario-xml-generator skill，帮我生成可用于 VTD 的场景文件。
```

或者更完整一点：

```text
请使用 openscenario-xml-generator skill。
目标：根据我的场景描述生成可用于 VTD 的 OpenSCENARIO 场景文件。
要求：
- 由你主导 XML 设计
- MCP 只作为结构辅助和校验辅助
- 先生成 XML
- 然后用 validate_xml 校验
- 如果失败，再用 explain_validation_errors 做局部修复
```

你也可以直接给 benchmark prompt：

```text
请使用 openscenario-xml-generator skill。
请根据 benchmarks/prompts/minimal-single-vehicle.md 生成可用于 VTD 的场景文件。
```

如果你平时说得更短，也可以直接这样说，Codex 也应该把它理解成同一类任务：

```text
生成 OpenX 场景代码
```

```text
生成 VTD 场景文件
```

```text
根据场景描述生成仿真场景文件
```

## 7. 推荐使用方式

### 方式 A：直接让 Codex 生成

适合：

- 需求已经比较清楚
- 结构不复杂
- 你不需要单独保存 guidance 包

流程：

1. 在 Codex 对话里说明要使用 `openscenario-xml-generator`
2. 给出你的场景需求
3. 先让 Codex 调用 `normalize_scenario_intent`
4. 如果需求比较复杂，再调用 `build_generation_packet` 或 `retrieve_schema_subgraph`
5. 对 VTD 运行时敏感字段，再调用 `recommend_vtd_candidates`
6. 让 Codex 生成可用于 VTD 的 XML 场景文件
7. 让 Codex 调用 `validate_xml`
8. 如果失败，再调用 `explain_validation_errors`；当错误较多时优先用 `summarize_validation_repairs`
9. schema 通过之后，再调用 `check_xml_intent_consistency`

### VTD 命名与约束闭环

当你要把具体的模拟器资源名、运行时资产名或可能冲突的标识符写进 XML 时，推荐固定按下面顺序走：

1. 先调用 `retrieve_vtd_asset`，确认这个 `asset_kind` 在当前 VTD 快照里有哪些真实候选项。
2. 再调用 `resolve_vtd_name`，确认候选名字在目标命名空间里是否有冲突。
   - 如果返回 `hard_constraint=True`，说明这是硬约束，XML 里必须写 `canonical_target`，不要保留 soft rename 的 `override_mapping`。
   - 如果返回 `hard_constraint=False`，并且命名空间是 `scenario_object`、`variable`、`external_object` 这类 soft namespace，那么 XML 里应写 `safe_name`；如果你还想保留用户原始命名意图，可以在 XML 外侧保留 `override_mapping`。
3. 只有在 VTD 资产和名称都稳定之后，再调用 `build_xml_guidance`，或者用 `retrieve_spec` + `get_element_schema` 处理 OpenSCENARIO 的结构问题。
4. 完整草稿写完后，再调用 `validate_xml`；失败时再用 `explain_validation_errors` 做局部修复。

### 方式 B：先生成 `.guidance.json`，再让 Codex 或外部 agent 生成

适合：

- 你想复用同一个 prompt
- 你想给新会话/外部 agent 一个稳定的辅助包
- 你想减少模型在结构判断上的试错

流程：

1. 先生成 `.guidance.json`
2. 再把 prompt 和 `.guidance.json` 一起交给 Codex 或外部 agent
3. 让模型自己决定 XML 写法
4. 用 MCP 做校验和修复闭环

## 8. 一个完整示例

下面给一个最推荐、也最稳定的示例。

### 8.1 先生成 benchmark guidance 包

```powershell
py -3.14 scripts/build_benchmark_guidance.py `
  --benchmark minimal-single-vehicle `
  --results-dir benchmarks/results
```

执行后会生成：

```text
benchmarks/results/minimal-single-vehicle.guidance.json
```

### 8.2 在 Codex 里这样说

可以直接复制下面这段：

```text
请使用 openscenario-xml-generator skill。

输入材料：
- prompt 文件：benchmarks/prompts/minimal-single-vehicle.md
- guidance 文件：benchmarks/results/minimal-single-vehicle.guidance.json

要求：
- 由你主导 XML 设计，不要把 guidance 当成刚性模板
- prompt_text 是最高优先级
- guidance 只用于帮助你处理结构风险、variant、choice、sequence、reference 和修复顺序
- 先输出 XML
- 再调用 validate_xml 做校验
- 如果失败，再调用 explain_validation_errors 做局部修复
- 尽量保持最小、保守、可通过 schema 的 OpenSCENARIO XML

输出内容：
- 最终 XML
- 关键假设说明
- 如果还有问题，列出 remaining blockers
```

### 8.3 如果你不想先生成 guidance

也可以直接说：

```text
请使用 openscenario-xml-generator skill。
创建一个最小合理的 OpenSCENARIO XML：
- 一个名为 ego 的车辆
- 车辆初始就在道路上
- 以稳定速度行驶
- 场景在 5 秒后结束

要求：
- 你自己决定 XML 设计
- 只在结构风险点使用 MCP 辅助
- 生成后必须调用 validate_xml
- 校验失败时调用 explain_validation_errors 并做局部修复
```

## 9. 常用文件位置

### 配置与启动

- Codex MCP 配置：
  `C:\Users\EDY\.codex\config.toml`
- MCP 启动脚本：
  `scripts/start_mcp_server.cmd`
- skill 安装脚本：
  `scripts/install_codex_skill.py`

### 技能与知识

- skill 文件：
  `skills/openscenario-xml-generator/SKILL.md`
- 结构化元素知识库：
  `knowledge/structured/elements/`
- schema：
  `knowledge/raw/schema/OpenSCENARIO.xsd`

### benchmark 与 guidance

- prompt：
  `benchmarks/prompts/`
- 已提交 benchmark 结果：
  `benchmarks/results/`
- benchmark guidance 配置：
  `benchmarks/guidance-inputs.json`

### VTD 快照重建

- VTD 快照构建脚本：
  `scripts/build_vtd_knowledge_snapshot.py`
- 本地重建命令：

```powershell
py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "D:\wyj\VTD-2020-install\VTD.2020\Runtime"
```

这个命令会刷新 `knowledge/structured/vtd/` 下的结构化快照。只要本机 VTD 运行时资源、别名或命名规则发生变化，就应该重新执行一次。

现在 `knowledge/structured/vtd/semantic/` 下还会同时刷新：

- `country-taxonomy.json`
- `name-policies.jsonl`
- `asset-families.jsonl`
- `asset-variants.jsonl`
- `source-provenance.jsonl`

## 10. 当前最实用的建议

如果你平时就是用 Codex 对话来生成 XML，那么建议你这样用：

1. 装好 MCP
2. 装好 skill
3. 新开 Codex 会话
4. 直接说“请使用 openscenario-xml-generator skill”
5. 让模型自己设计 XML
6. 只把 MCP 当成结构辅助和校验辅助

如果你准备把任务分给新的会话或者外部 agent，再加一步：

7. 先生成 `.guidance.json`

这样最符合你当前想要的工作方式：

- 模型自由度高
- MCP 只做辅助
- 但又不会完全失去 schema 约束和修复闭环
