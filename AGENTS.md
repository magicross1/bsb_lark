# BSB Lark - Backend Project

## Project Overview
- **Project Name**: bsb_lark
- **Tech Stack**: Python 3.12 / FastAPI
- **Primary Purpose**: BSB Transport Australia - Lark-based logistics backend
- **Data Source**: Lark Bitable (BSB Base, 37 tables)
- **Package Manager**: uv

## Project Structure
```
app/
  main.py                  # FastAPI entry + middleware + router mount
  config/
    app_settings.py        # Pydantic Settings (env vars)
    lark.py                # Lark client singleton
    cartage_matching.py    # Cartage address match threshold constants
  core/
    base_parser.py         # Base AI parser (PDF/image/text → AI → JSON)
    base_service.py        # Service base class
    lark.py                # Lark client singleton (re-export)
    llm.py                 # ZhipuAI client + model helpers
    lark_bitable_value.py  # extract_cell_text, link_field_contains_record_id
    utils.py               # Date/time helpers (Sydney timezone)
    midlleware/registry.py # Module auto-registration
  common/
    lark_tables.py         # All 37 Bitable table/field ID mappings
    lark_repository.py     # BaseRepository — Bitable CRUD 基类 (findOne/createOne/updateOne/deleteOne/list/batch_update)
    query_wrapper.py       # QueryWrapper 链式查询构建器 (eq/ne/not_empty/in_list/order_by/select)
    update_wrapper.py      # UpdateWrapper 链式更新构建器 (.eq().set().set_all().with_label())
    collection_utils.py    # 集合操作工具 (pluck/to_map/filter_by/group_by/partition)
    assert_utils.py        # 断言工具 (assert_in/assert_not_blank/assert_not_none/assert_true)
    bitable_fields.py      # Global Bitable field type registry (text/number/datetime/link/select)
    relation_loader.py     # RelationLoader + RelationConfig (批量关联字段解析, 消除 N+1)
    response.py            # Unified response envelope {code, data, message}
    exceptions.py          # AppError, NotFoundError, LarkApiError
    enums.py               # Depot, ContainerType, DeliverType, etc.
  entity/
    address.py             # NormalizedAddress, normalize_address(), address_match_score()
    relation.py            # RelationResolver, RelationHop (声明式跨表关联解析)
    schemas.py             # Master data output schemas
  cache/
    factory.py             # CacheFactory (in-memory cache)
    constants.py           # Cache key definitions
  controller/
    router.py              # Top-level router aggregation
    data/                  # Master data CRUD controllers
    llm/llm.py             # EDO + Cartage LLM controllers
    sync/                  # Sync controllers (vessel/container/clear/vbs)
    email/                 # Email controller (future)
    pricing/               # Pricing controller (future)
   service/
    cartage/               # Cartage 领域服务 (主数据缓存 + Writeback 统一入口)
      cartage.py
      model/
    consingee.py           # Consingee 领域服务
    warehouse_deliver_config.py  # Deliver config 领域服务
    edo/                   # EDO 领域服务 (Shipping Line/Empty Park 缓存 + dict_values)
      edo.py
    master/                # 主数据领域服务
     sync/                  # Sync services — 模板模式 + 按职责分层
       workflow/             # 抽象骨架层
         sync_template.py    # SyncTemplate 三步模板 (fetch_records → fetch_provider_data → build_update_wrappers → _persist)
         sync_data.py        # SyncData 基类 (Pydantic → UpdateWrapper 自动转换)
         batch_sync_result.py # BatchSyncResult (total/synced/errors)
       scene/                # 场景实现层
         vbs/                # VBS 码头同步 (5 个码头各一个 SyncTemplate 子类)
         vessel/             # 船期同步
         container/          # 集装箱状态同步
         clear/              # 清关状态同步
       constants/            # 各域查询条件常量
       utils/                # datetime_parser (safe_ts), link_config, link_resolver
       request/              # 请求对象 (Pydantic)
       factory/              # VBS 策略工厂
    ...                    # Other domain services
    llm_service/
      llm_service.py      # LLM application service (facade: parse + process + enrich)
      cartage/
        cartage_llm.py     # Cartage LLM orchestration (file/text → parser)
        parser.py          # CartageParser (inherits BaseParser)
        prompts.py         # CARTAGE_SYSTEM_PROMPT, CARTAGE_USER_HINT
        schemas.py         # CartageParseResult, CartageDictValues, etc.
        result_builder.py  # Raw LLM → CartageParseResult
        enrichment.py      # CartageEnrichmentService (parse result → Bitable match)
        process_schemas.py # CartageProcessResult, AddressMatch, ExportBookingMatch
        export_bookings.py # expand_export_bookings()
      edo/
        edo_llm.py         # EDO LLM orchestration
        parser.py          # EdoParser
        schemas.py         # EdoEntry, EdoParseResult
  repository/
    warehouse_address.py   # MD-Warehouse Address
    warehouse_deliver_config.py  # MD-Warehouse Deliver Config
    consingee.py           # MD-Consingee
    ...                    # Other table repositories (each 1 table)
```

## Architecture Rules (铁律 — 强约束)

本节定义 `bsb_lark` 的目录职责、分层边界、允许依赖方向与禁止事项。这是强约束，不是建议。

### 调用方向
唯一允许的主链路：`main` → `controller` → `service` → `repository/cache`

基础能力可被下游各层使用：`config`、`core`、`common`、`entity`，但它们只能提供"公共能力"，不能反向接管业务流程。

### 允许依赖
- `controller` → `service`
- `service` → `repository`
- `service` → `cache`
- `service` → `entity`
- `llm_service` → parser / enrichment / domain service
- `repository` → `common` / `core` / `config`
- `cache` → `config` / `common`

### 明确禁止
- `controller` → `repository` / `cache` (跨层)
- `controller` → `entity` 后自行业务编排
- `repository` → `service` / `controller` (反向)
- `cache` → `service` (反向)
- 同级 controller / service / repository 互调
- controller 内实例化 repository
- service 使用 fastapi 类型或返回 HTTP response
- parser 直接查主数据 (repository/cache)

### 文件名必须和职责一致
- `router.py` → 只放路由/HTTP入口
- `service.py` / `xxx_service.py` → 只放 service
- `repository.py` / `xxx_repository.py` → 只放 repository
- `parser.py` → 只放解析逻辑
- `schemas.py` → 只放数据模型
- `prompts.py` → 只放 AI 提示词
- `container.py` / `xxx_container.py` → 只放依赖装配与组合根
- `deps.py` → 只放依赖提供器，且必须用于框架注入场景（如 `Depends(...)`）
- 禁止用 `__init__.py` 做跨层便利导出
- 禁止用 `deps.py` 伪装 service 注册表
- 禁止用 `container.py` 承载业务逻辑

### Controller 必须薄
只做：参数接收 → 基础校验 → 调 service → 返回 response

禁止在 controller 中出现：复杂条件分支、多阶段业务流程、匹配算法、仓储实例化、缓存清理策略

### Service 承担业务语义
service 是唯一可以定义"做什么"的地方。如果 service 调 service，只能发生在"应用服务 → 领域服务"方向。普通同级 service 不允许互相调用。需要编排时，必须抽成明确的 facade / application service。

### Repository 只回答"怎么取数据"
不回答：为什么取、取完怎么拼、失败后怎么回 HTTP

### Cache 只做性能优化，不做业务入口
不能被 controller 直接使用做业务决策。不能在 repository 中混入 cache 命中逻辑。不能替代 service 的业务判断。

### LLM 场景专用规则
链路：`controller` → `LLM application service` → `parser / enrichment / domain service` → `repository/cache`

- Parser 负责：prompt、模型调用、原始响应转结构化结果
- Enrichment 负责：基于 parse result 做业务补全与匹配
- Domain service 负责：查询主数据、使用 cache、组合 repository
- 禁止：controller → parser / repository / cache；parser → repository / cache

### 依赖装配规则
依赖装配只能出现在：`app/main.py`、专门的 container / providers 模块、明确标注为 composition root 的文件。

禁止在 controller 业务路由文件、repository、entity 中做依赖装配。

### 不确定时按顺序判断
1. HTTP 入口? → `controller`
2. 业务语义或用例编排? → `service`
3. 数据访问? → `repository`
4. 性能缓存? → `cache`
5. 纯规则/纯对象/纯计算? → `entity`
6. 跨模块通用基础? → `core` / `common`

### 最终原则
宁可多一层清晰的 service，也不要少一层边界。宁可显式编排，也不要隐式绕行。

### Sync Module 三步模式（强规范）
所有爬虫同步模块（Vessel/Container/Clear/VBS 及后续新增）必须遵循 `SyncTemplate` 模板方法三步模式：

**步骤 1：fetch_records(condition)**
- 从 Bitable 筛选待同步记录
- 声明式 `_CONDITIONS` dict（condition_name → `QueryWrapper`），用 `assert_in` 校验
- `QueryWrapper` 同时存储服务端 filter + 客户端 predicate，两阶段互补

**步骤 2：fetch_provider_data(records)**
- 调外部 Provider，返回 `list[SyncData]`
- 单 Provider：固定调一个爬虫
- 多 Provider 路由：按业务字段（如 Terminal Full Name）决定调哪个 Provider
- Provider 路由逻辑在 service 层，controller 不感知
- `SyncData` 子类用 Pydantic `alias` 声明「Python 字段名 → 飞书列名」映射
- `LinkResolver` 解析关联字段为 record_id，`safe_ts` 转日期为毫秒时间戳

**步骤 3：build_update_wrappers(data_list) → _persist()**
- `SyncData.to_update_wrapper()` 自动转换（exclude_none + exclude metadata + by_alias → `UpdateWrapper`）
- `_persist()` 写回 Bitable: `batch_update` → 失败回退逐条 `updateOne`

**文件结构模板**：
```
service/sync/workflow/                # 抽象骨架层
  sync_template.py                    # SyncTemplate 基类
  sync_data.py                        # SyncData 基类
  batch_sync_result.py                # BatchSyncResult
service/sync/scene/{module}/          # 场景实现层
  {module}_sync.py                    # SyncTemplate 子类
  {module}_data.py                    # SyncData 子类
service/sync/constants/               # 各域查询条件常量
  {module}_constants.py               # _CONDITIONS dict
service/sync/utils/                   # 共享工具
  datetime_parser.py                  # safe_ts, parse_datetime_to_timestamp
  link_config.py                      # LinkConfig
  link_resolver.py                    # LinkResolver
service/sync/request/                 # 请求对象 (Pydantic)
  {module}_sync_request.py
  {module}_batch_sync_request.py
service/sync/factory/                 # 策略工厂 (VBS 多码头)
controller/sync/{module}.py           # GET /sync/{name}/conditions + POST /sync/{name} + POST /sync/{name}/batch
```

**关键约束**：
- `QueryWrapper` 是唯一条件定义机制，禁止 `filter_fn` 双轨制
- `QueryWrapper` 每个子句同时存储 `condition_node`(服务端) 和 `predicate`(客户端)
- `eq("record_id", rid)` / `in_list("record_id", ids)` 特殊处理：不走 search API，走直连 GET/batch_get
- `.any_empty(fields)` — 任一字段为空 → `OR(f1="", f2="", ...)`
- `.not_in_or_empty(field, values)` — 字段为空或不在列表中 → `OR(field="", AND(field!="v1", ...))`
- `.client_filter(predicate)` — 纯客户端筛选条件（如 `ETA < now()`）
- Bitable **不支持 `NOT`** — 为空用 `=""`，非空用 `!=""`
- datetime 字段写回必须转毫秒时间戳 `int(dt.timestamp() * 1000)`
- number 字段写回必须转 `float()`
- 新增条件只需在 `{MODULE}_CONSTANTS.py` 的 `_CONDITIONS` dict 注册，不改逻辑代码
- 集合操作用 `collection_utils`（`pluck` / `to_map` / `filter_by` / `group_by` / `partition`）
- 断言用 `assert_utils`（`assert_in` / `assert_not_blank` / `assert_not_none` / `assert_true`）

**Sync 模块"不发明方法"原则（铁律）**：
1. **Repository 必须是独立文件** — 禁止方法内 `class _XxxRepo(BaseRepository)`，一表一文件放 `repository/`
2. **用已有工具** — `extract_link_record_ids`/`to_map`/`pluck`/`safe_ts`/`LinkResolver`/`LinkConfig` 已覆盖 90% 场景，优先用它们
3. **不造新轮子** — link 字段反查用 `repo.list(in_list("record_id", ids))` + `to_map`，不用 `RelationLoader` 手动注入再 pop
4. **datetime 字段用 `int`** — SyncData 中 datetime 字段一律 `int | None`（毫秒时间戳），用 `safe_ts()` 转换
5. **constants 中 client_filter 处理已有数据时兼顾 int/str** — Bitable 读回 datetime 为 int 毫秒时间戳，`_to_datetime()` 必须处理两种格式

## Code Standards

### Python
- Python 3.12+ with type hints everywhere
- `from __future__ import annotations` in every file
- Pydantic v2 for all data validation
- No `Any` without justification
- `async/await` for all I/O operations

### Lark SDK
- `lark-oapi` Python SDK for all Bitable operations
- Table/field IDs managed centrally in `common/lark_tables.py`
- `field_names` parameter MUST use `json.dumps()` not `str()`
- BaseRepository provides generic CRUD, subclasses only set `table_id`

## Documentation Sync Rule
**CRITICAL**: 任何代码变更后必须同步更新：
- `AGENTS.md` — 项目结构、约定变更
- `.ai/progress.md` — 做了什么、下一步
- `.ai/architecture.md` — 架构、目录结构变更
- `.ai/decisions.md` — 技术决策变更

## Git Conventions
- Branch: `feat/xxx`, `fix/xxx`, `refactor/xxx`, `chore/xxx`
- Commits: Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`)
- PR before merge to main

## Commands
```bash
uv run uvicorn app.main:app --reload --port 3000
uv run ruff check . && uv run ruff format .
uv run mypy app/
uv run pytest
```

## Lark CLI
```bash
lark-cli base +base-get --base-token WXcubLU2oaJbHdsNTzCjy16Spwc
lark-cli base +field-list --base-token WXcubLU2oaJbHdsNTzCjy16Spwc --table-id TABLE_ID
lark-cli base +record-list --base-token WXcubLU2oaJbHdsNTzCjy16Spwc --table-id TABLE_ID
```
