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
  main.py                  # FastAPI entry + auto module registration
  config/
    settings.py            # Pydantic Settings (env vars)
    lark.py                # Lark client singleton
  core/
    base_repository.py     # Generic Bitable CRUD
    base_service.py        # Service base class
    response.py            # Unified response {code, data, message}
    exceptions.py          # AppError, NotFoundError, LarkApiError
    middleware.py           # Correlation ID + error handling
    registry.py            # Auto-discover & register module routers
  shared/
    lark_tables.py         # 37 Bitable table/field ID mappings
    enums.py               # Depot, ContainerType, DeliverType
    utils.py               # Date/time helpers (Sydney timezone)
  modules/                 # Business modules (auto-registered)
    master_data/           # MD-* tables
    pricing/               # MD-Price-* + fee calculators
    operations/            # Op-* + spider strategies
    email/                 # Email automation
    sync/                  # Cross-table data sync
```

## Key Patterns
- Service Layer Pattern: controllers → services → Lark SDK
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
| NODE_ENV | 运行环境 | No (default: development) |

---
*最后更新: 2026-04-10*
