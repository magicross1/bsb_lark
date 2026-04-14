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
    lark_repository.py     # Generic Bitable CRUD base class
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
    email/                 # Email controller (future)
    pricing/               # Pricing controller (future)
    sync/                  # Sync controller (future)
  service/
    cartage.py             # Cartage domain service (repository composition + cache)
    consingee.py           # Consingee domain service
    warehouse_deliver_config.py  # Deliver config domain service
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
