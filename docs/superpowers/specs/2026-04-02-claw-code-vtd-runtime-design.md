# claw-code VTD 一体化垂域运行时设计

## Goal

把现有 `OPenscenario` 仓库中的 OpenSCENARIO 结构化知识、VTD 静态资产知识、MCP 工具链、skill 设计、benchmark 资产与生成修复闭环，整体并入 `claw-code` 的 Rust 主运行时中，重构为一个默认面向 VTD 仿真场景开发的垂域智能开发环境。

升级后的产品目标不是“给通用 coding agent 多挂几个工具”，而是让 `claw-code` 的默认工作模式变成：

`自然语言场景需求 -> 场景意图归一化 -> VTD 资产与命名稳定化 -> OpenSCENARIO XML 生成 -> schema 校验 -> 有界修复 -> 意图一致性检查 -> 可交付场景资产落盘`

同时保留 `claw-code` 已有的多模型接入、provider abstraction、工具权限系统、MCP transport、REPL 会话与插件能力。

## Why This Exists

当前两个仓库各自已经有明显价值，但仍然是分裂状态：

- `OPenscenario` 已经积累了大量 VTD / OpenSCENARIO 领域知识、MCP 能力与 benchmark 资产。
- `claw-code` 已经有可扩展的 Rust agent runtime、多模型接入、工具系统、MCP 编排、session 状态机和 CLI 入口。

如果继续保持“领域知识在一个仓库、agent runtime 在另一个仓库”的形态，后续会持续出现这些问题：

- 默认系统目标仍然是通用编码，而不是 VTD 场景开发。
- 场景生成闭环不在主状态机内，稳定性取决于 prompt 纪律。
- 知识底座、工具链、产物协议与运行时之间没有统一契约。
- 主车控制算法接入只能作为后补扩展，无法成为一等设计对象。

因此需要把它们在产品和运行时层面真正融为一体。

## Product Definition

目标产品是一套默认面向 VTD 的垂域 agent runtime，而不是一个外挂 skill 集。

对用户而言，它应表现为：

- 用户只需要描述场景需求，而不是逐步指挥工具调用。
- 系统对一切自由文本提示默认采用 `VTD-first` 路由策略。
- 系统自动检索真实可用的 VTD 资产，而不是自由幻想资源名称。
- 系统自动生成并修复 OpenSCENARIO XML，直到达到可交付标准或明确有界失败。
- 系统输出的是一组可消费的场景资产，而不是单独一段聊天文本。
- 同时支持默认主车轨迹模式和外部主车控制器接入模式。

一句话定义：

`把 claw-code 改造成一个保留多模型能力、默认面向 VTD 场景开发、内建知识图谱与生成修复闭环、可直接产出可交付仿真场景资产的垂域智能开发环境。`

这里的“默认面向 VTD”含义固定为：

- 所有用户自由文本请求默认先按 VTD 场景开发任务处理。
- 只有明显属于工具管理、配置查看、git 操作、plugin 管理、session 管理、帮助命令等元任务时，才走非 VTD 领域分支。
- 不再保留“通用 coding agent 和 VTD agent 并列二选一”的产品入口。

## Phase-1 Scope

首期实现只做一个硬闭环，不追求把整个仿真工程生态一次做全。

首期必须做到：

- 从自然语言场景需求生成 `ScenarioIntent` 风格的结构化中间表示。
- 自动检索和筛选真实存在的 VTD 静态资产。
- 对运行时敏感名称执行命名稳定化与冲突规避。
- 生成 schema 正确的 OpenSCENARIO XML。
- 对常见验证错误执行有界修复。
- 对生成结果做意图一致性检查。
- 以文件形式输出可交付场景资产。
- 为主车外部控制算法预留接入接口。
- 在没有外部控制器时支持 `trajectory-driven` 回退模式。
- `trajectory-driven` 模式内部允许使用默认轨迹模板或默认行为模板，但它们都属于同一个执行模式，而不是新增第三种运行模式。

首期不作为硬交付的内容：

- 自动生成复杂 OpenDRIVE 地图。
- 完整 VTD 工程目录打包器。
- 大规模批量仿真调度平台。
- 全覆盖的外部控制协议实现。

这些能力需要在数据契约和接口层面预留位置，但不进入首期交付承诺。

## Non-Goals

以下目标明确不属于本次设计：

- 不把系统降级为纯规则驱动的 XML 拼装器。
- 不要求 MCP 取代模型进行场景设计和最终决策。
- 不要求首期彻底去除所有 Python 构建脚本。
- 不在首期实现 VTD 可执行程序的安装、运行或动态调用。
- 不把 `claw-code` 现有多模型能力改造成只服务单一厂商模型。

## Core Principles

### 1. LLM First, Workflow Guarded

大模型继续主导场景理解、结构设计、候选比较和最终输出。

运行时只在高风险节点设置强制检查点：

- 意图归一化
- VTD 资产与命名稳定化
- XML 校验
- 修复重试上限
- 意图一致性检查

这保证模型自由度和工程闭环同时存在。

### 2. VTD Priority

当 OpenSCENARIO 通用知识、用户自然语言表达和 VTD 运行时事实发生冲突时，优先级固定为：

1. VTD 静态资产与运行时命名事实
2. VTD 区域/版本/变体规则
3. OpenSCENARIO 结构化 schema 知识
4. 模型自由推断

### 3. Integrated Runtime, Not Loosely Coupled Tooling

目标不是保持两个仓库松耦合，而是把领域知识和场景闭环并入 `claw-code` 主运行时。

其中：

- 构建期知识生成脚本可以继续使用 Python。
- 运行时在线查询、工作流编排、校验闭环和产物装配以 Rust 为主。

### 4. Knowledge as Structured Runtime Substrate

知识层不是“文档检索”或“若干 JSON 文件堆积”，而是统一的领域语义底座。

必须同时支持：

- schema 结构事实
- VTD 资产事实
- 命名与保留字策略
- OSC 到 VTD 的桥接关系
- repair guidance
- 可增量添加的企业规则和项目规则

### 5. Deliverable Artifacts Over Chatty Output

最终成功标准不是“回复内容看起来合理”，而是：

- XML 文件存在
- schema 校验通过
- 与意图一致
- 相关 sidecar 和绑定配置可以被后续流程消费

## Target Architecture

### Layer 1: Provider Layer

保留 `claw-code` 现有 `api` crate 与 provider abstraction。

这一层不做 VTD 特化，继续负责：

- 多模型提供商接入
- 模型别名解析
- streaming message
- 上游 API 协议兼容

设计要求：

- 保持 Claude / OpenAI-compatible / 其他未来 provider 的兼容能力。
- 不让 VTD 垂域逻辑侵入 provider 层。

### Layer 2: Agent Runtime Layer

保留 `runtime` crate 的会话状态机、权限系统、工具回合、MCP transport 和 prompt 组装能力，但修改默认系统目标。

新增：

- `DomainWorkflowDispatcher`
- VTD 默认系统角色配置
- `VTD-first` 任务路由逻辑
- 场景工作流检查点策略

运行时的新职责：

- 默认把用户自由文本任务送入 VTD 领域工作流。
- 只在请求显然属于元操作时绕过 VTD 场景工作流。
- 在进入 VTD 路由后，再细分为场景生成、场景修复、资产查询、控制器绑定等子工作流。
- 在关键检查点要求工具链和验证链提供结构化反馈。

### Layer 3: VTD Domain Kernel

新增一个明确的领域工作流核心，负责把“用户需求 -> 场景产物”的流程稳定化。

核心职责：

- 构建和维护 `ScenarioIntent` 类中间表示。
- 生成 `xml_intent_check`、`scenario_block_plan`、`reference_closure` 和 `remaining_blockers`。
- 触发资产候选检索和命名稳定化。
- 调度 XML 生成、校验、修复和一致性检查。
- 为最终产物装配提供结构化输入。

该层不是静态规则引擎，而是“让模型更稳地做决策”的结构化支架。

### Layer 4: Knowledge Runtime Layer

把 `OPenscenario` 中现有知识资产统一升级为运行时可消费的领域知识底座。

内部按 4 个子层组织：

1. `Raw Sources`
2. `Structured Facts`
3. `Semantic Views`
4. `Policy / Rule Packs`

对应作用：

- `Raw Sources` 负责保留 schema、VTD 原始资源定义、原始文档和原始企业规则。
- `Structured Facts` 负责形成稳定数据契约，例如 element record、asset record、name policy、bridge binding、repair pattern。
- `Semantic Views` 负责生成适合模型推理的高密度视图，例如 schema 子图、资产家族、候选排序、repair batch。
- `Policy / Rule Packs` 负责未来规则扩展，允许以注册包方式新增客户规则、项目规则、资产白名单和企业命名规范。

### Layer 5: Tool Orchestration Layer

保留现有 `GlobalToolRegistry` 模式，但把关键 VTD 能力收敛为内建的领域工具面，而不只是依赖外部 prompt 约定。

目标工具集至少包括：

- `normalize_scenario_intent`
- `recommend_vtd_assets`
- `resolve_runtime_names`
- `plan_xml_structure`
- `validate_scenario_xml`
- `repair_scenario_xml`
- `check_xml_intent_consistency`
- `assemble_vtd_scenario_package`
- `attach_ego_controller`

这些工具的语义应与当前 `OPenscenario` 的 phase-2 MCP 工具链保持一致，但运行时上应优先表现为 `claw-code` 的一等工具。

首期迁移契约固定为：

- 以下 phase-2 工具语义必须一等迁移，并保留可验证的输入输出契约：
  - `normalize_scenario_intent`
  - `build_generation_packet`
  - `retrieve_schema_subgraph`
  - `recommend_vtd_candidates`
  - `validate_xml`
  - `summarize_validation_repairs`
  - `check_xml_intent_consistency`
- 首期 Rust 实现可以增加更贴产品语义的别名，但原始 phase-2 工具名和返回字段必须仍可映射，避免 benchmark 和迁移测试失效。
- 若某工具在首期不直接暴露给最终用户，也必须在运行时内部保留等价能力。

### Phase-1 Tool Surface Mapping

为避免首期工具面与迁移契约分裂，首期映射关系固定如下：

| `OPenscenario` phase-2 能力 | `claw-code` Phase-1 形态 | 分类 |
| --- | --- | --- |
| `normalize_scenario_intent` | `normalize_scenario_intent` | `public` |
| `build_generation_packet` | `build_generation_packet` | `public` |
| `retrieve_schema_subgraph` | `plan_xml_structure` 调用的底层能力；必要时保留同名调试入口 | `internal composite + optional alias` |
| `recommend_vtd_candidates` | `recommend_vtd_assets` 调用的底层能力；必要时保留同名调试入口 | `internal composite + optional alias` |
| `validate_xml` | `validate_scenario_xml`；首期必须保留 `validate_xml` 兼容别名 | `public alias` |
| `summarize_validation_repairs` | `repair_scenario_xml` 调用的底层能力；必要时保留同名调试入口 | `internal composite + optional alias` |
| `check_xml_intent_consistency` | `check_xml_intent_consistency` | `public` |
| 运行时命名稳定化能力 | `resolve_runtime_names` | `public` |
| 场景产物装配能力 | `assemble_vtd_scenario_package` | `public` |
| ego 控制绑定能力 | `attach_ego_controller` | `public` |

规划约束：

- `public` 表示首期用户和 benchmark 可以直接依赖。
- `public alias` 表示对外推荐新名字，但兼容旧名字以降低迁移成本。
- `internal composite` 表示能力必须存在，但可以折叠进更贴产品语义的上层工具中。
- 首期不允许把上表列出的 phase-2 能力直接标成 `deferred`。

### Layer 6: Artifact Layer

最终产物层不应该只生成一个 XML 字符串，而应装配为一个最小可交付场景资产包。

首期最小产物集合：

- `scenario.xosc`
- `scenario.intent.json`
- `asset-selection.json`
- `validation-report.json`
- `assumptions.md`
- `controller-binding.json` 可选

后续扩展方向：

- VTD 工程目录布局
- catalog 组织
- 批量场景管理
- 回归执行工件

## Knowledge Runtime Design

### Data Domains To Import

从 `OPenscenario` 仓库导入并内聚到 `claw-code` 的知识资产至少包括：

- `knowledge/raw/schema/`
- `knowledge/raw/docs/`
- `knowledge/structured/elements/`
- `knowledge/structured/vtd/`
- `knowledge/structured/bridges/`
- `benchmarks/`

导入后它们不再是外挂知识仓，而是 `claw-code` 的产品知识底座。

### Canonical Knowledge Contracts

知识层需要稳定以下核心实体契约：

- `entity`
- `attribute`
- `relation`
- `constraint`
- `provenance`
- `policy`
- `repair_hint`

这些契约不要求首期上图数据库，但必须先把“图语义模型”做对。

### Why Not Start With A Graph Database

首期建议保留 `json/jsonl` 为主的仓库内结构化资产形式，原因如下：

- 当前知识资产已大量以文件形式存在。
- 首期重点是运行时整合和产品闭环，而不是基础设施迁移。
- 先做稳定的数据契约，后续再切图数据库或图 + 向量混合检索也不会推倒重来。

因此：

- 先实现“图语义模型优先”
- 再评估是否需要“图数据库落地”

### Extension Interfaces

为未来规则和知识扩展预留显式接口：

- `DomainKnowledgeProvider`
- `ScenarioPolicyProvider`
- `AssetResolver`
- `NameResolver`
- `RepairAdvisor`
- `ControllerBindingProvider`

未来新增规则时，应通过 provider 或 pack 注册，而不是直接改主状态机或散落在 prompt 中。

首期约束：

- 上述扩展接口只要求以最小 trait / provider 占位形式落地。
- 首期不要求做完整插件化规则市场，也不允许为了扩展性牺牲主闭环可交付性。

## Scenario Workflow Design

### Required Runtime Checkpoints

每个成功场景生成回合都必须显式经过这些检查点：

1. `parsed_intent`
2. `vtd_asset_resolution`
3. `runtime_name_resolution`
4. `schema_valid`
5. `repair_budget_not_exhausted`
6. `intent_consistent`
7. `artifact_ready`

这些检查点决定系统是否可以宣告任务完成。

### Phase-1 Runtime-Sensitive Inventory

首期必须被稳定化的运行时敏感字段和资产种类固定如下。

运行时敏感命名字段类别：

- `ScenarioObject.name`
- `Vehicle.model3d`
- `ExternalObjectReference.name`
- `TrafficSignalController.name`
- `TrafficSignalStateAction.name`
- 所有进入 VTD 软命名空间的 `scenario_object`、`variable`、`external_object` 类名称

运行时敏感资产种类：

- `model`
- `external`
- `signal`
- `decal`
- `style`
- `tile`

首期完成“名称稳定化”的判定标准：

- 硬约束命名字段必须收敛到唯一 `canonical_target`
- 软命名空间字段必须收敛到唯一 `safe_name`
- 若需要保存用户原始称呼，只能作为 sidecar 映射存在，不能继续作为 XML 中的未收敛名称

首期完成“资产解析”的判定标准：

- 每个运行时敏感资产字段都必须收敛到一个明确候选
- 候选的 `asset_kind` 必须属于上述首期清单
- 若请求超出首期支持资产种类，则返回 `bounded_failure`

### Canonical Execution Flow

运行时推荐工作流固定为：

1. 用户输入自然语言场景需求。
2. 系统把需求归一化为 `ScenarioIntent`。
3. 系统为运行时敏感字段检索 VTD 资产候选与命名策略。
4. 模型基于场景意图和结构化上下文生成 OpenSCENARIO XML 草稿。
5. 系统执行 schema 校验。
6. 若失败，系统聚合多错误并执行有界修复。
7. 校验通过后执行意图一致性检查。
8. 检查通过后把场景与 sidecar 资产一起落盘。

这个流程应由运行时保障存在，但不应把具体 XML 编写退化为纯规则生成。

### Initial Repair Policy

首期“常见验证错误”和“有界修复”定义固定如下。

纳入首期自动修复范围的问题类型：

- schema 缺少必需属性
- schema 缺少必需子元素
- 子元素顺序错误
- choice 分支选择错误
- enum 字段取值非法
- multiplicity 超限或不足
- 引用字段缺失或引用目标未闭合
- 运行时命名冲突或命中保留名
- 运行时资产字段未解析到真实候选
- 意图一致性缺失：
  - 请求的主体未出现
  - 请求的关键动作未编码
  - 请求的触发条件未编码
  - 请求的停止条件未编码

首期修复预算固定为：

- 最多 3 轮完整修复循环
- 如果归一化后的错误签名连续 2 轮完全相同，则提前停止并返回 `bounded_failure`
- 如果出现无法消解的 `blocker` 级别约束冲突，则立即停止并返回 `bounded_failure`
- schema 失败修复与意图一致性失败修复共用同一个 3 轮预算

### Post-Consistency Failure Path

当 XML 已经 schema 通过，但意图一致性检查失败时，运行时必须按以下规则处理：

1. 把一致性缺失项归类到同一 repair pipeline 中。
2. 如果缺失项属于首期自动修复范围，则消耗同一个 repair budget 执行局部修复。
3. 每次因一致性问题修改 XML 后，必须重新执行：
   - `validate_xml`
   - `check_xml_intent_consistency`
4. 如果一致性问题不属于自动修复范围，或预算耗尽，则返回 `bounded_failure`。

### Delivery Standard

首期“可交付标准”固定为同时满足以下条件：

- `scenario.xosc` 已落盘
- XML schema 校验通过
- `remaining_blockers` 中不存在 `blocker` 级问题
- 所有运行时敏感名称都已经过命名稳定化
- 所有运行时敏感资产字段都已解析到明确候选
- 意图一致性检查通过
- 必需 sidecar 已生成：
  - `scenario.intent.json`
  - `asset-selection.json`
  - `validation-report.json`
  - `assumptions.md`
- 当请求为 `controller-bound` 时，`controller-binding.json` 必须存在

如果运行时敏感资产字段仍然需要用户人工裁决，则当前回合不算成功完成，必须返回 `bounded_failure`，并在 sidecar 中附带候选集和待决策原因。

## Ego Control Interface Design

主车控制模式从首期开始就是一等设计对象。

### Supported Modes

系统支持两类 ego 执行模式：

1. `trajectory-driven`
2. `controller-bound`

其中：

- `trajectory-driven` 是默认模式，用于演示、回归和没有外部控制器时的场景落地。
- `controller-bound` 用于对接外部主车控制算法。

这里明确规定：

- 不存在第三种独立的“默认行为模式”运行状态。
- “默认轨迹模板”和“默认行为模板”都是 `trajectory-driven` 的内部策略。

### Three-Layer Control Contract

控制接入拆为 3 层：

1. `Scenario Contract`
2. `Binding Config`
3. `Runtime Adapter`

含义如下：

- `Scenario Contract` 定义哪个对象是 ego、初始位姿、目标语义和控制模式。
- `Binding Config` 记录控制器类型、IO 约定、连接方式和 fallback 策略。
- `Runtime Adapter` 负责把场景与外部控制程序真正接起来。

首期要求：

- 能输出标准化的控制绑定配置。
- 允许没有控制器时退回默认轨迹模式。
- 不把所有控制细节硬塞进 XML 本体。

未来允许的接入方式：

- 进程外控制器
- Python/C++ bridge
- 模块化控制器
- 默认轨迹生成器

## Repository Integration Plan

### Target Layout

建议把 `claw-code` 调整为如下形态：

```text
claw-code/
  rust/
    crates/
      api/
      runtime/
      tools/
      commands/
      claw-cli/
      plugins/
      vtd-model/
      vtd-knowledge/
      vtd-engine/
      vtd-artifacts/
    domains/
      vtd/
        knowledge/
          raw/
          structured/
        benchmarks/
        templates/
        examples/
        policies/
    scripts/
      build_vtd_knowledge.py
      import_openscenario_assets.py
      validate_vtd_benchmarks.py
```

该布局把运行时代码、领域知识和构建脚本明确分层。

### Migration Rule

迁移边界固定为：

- `build-time` 可以继续使用 Python
- `run-time` 应以 Rust 为主

这意味着：

- 知识快照构建、schema 解析、离线导入可继续使用 Python。
- 在线查询、场景工作流、产物装配和用户交互路径最终由 Rust 接管。

### Phase-2 MCP Contract Carryover

为保证迁移计划可执行，首期必须把 `OPenscenario` phase-2 的能力边界显式冻结为下列契约：

- `normalize_scenario_intent`
  - 输入：自然语言请求
  - 输出：稳定的 `ScenarioIntent`
- `build_generation_packet`
  - 输入：用户请求与可选上下文
  - 输出：面向生成阶段的结构化聚合包
- `retrieve_schema_subgraph`
  - 输入：目标元素或场景查询
  - 输出：场景级 schema 结构闭包
- `recommend_vtd_candidates`
  - 输入：资产类型、国家范围、目标命名空间或场景上下文
  - 输出：VTD 候选排序和命名建议
- `validate_xml`
  - 输入：完整 XML 文本
  - 输出：标准化校验结果和错误列表
- `summarize_validation_repairs`
  - 输入：多条验证错误
  - 输出：最小 repair batch 和修复顺序
- `check_xml_intent_consistency`
  - 输入：XML 与 `ScenarioIntent`
  - 输出：一致性状态、缺失项和冲突项

首期 Rust 设计必须对这些能力建立：

- 等价运行时接口
- 回归测试
- benchmark 兼容验证

如果首期要更名或折叠工具，只能在保留这些语义边界和测试义务的前提下进行。

### Codebase Pressure Points

当前 `claw-code` 里有几个已知压力点：

- `rust/crates/tools/src/lib.rs` 过大
- `rust/crates/claw-cli/src/main.rs` 过大
- `runtime` 已经承载核心平台逻辑

因此迁移策略应是“围绕 VTD 能力做定向抽模块”，而不是一开始就做全局式大重构。

## Phased Rollout

### Phase A: Asset Import And Freeze

目标：

- 把 `OPenscenario` 知识资产、benchmark、schema、VTD snapshot 导入 `claw-code`。
- 建立 `domains/vtd/` 目录与导入 manifest。
- 明确哪些文件是运行时必需资产，哪些是构建期产物。

### Phase B: Rust Knowledge Runtime

目标：

- 实现 `vtd-model` 和 `vtd-knowledge`。
- 让 Rust 运行时具备稳定的知识加载、检索、过滤和语义视图组合能力。

### Phase C: Domain Tools And Workflow Kernel

目标：

- 实现 `vtd-engine`。
- 把现有 Python MCP 核心能力迁成 Rust 领域工具。
- 形成稳定的场景工作流工具面。

### Phase D: Runtime Fusion

目标：

- 修改 `runtime` 与 `prompt`。
- 把默认系统角色改为 VTD 场景开发 agent。
- 让场景类任务自动进入领域工作流。

### Phase E: Ego Controller And Dual-Mode Delivery

目标：

- 加入 `controller-binding` 设计与产物。
- 同时支持默认轨迹模式和外部控制器接入模式。

### Phase F: Product Gates

目标：

- 补齐 CLI 入口、示例、文档和 benchmark gate。
- 用硬门槛定义“成功生成”。

首期 gate 矩阵固定为：

- `schema_valid == true`
- `intent_consistent == true`
- `remaining_blockers` 中没有 `blocker`
- 所有硬约束命名字段都已收敛
- 所有运行时敏感资产字段都已解析
- 产物文件集合完整
- 对于 `controller-bound` 请求，控制绑定文件存在
- benchmark 结果中不允许把失败样例标成 `pass`

## Success Criteria

首期实现成功的定义如下：

1. 用户输入自然语言场景需求后，系统能稳定识别为 VTD 场景任务。
2. 系统能从内建知识底座中检索并选择真实可用的 VTD 资产。
3. 系统能生成 schema 正确的 OpenSCENARIO XML。
4. 常见验证错误能在有界重试预算内自动修复。
5. 系统能输出默认轨迹模式场景。
6. 系统能为外部 ego 控制器输出绑定配置接口。
7. benchmark 具备硬门槛，失败不会被伪装成成功。
8. 多模型接入能力保持可用。

## Initial Contract Appendix

以下契约是首期计划必须依赖的最小字段集。

### `ScenarioIntent`

作用：

- 表示场景需求的稳定结构化中间表示。

最小字段：

- `prompt_text`
- `parameters`
- `entities`
- `environment`
- `map_context`
- `init_actions`
- `story_actions`
- `triggers`
- `stop_conditions`
- `control_mode`
- `assumptions`

所有权与生命周期：

- 由意图归一化阶段创建
- 在整个生成、修复、一致性检查周期内只增量补充，不允许被后续阶段语义漂移式重写

### `xml_intent_check`

作用：

- 把用户需求中的关键行为映射到预期 XML 编码位置。

最小字段：

- `checks[]`
- 每个 `check` 至少包含：
  - `intent_item`
  - `expected_xml_region`
  - `status`
  - `notes`

所有权与生命周期：

- 由领域内核在 XML 初稿前生成
- 在每轮修复后更新状态

### `scenario_block_plan`

作用：

- 定义场景主要 XML 区块的生成顺序和责任边界。

最小字段：

- `blocks[]`
- 每个 `block` 至少包含：
  - `name`
  - `purpose`
  - `depends_on`
  - `planned_elements`

### `reference_closure`

作用：

- 记录所有必须闭合的对象、引用和命名空间依赖。

最小字段：

- `objects`
- `parameters`
- `variables`
- `references`
- `unresolved`

### `remaining_blockers`

作用：

- 汇总未解决问题，决定是否可以宣告成功。

最小字段：

- `issues[]`
- 每个 `issue` 至少包含：
  - `severity`
  - `kind`
  - `message`
  - `owner_stage`

判定规则：

- 只要存在 `severity == blocker` 的条目，就不能进入成功完成态

### `controller-binding.json`

作用：

- 描述 ego 外部控制器绑定所需的非 XML 配置。

最小字段：

- `mode`
- `ego_object_name`
- `controller_type`
- `adapter_kind`
- `io_contract`
- `fallback_policy`

### `asset-selection.json`

作用：

- 记录所有运行时敏感资产字段的候选、最终选择和失败原因。

最小字段：

- `requests[]`
- 每个 `request` 至少包含：
  - `field_path`
  - `asset_kind`
  - `candidates`
  - `selected_candidate`
  - `status`
  - `notes`

判定规则：

- 若任一运行时敏感字段 `status != resolved`，则本次回合不能进入成功完成态

### `validation-report.json`

作用：

- 记录 schema 校验、修复尝试和最终验证状态。

最小字段：

- `schema_valid`
- `repair_attempts`
- `errors`
- `final_error_signature`
- `status`

### `assumptions.md`

作用：

- 记录模型在场景生成过程中主动采用的关键假设。

最小内容：

- 场景范围假设
- 资产选择假设
- 控制模式假设
- 省略项说明

### `ScenarioPackageManifest`

作用：

- 描述一个场景交付包包含哪些文件以及各自状态。

最小字段：

- `scenario_path`
- `intent_path`
- `asset_selection_path`
- `validation_report_path`
- `assumptions_path`
- `controller_binding_path`
- `status`

补充规则：

- 当 `control_mode != controller-bound` 时，`controller_binding_path` 允许为空值
- 首期它是产物装配层的内部结构，不是必须对最终用户落盘的交付文件

## Risks And Mitigations

### 1. `claw-code` 当前不是 git 仓库

风险：

- 当前本地路径 `D:\wyj\claw-code` 没有 `.git`，无法直接创建功能分支、提交代码或按正常协作流推进实施。

缓解：

- 先在 `OPenscenario` 中固化设计和后续计划。
- 真正实施前，必须拿到带 `.git` 的 `claw-code` 仓库副本，或先初始化为正式 git 仓库。

### 2. 主文件过大导致集成成本上升

风险：

- `main.rs`、`tools/lib.rs` 等大文件使功能继续堆叠时的维护成本快速上升。

缓解：

- 增量抽离 VTD 相关模块，不做无边界重构。
- 优先新增新 crate 和新模块，再逐步收缩旧文件职责。

### 3. Python 逻辑长期滞留在线路径

风险：

- 如果关键运行时能力长期停留在 Python sidecar，最终产品仍然不是一体化 Rust runtime。

缓解：

- 明确“构建期 Python、运行期 Rust”的边界。
- 新设计的首要目标就是逐步让 Rust 接管在线路径。

### 4. 模型自由度与工程闭环失衡

风险：

- 约束太弱会继续不稳定，约束太强会退化为规则拼装器。

缓解：

- 采用“强检查点、弱生成约束”的策略。
- 让模型主导设计，让运行时主导合格性判断。

### 5. 控制器接口后补导致体系分裂

风险：

- 如果控制器接入不是首期架构的一部分，后续会形成“场景生成系统”和“控制接入系统”两套孤岛。

缓解：

- 从首期开始把 `controller-bound` 与 `trajectory-driven` 设为双一等模式。

## Preconditions For Implementation

在开始代码实现前，需要满足以下前置条件：

- 提供带 `.git` 的 `claw-code` 仓库工作副本。
- 确认 `OPenscenario` 中哪些知识资产作为首批导入源。
- 确认 `claw-code` 的 Rust workspace 作为唯一在线运行时主战场。

在这些条件满足之前，当前阶段只进行设计固化与实施计划准备。
