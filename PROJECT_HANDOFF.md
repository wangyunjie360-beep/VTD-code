# VTD-code 项目交接文档

生成时间：2026-05-20  
交接仓库：https://github.com/wangyunjie360-beep/VTD-code.git  
本地源目录：`D:\wyj\OPenscenario`

## 1. 项目定位

本项目是一个面向 VTD / OpenSCENARIO 的“AI 主导 + 知识库工具辅助”的场景生成系统。

核心目标不是把规则硬编码成一个传统生成器，而是让大模型作为主决策者完成场景理解、XML 草拟和修复；本系统提供可追溯的结构化知识、VTD 资源知识、Schema 查询、命名约束、校验和一致性检查工具，降低模型幻觉和错误 XML 的概率。

一句话架构：

```text
用户自然语言需求
  -> AI / Claude Code / Codex 作为主生成者
  -> OpenSCENARIO MCP 工具查询 Schema、VTD 资产、命名约束、校验结果
  -> AI 生成或修复 OpenSCENARIO XML
  -> validate_xml + check_xml_intent_consistency 形成可交付证据链
```

## 2. 交付范围

本次交付包含：

- Python MCP 服务源码：`src/openscenario_mcp/`
- OpenSCENARIO 结构化 Schema 知识：`knowledge/structured/elements/`
- VTD 资源 / 命名 / 语义知识：`knowledge/structured/vtd/`
- OSC 与 VTD 绑定策略：`knowledge/structured/bridges/osc_vtd/`
- 诊断模式：`knowledge/diagnostics/patterns.json`
- 原始 Schema：`knowledge/raw/schema/OpenSCENARIO.xsd`
- 全量知识图谱导出：`knowledge/graph_export/`
- 可视化友好知识图谱：`knowledge/graph_visual/`
- Claude/GPT AI 主导完整案例：`docs/case-runs/lane-change-cn-ai-primary/`
- 旧版本地工具链案例：`docs/case-runs/lane-change-cn/`
- benchmark、测试、脚本、使用文档和阶段汇报材料
- 本交接文档：`PROJECT_HANDOFF.md`

不交付或已排除：

- `.git/`
- `.codex-tmp/`
- `.review_*`
- `.pytest_cache/`
- `src/openscenario_mcp.egg-info/`
- pytest 临时目录
- 本地审查 scratch/runtime 目录
- 大量视频逐帧截图目录，例如 `scenarios/video_frames/`、`scenarios/preview_test_frames/`、`scenarios/preview_test_frames2/`

## 3. 上传前体积

本地原始目录统计：

- 全目录：约 `1229.95 MB`
- 排除 `.git`、缓存、临时目录后：约 `929.87 MB`
- 再排除运行截图帧目录后的交付目录：约 `404.84 MB`
- 交付文件数：约 `1585`

注意：`knowledge/graph_export/graph.graphml` 单文件约 `115.3 MB`，超过 GitHub 普通 Git 单文件 100MB 限制，因此发布仓库使用 Git LFS 跟踪 `.graphml` 等大文件。

## 4. 顶层目录说明

```text
benchmarks/                     benchmark 输入、结果、无效 XML 样例
docs/                           使用文档、案例运行报告、设计/计划文档
knowledge/                      项目知识库与知识图谱产物
roads/                          OpenDRIVE 道路样例
scenarios/                      OpenSCENARIO 场景样例和少量预览媒体
scripts/                        导出、验证、案例运行、报告生成脚本
skills/                         Codex / agent 工作流 skill
src/openscenario_mcp/           MCP 服务与工具源码
tests/                          单元测试、集成测试、PowerShell 资产检查
tools/                          esmini 本地运行工具
进展汇报/                        中文阶段汇报材料和 PPT
```

## 5. 核心代码模块

### 5.1 MCP 服务入口

- `src/openscenario_mcp/__main__.py`
- `src/openscenario_mcp/server.py`
- `src/openscenario_mcp/runtime.py`

启动命令：

```powershell
py -3.14 -m openscenario_mcp
```

或：

```powershell
scripts\start_mcp_server.cmd
```

### 5.2 MCP 工具清单

主要工具都在 `src/openscenario_mcp/tools/`：

- `build_generation_packet`：从自然语言请求构造生成包，包括 intent、Schema 计划、VTD 计划、命名计划、校验计划
- `normalize_scenario_intent`：将用户需求规范化为结构化 intent
- `retrieve_spec`：检索元素、属性、概念、错误诊断相关知识
- `get_element_schema`：查询某个 OpenSCENARIO 元素的结构、属性、子节点、顺序和修复策略
- `retrieve_schema_subgraph`：按 roots / intent 返回局部 Schema 子图
- `retrieve_vtd_asset`：检索 VTD 资产候选
- `resolve_vtd_name`：解析并约束 VTD / XML 命名
- `recommend_vtd_candidates`：推荐 VTD 资产或命名候选
- `build_vtd_guidance`：聚合 VTD 命名、资产候选和约束建议
- `build_xml_guidance`：聚合 XML 生成 / 修复指导
- `validate_xml`：基于本地 XSD 做 XML Schema 校验
- `explain_validation_errors`：把校验错误转成可修复诊断
- `summarize_validation_repairs`：汇总多个错误的修复建议
- `check_xml_intent_consistency`：检查最终 XML 是否覆盖 intent 中的实体、动作、触发和停止条件

## 6. 知识库说明

### 6.1 OpenSCENARIO Schema 知识

位置：

- `knowledge/raw/schema/OpenSCENARIO.xsd`
- `knowledge/structured/elements/*.json`
- `knowledge/structured/schema_scope.json`
- `knowledge/structured/coverage_report.json`

当前结构化元素覆盖了本地 XSD 中的全量元素范围。`coverage_report.json` 用于记录缺失元素、额外元素、悬空 child 引用和元数据缺口。

再生成命令：

```powershell
py -3.14 scripts/generate_xsd_record_stubs.py
py -3.14 scripts/report_schema_coverage.py
```

### 6.2 VTD 知识

位置：

- `knowledge/structured/vtd/assets/`
- `knowledge/structured/vtd/rules/`
- `knowledge/structured/vtd/semantic/`
- `knowledge/structured/vtd/extractor_manifest.json`
- `knowledge/structured/vtd/summary.json`

内容包括：

- VTD runtime asset 快照
- signals、models、externals、tiles、styles、samples、addons、decals 等资产记录
- alias、reserved-name、country-preferences 等命名规则
- 语义层 asset families、asset variants、name policies、country taxonomy、source provenance

从本机 VTD runtime 重新抽取：

```powershell
py -3.14 scripts/build_vtd_knowledge_snapshot.py --runtime-root "D:\wyj\VTD-2020-install\VTD.2020\Runtime"
```

接手人如果没有这一路径，需要改成自己的 VTD Runtime 根目录。

### 6.3 OSC-VTD 桥接知识

位置：

- `knowledge/structured/bridges/osc_vtd/field-bindings.jsonl`
- `knowledge/structured/bridges/osc_vtd/generation-policies.jsonl`
- `knowledge/structured/bridges/osc_vtd/guidance-recipes.jsonl`

这部分用于描述 OpenSCENARIO 字段与 VTD runtime 资源、命名策略、生成策略之间的关联。

## 7. 知识图谱交付

### 7.1 全量图谱

位置：`knowledge/graph_export/`

核心文件：

- `nodes.jsonl`
- `edges.jsonl`
- `graph.graphml`
- `ontology.md`
- `traceability.md`
- `manifest.json`
- `sample-subgraph.json`
- `examples/query-examples.md`

统计：

- 节点：`66,698`
- 边：`154,886`
- 节点和边均包含 traceability
- `graph.graphml` 约 `115.3 MB`，使用 Git LFS 跟踪

全量图谱包含大量 `NamePolicy` 与 `CONSTRAINS_NAME`，适合机器查询、审计、溯源，不适合直接全图可视化。

### 7.2 可视化友好图谱

位置：`knowledge/graph_visual/`

统计：

- 节点：`810`
- 边：`1,989`
- `graph.graphml` 约 `2.28 MB`

处理策略：

- 去除 `NamePolicy`
- 去除 `CONSTRAINS_NAME`
- 去除具体 VTD asset/family/variant 爆炸节点
- 将 VTD 资源汇总为 `VTDAssetKind`

推荐给客户直接用可视化工具打开的是 `knowledge/graph_visual/graph.graphml`。

导出脚本：

```powershell
py -3.14 scripts/export_knowledge_graph.py
py -3.14 scripts/export_visual_knowledge_graph.py
```

## 8. AI 主导案例

位置：`docs/case-runs/lane-change-cn-ai-primary/`

这是按当前项目定位重跑的核心交付案例：Claude Code 通过 GPT 网关作为主生成 AI，OpenSCENARIO MCP 工具只做查询、命名、校验和一致性检查。

关键文件：

- `full-flow-report.md`：完整 Markdown 报告，包含流程图、时序图、每次 AI <-> 工具交互
- `claude-gpt-primary-stream.jsonl`：Claude/GPT 原始 stream，已移除模型内部推理和密钥
- `interactions.json`：解析后的 15 次工具调用
- `ai-primary-output.json`：AI 最终结构化输出
- `lane_change_cn_ai_primary.xosc`：最终 XML
- `independent-verification.json`：本地独立复核结果
- `summary.json`：运行摘要

运行脚本：

```powershell
py -3.14 scripts/run_ai_primary_full_flow_case.py --timeout-seconds 700 --max-budget-usd 2.00
```

只重建报告，不重新调用模型：

```powershell
py -3.14 scripts/run_ai_primary_full_flow_case.py --rebuild-report
```

该案例最终验证：

- AI 工具交互次数：`15`
- AI 侧 `validate_xml=True`
- 独立 `validate_xml=True`
- 独立 `check_xml_intent_consistency=True`
- intent matched：`entity:ego`、`lane_change`、`speed_change`、`simulation_time`、`stop_trigger`

## 9. Claude Code 接入 GPT 的正确方式

当前已验证的链路：

```text
Claude Code
  -> Anthropic Messages 格式网关
  -> https://xlabapi.com
  -> gpt-5.5
```

本机用户配置在：

```text
C:\Users\EDY\.claude\settings.json
```

关键项：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://xlabapi.com",
    "ANTHROPIC_MODEL": "gpt-5.5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "gpt-5.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "gpt-5.5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-5.5",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  },
  "model": "gpt-5.5"
}
```

密钥项 `ANTHROPIC_AUTH_TOKEN` 不写入文档和仓库。接手人需要在自己的机器上配置。

验证命令：

```powershell
claude -p "Return exactly: claude gpt bridge ok" --model gpt-5.5 --output-format json --no-session-persistence --max-budget-usd 0.10 --setting-sources user
```

预期 `modelUsage` 中出现 `gpt-5.5`。

## 10. 安装与运行

### 10.1 Python 环境

项目要求：

- Python `>=3.12`
- 本机已用 `py -3.14` 验证

安装：

```powershell
py -3.14 -m pip install -e .
```

### 10.2 MCP Server

```powershell
py -3.14 -m openscenario_mcp
```

或：

```powershell
scripts\start_mcp_server.cmd
```

### 10.3 Codex MCP 注册

参见：

- `docs/codex-mcp-setup.md`

配置示例：

```toml
[mcp_servers.openscenario]
command = "D:\\wyj\\OPenscenario\\scripts\\start_mcp_server.cmd"
```

### 10.4 Skill

项目内 skill：

- `skills/openscenario-xml-generator/SKILL.md`

安装：

```powershell
py -3.14 scripts/install_codex_skill.py
```

## 11. 测试与验证

常用验证：

```powershell
py -3.14 -m pytest -v -p no:cacheprovider
```

轻量核心验证：

```powershell
py -3.14 -m pytest tests/unit/test_validate_tool.py tests/unit/test_check_xml_intent_consistency_tool.py tests/unit/test_build_generation_packet_tool.py tests/unit/test_retrieve_vtd_asset_tool.py tests/unit/test_recommend_vtd_candidates_tool.py -v -p no:cacheprovider
```

benchmark 验证：

```powershell
py -3.14 scripts/validate_benchmark_output.py
```

OpenX 资产检查：

```powershell
powershell -ExecutionPolicy Bypass -File tests\Test-OpenXAssets.ps1 -Target all
```

esmini runtime 检查：

```powershell
powershell -ExecutionPolicy Bypass -File tests\Test-EsminiRuntime.ps1 -EsminiPath 'D:\wyj\OPenscenario\tools\esmini-v2.60.0\esmini\bin\esmini.exe' -Target scripted
```

## 12. 已实现能力清单

- MCP server 可启动并注册工具
- OpenSCENARIO XSD 本地结构化
- Schema 元素检索、子图检索、元素 schema 查询
- XML Schema 校验
- 校验错误归类和修复建议
- intent 结构化、生成包构造、XML 与 intent 一致性检查
- VTD asset 快照、检索、命名解析、候选推荐
- VTD 语义层 family / variant / name policy
- OSC-VTD bridge guidance
- Codex skill 工作流
- benchmark 样例和结果
- 全量知识图谱导出
- 可视化友好知识图谱导出
- Claude/GPT AI 主导完整案例报告
- 阶段性中文汇报和 PPT
- esmini 本地工具与基础 OpenX 场景样例

## 13. 未来待补充

### 13.1 生成质量

- 增加更多真实 VTD runtime 场景模板
- 将道路拓扑、车道方向、目标车道合法性纳入 intent consistency
- 增加交通参与者多车交互的语义检查
- 增加天气、光照、交通灯、行人、自车/他车策略的专门生成策略
- 将 `speed_change` 初始速度与 Storyboard Init 做更精确的一致性校验

### 13.2 校验能力

- 当前主要是 XSD schema 校验，还需要补充 VTD runtime 加载校验
- 增加 esmini / VTD 双运行时 smoke test
- 增加道路文件存在性、roadId/laneId 合法性检查
- 增加 OpenSCENARIO 1.1 / 1.2 / 1.4 多版本兼容策略

### 13.3 知识库

- 增量更新 VTD runtime 资产快照
- 增加更多国家/地区交通资产和命名策略
- 将当前 JSONL 知识库接入图数据库或向量索引
- 为全量知识图谱提供 Cypher / Gremlin / SPARQL 查询样例

### 13.4 AI 工作流

- 将 AI 主导案例从单个 lane-change 扩展为批量 benchmark
- 固化 Claude Code / Codex / 其他 LLM 的统一工具调用日志格式
- 增加失败案例集：无效 XML、缺失实体、非法枚举、VTD 名称冲突
- 对 prompt 模板进行版本化，避免模型升级后交互格式漂移

### 13.5 工程化

- 引入 CI：pytest、schema coverage、benchmark validation、secret scan
- 对大文件使用 Git LFS 或外部 artifact release
- 拆分 `tools/esmini-*` 为可选下载项，减小仓库体积
- 为 Windows / Linux 提供统一启动脚本
- 完善 README，让新接手人员 10 分钟内跑通 smoke test

## 14. 重要风险和注意事项

- `knowledge/graph_export/graph.graphml` 超过 100MB，必须 Git LFS。
- `tools/esmini-*` 体积较大，且可能涉及第三方工具分发许可，正式对外发布前需要确认许可。
- VTD runtime 原始安装目录没有完整提交，只提交了结构化抽取结果和测试 fixture。
- 当前 `.xosc` 示例和 MCP validator 使用的 OpenSCENARIO 版本可能不同：旧 esmini 样例偏 1.1，MCP Schema 工具当前基于本地 OpenSCENARIO 1.4.0 XSD。
- Claude/GPT 接入依赖本机 `.claude/settings.json` 和私有 API key，仓库不包含 key。
- `docs/case-runs/lane-change-cn-ai-primary/claude-gpt-primary-stream.jsonl` 已脱敏模型推理和密钥，只保留工具调用、工具结果和最终输出。

## 15. 推荐接手顺序

1. 读 `README.md` 和本文档。
2. 安装 Python 依赖：`py -3.14 -m pip install -e .`
3. 跑核心单测。
4. 启动 MCP：`py -3.14 -m openscenario_mcp`
5. 看 `docs/case-runs/lane-change-cn-ai-primary/full-flow-report.md`
6. 打开 `knowledge/graph_visual/graph.graphml` 做图谱可视化。
7. 如需机器查询全量图谱，再使用 `knowledge/graph_export/`。
8. 根据新 VTD runtime 路径重建 VTD snapshot。

## 16. 最近验证记录

最近已执行并通过：

```powershell
py -3.14 -m py_compile scripts/run_ai_primary_full_flow_case.py scripts/run_full_flow_case.py
py -3.14 -m pytest tests/unit/test_validate_tool.py tests/unit/test_check_xml_intent_consistency_tool.py tests/unit/test_build_generation_packet_tool.py tests/unit/test_retrieve_vtd_asset_tool.py tests/unit/test_recommend_vtd_candidates_tool.py -v -p no:cacheprovider
```

结果：

```text
11 passed
```

AI 主导案例独立验证：

```json
{
  "validation_ok": true,
  "intent_consistent": true,
  "missing": [],
  "extra": []
}
```

