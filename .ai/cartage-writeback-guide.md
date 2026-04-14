# Cartage 自动录入系统 — 技术文档

> 供团队参考和改良。最后更新: 2026-04-14

---

## 1. 系统概述

本系统实现从 Cartage Advise 附件（PDF/图片/文本）到飞书多维表格（Bitable）的自动录入流程：

```
附件 → AI解析 → 地址匹配 → 写回Bitable
```

当前已实现 **进口柜（Import）** 和 **出口柜（Export）** 分支。

---

## 2. 完整录入流程（Import）

### 流程图

```
Cartage Advise 附件
        │
        ▼
  ┌─────────────┐
  │ Step 1: 解析  │  AI (智谱 glm-5v-turbo) 提取结构化数据
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ Step 2: 匹配  │  地址 → MD-Warehouse Address → Deliver Config + Consingee
  └──────┬──────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────┐
  │ Step 3: 写回 Bitable                                     │
  │                                                          │
  │  3a. 查 Op-Import 是否存在重复 Container Number           │
  │      → 如果存在：跳过该柜（不中止全部）                    │
  │                                                          │
  │  3b. 逐柜创建 1 个 Op-Cartage + 1 个 Op-Import           │
  │      (1-to-1 关系: 每个柜号独立一组记录)                   │
  │                                                          │
  │      对每个不重复的柜号:                                   │
  │      ┌─ 创建 Op-Cartage ─────────────────────────────┐   │
  │      │ Booking Reference (文本)                       │   │
  │      │ Consingnee Name (直接关联, record_id 已知)      │   │
  │      │ Deliver Config (直接关联, record_id 已知)       │   │
  │      └────────────────────────────────────────────────┘   │
  │                         │                                │
  │                         ▼                                │
  │      ┌─ 创建 Op-Import ──────────────────────────────┐   │
  │      │ 1) Container Number (文本)                     │   │
  │      │ 2) FULL Vessel Name (双向关联 → Op-Vessel Schedule) │
  │      │    查找条件: Vessel Name + Voyage + Base Node   │   │
  │      │    → 找到：关联已有记录                          │   │
  │      │    → 没找到：新建 Vessel Schedule 记录并关联     │   │
  │      │       新建字段: Vessel Name, Voyage, Base Node  │   │
  │      │ 3) Container Type (单选)                        │   │
  │      │ 4) Commodity (单选)                             │   │
  │      │ 5) Container Weight (数字, 吨)                  │   │
  │      │ 6) Op-Cartage (双向关联 → 刚创建的 Op-Cartage)   │   │
  │      └────────────────────────────────────────────────┘   │
  │                                                          │
  │  Import Booking 字段由 Bitable 双向关联自动回填            │
  └──────────────────────────────────────────────────────────┘
```

### 不录入的字段（Import）

以下 Op-Import 字段**不属于 Cartage 录入流程**，由其他系统负责：

| 字段 | 由谁录入 |
|------|---------|
| Shipping Line | EDO 流程 |
| Empty Park | EDO 流程 |
| EDO PIN | EDO 流程 |
| EDO File | EDO 流程 |
| VesselIn | 爬虫 |
| InVoyage | 爬虫 |
| PortOfDischarge | 爬虫 |
| CommodityIn | 爬虫 |
| Dention Days, First Free, Last Free | 码头数据 |
| ISO, Gross Weight | 码头数据 |
| Terminal Full Name | 码头数据 |
| EstimatedArrival, ImportAvailability 等 | 码头数据 |
| StorageStartDate, ON_BOARD_VESSEL_Time 等 | 码头数据 |

---

## 2b. 完整录入流程（Export）

### 流程图

```
Cartage Advise 附件 (Export)
        │
        ▼
  ┌─────────────┐
  │ Step 1: 解析  │  AI 提取 booking_reference, release_qty, container_type, commodity...
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ Step 2: 展开  │  release_qty > 1 时，拆成多条 (BR-1, BR-2, ...)
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ Step 3: 匹配  │  地址 → MD-Warehouse Address → Deliver Config + Consingee
  └──────┬──────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────┐
  │ Step 4: 写回 Bitable                                     │
  │                                                          │
  │  4a. 重复检查 — 查 Op-Export Container Number 重复         │
  │      → 如果存在：跳过该条                                   │
  │                                                          │
  │  4b. 逐条循环 (1-to-1): 创建 Op-Cartage + Op-Export       │
  │                                                          │
  │      Op-Cartage:                                          │
  │      - Booking Reference (展开后带 -序号)                  │
  │      - Consingnee Name (直接关联)                          │
  │      - Deliver Config (直接关联)                           │
  │                                                          │
  │      Op-Export:                                           │
  │      - Booking Reference                                  │
  │      - Release Qty (展开后为 1)                            │
  │      - Container Number (可能为空)                         │
  │      - FULL Vessel Name (同 Import: 三字段查找/创建)       │
  │      - Container Type (单选)                              │
  │      - Commodity (单选)                                   │
  │      - Op-Cartage (双向关联)                               │
  └──────────────────────────────────────────────────────────┘
```

### 不录入的字段（Export）

| 字段 | 由谁录入 |
|------|---------|
| Shipping Line | 待定 |
| Empty Park | 待定 |
| Qty On Release | 待定 |
| Release Status | 待定 |
| Ready Date / Expiry Date | 待定 |

### Export 展开逻辑

当 `release_qty > 1` 时，`expand_export_bookings()` 将一条 booking 拆成 N 条：
- **Booking Reference 保持原值不变**（如 RSG20811，会重复没问题）
- **Container Number 加序号后缀**：`booking_ref-序号`（如 RSG20811-1, RSG20811-2）
- `release_qty` 改为 1
- 其他字段 (container_type, commodity, vessel_name 等) 复制到每条

---

## 3. 核心技术方法

### 3.1 AI 文档解析 (BaseParser + CartageParser)

**基类**: `app/core/base_parser.py` — `BaseParser`

提供统一的解析入口 `parse(source)`，自动路由：
- PDF → `parse_pdf()` (PyMuPDF 转 PNG → base64 → 多模态 API)
- 图片 → `parse_image()` (base64 → 多模态 API)
- TXT 文件 → `parse_text_file()`
- 纯文本 → `parse_text()`

**子类只需提供**:
- `system_prompt` — AI 提示词
- `user_hint` — 用户提示
- `build_result(raw_json)` — 原始 JSON → 结构化结果

**模型**: 智谱 glm-5v-turbo (多模态)，支持 thinking 模式 (budget_tokens=8192)

**CartageParser** (`app/service/llm_service/cartage/parser.py`):
- Prompt 中注入字典值 (`CartageDictValues`)，让 AI 直接输出 Bitable 可用的选项值
- 区分 Import / Export 两套字段

### 3.2 字典值注入 (CartageDictValues)

**文件**: `app/service/llm_service/cartage/schemas.py`

```python
class CartageDictValues(BaseModel):
    base_nodes: list[str]        # 港口: PORT OF SYDNEY, PORT OF MELBOURNE, ...
    container_types: list[str]   # 箱型: 20GP, 20HC, 40GP, 40HC, ...
    commodities: list[str]       # 货物: HAZ, GEN, GENL, REEF, OOG, BBLK, MT, EMPTY, MTHZ
    shipping_lines: list[str]    # 船公司: COSCO, MAERSK, ONE, ...
    deliver_types: list[str]     # 配送: Sideloader(SDL), Drop Trailer(DROP), Standard Trailer(STD)
```

**策略**: 默认值硬编码在代码中，与 Bitable select 字段选项一致。后续可从 Bitable Dict Table 动态拉取覆盖。

AI 输出直接匹配字典值，减少后处理。例如 AI 会输出 `"PORT OF SYDNEY"` 而非 `"AUSYD"`。

### 3.3 地址匹配 (Address Match)

**文件**: `app/entity/address.py` + `app/service/llm_service/cartage/enrichment.py`

**流程**:
1. `normalize_address()` — 标准化地址（大写、缩写街型 RD/ST/LN、去掉 state 全称、合并双空格）
2. 粗筛 — 用 postcode 词边界匹配 + street_name 子串匹配，限制候选集
3. `address_match_score()` — 评分: postcode(30) + street_name(25) + street_number(20) + street_type(10) + unit(10) + suburb(5)
4. 最佳匹配 → 阈值判断

**阈值** (`app/config/cartage_matching.py`):
- MATCH_THRESHOLD = 0.6 — 低于此分数视为无匹配
- REVIEW_THRESHOLD = 0.8 — 0.6~0.8 之间标记 needs_review=True

**Deliver Config 匹配**: 按地址 record_id + deliver_type 查 MD-Warehouse Deliver Config

**Consingee 匹配**: 按地址 record_id 查 MD-Consingee，多候选时用名字相似度 (`_name_similarity()`) 排序

### 3.4 写回配置驱动 (WritebackFieldRule)

**文件**: `app/service/llm_service/cartage/writeback_config.py`

核心思想：**每个 Bitable 字段的写入规则用配置声明，而非硬编码逻辑**。

```python
@dataclass(frozen=True)
class WritebackFieldRule:
    bitable_field: str           # Bitable 字段名
    source_key: str              # 来源数据 key
    required: bool = False       # 是否必填
    default_value: str | None = None  # 缺省值
    link_lookup: LinkLookup | None = None  # 关联字段查找规则
    is_direct_link: bool = False  # source_key 已经是 record_id，直接写入
```

**当前配置**:

**Op-Cartage** (`OP_CARTAGE_IMPORT_RULES`):
| Bitable 字段 | 来源 | 类型 | 规则 |
|-------------|------|------|------|
| Booking Reference | booking_reference | 文本 | 必填, 默认 "TBC" |
| Consingnee Name | consingee_id | 直接关联 | `is_direct_link=True`, enrichment 已解析出 record_id |
| Deliver Config | deliver_config_id | 直接关联 | `is_direct_link=True`, enrichment 已解析出 record_id |

**Op-Import** (`OP_IMPORT_RULES`):
| Bitable 字段 | 来源 | 类型 | 规则 |
|-------------|------|------|------|
| Container Number | container_number | 文本 | 必填, 默认 "TBC" |
| FULL Vessel Name | vessel_name | 双向关联 | 查 Op-Vessel Schedule, 找不到则创建 |
| Container Type | container_type | 单选 | 直接写入 |
| Commodity | commodity | 单选 | 直接写入 |
| Container Weight | container_weight | 数字 | 直接写入 |

**Op-Cartage (Export)** (`OP_CARTAGE_EXPORT_RULES`):
| Bitable 字段 | 来源 | 类型 | 规则 |
|-------------|------|------|------|
| Booking Reference | booking_reference | 文本 | 必填, 默认 "TBC" |
| Consingnee Name | consingee_id | 直接关联 | `is_direct_link=True` (非必填，出口可能无地址) |
| Deliver Config | deliver_config_id | 直接关联 | `is_direct_link=True` (非必填) |

**Op-Export** (`OP_EXPORT_RULES`):
| Bitable 字段 | 来源 | 类型 | 规则 |
|-------------|------|------|------|
| Booking Reference | booking_reference | 文本 | 必填, 默认 "TBC" |
| Container Number | container_number | 文本 | 可选 (展开后可能无) |
| Release Qty | release_qty | 数字 | 直接写入 |
| FULL Vessel Name | vessel_name | 双向关联 | 同 Import: 三字段查找/创建 (可选，PDF 可能无船名) |
| Container Type | container_type | 单选 | 直接写入 |
| Commodity | commodity | 单选 | 直接写入 |

### 3.5 关联字段解析 (LinkFieldResolver)

**文件**: `app/entity/link_resolver.py`

处理"先查再填"模式：对于双向关联字段，先在目标表查找已有记录，找到则关联，找不到则创建后关联。

```python
@dataclass(frozen=True)
class LinkLookup:
    target_table_id: str              # 目标表 ID
    search_field: str                 # 搜索字段名
    create_if_missing: bool = False   # 找不到时是否创建
    create_fields: dict[str, str]     # 创建时的字段模板
    create_links: dict[str, NestedLink]  # 创建时的嵌套关联
    filter_expr: str | None = None    # 复合过滤模板
    sort_field: str | None = None     # 排序字段
    sort_desc: bool = False           # 降序
    default_if_missing: str | None = None  # 找不到时的默认值
```

#### 复合过滤 (filter_expr)

当单一字段不足以唯一确定记录时，使用 `filter_expr` 添加额外条件。

**示例 — Vessel Schedule 查找**:

同一船名可能有不同航次和港口，需要 Vessel Name + Voyage + Base Node 三字段匹配：

```python
LinkLookup(
    target_table_id=T.op_vessel_schedule.id,
    search_field="Vessel Name",
    filter_expr='AND(CurrentValue.[Voyage]="{voyage}", CurrentValue.[Base Node]="{base_node}")',
    create_if_missing=True,
    create_fields={
        "Vessel Name": "{value}",
        "Voyage": "{voyage}",
    },
    ...
)
```

`filter_expr` 中的 `{voyage}` 和 `{base_node}` 会被 context 中的对应值替换，最终生成：

```
AND(
  CurrentValue.[Vessel Name]="COSCO ROTTERDAM",
  AND(
    CurrentValue.[Voyage]="209S",
    CurrentValue.[Base Node]="PORT OF MELBOURNE"
  )
)
```

**关键发现**: Bitable 支持通过**关联字段的显示文本**进行过滤。例如 `CurrentValue.[Base Node]="PORT OF MELBOURNE"` 可以匹配到关联了 PORT OF MELBOURNE 的记录。

#### 嵌套关联 (NestedLink)

创建新记录时，该记录本身也可能包含关联字段。`NestedLink` 处理这种级联创建。

**示例 — 创建新 Vessel Schedule 时同时关联 Base Node**:

```python
create_links={
    "Base Node": NestedLink(
        source_key="base_node",  # context 中取值
        lookup=LinkLookup(
            target_table_id=T.md_base_node.id,
            search_field="Base Node",
            create_if_missing=True,
            create_fields={"Base Node": "{value}"},
        ),
    ),
},
```

流程：
1. 解析 `source_key="base_node"` → "PORT OF MELBOURNE"
2. 在 MD-Base Node 中搜索 "PORT OF MELBOURNE"
3. 找到 → 返回 record_id
4. 找不到 → 创建新记录 → 返回 record_id
5. 将 record_id 写入 Vessel Schedule 的 Base Node 字段

### 3.6 写回执行 (CartageWritebackService)

**文件**: `app/service/llm_service/cartage/writeback.py`

**执行顺序**:

**Import 分支**:
```
1. 重复检查 — 遍历所有 container_number，查 Op-Import 重复
   → 重复的跳过（记入 skipped 列表），不重复的继续
   → 全部重复时直接返回空结果

2. 逐柜循环 (1-to-1: 每个柜号独立创建一组记录):
   a. 创建 Op-Cartage — 用 OP_CARTAGE_IMPORT_RULES 构建字段
      (Consingnee Name / Deliver Config 用 is_direct_link 直接写入 record_id)
   b. 创建 Op-Import — 用 OP_IMPORT_RULES 构建字段 (含 LinkFieldResolver 解析关联)
      添加 Op-Cartage 关联 → 指向刚创建的 Op-Cartage record_id
```

**Export 分支**:
```
1. 展开 — expand_export_bookings() 将 release_qty>1 的 booking 拆成多条
   Booking Reference 保持原值不变, Container Number 加 -序号 后缀, release_qty 改为 1

2. 重复检查 — 遍历所有展开后的 booking，按 Container Number 查 Op-Export 重复
   → 重复的跳过，无 Container Number 时跳过重复检查

3. 逐条循环 (1-to-1):
   a. 创建 Op-Cartage — 用 OP_CARTAGE_EXPORT_RULES 构建字段
      (Consingnee / Deliver Config 非必填，出口可能无地址匹配)
   b. 创建 Op-Export — 用 OP_EXPORT_RULES 构建字段 (含 Vessel Schedule 查找/创建)
      添加 Op-Cartage 关联 → 指向刚创建的 Op-Cartage record_id
```

**1-to-1 关系**: 每个 Container 创建独立的 Op-Cartage + Op-Import。同一 Cartage Advise 有 N 个柜 = N 个 Op-Cartage + N 个 Op-Import。Import Booking 字段由 Bitable 双向关联自动回填。

**重复跳过**: 不再因一个重复柜号而中止全部录入。重复的柜号被跳过，其余正常录入，跳过信息在返回结果的 `skipped` 列表中。

**`_build_fields()` 通用方法**: 根据 `WritebackFieldRule` 配置，从 source dict 取值，按规则写入：
- `is_direct_link=True` → 直接写入 `[record_id]` (enrichment 已解析)
- 有关联规则 (`link_lookup`) → 调用 `LinkFieldResolver.resolve()` 查找/创建
- 无关联规则 → 直接写入值

### 3.7 LinkFieldResolver 内存缓存

**文件**: `app/entity/link_resolver.py`

同一请求内，相同 `lookup + value + filter_expr` 只查一次 Bitable，结果缓存在内存中。

**典型场景**: 多柜共享同一 Vessel Schedule 时：
- 第 1 个柜：查 Bitable → 找到/创建 → 缓存结果
- 第 2-5 个柜：直接命中缓存，不再调 API

缓存 key 格式: `{target_table_id}|{search_field}={value}|{rendered_filter_expr}`

### 3.8 地址匹配缓存

**文件**: `app/service/cartage.py` + `app/cache/`

CartageService 维护三级内存缓存，避免重复 Bitable API 调用：
1. `addresses` — MD-Warehouse Address 全量（~1300 条）
2. `deliver_configs` — MD-Warehouse Deliver Config 全量
3. `consingees` — MD-Consingee 全量

首次访问时从 Bitable 拉取，后续命中缓存。`clear_cache()` 手动清除。

---

## 4. Bitable 关键字段属性

### Op-Vessel Schedule

| 字段 | 类型 | 说明 |
|------|------|------|
| FULL Vessel Name | type=20 (公式) | 只读，自动拼接 Vessel Name + Voyage + Base Node |
| Vessel Name | type=1 (文本) | 可写 |
| Voyage | type=1 (文本) | 可写 |
| Base Node | type=18 (单向关联) | 关联 MD-Base Node，可写 |
| Terminal Name | type=21 (双向关联) | 关联 MD-Terminal |
| Op-Import | type=21 (双向关联) | 由 Op-Import 自动回填 |
| Op-Export | type=21 (双向关联) | 由 Op-Export 自动回填 |

**唯一键**: Vessel Name + Voyage + Base Node 三字段组合

### Op-Import

| 字段 | 类型 | 说明 |
|------|------|------|
| Container Number | type=1 (文本) | 唯一键，重复则中止 |
| FULL Vessel Name | type=21 (双向关联) | 关联 Op-Vessel Schedule |
| Container Type | type=3 (单选) | 选项: 20GP/20HC/20RE/20OT/40GP/40HC/40RE/40OT |
| Commodity | type=3 (单选) | 选项: HAZ/GEN/GENL/REEF/OOG/BBLK/MT/EMPTY/MTHZ |
| Container Weight | type=2 (数字) | 单位: 吨 |
| Shipping Line | type=21 (双向关联) | **EDO 流程负责，Cartage 不写** |
| Op-Cartage | type=21 (双向关联) | 关联 Op-Cartage |

### Op-Cartage

| 字段 | 类型 | 说明 |
|------|------|------|
| Booking Reference | type=1 (文本) | |
| Consingnee Name | type=21 (双向关联) | 关联 MD-Consingee, 直接写入 record_id |
| Deliver Config | type=21 (双向关联) | 关联 MD-Warehouse Deliver Config, 直接写入 record_id |
| Import Booking | type=21 (双向关联) | 由 Op-Import 双向关联自动回填 (1-to-1 时每个 Cartage 只有 1 条) |
| Export Booking | type=21 (双向关联) | 由 Op-Export 双向关联自动回填 (1-to-1 时每个 Cartage 只有 1 条) |

### Op-Export

| 字段 | 类型 | 说明 |
|------|------|------|
| Booking Reference | type=1 (文本) | |
| Container Number | type=1 (文本) | 可选，展开后可能无 |
| Release Qty | type=2 (数字) | 展开后为 1 |
| FULL Vessel Name | type=21 (双向关联) | 关联 Op-Vessel Schedule (可选) |
| Container Type | type=3 (单选) | 选项同 Import |
| Commodity | type=3 (单选) | 选项同 Import |
| Shipping Line | type=21 (双向关联) | **Cartage Export 不写** |
| Op-Cartage | type=21 (双向关联) | 关联 Op-Cartage |

### Link Field 读写格式

| 操作 | 格式 |
|------|------|
| **写入** | `["recXXX"]` (纯字符串数组) |
| **读取** (get_record) | `[{"record_ids": ["recXXX"], "text": "...", "type": "text"}]` |
| **读取** (batch_get) | `{"link_record_ids": ["recXXX"]}` |

---

## 5. Bitable API 注意事项

1. **field_names 参数**: 必须用 `json.dumps(["field1", "field2"])`，不能用 `str()`
2. **batch_get_records SDK bug**: `.records()` 应改为 `.record_ids()`
3. **select 字段写入**: 值必须是已有选项（精确匹配），否则静默丢弃
4. **link 字段过滤**: `CurrentValue.[Base Node]="PORT OF MELBOURNE"` 可以按关联记录的显示文本过滤
5. **link 字段写入**: 使用 `["recXXX"]` 格式，不用 `[{"record_ids": ["recXXX"]}]`

---

## 6. 代码目录结构

```
app/
  config/
    cartage_matching.py          # 地址匹配阈值
  core/
    base_parser.py               # AI 解析基类
    llm.py                       # 智谱 AI 客户端
    lark_bitable_value.py        # Bitable 值提取工具函数
  common/
    lark_tables.py               # 37 表 ID 映射
    lark_repository.py           # Bitable CRUD 基类
  entity/
    address.py                   # 地址标准化 + 匹配评分
    link_resolver.py             # 关联字段查找/创建 (LinkFieldResolver + LinkLookup + NestedLink)
  cache/
    factory.py                   # 缓存工厂
  service/
    cartage.py                   # Cartage 领域服务 (三级缓存)
    llm_service/
      llm_service.py             # LLM 应用服务 (facade)
      cartage/
        parser.py                # CartageParser (继承 BaseParser)
        prompts.py               # AI 提示词 (含字典值注入)
        schemas.py               # 数据模型 (ImportContainerEntry, CartageDictValues 等)
        result_builder.py        # 原始 JSON → CartageParseResult
        enrichment.py            # CartageEnrichmentService (地址/consingee 匹配)
        process_schemas.py       # CartageProcessResult, AddressMatch
        export_bookings.py       # 出口柜 release_qty 展开
        writeback.py             # CartageWritebackService (写回 Bitable)
        writeback_config.py      # WritebackFieldRule 配置 (声明式, 非硬编码)
        writeback_schemas.py     # CartageWritebackResult
  controller/
    llm/llm.py                   # HTTP 端点
  repository/
    cartage.py, import_.py, export_.py  # Op-* 表仓储
```

---

## 7. 已知局限与改进方向

| 项目 | 当前状态 | 改进方向 |
|------|---------|---------|
| 字典值来源 | 硬编码在 CartageDictValues | 从 Bitable Dict Table 动态拉取 |
| 地址匹配缓存 | 启动后首次访问拉取全量 | 定时刷新或 webhook 驱动 |
| 依赖注入 | 模块级单例 (`LLMService()`) | FastAPI Depends 或 DI 容器 |
| Container Type/Commodity 校验 | 无校验，写入不匹配值会被 Bitable 静默丢弃 | 写入前校验选项是否存在，不存在则 fallback |
| Export 写回 | ✅ 已实现 | 出口柜 release_qty 展开为多条，1-to-1 Cartage-Export 关系 |
| 错误处理 | 写回失败时部分记录已创建 | 需要事务性保证或清理机制 |
| Vessel Schedule Base Node 更新 | 已有记录 Base Node 为空时不更新 | 考虑 find 时补充更新空字段 |
