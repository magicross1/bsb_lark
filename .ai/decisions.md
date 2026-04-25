# Decisions Log

> 每个重要决策都记录在这里。AI 不会重复问你"为什么不用 X"。

## Format

每条决策按以下格式记录：

```
### [YYYY-MM-DD] 决策标题
**背景**: 为什么需要做这个决定
**决定**: 最终选了什么
**备选方案**: 考虑过但没选的方案
**原因**: 为什么选这个
```

---

## Decisions

### [2026-04-10] 使用 Python + FastAPI 而非 TypeScript
**背景**: 需要选择后端技术栈来操作 Lark API
**决定**: Python 3.12 + FastAPI
**备选方案**: TypeScript + Fastify, Python + Quart
**原因**: 团队已熟悉 Python，现有爬虫代码可直接复用，FastAPI 比 Quart 更现代

### [2026-04-10] Bitable 为主数据源，暂不加 Redis
**背景**: 是否需要缓存层
**决定**: 纯 Bitable，暂不加 Redis
**备选方案**: Bitable + Redis 缓存, Bitable + PostgreSQL
**原因**: Bitable 读 API 50次/秒够用，加 Redis 增加复杂度和运维成本，YAGNI

### [2026-04-10] 模块化分层架构，自动注册
**背景**: 项目组织方式
**决定**: 按业务域分模块（master_data/pricing/operations/email/sync），每个模块 router/service/repository/schemas 四件套，框架自动扫描注册
**备选方案**: 按技术层分目录（controllers/services/repositories）
**原因**: 业务内聚，新增模块只需加目录+router.py，零改动框架层

### [2026-04-10] 使用 larksuiteoapi Python SDK
**背景**: 需要与 Lark Open API 交互
**决定**: 使用官方 Python SDK
**备选方案**: 直接 HTTP 请求、lark-cli 封装
**原因**: 官方维护、Token 自动管理、类型提示

### [2026-04-12] BaseParser 基类统一 AI 解析逻辑
**背景**: EDO 和 Cartage parser 有大量重复代码（AI 调用、JSON 提取、PDF 转图片），且只支持 PDF 输入
**决定**: 抽取 BaseParser 基类，子类只需提供 system_prompt + user_hint + build_result()
**备选方案**: 继续各自独立实现、用 Mixin 拆分
**原因**: 消除重复代码，统一支持多格式输入（PDF/图片/TXT/字符串），新增文档类型只需写 schemas + prompt

### [2026-04-12] 使用智谱 AI (ZhipuAI) 多模态模型
**背景**: 需要从物流 PDF 中提取结构化数据
**决定**: 使用智谱 glm-5v-turbo 多模态模型，PDF→PNG→base64→多模态 API→JSON
**备选方案**: OCR (Tesseract/PaddleOCR) + 规则提取、OpenAI GPT-4o
**原因**: 多模态模型直接理解版面布局和上下文，比 OCR+规则更灵活；智谱国内访问快、价格低；thinking 模式提高准确率

### [2026-04-12] Cartage Import/Export 分离 + CartageDictValues 注入
**背景**: Cartage 解析需要区分进口柜和出口柜，字段完全不同；字典值（Base Node/Container Type/Commodity/Shipping Line）不应硬编码
**决定**: ImportContainerEntry 和 ExportBookingEntry 分开；CartageDictValues 作为可注入参数，默认值硬编码，service 层从 Bitable 拉取覆盖
**备选方案**: 统一 ContainerEntry 用 Optional 字段、字典值全硬编码
**原因**: Import/Export 字段集本质不同（出口无 container_number 有 release_qty/shipping_line），强类型更安全；字典值注入解耦了 parser 和 Bitable

### [2026-04-15] EDO 匹配三层策略 (精确→别名→模糊)
**背景**: EDO 解析出 Shipping Line 和 Empty Park 名称后需要匹配到 Bitable 主数据，但名称可能有变体（缩写、别名、地址差异）
**决定**: 三层递进匹配：精确名→别名→模糊名+地址；Shipping Line 额外支持 Short Name fallback；Empty Park Alias 字段（分号分隔）支持多别名
**备选方案**: 纯模糊匹配、只用 AI 输出名直接搜索、让 AI 输出 record_id
**原因**: 精确匹配最可靠优先使用；别名覆盖常见变体（如 "PATRICK" vs "PAT"）；模糊兜底处理拼写差异；AI 不可能知道 record_id 所以不选该方案

### [2026-04-15] EDO 写回用 UPDATE 而非 CREATE
**背景**: EDO 数据需要写入已有的 Op-Import 记录（按 Container Number 关联）
**决定**: 按 Container Number 查找 Op-Import → UPDATE 写入 EDO PIN / Shipping Line(link) / Empty Park(link) / Record Status / Source EDO
**备选方案**: 创建新记录、在 Op-Cartage 上写 EDO 字段
**原因**: EDO 是进口柜的补充信息，Op-Import 已由 Cartage 流程创建；UPDATE 比 CREATE 避免数据分裂；Record Status 防止重复处理

### [2026-04-21] VBS Patrick VIC 用多候选 regex 而非 operation 分支
**背景**: Patrick VIC 的 VBS HTML 使用不同的 form 前缀 (`MovementDetailsForm` vs `ContainerVesselDetailsForm`) 和不同字段名 (`ContainerAvailability` vs `ImportAvailability`, `ContainerStorageStart` vs `ImportStorageDate`)
**决定**: `_CTNS_REGEX_PATTERNS` 每个字段配多个候选 pattern，按顺序尝试取第一个匹配
**备选方案**: 按 operation 传参到 `_parse_ctn_info` 用不同 pattern 集；解析前检测 HTML 前缀
**原因**: 多候选 pattern 零分支、零传参，新增码头只需追加 pattern 到列表末尾；`_extract_by_regex` 天然支持 fallback

### [2026-04-22] Repository 层 MyBatis-Plus 风格重构 — QueryWrapper + UpdateWrapper
**背景**: 旧 `BitableQuery` 只支持构建服务端 filter，查询和更新操作缺乏统一的链式构建器；Repository 方法签名不一致（有的传 record_id 字符串，有的传 dict）
**决定**: 引入 `QueryWrapper` + `UpdateWrapper` 链式构建器（MyBatis-Plus 风格），统一 Repository 接口
**备选方案**: 继续用 BitableQuery + 手动拼 fields dict
**原因**: 链式 API 更符合 Python 习惯；QueryWrapper 同时存储 condition_node + predicate 消除双轨制；UpdateWrapper 封装条件+赋值消除手动字段构建；统一方法签名（findOne/updateOne/deleteOne 都接收 Wrapper）

### [2026-04-22] Sync 模板模式重构 — SyncTemplate + SyncData 替代 base.py 共享逻辑
**背景**: 旧 `service/sync/base.py` 将 FieldMapping/BatchCondition/OverwritePolicy/LinkResolver + build_update_fields/batch_write_back 全部放在一个文件，职责不清晰；FieldMapping 需要手动声明 field_type + overwrite policy
**决定**: 引入 `SyncTemplate` 模板方法 + `SyncData` Pydantic 自动映射，按职责分层
**备选方案**: 继续用 base.py 共享函数 + FieldMapping 声明式配置
**原因**: SyncData 用 Pydantic alias 自动实现字段映射，不需要 FieldMapping；SyncTemplate 模板方法强制三步流程一致性；按职责分目录（workflow/scene/constants/utils/request/factory）比单文件更清晰；SyncData.to_update_wrapper() 自动 exclude_none + exclude metadata + by_alias，消除手动 build_update_fields

### [2026-04-22] 集合操作 + 断言工具提取到 common/
**背景**: sync 模块中大量重复的集合操作（pluck/to_map/filter_by）和断言模式（if x is None: raise ValueError），分散在各 service 文件
**决定**: 提取到 `app/common/collection_utils.py` 和 `app/common/assert_utils.py`
**备选方案**: 继续在各模块内联实现
**原因**: 消除重复代码；统一的工具函数有统一的命名和行为；CLAUDE.md 已写入使用规范

### [2026-04-23] Sync 模块禁止内联创建 Repository
**背景**: `_resolve_base_node` 在方法内动态创建 `_BaseNodeRepo(BaseRepository)` 内联类 + 用 `RelationLoader` 手动 pop/覆盖字段，模式复杂且违反"一表一文件"约定
**决定**: Repository 必须是独立文件（`repository/base_node.py`），通过构造函数注入到 Service。link 字段反查用已有工具：`extract_link_record_ids`(提取 record_id) + `BaseRepository.list(in_list("record_id", ids))`(批量查) + `to_map`(构建映射)
**备选方案**: 继续用 RelationLoader + 内联 Repo；在 _record_to_dict 层统一处理 link 字段
**原因**: 一表一文件是项目铁律；内联类绕过了正常的依赖管理；已有的 `extract_link_record_ids` + `to_map` 组合更简洁直接

### [2026-04-23] Sync constants 暂用纯 client_filter，记为技术债
**背景**: Bitable search API 的 OR+嵌套AND filter 语法不稳定，`not_in_or_empty` 生成的嵌套 filter 被 400 拒绝
**决定**: 4 个 constants 文件（vessel/container/clear/vbs）全部只用 `client_filter`，每次全量拉取后客户端筛
**备选方案**: 继续调试 Bitable filter 语法；混合使用服务端 filter + client_filter
**原因**: 数据量小（<20条）时全拉可接受；纯 client_filter 语法简单可靠；等数据量增长后应逐步把条件推回服务端 filter，减少 API 拉取量

### [2026-04-23] Sync 模块"不发明方法"原则
**背景**: 多次修 bug 时在 sync 场景内发明了新方法/新类（如内联 Repo、手动 pop 逻辑），偏离已有工具链
**决定**: Sync 模块修改必须遵循以下规则：
1. **Repository 必须是独立文件** — 禁止方法内 `class _XxxRepo(BaseRepository)`
2. **用已有工具** — `extract_link_record_ids`/`to_map`/`pluck`/`safe_ts`/`LinkResolver`/`LinkConfig` 已覆盖 90% 场景，优先用它们
3. **不造新轮子** — link 字段反查用 `repo.list(in_list("record_id", ids))` + `to_map`，不用 `RelationLoader` 手动注入再 pop
4. **datetime 字段用 `int`** — SyncData 中 datetime 字段一律 `int | None`（毫秒时间戳），用 `safe_ts()` 转换
5. **constants 中 client_filter 处理已有数据时兼顾 int/str** — Bitable 读回 datetime 为 int 毫秒时间戳，`_to_datetime()` 必须处理两种格式

---
*最后更新: 2026-04-23*
