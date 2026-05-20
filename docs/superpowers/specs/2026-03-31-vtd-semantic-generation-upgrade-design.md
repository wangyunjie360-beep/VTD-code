# VTD 语义知识层与生成闭环升级设计

## Goal

在现有 phase-1 成果上，把项目从“可查询 schema + 可查询 VTD 资产 + 可做命名冲突检查”的辅助系统，升级为一套面向 VTD 场景开发的、`LLM-first, MCP-assisted` 的结构化生成支撑系统。

升级后的系统目标不是让 MCP 取代大模型生成 XML，而是让 MCP 为大模型提供更强的中间层：

- 把自然语言场景需求稳定落成结构化场景意图
- 把 OpenSCENARIO 语法知识和 VTD 运行时知识真正桥接起来
- 把 VTD 资产、变体、国家版本、命名策略从“平面快照”升级为“可解释语义层”
- 把校验失败从“逐条报错解释”升级为“可聚合、可定位、可回写的 repair guidance”
- 把 benchmark 从“存在性检查”升级为“可 fail 的质量闸门”

系统仍保持以下分工：

- 大模型负责场景理解、方案选择、候选权衡、XML 草拟和最终决策
- MCP 负责结构化检索、候选聚合、约束提示、命名收敛、校验与修复辅助
- 当 OpenSCENARIO 通用知识与 VTD 静态资产定义发生冲突时，优先采用 VTD 侧事实和规则

## Why This Upgrade Is Needed

phase-1 已经完成了两个重要底座：

1. OpenSCENARIO 结构化语法知识库
2. VTD 资产快照与命名冲突工具

但当前系统仍有 4 个核心短板：

### 1. 缺意图闭环

`ScenarioIntent` 目前主要停留在 skill 约定和 benchmark sidecar 中，还没有进入 MCP 工具面，也没有被 runtime 和校验闭环真正消费。

这会导致：

- prompt 到 XML 的中间状态不可稳定复用
- `intent_consistent` 更多依赖人工或 sidecar 自报
- benchmark 可以“格式正确但语义漂移”

### 2. 缺语义派生层

当前 VTD 知识主要是标准化快照：

- `assets/*.jsonl`
- `rules/*.jsonl`

它适合事实查询和溯源，但还不足以支撑更高鲁棒性的生成决策，因为它没有显式表达：

- 同一语义资产族的不同国家/版本/材质变体
- 哪些命名空间属于 hard constraint，哪些属于 soft constraint
- 哪些 OpenSCENARIO 字段应该绑定到哪类 VTD 资产
- 哪些候选项是推荐项、降级项、排除项

### 3. 缺场景级 MCP 服务

当前 MCP 更像“工具箱”，不是“中间层服务”：

- 有单元素 schema 查询
- 有 VTD 资产检索和名称解析
- 有 XML 校验和错误解释

但没有：

- 意图归一工具
- schema 子图/闭包查询
- 场景级候选推荐
- repair batch 聚合
- XML 与意图一致性核对
- 一次性 generation packet

### 4. 缺硬评测闸门

当前 benchmark 已有基础资产，但仍偏弱：

- guidance 没有提交版 gold
- 正向样例少
- 负样例少
- sidecar 契约未被严格执行
- `bounded_failure` 不会让回归失败

这意味着升级后的系统即使功能更多，也还缺少真正的质量控制。

## Design Principles

### Principle 1: LLM First

大模型拥有场景建模和最终决策自由度。

系统不走“纯规则驱动生成 XML”路线，不把服务端做成硬编码模板引擎。

### Principle 2: MCP Assisted

MCP 只负责高价值、结构化、可校验、可追溯的辅助信息：

- 事实
- 约束
- 候选
- 冲突
- 修复建议

MCP 不替模型做完整场景决策。

### Principle 3: VTD Priority

当存在冲突时，优先级固定为：

1. `VTD 静态资产事实`
2. `VTD 区域/变体/命名策略`
3. `OpenSCENARIO 结构化语法知识`
4. `模型自由推断`

### Principle 4: Derived Semantic Layers

原始快照保留为事实层，不直接推翻。

所有更智能、更适合生成的知识都以“派生层”形式叠加，而不是污染原始快照。

### Principle 5: Narrow, Explainable Contracts

每个 MCP 工具都应该返回可解释、可追溯、可组合的结果，而不是模糊的大包。

## Target Architecture

升级后采用 6 层架构。

### Layer 1: OpenSCENARIO Schema Base

继续保留现有：

- `knowledge/structured/elements/`
- `ElementRecord`
- `KnowledgeBase`

职责：

- XSD 结构知识
- choice/sequence/all 约束
- attribute / enum / parent context
- element-level strategy
- 基础 repair hint

### Layer 2: VTD Snapshot Base

继续保留现有：

- `knowledge/structured/vtd/assets/*.jsonl`
- `knowledge/structured/vtd/rules/*.jsonl`
- `VtdAssetRecord`
- `VtdNameRule`
- `VtdKnowledgeBase`

职责：

- VTD 原始事实层
- canonical name、alias、source path 溯源
- snapshot 构建和重建

### Layer 3: VTD Semantic Derived

新增目录：

- `knowledge/structured/vtd/semantic/asset-families.jsonl`
- `knowledge/structured/vtd/semantic/asset-variants.jsonl`
- `knowledge/structured/vtd/semantic/name-policies.jsonl`
- `knowledge/structured/vtd/semantic/source-provenance.jsonl`
- `knowledge/structured/vtd/semantic/country-taxonomy.json`

职责：

- 把 phase-1 快照提升为可解释语义层
- 显式表达 family、variant、policy、taxonomy、provenance
- 为推荐、收敛、降级提供结构化依据

### Layer 4: OSC ↔ VTD Bridge

新增目录：

- `knowledge/structured/bridges/osc_vtd/field-bindings.jsonl`
- `knowledge/structured/bridges/osc_vtd/generation-policies.jsonl`
- `knowledge/structured/bridges/osc_vtd/guidance-recipes.jsonl`

职责：

- 把 OpenSCENARIO 的 element/attribute/parent_context 映射到 VTD 语义层
- 定义哪些字段要查哪类资产
- 定义 hard/soft constraint
- 定义优先收敛策略和推荐 recipe

### Layer 5: Scenario Intent IR

新增一套场景级中间表示。

除了现有 `ScenarioIntent` 外，还要正式引入：

- `xml_intent_check`
- `scenario_block_plan`
- `reference_closure`
- `decision_trace`
- `remaining_blockers`

职责：

- 把 prompt 到 XML 之间的中间状态固定下来
- 作为规划、repair、benchmark、回归的共同语言

### Layer 6: MCP Service Layer

在现有工具之上新增场景级工具。

职责：

- 提供场景意图归一
- 提供 schema 子图查询
- 提供 VTD 候选推荐
- 提供 repair batch 聚合
- 提供 XML/intent 一致性核对
- 提供一次性 generation packet

## New Core Data Entities

说明：

- 本节给出的是设计目标字段集合
- 哪些字段属于首批必填、哪些字段可后续补齐，将在 implementation plan 的 contract-freeze 任务中逐项冻结

### `VtdAssetFamily`

作用：

- 把同一语义对象的多个变体聚到一起
- 给出首选项和 fallback

建议字段：

- `family_id`
- `canonical_key`
- `asset_kind`
- `preferred_variant_id`
- `variant_ids`
- `country_scopes`
- `semantic_tags`
- `selection_policy`
- `notes`

### `VtdAssetVariant`

作用：

- 表示最终可引用的具体变体

建议字段：

- `variant_id`
- `family_id`
- `asset_id`
- `country_scope`
- `variant_tags`
- `source_type`
- `source_rank`
- `referencable_as`
- `usage_tags`
- `quality_flags`

### `VtdNamePolicy`

作用：

- 显式物化命名策略，而不是只在工具里临时扫名字

建议字段：

- `policy_id`
- `namespace`
- `asset_kind`
- `country_scope`
- `rule_kind`
- `severity`
- `match_mode`
- `canonical_target`
- `safe_name_strategy`
- `reason`
- `source_paths`

### `OscVtdBindingRule`

作用：

- 连接 OpenSCENARIO 字段与 VTD 语义层

建议字段：

- `binding_id`
- `element`
- `attribute`
- `parent_context`
- `binding_kind`
- `namespace`
- `asset_kind`
- `family_selector`
- `constraint_mode`
- `selection_recipe`
- `fallback_policy`

### `CountryVariantTaxonomy`

作用：

- 提供唯一国家/区域真相源

建议字段：

- `canonical_country_code`
- `aliases`
- `labels`
- `priority_rank`
- `region_group`

## New MCP Tool Surface

说明：

- 本节给出目标 tool contract
- 首批实现只冻结最小必需字段
- 非关键扩展字段由 implementation plan 中的 contract-freeze 任务显式确定

在保留现有工具的基础上，新增 6 类工具。

### `normalize_scenario_intent`

输入：

- `request`
- `locale` 可选
- `draft_assumptions` 可选

输出：

- `intent`
- `intent_checklist`
- `open_questions`
- `unresolved_slots`
- `assumptions`

用途：

- 把 prompt 稳定落成可消费 IR

### `retrieve_schema_subgraph`

输入：

- `query`
- `intent` 可选
- `roots` 可选
- `parent_context` 可选
- `depth`

输出：

- `focus_blocks`
- `nodes`
- `edges`
- `required_paths`
- `choice_points`
- `reference_bindings`
- `assembly_order`
- `evidence`

用途：

- 把单元素查询升级为场景级结构查询

### `recommend_vtd_candidates`

输入：

- `query`
- `asset_kind`
- `namespace`
- `country_code` 可选
- `requested_name` 可选
- `draft_names` 可选
- `top_k`

输出：

- `recommended`
- `fallbacks`
- `rejected`
- `name_resolution`
- `ranking_reasons`
- `source_paths`

用途：

- 给模型提供候选优先级，而不是只做平面命中

### `summarize_validation_repairs`

输入：

- `errors`
- `xml` 可选
- `intent` 可选

输出：

- `root_causes`
- `repair_batches`
- `minimal_patch_scope`
- `followup_queries`
- `intent_risk`

用途：

- 把逐条报错升级为 repair plan

### `check_xml_intent_consistency`

输入：

- `xml`
- `intent`
- `checklist` 可选

输出：

- `matched`
- `missing`
- `extra`
- `intent_consistent`
- `blockers`

用途：

- 把 sidecar 自报升级为实际核对

### `build_generation_packet`

输入：

- `request`
- `country_code` 可选
- `stage`

输出：

- `intent`
- `schema_plan`
- `vtd_plan`
- `naming_plan`
- `validation_plan`
- `open_questions`

用途：

- 向 LLM 提供一次性、结构化、可解释的场景级辅助包
- 它不是首批落地工具，而是在前置场景级工具稳定后再做的聚合层

## Upgraded Generator Workflow

升级后的推荐工作流如下：

1. 用户给出自然语言场景需求
2. 大模型先调用 `normalize_scenario_intent`
3. 大模型根据 intent 调用 `retrieve_schema_subgraph`
4. 对涉及 VTD 运行时资源的字段调用 `recommend_vtd_candidates`
5. 大模型自己选择方案并草拟 XML
6. 调用 `validate_xml`
7. 如果失败，先调用 `summarize_validation_repairs`
8. 大模型仅修复最小 patch scope
9. 调用 `check_xml_intent_consistency`
10. 只有 schema 通过且 intent 一致时，才视为成功

说明：

- `build_generation_packet` 不属于这个最小必需工作流
- 它是在上述单项服务稳定之后，再提供给大模型的聚合型快捷入口
- 因此它属于后续批次，不作为前置依赖

## First-Batch Bridge Fields

桥接层第一批只覆盖高风险字段，避免一开始做得过宽。

首批字段：

- `ScenarioObject.name`
- `Vehicle.model3d`
- `ExternalObjectReference.name`
- `TrafficSignalController.name`
- `TrafficSignalStateAction.name`
- `TrafficSignalAction.name`
- 与 runtime asset 直接绑定的用户给定名称字段

原因：

- 这些字段最容易与 VTD 现有资产冲突
- 这些字段对 VTD runtime 兼容性影响最大
- 做好这些字段，收益最高

## Benchmark And Verification Upgrade

benchmark 层需要同步升级，否则无法证明新系统真的更稳。

### Must-Have Upgrades

- 提交版 `.guidance.json` gold 文件
- 正向 benchmark 扩到多个场景族
- 负样例扩到多个 failure bucket
- sidecar 契约严格执行
- `bounded_failure` 不再默认通过

### New Failure Buckets

至少新增以下评测分类：

- `xml_parse/root`
- `schema_structure`
- `enum_or_attribute`
- `intent_missing`
- `intent_extra`
- `guidance_packet_drift`
- `vtd_asset_lookup_miss`
- `vtd_name_resolution_conflict`
- `runtime_playback_failure`
- `nondeterministic_output`

### New Benchmark Families

建议按场景族扩展：

- `parameter/reference`
- `route/trajectory`
- `conditions`
- `traffic/environment`
- `controller/actions`
- `VTD naming`

## Phased Delivery Plan

### Batch 1: 命名与国家归一基础层

目标：

- 物化 `reserved-name` 和 soft namespace rule
- 把 country taxonomy 前移到抽取层

这是最高优先级，因为当前 `reserved-names = 0` 是明显空洞。

### Batch 2: VTD 语义派生层

目标：

- 引入 family / variant / provenance / name policy
- 先把 bridge 依赖的数据抽象稳定下来
- 冻结 semantic-layer contract

### Batch 3: OSC ↔ VTD 桥接层

目标：

- 建立 field binding
- 建立 generation policy
- 首先覆盖高风险字段

### Batch 4: 场景意图与场景级 MCP

目标：

- 把 `ScenarioIntent` 正式纳入工具面
- 新增 schema subgraph、candidate recommendation、repair aggregation、intent consistency

说明：

- `build_generation_packet` 不在 Batch 4 内强制落地
- Batch 4 先交付场景级基础工具
- 等 contract 稳定后，再进入下一批聚合型 packet 服务

### Batch 5: 聚合型 generation packet

目标：

- 基于已经稳定的 intent、schema、VTD、repair 工具
- 新增 `build_generation_packet`
- 提供给大模型一次性场景级辅助入口

### Batch 6: 评测硬门

目标：

- 把 benchmark 升级为真正的 gate
- 增加 guidance gold、negative cases、runtime bridge tests

### Batch 7: 大规模批量补库

目标：

- 按 asset kind、country、schema domain、benchmark family 批量并行补齐

这一批最适合大量子代理并行推进。

## Parallelization Strategy

升级工作必须按“可并行批处理”和“需串行冻结 contract”的原则拆分。

### Suitable For Parallel Agents

- country code / taxonomy 清洗
- variant tag 补全
- asset family 聚类
- provenance enrich
- name policy 物化
- OSC↔VTD 字段绑定录入
- guidance recipe 整理
- benchmark prompt/gold/negative case 扩充

### Must Stay Sequential

- 核心数据 contract 冻结
- MCP tool contract 冻结
- generation packet contract 冻结
- benchmark gate 判定标准

## Risks

### Risk 1: 语义层过大，复杂度失控

缓解：

- 保留原始快照不动
- 只在派生层新增能力
- 先做高风险字段和高收益场景族

### Risk 2: 服务端替代模型决策

缓解：

- 服务端只输出事实、候选、优先级和 repair scope
- 不把 orchestration 做成模板引擎

### Risk 3: 桥接层规则错误导致误约束

缓解：

- 每条 bridge rule 都保留来源和适用范围
- 先覆盖少量高风险字段
- 每一批规则都配 benchmark

### Risk 4: benchmark 变多但不够硬

缓解：

- 先修 gate，再加样例
- gold、negative、runtime bridge 一起补

### Risk 5: runtime 评测被误解为需要运行 VTD

缓解：

- phase-2 的 runtime 评测只允许使用仓库现有可控运行链，例如 `esmini` 冒烟链路或静态/半静态验证夹具
- `runtime_playback_failure` 指“生成结果无法通过可控下游回放或仿真 smoke gate”，不是指运行 VTD 可执行程序
- 不安装、不启动、不依赖 VTD 本体

## Non-Goals

本次升级不追求：

- 安装或运行 VTD 本体
- 把 MCP 变成“自动生成 XML 的唯一引擎”
- 一次性支持所有 VTD 年份版本
- 一次性穷尽所有 OpenSCENARIO 字段的桥接规则
- 用 VTD 可执行程序作为 phase-2 的 benchmark 必选运行环境

## Implementation Readiness

该设计已经具备进入 implementation planning 的条件。

推荐实施顺序固定为：

1. `reserved-name 物化`
2. `country taxonomy 前移`
3. `asset family / variant / provenance`
4. `OSC↔VTD binding`
5. `intent layer`
6. `schema subgraph + VTD candidate recommendation`
7. `repair aggregation`
8. `build_generation_packet`
9. `benchmark hard gate`

这条顺序的核心理由是：

- 先补最基础的命名和国家归一漏洞
- 再做桥接和语义层
- 最后再做场景级工具和评测硬门

否则只会把现有的不稳定性自动化、放大化。
