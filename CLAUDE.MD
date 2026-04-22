# BSB Lark Architecture Rules

## 目标

本文件定义 `bsb_lark` 的目录职责、分层边界、允许依赖方向与禁止事项。

这是强约束，不是建议。

- 使用中文回复  代码注释也使用中文

- 任何新增代码都必须先判断自己属于哪一层，再放到对应目录。
- 同级职责不允许互相调用。
- 不允许跨层调用。
- 不允许职责混淆。
- 不允许为了“省一层”而绕过既定调用链。

---

## 零、文件名必须和职责一致

文件名不是随便起的，文件名必须准确表达它的唯一主要职责。

这是强约束：

- 看到文件名，应该能直接判断这个文件负责什么。
- 文件的真实职责，必须和文件名一致。
- 如果文件名和职责不一致，优先改名；如果只是无意义转发，直接删除。

### 命名规则

- `router.py` 只能放路由聚合或 HTTP 入口定义。
- `service.py` / `xxx_service.py` 只能放 service。
- `repository.py` / `xxx_repository.py` 只能放 repository。
- `parser.py` 只能放解析逻辑。
- `schemas.py` 只能放数据模型。
- `container.py` / `xxx_container.py` 只能放依赖装配与组合根。
- `deps.py` 只能放依赖提供器，且通常用于框架注入场景，例如 `Depends(...)`。

### 严格禁止

- 用 `deps.py` 伪装 service 注册表。
- 用 `container.py` 承载业务逻辑。
- 用 `router.py` 暴露 parser、service、repository。
- 用 `__init__.py` 做跨层便利导出，导致包名与真实职责不一致。
- 文件名叫 `deps`，内容却只是 import / re-export 一堆单例对象。
- 文件名叫 `container`，内容却不是组合根。

### 对 `deps.py` 的特别说明

`deps.py` 不是“随便放依赖对象的地方”。

只有在以下情况下才允许使用 `deps.py`：

- 它明确服务于框架依赖注入
- 它导出的是 provider 函数
- controller 通过 `Depends(...)` 使用它

如果一个 `deps.py` 只是：

- 从别处 import service
- 再转发给 controller
- 没有 provider 函数
- 没有 `Depends(...)`

那么这个文件原则上应该删除，或者改名为更准确的名称。

### 对 `container.py` 的特别说明

`container.py` 的意义是组合根，是“组装依赖”的地方。

它存在的前提是：

- 只负责把 repository 组装成 service
- 只负责把 parser / enrichment / service 组装成 use case facade
- 不承担业务逻辑
- 不承担 HTTP 逻辑

如果 `container.py` 只是变成一个新的“万能中转站”，或者把不相关领域强行塞在一起，就应该拆分。

例如：

- `app/container.py` 可以作为通用装配根
- `app/llm_container.py` 可以作为 LLM 专用装配根

但前提仍然是：文件名和职责必须一一对应。

### 最终判定标准

如果某个文件需要靠注释解释“虽然它叫这个名字，但其实它做的是另一件事”，那它的命名大概率已经错了。

---

## 一、目录职责

### `app/main.py`

应用入口与装配根。

只负责：

- 创建 `FastAPI` 应用
- 注册中间件
- 挂载路由
- 组装依赖
- 启动应用

禁止：

- 编写业务逻辑
- 直接操作 Lark/Bitable
- 编写解析逻辑
- 编写缓存匹配逻辑

### `app/config/`

配置层。

只负责：

- 环境变量
- 配置对象
- 配置常量

禁止：

- 业务判断
- 网络请求
- 数据访问

### `app/core/`

基础设施抽象与跨模块公共能力。

只负责：

- LLM/Lark client 获取
- 通用 parser 基类
- 通用 service/repository 基类
- middleware
- 与具体业务无关的基础能力

禁止：

- 放具体业务规则
- 放具体表的仓储实现
- 放某个模块专用的业务流程

### `app/common/`

公共通用组件。

只负责：

- 通用响应结构
- 通用异常
- 通用表定义映射
- 通用 repository 抽象或公共工具

禁止：

- 业务编排
- 路由定义
- 模块专属规则

### `app/entity/`

领域对象与纯业务模型。

只负责：

- 领域实体
- 值对象
- 纯函数规则
- 不依赖 I/O 的业务计算

禁止：

- HTTP
- Repository
- Cache
- 外部 SDK 调用

### `app/controller/`

接口层。

只负责：

- 定义 HTTP 路由
- 接收请求参数
- 调用 service
- 返回统一响应
- 做最薄的一层输入校验

禁止：

- 直接 new `Repository`
- 直接访问 `Cache`
- 直接调用 Lark SDK / LLM SDK
- 编写业务匹配逻辑
- 编写解析后富化逻辑
- 在 controller 中拼装完整业务流程

### `app/service/`

服务层。

这是业务规则与用例编排层，必须进一步区分两类职责。

#### `app/service/*.py`

领域服务。

只负责：

- 单一业务域能力
- 组合一个或多个 repository
- 必要时使用 cache
- 执行业务规则

禁止：

- 处理 HTTP 细节
- 返回 `ApiResponse`
- 依赖 `fastapi`

#### `app/service/llm_service/`

应用服务 / 用例编排层。

只负责：

- 组织 LLM 解析流程
- 连接 parser、enrichment、domain service
- 暴露清晰的 use case 入口

禁止：

- 直接定义 HTTP 路由
- 直接放底层 SDK client 初始化
- 与 `controller` 双向耦合

说明：

- 如果确实需要“service 调 service”，只能发生在“应用服务 -> 领域服务”这个固定方向。
- 普通同级 service 不允许互相调用。
- 不能出现 `AService -> BService -> CService` 的横向串联。
- 需要编排时，必须抽成明确的 facade / application service。

### `app/repository/`

数据访问层。

只负责：

- 封装 Lark Bitable 数据读写
- 表级 CRUD
- 查询转换

禁止：

- 业务规则
- HTTP
- 响应格式
- 反向调用 service
- 直接依赖 controller

### `app/cache/`

缓存层。

只负责：

- 缓存 key 定义
- 缓存工厂
- 缓存读写与失效

禁止：

- 业务编排
- 直接暴露给 controller
- 直接依赖 HTTP 上下文

缓存只能被 service 使用，不能被 controller 或 repository 直接拿来做业务决策入口。

---

## 一.五、公共工具使用规范

### `app/common/` 下的工具必须优先使用，禁止在业务代码中重复实现。

### Repository 层 — `BaseRepository` + `QueryWrapper` + `UpdateWrapper`

所有 Bitable 数据访问必须通过 `BaseRepository` 子类，使用链式构建器：

```python
# 查询 — QueryWrapper
records = await repo.list(QueryWrapper().not_empty("Terminal").order_by("ETA"))
record = await repo.findOne(QueryWrapper().eq("Container Number", "ABCD1234567"))

# 更新 — UpdateWrapper
await repo.updateOne(
    UpdateWrapper().eq("record_id", rid).set("Status", "Done").set("Tag", "OK")
)

# 批量更新
await repo.batch_update([
    UpdateWrapper().eq("record_id", r.record_id).set_all(fields).with_label(r.cn)
    for r in data_list
])

# 按 record_id 查 — 走直连 API，不走 search
record = await repo.findOne(QueryWrapper().eq("record_id", rid))
records = await repo.list(QueryWrapper().in_list("record_id", ids))
```

**禁止**：
- 直接传 record_id 字符串给查询/删除方法（必须用 `QueryWrapper.eq("record_id", ...)`)
- 手动拼 filter dict（必须用 `QueryWrapper` 链式方法）
- 在 service 中直接构造 `AppTableRecord`（由 `BaseRepository` 内部转换）

### 集合操作 — `collection_utils`

```python
from app.common.collection_utils import pluck, to_map, filter_by, group_by, partition

cns = pluck(records, "Container Number")           # 提取非空字段值列表
cn_to_rid = to_map(records, "Container Number")    # 字段 → record_id 映射
records = filter_by(all_records, "CN", cn_set)      # 按字段值集合过滤
grouped = group_by(records, lambda r: r.get("Terminal"))  # 按函数分组
yes, no = partition(records, lambda r: ...)          # 按谓词分两组
```

**禁止**：在业务代码中重复写 `[v for r in records if (v := r.get(field))]` 等模式。

### 断言 — `assert_utils`

```python
from app.common.assert_utils import assert_in, assert_not_blank, assert_not_none

query = assert_in(condition, _CONDITIONS, f"未知条件 '{condition}'")
assert_not_blank(vessel_name, f"记录 {rid} 缺少 Vessel Name")
assert_not_none(value, "参数不能为空")
```

**禁止**：在业务代码中重复写 `if x is None: raise ValueError(...)` 三行断言模式。

### 时间戳转换 — `safe_ts`

```python
from app.service.sync.utils.datetime_parser import safe_ts

eta = safe_ts(raw, "ETA")  # 从 dict 取值并转毫秒时间戳，空值返回 None
```

**禁止**：在各模块中重复定义 `_ts()` 辅助函数。

---

## 二、标准分层调用方向

唯一允许的主链路如下：

`main` -> `controller` -> `service` -> `repository/cache`

基础能力可被下游各层使用：

- `config`
- `core`
- `common`
- `entity`

但它们只能提供“公共能力”，不能反向接管业务流程。

### 允许依赖

- `controller` -> `service`
- `service` -> `repository`
- `service` -> `cache`
- `service` -> `entity`
- `repository` -> `common` / `core` / `config`
- `cache` -> `config` / `common`
- `llm_service` -> parser / enrichment / domain service

### 明确禁止

- `controller` -> `repository`
- `controller` -> `cache`
- `controller` -> `entity` 后自行完成业务编排
- `repository` -> `service`
- `repository` -> `controller`
- `cache` -> `service`
- 同级 `controller` 相互调用
- 同级普通 `service` 相互调用
- 同级 `repository` 相互调用

---

## 三、同级禁止互调规则

同一层的模块必须各自负责自己的边界，不允许横向穿透。

### Controller 层

禁止：

- `cartage controller` 调 `edo controller`
- `master data controller` 调 `llm controller`

如果需要复用逻辑，抽到 `service` 或 `core/common`。

### Service 层

禁止：

- `driver service` 直接调用 `vehicle service`
- `warehouse service` 直接调用 `terminal service`
- `cartage service` 直接调用 `edo service`

如果一个用例需要协调多个能力，创建一个明确的 application service / facade 来编排。

### Repository 层

禁止：

- `ARepository` 调 `BRepository`

跨表协作由 service 负责，repository 只关注自己的表与数据访问。

---

## 四、链路设计原则

### 1. Controller 必须保持薄

controller 只保留：

- 参数接收
- 参数基础校验
- 文件接收
- 调 service
- 返回 response

不允许在 controller 中出现：

- 复杂条件分支
- 多阶段业务流程
- 匹配算法
- 仓储实例化
- 缓存清理策略

### 2. Service 必须承担业务语义

service 是唯一可以定义“做什么”的地方。

例如：

- “解析 cartage 文档”
- “解析后做地址富化”
- “查询匹配所需主数据并缓存”

这些都应属于 service，而不是 controller 或 repository。

### 3. Repository 只回答“怎么取数据”

repository 不回答：

- 为什么取
- 取完怎么拼业务结果
- 失败后怎么回 HTTP

repository 只回答：

- 去哪张表
- 用什么字段
- 返回什么原始记录

### 4. Cache 只做性能优化，不做业务入口

cache 不能变成新的业务层。

不允许：

- 在 controller 直接读 cache 决定返回内容
- 在 repository 中混入 cache 命中逻辑
- 用 cache 替代 service 的业务判断

---

## 五、LLM 场景专用规则

`EDO`、`CARTAGE` 一类链路必须统一为：

`controller` -> `LLM application service` -> `parser / enrichment / domain service` -> `repository/cache`

### Controller 负责

- 接收文件或文本
- 调用一个清晰的 service 入口
- 返回结构化响应

### LLM application service 负责

- 决定当前 use case 是 `parse` 还是 `process`
- 组织 parser
- 在需要时调用 enrichment
- 在需要时调用 domain service

### Parser 负责

- prompt
- 模型调用
- 原始响应转结构化结果

### Enrichment 负责

- 基于 parse result 做业务补全与匹配

### Domain service 负责

- 查询主数据
- 使用 cache
- 组合 repository

### 禁止的错误链路

- `controller` -> `parser`
- `controller` -> `repository`
- `controller` -> `cache`
- `parser` -> `repository`
- `parser` -> `cache`
- `repository` -> `parser`

---

## 六、依赖装配规则

依赖装配只能出现在以下位置之一：

- `app/main.py`
- 专门的 container / providers 模块
- 明确标注为 composition root 的依赖注入文件

禁止在以下位置做依赖装配：

- `controller` 业务路由文件
- `repository`
- `entity`

特别强调：

- `controller` 不允许 `Repository()` 后再传给 `Service(...)`
- `controller` 不允许同时知道 service 和 repository 的构造细节
- 装配文件必须用能体现职责的名字，例如 `container.py`、`llm_container.py`、`providers.py`
- 如果文件名是 `deps.py`，那它必须真的是依赖提供器，而不是 service 注册表

---

## 七、命名与目录组织约束

### Controller

- 一个 controller 文件只负责一个明确入口域
- 不在 `controller/__init__.py` 中 re-export service、parser、repository
- controller 文件名必须体现入口职责，不能用模糊名字隐藏业务编排

### Service

- `service/*.py` 放领域服务
- `service/llm_service/` 放应用服务与 LLM 用例编排
- 不把 parser 伪装成 service
- 文件名是 `service` 就只能承担 service 语义，不能混入 router / repository / parser 职责

### Repository

- 一个 repository 对应一个表或一个明确的数据来源
- 不在 repository 中做“跨表业务拼装”
- 文件名是 `repository` 就只能负责数据访问

### Cache

- cache key、factory、adapter 分文件管理
- cache 名称必须表达业务用途，不表达控制层动作
- 文件名必须体现缓存职责，不能把缓存和业务编排混放在同一文件

---

## 八、代码评审判定标准

出现以下任意情况，视为架构违规：

- controller 直接 import repository
- controller 直接 import cache
- controller 内实例化 repository
- service 使用 `fastapi` 类型或返回 HTTP response
- repository 内出现业务流程判断
- 同级 service 互相调用
- 同级 repository 互相调用
- parser 直接查主数据
- 为了少写一个 service 而让 controller 直接串多个下层对象

---

## 九、决策原则

当你不确定代码应该放哪里时，按下面顺序判断：

1. 这是 HTTP 入口问题吗？
   是：放 `controller`
2. 这是业务语义或用例编排吗？
   是：放 `service`
3. 这是数据访问吗？
   是：放 `repository`
4. 这是性能缓存吗？
   是：放 `cache`
5. 这是纯规则、纯对象、纯计算吗？
   是：放 `entity`
6. 这是跨模块通用基础能力吗？
   是：放 `core` 或 `common`

如果一个实现同时满足多个答案，说明职责已经混淆，必须继续拆分。

---

## 十、最终原则

宁可多一层清晰的 service，也不要少一层边界。

宁可显式编排，也不要隐式绕行。

宁可拆小职责，也不要把 controller、service、repository、cache 混成一个“能跑就行”的链路。
