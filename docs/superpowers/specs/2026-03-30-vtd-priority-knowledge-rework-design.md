# VTD 优先知识图谱与 MCP 重构设计

## Goal

重构现有 OpenSCENARIO 知识图谱与 MCP 辅助层，使系统从“只懂 XML 语法”升级为“同时理解 OpenSCENARIO 语法约束和 VTD 运行时资产语义”，并在两者冲突时明确以 VTD 资产与命名规则为主导。

最终系统仍然保持 `LLM-first, MCP-assisted`：

- 大模型负责场景理解、方案决策、XML 草拟和修复
- MCP 负责结构化检索、命名约束提示、语法校验、失败诊断
- 当 OpenSCENARIO 通用知识与 VTD 静态资产定义发生冲突时，优先采用 VTD 侧的可用资源、命名和引用规则

## Design Summary

当前系统的问题不是 XSD 覆盖不够，而是知识层只有“OpenSCENARIO 语法图谱”，没有“VTD 资产图谱”。

这导致模型虽然能生成通过 XSD 的 XML，但在以下方面仍然容易失真：

- 生成了 VTD 中不存在或不可直接引用的资源名
- 把 VTD 已有强语义资源名误当作普通变量名或实体名
- 忽略国家/区域变体，选中了错误的信号、路侧设施或 PBR 映射
- 在场景语义合理但运行时资源不兼容时，没有能力优先向 VTD 真实资源收敛

本次重构采用“双层知识图谱 + 轻量约束 MCP”的方案：

- 保留现有 OpenSCENARIO 结构化元素知识，继续负责 XML 语法、父子关系、属性和 choice/sequence 约束
- 新增 VTD 资产知识层，负责模型、信号、贴花、道路标记、区域扩展、PBR 映射、宏配置、默认工程资源目录等运行时语义
- 新增命名解析与冲突规则层，负责判断某个名字是否已被 VTD 占用、是否存在规范别名、是否必须落到某个 canonical asset name
- MCP 只输出高信号辅助信息，不代替大模型做场景决策

## Target Outcome

第一阶段完成后，系统应支持如下生成闭环：

1. 用户描述一个面向 VTD 的场景需求。
2. 大模型先按自然语言构建场景意图。
3. 在生成 XML 前，大模型可以查询：
   - OpenSCENARIO 语法元素约束
   - VTD 可用资产
   - 某个候选名字是否与 VTD 资源冲突
   - 某个资源名是否存在 canonical 形式或区域变体
4. 大模型按 VTD 优先原则生成 XML。
5. MCP 继续负责 XSD 校验与错误解释。
6. 如果 XML 语法合法但资源命名存在高风险，MCP 应能返回“建议改名/改引用”的辅助结果。
7. 大模型自行决定是否采用建议，并完成最终 XML 修复。

## Priority Rule

系统必须显式执行以下优先级：

1. `VTD 静态资产定义`
2. `VTD 资源映射与区域扩展规则`
3. `OpenSCENARIO 结构化语法知识`
4. `模型基于上下文的自由推断`

这条规则影响三类决策：

- 资源引用名选择
- 高语义名称的占用判断
- 当“语法上可行”但“VTD 中无此资源”时，优先提示贴近 VTD 的替代项，而不是保留通用名称

## VTD-First Execution Semantics

`VTD-first` 不是单一语义，而是分为“硬约束”与“软约束”两层。

### Hard Constraint

以下内容属于硬约束，最终 XML 必须收敛到 VTD 可识别结果：

- 会被 VTD 运行时直接解析的资源引用名
- 由 VTD 资产定义文件给出的 canonical asset name
- 已被 `SetupFiles/*.DAT`、`pbr_*.xml`、`decalScatterConfig*.xml` 等显式定义的运行时对象名

对这些字段：

- MCP 返回的 canonical target 视为权威结果
- skill 不应把“仅语法合法但 VTD 无此资源”的自由文本保留为最终运行时引用
- 如果用户给了一个与 VTD 不一致的资源名，系统应自动向最近的 VTD canonical 结果收敛，并在说明里保留映射理由

### Soft Constraint

以下内容属于软约束，MCP 只给 guidance，不强行拒绝：

- `ScenarioObject.name`
- 普通变量名
- 用户自定义但不会被 VTD 直接当作资产 ID 解析的逻辑名称

对这些字段：

- 如果名字不冲突，允许模型自由生成
- 如果与 VTD 既有强语义名称精确冲突，默认自动改写为安全名并返回改名说明
- 如果只是近似冲突或存在多义性，返回 warning guidance，由模型决定是否采用

### User Override Policy

如果用户显式要求保留一个与 VTD 强冲突的逻辑名称：

- 对硬约束字段，不允许保留冲突值，最终 XML 仍需收敛到 VTD 可识别值
- 对软约束字段，可以保留用户语义，但应自动生成一个不冲突的内部名称，并在结果说明里明确“用户名 -> 实际 XML 名”的映射

因此，`VTD-first` 在 phase 1 中的定义是：

- 对运行时可解析资源是硬约束
- 对普通逻辑命名是高优先级 guidance，必要时自动避冲突，但不压制场景语义设计自由度

## Scope

### In Scope

纳入知识图谱的内容限定为“能被 VTD 场景、配置或资源目录直接引用，或会直接影响资源命名/解析的静态资产”。

第一阶段纳入：

- `VisualLib/Models` 与 `VisualLib/ModelsPBR`
- `VisualLib/Styles`
- `VisualLib/TileLib`
- `SetupFiles/*.DAT`
- `Tools/pbr_*.xml`
- `DefaultProject/Config/*.xml`
- `DefaultProject/Config/Macros/*.rmcr`
- `Tools/resourceDirs.txt`
- `Samples/*.tdo`
- `AddOns` 下与资源或通信配置相关的 XML

phase 1 的数据源边界明确限定为：

- 仅针对当前已确认安装树中的 `VTD.2020`
- 仅针对当前已确认资源发行集 `Runtime/Tools/RodDistro_6980_Rod4.6.1`
- 仅生成这一套资源树的静态知识快照

phase 1 不承诺：

- 自动兼容其他 VTD 年份版本
- 自动兼容不同发行包命名
- 自动兼容任意同布局安装目录

后续如果要支持多版本，将作为单独扩展项目处理。

### Out of Scope

第一阶段不把以下内容建成核心图谱实体：

- 安装器 `.bin`、`.tar`、`.tgz`
- 可执行程序本体
- 普通说明文档和 license 文件
- 与 XML 生成无直接关系的通用图片、字体、脚本工具

这些内容最多进入源清单，不进入运行时检索主路径。

## Source Materials Confirmed

当前已确认的高价值源包括但不限于：

- `D:/wyj/VTD-2020-install/VTD.2020/Runtime/Tools/RodDistro_6980_Rod4.6.1/Tools/resourceDirs.txt`
- `D:/wyj/VTD-2020-install/VTD.2020/Runtime/Tools/RodDistro_6980_Rod4.6.1/Tools/pbr_objects.xml`
- `D:/wyj/VTD-2020-install/VTD.2020/Runtime/Tools/RodDistro_6980_Rod4.6.1/DefaultProject/Config/decalScatterConfig01.xml`
- `D:/wyj/VTD-2020-install/VTD.2020/Runtime/Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_EXTERNALS_ADD_COUNTRYCN.DAT`
- `D:/wyj/VTD-2020-install/VTD.2020/Runtime/Tools/RodDistro_6980_Rod4.6.1/VisualLib/Models/AddOns/CountryCN/SetupFiles/TT_SIGNALS_ADD_COUNTRYCN.DAT`

这些源已经显示出以下事实：

- VTD 存在 canonical asset name、filename、icon path、group、odrType、国家扩展等结构化字段
- 同一资源可能同时存在基础版、国家版、PBR 版、隧道版等变体
- 有些名字并不是“自由文本”，而是运行时约定名
- 资源目录解析不是单一目录，而是由资源目录配置与扩展目录共同决定

## Data Model Design

### Keep Existing OpenSCENARIO Schema Layer

保留当前 `ElementRecord` 和 `KnowledgeBase` 作为 OpenSCENARIO 语法层，不在这个数据结构里硬塞 VTD 资产字段。

原因：

- 语法知识与资产知识的生命周期不同
- 语法元素按 XSD 管理，VTD 资产按静态资源树管理
- 混写会让检索、测试和后续增量同步都变得脆弱

### Add VTD Asset Layer

新增 `VtdAssetRecord`，用于表达一个 VTD 可用资产或可引用对象。

记录应至少包含：

- `asset_id`
- `asset_kind`
- `canonical_name`
- `display_name`
- `aliases`
- `filename`
- `relative_path`
- `source_path`
- `country_codes`
- `variant_tags`
- `group_path`
- `runtime_family`
- `metadata`

其中：

- `canonical_name` 是 MCP 返回给模型时的首选名
- `aliases` 用于承接 DAT、XML、文件名、历史命名差异
- `variant_tags` 用于标记 `PBR`、`TUNNEL`、`CountryCN` 等扩展
- `runtime_family` 用于表达 `signal`、`external`、`decal`、`vehicle_model`、`pedestrian_model`、`macro` 等粗分类

### Add Naming Rule Layer

新增 `VtdNameRule`，用于表达某个名称与 VTD 资产的关系，而不是表达某个具体模型文件。

规则应至少包含：

- `name`
- `rule_kind`
- `severity`
- `canonical_target`
- `asset_kind`
- `reason`
- `scope`
- `source_path`

典型规则包括：

- `reserved_asset_name`
- `canonical_alias`
- `country_specific_preference`
- `discouraged_freeform_name`
- `collides_with_existing_asset`

### Naming Namespace Contract

phase 1 的命名冲突判定必须按命名空间分域，不允许把所有名字混成一个全局冲突表。

最小命名空间集合定义为：

- `runtime_asset`
  - 指会被 VTD 直接解析为资产或资源对象的名称
- `scenario_object`
  - 指 OpenSCENARIO 中的 `ScenarioObject.name`
- `variable`
  - 指 OpenSCENARIO 中变量名
- `external_object`
  - 指外部对象或外部资源逻辑标识

`scope` 字段在 phase 1 中固定表达为：

- `namespace`
- `asset_kind`
- `country_code`

例如：

- `runtime_asset/signal/CN`
- `runtime_asset/decal/global`
- `scenario_object/vehicle/global`

### Name Normalization Contract

phase 1 使用保守归一规则，避免过度误报。

最小归一流程为：

1. 保留原始字符串
2. 去除首尾空白
3. 生成 `lowercase` 比较键
4. 对已知 alias 再建立单独 alias 索引

phase 1 不做激进归一：

- 不把所有符号都删除后再全局比较
- 不把国家后缀、`PBR`、`TUNNEL` 等语义标签直接抹掉

变体标签应通过结构化字段解析，而不是靠模糊删词匹配。

### Severity Contract

phase 1 的 `severity` 固定为：

- `info`
  - 只是 alias 归一或 canonical 提示，不构成真实风险
- `warning`
  - 存在近似冲突、变体歧义或国家版本不明确
- `high`
  - 与已存在 VTD canonical name 或已知 alias 在同命名空间内精确冲突

`high-risk` 的判定条件固定为：

- 候选名与现有 canonical name 大小写无关精确一致
- 或与已登记 alias 大小写无关精确一致
- 且二者位于相同 `namespace`
- 且 `asset_kind` 相容

### Add VTD Knowledge Container

新增独立的 `VtdKnowledgeBase`，不要复用 `KnowledgeBase.records_by_element`。

建议包含：

- `assets_by_id`
- `assets_by_canonical_name`
- `rules_by_name`
- `sources`

这样运行时可以并行加载两套知识：

- OpenSCENARIO schema knowledge
- VTD runtime asset knowledge

## Extraction Design

### Extraction Principles

- 只做静态读取，不安装、不运行 VTD
- 优先解析“定义文件”而不是仅按文件名猜测语义
- 先抽 canonical 资源，再补 alias 和变体
- 抽取过程必须保留 `source_path`

### Extraction Passes

第一阶段的抽取按四个 pass 执行：

1. `资源目录 pass`
   - 解析 `resourceDirs.txt`
   - 识别基础资源搜索路径和扩展包层级
2. `定义文件 pass`
   - 解析 `SetupFiles/*.DAT`
   - 解析 `pbr_*.xml`
   - 解析 `decalScatterConfig*.xml`
3. `目录资产 pass`
   - 扫描 `VisualLib`、`DefaultProject`、`Samples`
   - 把文件系统实体映射到结构化资产记录
4. `规则归一 pass`
   - 归并 alias
   - 标注国家/区域/材质变体
   - 生成命名冲突规则

## MCP Tool Surface

MCP 仍然保持辅助定位，不取代模型决策。

### Keep Existing Tools

保留：

- `retrieve_spec`
- `get_element_schema`
- `validate_xml`
- `explain_validation_errors`
- `build_xml_guidance`

这些工具继续负责语法层和校验层。

### Add VTD-Focused Tools

新增三类工具。

#### `retrieve_vtd_asset`

作用：

- 根据名称、别名、用途、国家或类别检索 VTD 资产

返回重点：

- canonical name
- asset kind
- country/variant
- source path
- aliases
- 关键元数据

#### `resolve_vtd_name`

作用：

- 判断候选名字是否与现有 VTD 资产冲突
- 如果冲突，返回 canonical target 和推荐替代项

这个工具针对：

- `ScenarioObject.name`
- 变量名
- 用户自由给定的资源名
- 场景中引用的外部对象名

最小输入 contract：

- `name`
- `namespace`
- `asset_kind`
- `country_code`

最小输出 contract：

- `normalized_name`
- `severity`
- `rule_kind`
- `canonical_target`
- `alternatives`
- `reason`
- `source_paths`

#### `build_vtd_guidance`

作用：

- 把资产检索、命名冲突、区域偏好打包成一个简洁 guidance

目标不是生成 XML，而是让模型在生成前快速获得：

- 哪些名字不要用
- 哪个资源名是首选
- 某类资源在当前国家/区域下有哪些合法候选

该工具在 phase 1 中被定义为薄包装：

- 它只组合 `retrieve_vtd_asset` 与 `resolve_vtd_name`
- 不引入第二套独立推理规则
- 不取代现有 `build_xml_guidance`

它的职责只是把 VTD 侧高价值结果压缩成便于模型消费的一次性 guidance 包。

## Generator Workflow Impact

技能层不改成“规则驱动生成”，仍然保持“大模型主导”。

但生成流程增加两个辅助检查点：

1. 在落具体资源名之前，查询 VTD 资产层
2. 在最终返回 XML 前，对高风险名称做一次冲突检查

这意味着系统不会强行卡死模型，而是把“高概率翻车的命名与资源选择”提前暴露出来。

## Conflict Handling

冲突分为三类：

### Type 1: 语法允许，但 VTD 无此资源

处理：

- 返回 VTD 中最接近的 canonical 资源候选
- 不把通用名称视为优先答案

### Type 2: 用户名称与 VTD 既有资源强冲突

处理：

- 标记高风险
- 返回冲突原因和建议替代名
- 由模型自行决定是否保留用户名，但 guidance 必须明确提示

### Type 3: OpenSCENARIO 通用知识和 VTD 约定不一致

处理：

- 在 guidance 中明确标注“VTD override”
- 检索和建议都优先输出 VTD 侧结果

## Testing Strategy

测试必须覆盖四层。

### Model Contract Tests

- `VtdAssetRecord` 字段稳定
- `VtdNameRule` 字段稳定
- `VtdKnowledgeBase` 加载结构稳定

### Extractor Tests

- DAT 解析
- PBR XML 解析
- decal scatter XML 解析
- 目录扫描和 alias 归并

### MCP Tool Tests

- `retrieve_vtd_asset` 能按 canonical name 和 alias 命中
- `resolve_vtd_name` 能识别冲突并返回推荐名
- `build_vtd_guidance` 能输出紧凑高信号 guidance

### Integration Tests

- 运行时可同时加载 schema knowledge 与 VTD knowledge
- 现有语法工具行为不回退
- XML 生成辅助链路能同时读到语法层和 VTD 层

## Risks

### Risk 1: 资产数量大，噪声高

缓解：

- 先抽“定义文件主导”的高语义资源
- 原始贴图文件和纯材质文件默认不直接进入主检索

### Risk 2: 同名异义或多重 alias

缓解：

- 明确 canonical name
- 把别名和 source path 一并保留
- 冲突规则与资产记录分离建模

### Risk 3: 过度约束，压制模型自由度

缓解：

- MCP 只返回 guidance，不代替模型生成
- 只在资源名、引用名、国家变体等高风险点给强提示

### Risk 4: 与现有 skill 耦合过深

缓解：

- 先通过新工具和 guidance 包扩展
- 尽量不破坏现有语法工具接口

## Non-Goals

本次设计不追求：

- 安装或运行 VTD
- 一次性支持所有 VTD 外部程序
- 让 MCP 自动生成完整 XML
- 把所有底层贴图文件都暴露给模型

## Implementation Readiness

该设计已经具备进入实现计划的条件。

需要执行的实现方向已经清晰：

- 新增 VTD 资产数据模型
- 新增静态资产抽取脚本
- 扩展运行时以并行加载两套知识
- 新增 VTD 资产检索与命名冲突工具
- 将 skill 调整为“生成前查资产，返回前查冲突”
- 保持 `VTD > 原始知识图谱 > 模型兜底推断`
