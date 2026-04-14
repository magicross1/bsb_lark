# BSB Lark

BSB Transport Australia - 基于 Lark Bitable 的物流运营后端

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 语言 | Python 3.12 | 团队熟悉，复用现有爬虫代码 |
| 框架 | FastAPI | 异步、自动 OpenAPI 文档、类型校验 |
| 数据源 | Lark Bitable (37 表) | 替代原 Google Sheets |
| Lark SDK | lark-oapi | 官方 Python SDK |
| AI | 智谱 ZhipuAI (glm-5v-turbo) | 多模态 PDF 解析 |
| 数据校验 | Pydantic v2 | FastAPI 原生集成 |
| 包管理 | uv | 比 pip 快 10-100x |
| 部署 | Docker + Docker Compose | |

## 快速开始

```bash
# 1. 安装 uv (如果没有)
pip install uv

# 2. 创建虚拟环境 & 安装依赖
uv sync

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LARK_APP_ID, LARK_APP_SECRET, ZHIPUAI_API_KEY

# 4. 启动开发服务器
uv run uvicorn app.main:app --reload --port 3000

# 5. 访问
# API: http://localhost:3000
# 文档: http://localhost:3000/docs
# 健康检查: http://localhost:3000/health
```

## 项目结构

```
app/
  main.py                  # FastAPI 入口 + 中间件 + 路由挂载
  config/
    app_settings.py        # Pydantic Settings (环境变量)
    lark.py                # Lark 客户端单例
    cartage_matching.py    # 地址匹配阈值常量
  core/
    base_parser.py         # AI 解析基类 (PDF/图片/TXT → AI → JSON)
    base_service.py        # Service 基类
    lark.py                # Lark 客户端 re-export
    llm.py                 # 智谱 AI 客户端 + 模型辅助函数
    lark_bitable_value.py  # Bitable 值提取工具函数
    utils.py               # 日期时间工具 (悉尼时区)
    midlleware/
      registry.py          # 模块自动注册
  common/
    lark_tables.py         # 37 表 ID/字段 ID 映射
    lark_repository.py     # Bitable CRUD 基类
    response.py            # 统一响应 {code, data, message}
    exceptions.py          # AppError, NotFoundError, LarkApiError
    enums.py               # Depot, ContainerType, DeliverType
  entity/
    address.py             # 地址标准化 + 匹配评分
    relation.py            # 跨表关联解析 (RelationResolver)
    link_resolver.py       # 关联字段查找/创建 (LinkFieldResolver)
  cache/
    factory.py             # 缓存工厂
    constants.py           # 缓存 key 定义
  controller/
    router.py              # 顶级路由聚合
    data/                  # 主数据 CRUD 控制器
    llm/llm.py             # Cartage + EDO AI 控制器
  service/
    cartage.py             # Cartage 领域服务 (三级缓存)
    consingee.py           # Consingee 领域服务
    warehouse_deliver_config.py  # Deliver Config 领域服务
    llm_service/
      llm_service.py       # LLM 应用服务 (facade)
      cartage/
        cartage_llm.py     # Cartage LLM 编排
        parser.py          # CartageParser (继承 BaseParser)
        prompts.py         # AI 提示词
        schemas.py         # ImportContainerEntry, ExportBookingEntry, CartageDictValues
        result_builder.py  # 原始 JSON → CartageParseResult
        enrichment.py      # 地址/Consingee 匹配
        process_schemas.py # CartageProcessResult, AddressMatch
        export_bookings.py # 出口柜 release_qty 展开
        writeback.py       # CartageWritebackService (写回 Bitable)
        writeback_config.py # WritebackFieldRule 配置 (声明式)
        writeback_schemas.py # CartageWritebackResult
      edo/
        edo_llm.py         # EDO LLM 编排
        parser.py          # EdoParser
        schemas.py         # EdoEntry, EdoParseResult
        prompts.py         # EDO 提示词
  repository/
    cartage.py             # Op-Cartage
    import_.py             # Op-Import
    export_.py             # Op-Export
    warehouse_address.py   # MD-Warehouse Address
    warehouse_deliver_config.py  # MD-Warehouse Deliver Config
    consingee.py           # MD-Consingee
    ...                    # 其他表仓储
```

## 已实现功能

### 1. Cartage 自动录入 (核心功能)

从 Cartage Advise 附件 (PDF/图片/TXT) 自动提取数据、匹配主数据、写回 Bitable。

**完整流程**: `附件 → AI解析 → 地址匹配 → 写回Bitable`

**进口柜 (Import)**:
- 每个 Container Number 创建 1 个 Op-Cartage + 1 个 Op-Import (1-to-1)
- 自动匹配: 仓库地址 → Deliver Config + Consingee
- 自动查找/创建: Vessel Schedule (Vessel Name + Voyage + Base Node 三字段唯一键)
- 重复 Container Number 自动跳过 (不中止全部)

**出口柜 (Export)**:
- Release Qty > 1 时自动展开为多条记录 (Booking Ref 不变, Container Number 加 -序号)
- 例: RSG20811, qty=2 → Container Number = RSG20811-1, RSG20811-2
- 每个 Container Number 创建 1 个 Op-Cartage + 1 个 Op-Export (1-to-1)
- Consingee/Deliver Config 非必填 (出口可能无地址匹配)

**写回配置驱动**: 所有 Bitable 字段的写入规则用 `WritebackFieldRule` 声明式配置，而非硬编码逻辑。

| API 端点 | 方法 | 说明 |
|----------|------|------|
| `POST /cartage/parse` | 上传文件 | 解析文档，返回结构化数据 |
| `POST /cartage/parse-text` | 文本 | 解析文本 |
| `POST /cartage/process` | 上传文件 | 解析 + 地址匹配 |
| `POST /cartage/process-text` | 文本 | 解析 + 地址匹配 |
| `POST /cartage/writeback` | 上传文件 | 完整流程: 解析 + 匹配 + 写回 Bitable |
| `POST /cartage/writeback-text` | 文本 | 完整流程 |
| `POST /cartage/clear-cache` | - | 清除缓存 |

### 2. EDO 解析

从 EDO (Empty Delivery Order) PDF 提取 container_number / edo_pin / shipping_line / empty_park。

| API 端点 | 方法 | 说明 |
|----------|------|------|
| `POST /edo/parse` | 上传文件 | 解析 EDO 文件 |

### 3. 主数据 CRUD

仓库地址、收货人、郊区等 9 个主数据表的只读端点。

| API 端点 | 方法 | 说明 |
|----------|------|------|
| `GET /master-data/warehouse-addresses` | 列表 | 仓库地址 |
| `GET /master-data/consingees` | 列表 | 收货人 |
| `GET /master-data/suburbs` | 列表 | 郊区 |
| `GET /master-data/drivers` | 列表 | 司机 |
| `GET /master-data/vehicles` | 列表 | 车辆 |
| `GET /master-data/terminals` | 列表 | 码头 |
| `GET /master-data/freight-forwarders` | 列表 | 货代 |
| `GET /master-data/empty-parks` | 列表 | 空箱堆场 |
| `GET /master-data/distance-matrix` | 列表 | 距离矩阵 |

## Bitable 表结构 (BSB Base - 37 表)

### 主数据 (MD-*)
| 表 | 说明 |
|----|------|
| MD-Warehouse Address | 仓库地址 |
| MD-Warehouse Deliver Config | 仓库配送配置 (Deliver Type, 开闭时间, 最大柜量) |
| MD-Consingee | 收货人 |
| MD-Suburb | 郊区 |
| MD-Base Node | 基础节点 (港口) |
| MD-Distance Matrix | 距离矩阵 |
| MD-Vehicle / MD-Driver / MD-Driver Config | 车辆/司机/配置 |
| MD-Contractor / MD-Sub Carrier / MD-Sub Carrier Box Rate | 承包商/子承运商 |
| MD-Shipping Line / MD-Empty Park / MD-Terminal | 船公司/空箱堆场/码头 |
| MD-Terminal Cost / MD-Terminal Fine | 码头费用/罚款 |
| MD-Freight Forwarder / MD-FF Contact | 货代/联系人 |

### 价格 (MD-Price-*)
| 表 | 说明 |
|----|------|
| MD-Price Level | 价格等级 |
| MD-Price Cartage / Terminal / Empty | 短驳费/码头费/空箱费 |
| MD-Price Extra / Overweight / Toll | 附加费/超重费/过路费 |

### 运营 (Op-*)
| 表 | 说明 |
|----|------|
| Op-Cartage | 短驳委托 (Booking Ref, Consingee, Deliver Config) |
| Op-Vessel Schedule | 船期 (Vessel Name, Voyage, Base Node) |
| Op-Import | 进口 (Container Number, Type, Weight, Commodity) |
| Op-Export | 出口 (Booking Reference, Release Qty, Container Type) |
| Op-Trip | 行程 |

### 字典
| 表 | 说明 |
|----|------|
| Dict Table | 字典值 (Container Type, Commodity, Deliver Type 等) |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| LARK_APP_ID | 是 | Lark 应用 ID |
| LARK_APP_SECRET | 是 | Lark 应用 Secret |
| LARK_BITABLE_APP_TOKEN | 是 | 多维表格 App Token |
| ZHIPUAI_API_KEY | 是 | 智谱 AI API Key |
| AI_MODEL | 否 | 智谱模型名 (默认 glm-5v-turbo) |
| PORT | 否 | 服务端口 (默认 3000) |
| ENV | 否 | 运行环境 (默认 development) |
| LOG_LEVEL | 否 | 日志级别 (默认 info) |

## Lark CLI

```bash
# 安装
npm install -g @larksuite/cli

# 登录
lark-cli auth login --recommend

# 常用命令
lark-cli base +base-get --base-token WXcubLU2oaJbHdsNTzCjy16Spwc
lark-cli base +field-list --base-token WXcubLU2oaJbHdsNTzCjy16Spwc --table-id TABLE_ID
lark-cli base +record-list --base-token WXcubLU2oaJbHdsNTzCjy16Spwc --table-id TABLE_ID --limit 10
```

## 开发命令

```bash
uv run uvicorn app.main:app --reload --port 3000   # 启动开发服务器
uv run ruff check . && uv run ruff format .          # 代码检查 + 格式化
uv run mypy app/                                     # 类型检查
uv run pytest                                        # 运行测试
```

## 技术文档

详细技术文档位于 `.ai/` 目录：

| 文件 | 内容 |
|------|------|
| `.ai/cartage-writeback-guide.md` | Cartage 自动录入完整技术文档 |
| `.ai/architecture.md` | 技术架构、目录结构、Bitable 完整表结构 |
| `.ai/decisions.md` | 技术决策记录 |
| `.ai/progress.md` | 开发进度日志 |
