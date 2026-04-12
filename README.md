# BSB Lark

BSB Transport Australia - 基于 Lark Bitable 的物流运营后端

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 语言 | Python 3.12 | 团队熟悉，复用现有爬虫代码 |
| 框架 | FastAPI | 异步、自动 OpenAPI 文档、类型校验 |
| 数据源 | Lark Bitable (37 表) | 替代原 Google Sheets |
| Lark SDK | lark-oapi | 官方 Python SDK |
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
# 编辑 .env 填入 LARK_APP_ID 和 LARK_APP_SECRET

# 4. 启动开发服务器
uv run uvicorn app.main:app --reload --port 3000

# 5. 访问
# API: http://localhost:3000
# 文档: http://localhost:3000/docs
# 健康检查: http://localhost:3000/health
```

## Python 解释器配置

项目虚拟环境路径：`.venv/Scripts/python.exe`

在 VS Code / PyCharm 中选择此路径作为项目解释器。

## 项目结构

```
bsb_lark/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # 环境变量配置
│   │   └── lark.py                # Lark 客户端
│   ├── core/
│   │   ├── __init__.py
│   │   ├── base_repository.py     # Bitable CRUD 基类
│   │   ├── base_service.py        # Service 基类
│   │   ├── response.py            # 统一响应格式
│   │   ├── exceptions.py          # 自定义异常
│   │   ├── middleware.py          # 请求中间件
│   │   └── registry.py            # 模块自动注册
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── lark_tables.py         # Bitable 表/字段 ID 映射
│   │   ├── enums.py               # 业务枚举
│   │   └── utils.py               # 工具函数
│   └── modules/
│       ├── __init__.py
│       ├── master_data/           # 主数据模块 (已实现)
│       │   ├── __init__.py
│       │   ├── router.py
│       │   ├── service.py
│       │   ├── repository.py
│       │   └── schemas.py
│       ├── pricing/               # 价格/费用模块 (待实现)
│       ├── operations/            # 运营/集装箱模块 (待实现)
│       ├── email/                 # 邮件自动化模块 (待实现)
│       └── sync/                  # 数据同步模块 (待实现)
├── tests/
│   └── __init__.py
├── .ai/                           # AI 知识文档 (自动加载)
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── AGENTS.md                      # AI 代理规则
└── opencode.json                  # OpenCode 配置
```

## 各文件详细说明

### `app/main.py` — FastAPI 入口

创建 FastAPI 应用实例，挂载中间件和自动注册所有业务模块路由。

- 创建 `FastAPI` app，设置标题和版本
- 添加 `AppMiddleware`（Correlation ID + 错误处理 + 响应计时）
- 添加 `CORSMiddleware`（开发环境允许所有跨域）
- 调用 `register_modules(app)` 自动扫描 `modules/` 下所有子目录，发现 `router.py` 则注册
- 内置端点：
  - `GET /health` — 健康检查，返回 `{"status": "ok", "env": "development"}`
  - `GET /modules` — 列出所有已注册模块及其路由
- `__main__` 入口：`uvicorn` 启动，开发模式自动热重载

---

### `app/config/settings.py` — 环境变量配置

基于 `pydantic-settings` 的配置类，从 `.env` 文件读取环境变量。

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `LARK_APP_ID` | str | `""` | Lark 应用 ID |
| `LARK_APP_SECRET` | str | `""` | Lark 应用 Secret |
| `LARK_BITABLE_APP_TOKEN` | str | `""` | 多维表格 App Token |
| `PORT` | int | `3000` | 服务端口 |
| `ENV` | str | `"development"` | 运行环境 |
| `LOG_LEVEL` | str | `"info"` | 日志级别 |

启动时自动读取 `.env` 文件，缺少必填变量会在首次使用时抛出异常。

---

### `app/config/lark.py` — Lark 客户端

初始化 Lark SDK 客户端单例。

- `get_lark_client()` — 返回 `lark.Client` 实例，全局只创建一次
- 使用 `settings.LARK_APP_ID` 和 `settings.LARK_APP_SECRET` 初始化
- 开发环境设置 `LogLevel.DEBUG`，生产环境 `LogLevel.INFO`
- SDK 内部自动管理 `tenant_access_token` 的获取和刷新

---

### `app/core/base_repository.py` — Bitable CRUD 基类

所有 Repository 的基类，封装 Lark Bitable API 的通用 CRUD 操作。子类只需设置 `table_id` 即可继承全部能力。

**类属性：**
- `table_id: str` — 子类必须设置，对应 Bitable 表 ID

**提供的方法：**

| 方法 | 说明 | 返回 |
|------|------|------|
| `list_records(page_size, page_token, filter_expr, sort_expr, field_names)` | 分页查询记录 | `list[dict]` |
| `get_record(record_id)` | 获取单条记录 | `dict` |
| `create_record(fields)` | 创建记录 | `dict` |
| `update_record(record_id, fields)` | 更新记录 | `dict` |
| `delete_record(record_id)` | 删除记录 | `None` |
| `batch_create_records(fields_list)` | 批量创建记录 | `list[dict]` |
| `list_fields()` | 列出表字段 | `list[dict]` |

**返回格式：** 每条记录都包含 `record_id` + `fields` 展开的字典。

**错误处理：**
- 记录不存在（code=1254006）→ 抛出 `NotFoundError`
- 其他 API 错误 → 抛出 `LarkApiError`

**新增 Repository 示例：**
```python
class DriverRepository(BaseRepository):
    table_id = T.md_driver.id  # 只需一行
```

---

### `app/core/base_service.py` — Service 基类

所有 Service 的基类，持有 `repository` 引用。

- `repository: BaseRepository` — 关联的 Repository 实例
- 子类通过构造函数注入 Repository

---

### `app/core/response.py` — 统一响应格式

所有 API 返回统一的 JSON 响应格式。

```json
// 成功
{"code": 0, "data": {...}, "message": "success"}

// 失败
{"code": -1, "data": null, "message": "error description"}
```

| 方法 | 说明 |
|------|------|
| `ApiResponse.ok(data, message)` | 成功响应，code=0 |
| `ApiResponse.error(code, message, data)` | 错误响应，code 非 0 |

---

### `app/core/exceptions.py` — 自定义异常

| 异常类 | code | 说明 |
|--------|------|------|
| `AppError` | -1 | 基础异常，所有业务异常的父类 |
| `NotFoundError` | 404 | 记录/资源不存在 |
| `ValidationError` | 422 | 数据校验失败 |
| `LarkApiError` | Lark API 返回的错误码 | Lark API 调用失败 |

所有异常都包含 `code`、`message`、`detail` 三个属性，被 `AppMiddleware` 统一捕获并转为标准响应。

---

### `app/core/middleware.py` — 请求中间件

`AppMiddleware` 继承 `BaseHTTPMiddleware`，对每个请求：

1. 生成 8 位 `correlation_id`，挂到 `request.state`
2. 记录请求开始时间
3. 捕获 `AppError` → 转为标准错误响应
4. 捕获未知异常 → 返回 500 错误响应
5. 在响应头中添加：
   - `X-Correlation-ID` — 请求追踪 ID
   - `X-Response-Time-Ms` — 响应耗时（毫秒）

---

### `app/core/registry.py` — 模块自动注册

自动扫描 `app/modules/` 下的所有子目录，发现 `router.py` 则注册到 FastAPI。

**工作原理：**
1. `pkgutil.iter_modules(modules.__path__)` 扫描所有子模块
2. 尝试 `importlib.import_module(f"app.modules.{name}.router")`
3. 如果模块有 `router` 属性（`APIRouter` 实例），则 `app.include_router(router)`
4. 将模块信息存入 `_MODULE_REGISTRY` 字典

**`/modules` 端点返回示例：**
```json
{
  "master_data": {
    "prefix": "/master-data",
    "routes": ["/warehouse-addresses", "/consingees", "/suburbs", ...]
  }
}
```

**新增模块只需：** 在 `modules/` 下创建目录，放入 `router.py`（导出 `router = APIRouter(...)`），重启即自动注册。

---

### `app/shared/lark_tables.py` — Bitable 表/字段 ID 映射

集中管理 BSB Base 所有 37 张表的 ID 和字段 ID，避免硬编码。

**核心类型：**
- `FieldRef(id, name)` — 字段引用，存储 `field_id` 和 `field_name`
- `TableDef(id, name, fields)` — 表定义，存储 `table_id`、表名和字段字典

**使用方式：**
```python
from app.shared.lark_tables import T

# 获取表 ID
T.md_driver.id           # "tblzxHN8llzAf2ge"

# 获取字段 ID
T.md_driver.fields["driver_name"].id   # "fldlP3B9Ra"

# 快捷方式：T.<table>.f("<field_key>")
T.md_driver.f("driver_name")           # "fldlP3B9Ra"
```

**已映射的表（32 张主表 + APP_TOKEN）：**

| 分类 | 表 |
|------|-----|
| 主数据 (MD-*) | Warehouse Address, Warehouse Deliver Config, Consingee, Suburb, Base Node, Distance Matrix, Vehicle, Driver, Driver Config, Contractor, Sub Carrier, Sub Carrier Box Rate, Shipping Line, Empty Park, Terminal, Terminal Cost, Terminal Fine, Freight Forwarder, FF Contact |
| 价格 (MD-Price-*) | Price Level, Price Cartage, Price Terminal, Price Empty, Price Extra, Price Overweight, Price Toll |
| 运营 (Op-*) | Cartage, Vessel Schedule, Import, Export, Trip |
| 字典 | Dict Table |

5 张副本表（名称含"副本"）未映射，因为它们是备份。

---

### `app/shared/enums.py` — 业务枚举

定义物流业务中常用的枚举值，全部继承 `str` 和 `Enum`，可直接用作字符串。

| 枚举类 | 值 | 说明 |
|--------|-----|------|
| `Depot` | NSW, VIC | 仓库区域 |
| `ContainerType` | 20STD, 40STD, 20SDL, 40SDL, 20DROP, 40DROP | 集装箱类型 |
| `DeliverType` | Import, Export, Empty | 配送类型 |
| `LogisticsStatus` | Pending, In Progress, Completed, Cancelled | 物流状态 |
| `TerminalName` | DP World NSW/VIC, Patrick NSW/VIC, Hutchison NSW, VICT VIC | 码头名称 |

---

### `app/shared/utils.py` — 工具函数

| 函数 | 说明 |
|------|------|
| `now_sydney()` | 返回当前悉尼时间（`Australia/Sydney` 时区） |
| `now_utc()` | 返回当前 UTC 时间 |
| `format_datetime(dt, fmt)` | 格式化 datetime 为字符串，默认 `"%Y-%m-%d %H:%M:%S"` |
| `parse_datetime(s, fmt)` | 解析字符串为 datetime |

---

### `app/modules/master_data/` — 主数据模块

#### `repository.py`

9 个 Repository 类，每个只需一行设置 `table_id`：

| Repository | 对应表 |
|-----------|--------|
| `WarehouseAddressRepository` | MD-Warehouse Address |
| `ConsingeeRepository` | MD-Consingee |
| `SuburbRepository` | MD-Suburb |
| `DriverRepository` | MD-Driver |
| `VehicleRepository` | MD-Vehicle |
| `TerminalRepository` | MD-Terminal |
| `FreightForwarderRepository` | MD-Freight Forwarder |
| `EmptyParkRepository` | MD-Empty Park |
| `DistanceMatrixRepository` | MD-Distance Matrix |

全部继承 `BaseRepository`，自动拥有 list/get/create/update/delete/batch_create/list_fields 七个方法。

#### `service.py`

`MasterDataService` 聚合 9 个 Repository，提供面向业务的方法。

- 构造函数中初始化所有 Repository 实例
- 每个方法直接代理到对应 Repository，未来可在 Service 层添加业务逻辑（如数据转换、校验、跨表查询）

#### `schemas.py`

Pydantic v2 响应模型，用于类型提示和自动 OpenAPI 文档生成。

| Model | 字段 |
|-------|------|
| `WarehouseAddressOut` | record_id, address, detail |
| `ConsingeeOut` | record_id, name, contact, phone, email |
| `SuburbOut` | record_id, suburb, state, postcode, rural_tailgate |

#### `router.py`

FastAPI 路由，前缀 `/master-data`，标签 `Master Data`。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/master-data/warehouse-addresses` | GET | 列出仓库地址 |
| `/master-data/warehouse-addresses/{record_id}` | GET | 获取单个仓库地址 |
| `/master-data/consingees` | GET | 列出收货人 |
| `/master-data/consingees/{record_id}` | GET | 获取单个收货人 |
| `/master-data/suburbs` | GET | 列出郊区 |
| `/master-data/drivers` | GET | 列出司机 |
| `/master-data/vehicles` | GET | 列出车辆 |
| `/master-data/terminals` | GET | 列出码头 |
| `/master-data/freight-forwarders` | GET | 列出货代 |
| `/master-data/empty-parks` | GET | 列出空箱堆场 |
| `/master-data/distance-matrix` | GET | 列出距离矩阵 |

所有列表端点支持 `page_size`（默认 100，最大 500）和 `filter_expr`（Bitable 过滤表达式）查询参数。

---

### `pyproject.toml` — 项目配置

使用 `uv` 管理的项目配置文件。

**核心依赖：**
- `fastapi>=0.115.0` — Web 框架
- `uvicorn[standard]>=0.34.0` — ASGI 服务器
- `pydantic>=2.10.0` — 数据校验
- `pydantic-settings>=2.7.0` — 环境变量管理
- `httpx>=0.28.0` — 异步 HTTP 客户端
- `lark-oapi>=1.4.0` — Lark SDK
- `apscheduler>=3.10.0` — 定时任务

**开发依赖（可选）：**
- `pytest`, `pytest-asyncio` — 测试
- `ruff` — 代码检查和格式化
- `mypy` — 类型检查

---

### `.env.example` — 环境变量模板

复制为 `.env` 并填入实际值：

```bash
LARK_APP_ID=cli_xxxxx              # Lark 开发者后台获取
LARK_APP_SECRET=xxxxx              # Lark 开发者后台获取
LARK_BITABLE_APP_TOKEN=WXcubLU2oaJbHdsNTzCjy16Spwc  # BSB Base Token（已填）
PORT=3000
ENV=development
LOG_LEVEL=info
```

---

### `Dockerfile` + `docker-compose.yml`

- Docker 镜像：`python:3.12-slim`
- 安装依赖 → 复制代码 → 暴露 3000 端口 → 启动 uvicorn
- docker-compose 从 `.env` 读取配置

```bash
docker-compose up --build
```

---

### `.ai/` — AI 知识文档

AI 每次新对话自动读取，保持上下文连续性。

| 文件 | 内容 |
|------|------|
| `product-brief.md` | 产品定义、目标用户、核心功能 ← 请填写 |
| `architecture.md` | 技术栈、目录结构、Bitable 完整表结构（37表） |
| `decisions.md` | 技术决策记录（Python vs TS、不加 Redis、模块化架构等） |
| `progress.md` | 开发进度日志 |
| `style-guide.md` | 代码风格约定 |

---

## Lark CLI

调试和查看 Bitable 数据的命令行工具：

```bash
# 安装
npm install -g @larksuite/cli

# 登录
lark-cli auth login --recommend

# 常用命令
lark-cli base +base-get --base-token WXcubLU2oaJbHdsNTzCjy16Spwc
lark-cli base +field-list --base-token WXcubLU2oaJbHdsNTzCjy16Spwc --table-id TABLE_ID
lark-cli base +record-list --base-token WXcubLU2oaJbHdsNTzCjy16Spwc --table-id TABLE_ID --limit 10
lark-cli auth status
```

## 开发命令

```bash
uv run uvicorn app.main:app --reload --port 3000   # 启动开发服务器
uv run ruff check .                                  # 代码检查
uv run ruff format .                                 # 代码格式化
uv run mypy app/                                     # 类型检查
uv run pytest                                        # 运行测试
```
