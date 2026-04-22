# Architecture

> 记录项目的技术架构决策，AI 每次新对话都能快速了解"这个项目怎么搭的"。

## Tech Stack
| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.12 | 团队熟悉，复用现有爬虫代码 |
| Framework | FastAPI | 异步、自动文档、类型校验 |
| Lark SDK | larksuiteoapi | Lark 官方 Python SDK |
| Validation | Pydantic v2 | FastAPI 原生，类型安全 |
| Testing | pytest + pytest-asyncio | Python 生态标准 |
| Package Manager | uv | 比 pip 快 10-100x |
| Task Scheduler | APScheduler | 定时任务（爬虫、邮件） |
| Deployment | Docker + Docker Compose | 与现有项目一致 |

## Directory Structure
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
    link_resolver.py       # LinkFieldResolver (关联字段查找/创建)
    schemas.py             # Master data output schemas
  cache/
    factory.py             # CacheFactory (in-memory cache)
    constants.py           # Cache key definitions
  component/               # 外部网站爬虫 Provider
    VbsSearchProvider.py       # VBS 码头查询 (集装箱可用性/ETA/Storage Date)
    HutchisonPortsProvider.py  # Hutchison Ports (import availability/match pin)
    OneStopProvider.py         # 1-Stop (集装箱信息/海关货物状态/空箱归还)
    ContainerChainProvider.py  # ContainerChain (import/export 集装箱信息)
    __init__.py
  controller/
    router.py              # Top-level router aggregation
    data/                  # Master data CRUD controllers
    llm/llm.py             # EDO + Cartage LLM controllers
    email/                 # Email controller (future)
    pricing/               # Pricing controller (future)
    sync/                  # Sync controller — 码头数据同步
  service/
    cartage.py             # Cartage 领域服务 (主数据缓存 + Writeback 统一入口)
    consingee.py           # Consingee 领域服务
    warehouse_deliver_config.py  # Deliver config 领域服务
    edo.py                 # EDO 领域服务 (Shipping Line/Empty Park 缓存 + dict_values)
    ...                    # Other domain services
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
    model/                 # 共享数据模型 (schemas/config 跨 service 使用)
      cartage_writeback_config.py  # WritebackFieldRule, OP_IMPORT/EXPORT_RULES
      cartage_writeback_schemas.py # CartageWritebackResult, WritebackRecordRef, SkippedContainer
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
        schemas.py         # EdoEntry, EdoParseResult, EdoDictValues, EdoProcessResult
        prompts.py         # EDO prompts (动态注入 Shipping Line + Empty Park)
        enrichment.py      # EdoEnrichmentService (精确→别名→模糊三层匹配)
        writeback.py       # EdoWritebackService (按 Container Number 查 Op-Import → UPDATE)
        writeback_schemas.py # EdoWritebackResult + EdoWritebackEntryRef
  repository/
    cartage.py             # Op-Cartage
    import_.py             # Op-Import
    export_.py             # Op-Export
    warehouse_address.py   # MD-Warehouse Address
    warehouse_deliver_config.py  # MD-Warehouse Deliver Config
    consingee.py           # MD-Consingee
    shipping_line.py       # MD-Shipping Line
    empty_park.py          # MD-Empty Park
    ...                    # Other table repositories
```

## Key Patterns
- Service Layer Pattern: controllers → services → Lark SDK
- BaseParser Pattern: AI 文档解析基类，子类只需提供 prompt + build_result()，统一支持 PDF/图片/TXT/字符串输入
- CartageDictValues Pattern: 字典值外部注入到 prompt，默认值硬编码，后续由 service 从 Bitable 拉取覆盖，AI 输出直接匹配字典值减少后处理
- Address Match Pattern: normalize_address → 粗筛(postcode/street) → address_match_score 评分 → 最佳匹配，阈值 MATCH_THRESHOLD=0.6, REVIEW_THRESHOLD=0.8
- CartageService Pattern: 三级缓存(addresses/deliver_configs/consingees)，避免重复 Bitable API 调用
- CartageWriteback Pattern: enriched result → 先写 Op-Cartage → 再写 Op-Import/Op-Export（带 Op-Cartage link），link field 写入格式 `["recXXX"]`
- EDO Match Pattern: Shipping Line 精确名→Short Name fallback；Empty Park 精确名→别名→模糊名+地址三层匹配；EdoDictValues 动态注入 Shipping Line + Empty Park 列表到 prompt
- EDO Writeback Pattern: 按 Container Number 查找 Op-Import → UPDATE 写入 EDO PIN / Shipping Line(link) / Empty Park(link) / Record Status / Source EDO
- RelationLoader Pattern: 批量关联字段解析 — 收集 record_id → 并发 batch_get → 注入回主记录，消除 N+1 串行调用
- Component Provider Pattern: 外部网站爬虫 Provider，每个 Provider 独立实现登录+抓取+解析，目前 4 个: VBS/Hutchison/1-Stop/ContainerChain
- SyncTemplate Pattern (模板方法): 所有爬虫同步模块统一遵循 `SyncTemplate` 三步骨架：
  1. `fetch_records(condition)` — 从 Bitable 筛选待同步记录（用 `_CONDITIONS` dict + `assert_in` 校验）
  2. `fetch_provider_data(records)` — 调外部 Provider，返回 `list[SyncData]`（用 `pluck` / `to_map` / `safe_ts`）
  3. `build_update_wrappers(data_list)` — `SyncData.to_update_wrapper()` 自动转换（Pydantic alias → 飞书列名）
  - `_persist()` 写回 Bitable: `batch_update` → 失败回退逐条 `updateOne`
  - 已实现：Vessel、Container、Clear、VBS（5 个码头各一个 SyncTemplate 子类）
- SyncData Pattern: Pydantic BaseModel 声明式定义「外部数据 → 飞书字段」映射
  - `_metadata_fields()` — 排除不写回的字段（record_id, container_number 等）
  - `alias` — Python 字段名 → 飞书列名（如 `eta` → `"ETA"`）
  - `to_update_wrapper()` — 自动 exclude_none + exclude metadata + by_alias → `UpdateWrapper`
- QueryWrapper Pattern (MyBatis-Plus 风格): 链式查询条件构建器，替代旧 BitableQuery
  - 每个子句同时存储 `condition_node`(服务端 search API filter) 和 `predicate`(客户端精筛)
  - `eq("record_id", rid)` / `in_list("record_id", ids)` 特殊处理：不走 search API，走直连 GET/batch_get
  - `.select("field1", "field2")` — 指定返回字段
  - `.order_by("field", desc=True)` — 排序
  - `.any_empty(fields)` / `.not_in_or_empty(field, values)` — 组合条件
  - `.client_filter(predicate)` — 纯客户端筛选（如 `ETA < now()`）
- UpdateWrapper Pattern (MyBatis-Plus 风格): 链式更新构建器
  - `.eq("record_id", rid).set("field", value).set_all(fields).with_label("CN")` — 链式调用
  - `with_label()` 仅用于日志标记，不写入 Bitable
- BaseRepository Pattern: 统一的 Bitable CRUD 基类
  - 单条操作带 One 后缀: `findOne` / `createOne` / `updateOne` / `deleteOne`
  - 批量操作: `list` / `page` / `batch_create` / `batch_update` / `batch_delete`
  - `list_fields()` → `list[FieldMeta]`（frozen dataclass，非 dict）
- Clear Provider Routing Pattern: 按 Terminal Full Name 选择 Provider：空→1-Stop customs fallback Hutchison；HUTCHISON PORTS - PORT BOTANY→只 Hutchison；其他→只 1-Stop customs
- VBS Terminal Routing Pattern: 按 Terminal Full Name 路由到 VBS operation：DP WORLD NS→dpWorldNSW / DP WORLD VI→dpWorldVIC / PATRICK NS→patrickNSW / PATRICK VI→patrickVIC / VICTORIA INTERNATIONAL→victVIC；Patrick VIC 的 HTML 使用 `MovementDetailsForm` 前缀（其他码头用 `ContainerVesselDetailsForm`），字段名也不同：ImportAvailability→ContainerAvailability, StorageStartDate→ContainerStorageStart；日期格式含秒需多格式尝试
- Collection Utils Pattern: `pluck` / `to_map` / `filter_by` / `group_by` / `partition` 消除 sync 场景中的重复集合操作
- Assert Utils Pattern: `assert_in` / `assert_not_blank` / `assert_not_none` / `assert_true` 消除重复断言代码
- Centralized Lark Client: 所有 Lark API 调用通过统一模块
- Token Auto-refresh: tenant_access_token 自动刷新
- Fail Fast: 环境变量启动时校验
- Structured Logging: 带 correlation ID 的结构化日志

## Lark CLI
- Tool: `@larksuite/cli` v1.0.7
- App ID: `cli_a947411943a15e15`
- Base Token: `WXcubLU2oaJbHdsNTzCjy16Spwc`
- Base Name: BSB
- Region: jp.larksuite.com (Australia/Sydney timezone)
- Auth: user identity (ALEX CHENG, ou_178b1e905512ed8eec39090968cb778e)
- Note: raw API (`lark-cli api`) 404 on jp region, use shortcuts (`+base-get`, `+field-list` etc.) instead

## Bitable Schema (BSB Base - 37 tables)

### Master Data (MD-*)
| Table | ID | Description |
|-------|-----|-------------|
| MD-Warehouse Address | tblDpXM58OER6hfB | 仓库地址 (Address, Location, Suburb link, Consingee link, Deliver link) |
| MD-Warehouse Deliver Config | tblIQSNhABhut1u7 | 仓库配送配置 (Deliver Type, Door Position, Open/Close Time, Max Containers) |
| MD-Consingee | tbli30rPlY5X5KT5 | 收货人 (Name, Contact, Phone, Email, Address link, Cartage link) |
| MD-Suburb | tbljmXaiKavx3Ycn | 郊区 (Suburb, State, Postcode, Location, Rural Tailgate) |
| MD-Base Node | tblxITA0SwQpePBr | 基础节点 (Base Node, Location, Type, State) |
| MD-Distance Matrix | tblurjC2qmgFmXFz | 距离矩阵 (Suburb, Base Node, Distance, Time, Toll Code) |
| MD-Vehicle | tblgc1OZ7ZFrCBNt | 车辆 (Rego Number, Vehicle Type/Class, Status, Depot, Driver link) |
| MD-Driver | tblzxHN8llzAf2ge | 司机 (Driver Name, Type, Status, MSIC, Vehicle link, Contractor link) |
| MD-Driver Config | tblnYYrqNM7Gact9 | 司机配置 (Labour Type/Rate, Fuel Surcharge, Truck Type, Deduction) |
| MD-Contractor | tblsS9OXQG5LrbGk | 承包商 (Company Name, ABN, BSB, Account, Payment Term) |
| MD-Sub Carrier | tblfaVZfljmbzYka | 子承运商 (Sub Carrier, Company Name link, Email, Box Rate link) |
| MD-Sub Carrier Box Rate | tbleewWnrNbAklTj | 子承运商箱费率 (Sub Carrier, Consingee, Deliver Config, Cartage link) |
| MD-Shipping Line | tblDcwZBZzMdIA0b | 船公司 (Shipping Line, Short Name, Import/Export link) |
| MD-Empty Park | tblpyqsI8mFtV1nO | 空箱堆场 (Empty Park, Location, Depot, De-hire Cost, Booking System) |
| MD-Terminal | tblmR6o4iDakZT3H | 码头 (Terminal Name, IS CODE, Port of Discharge, Depot, Base Node) |
| MD-Terminal Cost | tblKDcsGemKgDNLb | 码头费用 (Cost Type, Amount, Terminal link) |
| MD-Terminal Fine | tblwwKiGyef3hfF4 | 码头罚款 (Fine Type, Scene, Amount, Terminal link) |
| MD-Freight Forwarder | tbloEdmaeYAp4D1s | 货代 (Name, Code, Status, Credit Limit/Term, Price Level NSW/VIC link) |
| MD-FF Contact | tbl2hIFHr8BeqkmU | 货代联系人 (Contact Person, Phone, Email, Position, Tags) |

### Pricing (MD-Price-*)
| Table | ID | Description |
|-------|-----|-------------|
| MD-Price Level | tblVxSiE6t2grOuf | 价格等级 (Description, State, Fuel/DG Rate, links to all price tables) |
| MD-Price Cartage | tbl8RJJzlHE4Lt3i | 短驳费 (Fee Code, CTN Size, Zone, Amount, Deliver Type) |
| MD-Price Terminal | tbl7MiJUCa1Reo3c | 码头费 (Fee Type, Terminal, Amount) |
| MD-Price Empty | tbledfARPS0C7736 | 空箱费 (Empty Class, Description, Amount, Empty Park link) |
| MD-Price Extra | tblTPoMIzQ1tQ54q | 附加费 (Fee Code, Condition, Amount, Unit) |
| MD-Price Overweight | tblxsPlQkKKsd5K3 | 超重费 (Weight Range, Deliver Type, Amount) |
| MD-Price Toll | tblCpSWQ8QPQJSgJ | 过路费 (Description, Amount) |

### Operations (Op-*)
| Table | ID | Description |
|-------|-----|-------------|
| Op-Cartage | tblKUPmqga4woLk5 | 短驳委托 (Booking Ref, Consingee, Deliver Config, Import/Export Booking) |
| Op-Vessel Schedule | tblSB69pB2YPYUqK | 船期 (Vessel Name, Voyage, ETA, ETD, Cutoff, Terminal) |
| Op-Import | tblYS3JiR1KiU2hO | 进口 (Container Number, Type, Weight, Vessel, EDO, Terminal) |
| Op-Export | tblKCAzuxD8Jouvt | 出口 (Container Number, Type, Booking Ref, Release, Commodity) |
| Op-Trip | tblI7wx6V6LfMDA2 | 行程 (Driver, Prime Mover, Trailer, Date/Time, Logistics Status) |

### Config / Dictionary
| Table | ID | Description |
|-------|-----|-------------|
| Dict Table | tblfGiOEkdufx98J | 字典表 (ID, StartPlaceType, Deliver Type, State, Container Type, Commodity, Action Status) |

### 副本 (Backup Copies - 5 tables)
- MD-Price Empty 副本 (tblsw5oIAE3npJGW)
- MD-Price Terminal 副本 (tblP10OSrUpo15j4)
- MD-Price Cartage 副本 (tblnKTgmWsmDGPQB)
- 城市 副本 (tbl6u4zIxYeSRGrd)
- 起点-城市 副本 (tbl6kCPZd6wJhhfl)

## API Contracts
- RESTful 端点设计
- 统一响应格式: `{ code, data, message }`
- Bitable CRUD 操作端点
- Webhook 事件接收端点

## Environment Variables
| Variable | Purpose | Required |
|----------|---------|----------|
| LARK_APP_ID | Lark 应用 ID | Yes |
| LARK_APP_SECRET | Lark 应用 Secret | Yes |
| LARK_BITABLE_APP_TOKEN | 多维表格 App Token | Yes |
| PORT | 服务端口 | No (default: 3000) |
| ZHIPUAI_API_KEY | 智谱 AI API Key | Yes |
| AI_MODEL | 智谱模型名 | No (default: glm-5v-turbo) |

---
*最后更新: 2026-04-22*
