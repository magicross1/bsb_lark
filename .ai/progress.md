# Progress

> 项目开发进度日志。AI 从这里知道"做到哪了"。

## Current Sprint / Phase
远程仓库重构同步 + 4 个 Sync 模块 E2E 测试全部通过

## Changelog

### [2026-04-10] Project Initialization
**做了什么**:
- 创建项目基础结构 (AGENTS.md, opencode.json, .ai/)
- 确定技术栈: Python 3.12 + FastAPI + larksuiteoapi
- 安装 Lark CLI v1.0.7, 配置 auth login (user identity)
- 完整探索 BSB Bitable: 37 个表，涵盖物流/仓储管理
- 分析现有 Python 项目 (Desktop/BSB)，理解完整业务流程
- 搭建项目骨架: core 层 (base_repository/service/response/exceptions/middleware/registry)
- 搭建 shared 层: lark_tables.py (37表完整映射), enums.py, utils.py
- 搭建 master_data 示例模块 (router/service/repository/schemas)
- 实现模块自动注册机制 (registry.py)
- 创建 Dockerfile + docker-compose.yml

**遇到的问题**:
- lark-cli raw API 在 jp 区域 404，需使用 shortcut 命令 (+base-get 等)

**下一步**:
- 填入 .env 配置后验证项目可启动
- 实现 pricing 模块 (费用计算器)
- 实现 operations 模块 (集装箱状态追踪 + 爬虫策略迁移)
- 实现 email 模块 (邮件自动化)

### [2026-04-10] EDO AI 解析模块完成
**做了什么**:
- 新增 `app/config/ai.py` — 智谱 AI 客户端单例 (ZhipuAI SDK)
- Settings 新增 `ZHIPUAI_API_KEY` 和 `AI_MODEL` (默认 glm-5v-turbo)
- 新增 `app/modules/operations/edo/` 模块:
  - `schemas.py` — `EdoEntry`(container_number, edo_pin, shipping_line, empty_park) + `EdoParseResult`
  - `parser.py` — `EdoParser` 类，PDF→图片(base64)→智谱多模态 API→JSON 解析
    - 支持 PDF 多页、单 EDO 多箱、多 EDO 合并等场景
    - 支持 thinking 模型 (glm-5v-turbo 带 budget_tokens=8192)
    - PyMuPDF (fitz) 做 PDF→PNG 200dpi 转换
- 新增 `scripts/test_edo_parse.py` — 本地测试脚本，支持单文件/目录批量、模型切换
- 新增 `tests/edo_samples/TIIU5348694.PDF` — 测试样本
- pyproject.toml 新增依赖: `zhipuai>=2.0.0`, `pymupdf>=1.25.0`

**测试结果**:
- EDO PDF 解析成功，能正确提取 container_number / edo_pin / shipping_line / empty_park

**下一步**:
- 为 EDO 解析创建 FastAPI 端点 (router.py)
- 支持更多文档类型 (Import Delivery Order, Booking Confirmation 等)
- 对接 Bitable Op-Import 表写入解析结果
- 实现 pricing 模块 (费用计算器)

### [2026-04-12] Cartage AI 解析 + BaseParser 重构
**做了什么**:
- 新增 `app/modules/operations/cartage/` 模块:
  - `schemas.py` — `CartageContainerEntry`(container_number, container_type, container_weight, commodity) + `CartageParseResult`(booking_reference, direction, consingee_name, deliver_address, deliver_type_raw, vessel_name, voyage, port_of_discharge, containers)
  - `parser.py` — `CartageParser` (inherits BaseParser)，解析 Cartage/Time Slot Request PDF
- 新增 `app/core/base_parser.py` — AI 解析基类:
  - 统一入口 `parse()` 自动路由: PDF → `parse_pdf()`, 图片 → `parse_image()`, TXT → `parse_text_file()`, 字符串 → `parse_text()`
  - 公共逻辑: `_create_completion()` (AI 调用), `_build_image_messages()`, `_build_text_messages()`, `extract_json_from_response()`
  - 子类只需设置 `system_prompt` + `user_hint` + 实现 `build_result()`
- 重构 `EdoParser` 和 `CartageParser` 均继承 `BaseParser`，消除重复代码
- 新增 `scripts/test_cartage_parse.py` — Cartage 本地测试脚本
- 新增 `tests/cartage_samples/S35088 Time Slot Request.pdf` — 测试样本
- AGENTS.md 新增 Documentation Sync Rule

**测试结果**:
- Cartage PDF 解析成功: booking_reference=S00035088, direction=Import, 3个集装箱全部正确提取
- container_number / container_type / container_weight / vessel / voyage 全部与答案一致

### [2026-04-12] Cartage 解析重构 - Import/Export 分离 + 字典值注入
**做了什么**:
- 重构 `schemas.py`:
  - `ImportContainerEntry` — 进口柜字段 (container_number, vessel_name, voyage, base_node, container_type, commodity, container_weight)
  - `ExportBookingEntry` — 出口柜字段 (booking_reference, release_qty, vessel_name, voyage, base_node, container_type, commodity, shipping_line)
  - `CartageDictValues` — 可注入的字典值 (base_nodes, container_types, commodities, shipping_lines, deliver_types)，默认值来自 Bitable 实际数据，后续由 service 从 Bitable 拉取传入
  - `CartageParseResult` — import_containers + export_bookings 分离
- 重构 `parser.py`:
  - `system_prompt` 改为 property，动态注入 `CartageDictValues` 到 prompt
  - AI 自动将 AUSYD→PORT OF SYDNEY 映射，将货物描述→Commodity 代码映射
  - `_build_cartage_prompt()` 独立函数，接收 dict_values 生成 prompt
- 更新测试脚本支持 PDF/PNG/JPG/TXT + --text 直接字符串

**测试结果**:
- S35088 Time Slot Request.pdf: 全部字段与答案一致
- base_node=PORT OF SYDNEY, container_type=20GP, commodity=GEN (从 TEMPERED GLASS 推断)

### [2026-04-12] CartageService + API 端点 + 地址匹配
**做了什么**:
- 新增 `app/modules/operations/cartage/service.py` — CartageService 编排层:
  - `parse_document()` / `parse_text()` — 解析文档
  - `process_document()` / `process_text()` — 完整流程: 解析 → 地址匹配 → deliver_config 匹配 → consingee 匹配
  - `_match_deliver_address()` — normalize → 粗筛 (postcode/street) → `address_match_score()` 评分 → 最佳匹配
  - `_find_deliver_configs()` — 按匹配到的 address + deliver_type 查 MD-Warehouse Deliver Config
  - `_find_consingee_by_address()` — 按匹配到的 address 查 MD-Consingee
  - `expand_export_bookings()` — 出口柜 release_qty > 1 时展开为 N 条记录
  - 三级缓存: addresses / deliver_configs / consingees，避免重复 Bitable API 调用
- 新增 `app/modules/operations/cartage/router.py` — FastAPI 端点:
  - `POST /cartage/parse` — 上传文件解析 (PDF/image/TXT)
  - `POST /cartage/parse-text` — 文本解析
  - `POST /cartage/process` — 完整流程 (解析+匹配)
  - `POST /cartage/process-text` — 文本完整流程
  - `POST /cartage/clear-cache` — 清除缓存
- 新增 `app/modules/operations/edo/router.py` — EDO 解析端点:
  - `POST /edo/parse` — 上传 EDO 文件解析
- 新增 schemas: `AddressMatch`, `CartageProcessResult`, `ImportContainerMatch`, `ExportBookingMatch`
- 新增 `WarehouseDeliverConfigRepository` 到 master_data
- master_data service 新增 deliver_config 相关方法
- pyproject.toml 新增 ruff per-file-ignores (parser E501, router B008) + flake8-bugbear extend-immutable-calls

**地址匹配策略**:
- MATCH_THRESHOLD=0.6 (低于此分数视为无匹配，标记 needs_review)
- REVIEW_THRESHOLD=0.8 (0.6~0.8 之间标记 needs_review=True)
- 粗筛: postcode → street_name → 限制候选集大小
- 评分: postcode(30) + street_name(25) + street_number(20) + street_type(10) + unit(10) + suburb(5)

**下一步**:
- 放入更多 Cartage PDF 测试不同格式 (Export、不同货代模板)
- 实现 service 层: 从 Bitable 拉字典值 → 传给 parser → 验证 → 写回 Bitable
- 出口柜 release_qty > 1 时的记录展开逻辑
- 为 EDO 和 Cartage 创建 FastAPI 端点
- 解析结果与 Bitable 数据库匹配 (consingee → MD-Consingee, deliver_address → MD-Warehouse Address)

**下一步**:
- 放入更多 Cartage PDF 测试不同格式 (Export、不同货代模板)
- 集成测试: 完整 process 流程 (上传 PDF → 解析 → 地址匹配 → 返回)
- Bitable 写回: 解析结果写入 Op-Cartage / Op-Import / Op-Export
- Lark webhook 事件监听: Cartage Advise 附件上传自动触发解析

### [2026-04-13] Code Review 修复 (Round 2 — 剩余 HIGH + MEDIUM + LOW)
**做了什么**:
- **#4 HIGH** — `_number_ranges_overlap` 用 `range(start, end+1, step=2)` 只生成奇/偶数，导致 "10-18" vs "15-21" 判为不重叠。改为 `range(start, end+1)` + 区间交集判断 (`latest_start < earliest_end`)
- **#5 MEDIUM** — `_get_address_candidates` 中 `parsed.postcode in address_str` 是子串匹配，"2164" 会匹配 "12164 Something St"。改为 `re.compile(rf"\b{postcode}\b")` 词边界匹配
- **#7 MEDIUM** — Cartage 和 EDO router 中 `copyfileobj` 抛异常时 tmp_path 未赋值，temp file 泄漏。改为 `tmp_path = None` + `try/finally` 包裹整个文件操作，`if tmp_path` 才删
- **#8 MEDIUM** — `_load_addresses` 拉了 `Location` 和 `Detail` 字段但从未使用。精简为只拉 `["Address"]`
- **#10 MEDIUM** — EDO router 只允许 PDF/image，不支持 .txt/.text。`allowed` 集合新增 `.txt`/`.text`
- **#12 MEDIUM** — `normalize_address` 中删除 state/postcode 后可能残留双空格，导致无逗号地址的 suburb 检测失败。删除后增加 `re.sub(r"\s{2,}", " ", s)` 合并多余空格
- **#16 LOW** — `_validate_choice` 返回 None 时静默丢数据，加 `logger.warning()` 记录未匹配值

### [2026-04-13] Consingee 名字匹配 + Prompt 拆分
**做了什么**:
- **Consingee 名字相似度匹配** — 同一地址多个 consingee 时，用 AI 解析出的 `consingee_name` 做名字相似度选择最佳匹配，而非返回第一个
  - 新增 `_normalize_name()` — 去噪声词 (CO/PTY/LTD/INTERNATIONAL/TRADING 等) → 大写 → 分词
  - 新增 `_name_similarity()` — token 集合重叠率 (Jaccard-like)
  - `_find_consingee_by_address()` 新增 `consingee_name_hint` 参数，多候选时按名字相似度排序
  - `_match_deliver_address()` 透传 `consingee_name_hint`
- **Prompt 拆分到 prompts.py** — EDO 和 Cartage 的 system_prompt / user_hint 从 parser.py 拆到独立 prompts.py，方便阅读和修改
  - `app/modules/operations/edo/prompts.py` — `EDO_SYSTEM_PROMPT`, `EDO_USER_HINT`
  - `app/modules/operations/cartage/prompts.py` — `CARTAGE_USER_HINT`, `build_cartage_system_prompt()`
  - `parser.py` 改为 `from .prompts import ...`
  - pyproject.toml 新增 `**/prompts.py` E501 忽略

### [2026-04-13] 架构审计 + 适配新目录结构 + 铁律融入
**做了什么**:
- 适配同事架构重构: modules/ → controller/ + service/ + repository/ + entity/ + cache/ + common/
- 重应用所有 bug 修复到新目录结构:
  - #4 HIGH `_number_ranges_overlap` 区间交集修复 → `entity/address.py`
  - #5 MEDIUM postcode 词边界匹配 → `service/llm_service/cartage/enrichment.py`
  - #12 MEDIUM 双空格合并 → `entity/address.py`
  - Consingee 名字相似度匹配 → `service/llm_service/cartage/enrichment.py`
  - #8 精简字段 → `service/cartage.py`
- 修复 `field_names` 参数格式: `str()` → `json.dumps()` in `common/lark_repository.py`
- EDO prompt 拆分到 `service/llm_service/edo/prompts.py`
- 删除死代码 `app/modules/` 目录
- 修复 `core/midlleware/__init__.py` 遮蔽 `registry.py` 真实函数
- 清理 `repository/__init__.py` 和 `cache/__init__.py` 跨层便利导出
- Controller tmp_path 安全模式 (`tmp_path = None` + `try/finally` + `if tmp_path`)
- EDO 端点支持 .txt/.text
- 更新测试脚本 `scripts/test_cartage_service.py` 适配新导入路径
- 铁律 (CLAUDE.md) 融入 AGENTS.md

**审计发现的待讨论问题**:
- `llm_service = LLMService()` 模块级单例 vs 依赖注入 — 目前可用但不够干净
- Cartage prompt 目前是简化版（无 Import/Export 分离、无字典值注入）— 需讨论是否升级

### [2026-04-14] Bitable Writeback — Cartage 解析结果写回
**做了什么**:
- 新增 `app/repository/import_.py` — ImportRepository (Op-Import 表)
- 新增 `app/repository/export_.py` — ExportRepository (Op-Export 表)
- 新增 `app/service/llm_service/cartage/writeback_schemas.py` — CartageWritebackResult, WritebackRecordRef
- 新增 `app/service/llm_service/cartage/writeback.py` — CartageWritebackService:
  - `_write_cartage()` — 创建 Op-Cartage 记录 (Booking Reference, Consingnee Name, Deliver Config link)
  - `_write_imports()` — 批量创建 Op-Import 记录 (Container Number, Type, Weight, Commodity, Vessel, Voyage, Op-Cartage link)
  - `_write_exports()` — 批量创建 Op-Export 记录 (Booking Reference, Release Qty, Container Type, Commodity, Shipping Line, Op-Cartage link)，自动 expand_export_bookings
  - `_link()` 辅助函数 — 生成 Bitable link field 格式 `[{"record_ids": ["recXXX"]}]`
- LLMService 新增 `process_and_writeback_cartage_document/text` 方法
- Controller 新增 `POST /cartage/writeback` 和 `POST /cartage/writeback-text` 端点

**下一步**:
- 集成测试: 完整 writeback 流程验证
- Lark webhook 事件监听: Cartage Advise 附件上传自动触发解析+写回
- Refactor enrichment.py 使用 RelationResolver

### [2026-04-14] Vessel Schedule 复合查询 + Container Type 写回修复
**做了什么**:
- **LinkFieldResolver 支持 filter_expr** — `LinkLookup.filter_expr` 之前声明但未使用，现已实现模板渲染 + AND 组合过滤
  - `resolve()` 新增 `_find_existing()` 方法：当 `filter_expr` 存在时，构建 `AND(主搜索条件, 渲染后的filter_expr)` 复合过滤
  - 上下文变量通过 `format_map()` 注入到 filter_expr 模板
- **Vessel Schedule 查询升级为 Vessel Name + Voyage** — writeback_config.py 新增 `filter_expr='CurrentValue.[Voyage]="{voyage}"'`
  - 同一船名不同航次不再误匹配
  - 创建新 Vessel Schedule 记录时正确填充 Voyage + Base Node
- **修复 container_type 未写入** — writeback.py 的 source dict 缺少 `container_type` 键，导致 Container Type 字段始终为空
- **验证 Commodity/Container Type 字段类型** — Bitable 确认 Container Type (type=3) 和 Commodity (type=3) 均为 select 字段，可正常写入。已验证 Commodity="GEN" 成功持久化
- 清理 writeback.py 和 writeback_config.py 中未使用的 import (LinkLookup, OP_CARTAGE_IMPORT_RULES, field, Any)

**测试验证**:
- `COSCO ROTTERDAM / 209S` → 正确找到已有记录 `recvgKaLB8Xb0E`
- `COSCO ROTTERDAM / 999N` → 正确创建新记录并链接 Base Node (测试后已删除)

### [2026-04-14] Import 流程修正 — Base Node 三字段联合查询 + 去除 Shipping Line + Container Type 修复
**做了什么**:
- **Vessel Schedule 查询升级为 Vessel Name + Voyage + Base Node 三字段** — filter_expr 改为 `AND(CurrentValue.[Voyage]="{voyage}", CurrentValue.[Base Node]="{base_node}")`
  - 发现 Bitable 支持通过关联字段的显示文本过滤 (如 `CurrentValue.[Base Node]="PORT OF MELBOURNE"`)
  - 同一船名+航次+不同港口现在正确区分
  - 创建新 Vessel Schedule 记录时 Base Node 正确关联到 MD-Base Node
- **移除 Shipping Line from Op-Import 写回** — Shipping Line 属于 EDO 流程，Cartage Import 不应录入
  - 从 `OP_IMPORT_RULES` 删除 Shipping Line 规则
  - 从 writeback.py source dict 删除 `shipping_line` 键
  - 从 Import prompt 删除 shipping_line 提取要求 (Export prompt 保留)
- **修复 Container Type 写入** — source dict 缺少 `container_type` 键导致始终为空 (上一轮已修复，本轮验证通过)
- **更新 CartageDictValues** — commodity 选项从 5 个扩展到 9 个，与 Bitable 实际选项完全对齐: HAZ, GEN, GENL, REEF, OOG, BBLK, MT, EMPTY, MTHZ (修复 "REE"→"REEF" 不匹配问题)
- **新增文档** `.ai/cartage-writeback-guide.md` — 完整技术文档供同事参考改良

**E2E 验证** (使用 DELIVERY DOCKET...1219.pdf):
- Op-Cartage: Booking Reference ✅, Consingnee Name ✅, Deliver Config ✅, Import Booking ✅
- Op-Import: Container Number ✅, Container Type=40HC ✅, Commodity=GEN ✅, Container Weight ✅, FULL Vessel Name ✅
- Op-Vessel Schedule (新建): Vessel Name ✅, Voyage ✅, Base Node=PORT OF MELBOURNE ✅

---

### [2026-04-14] 多柜号支持 — Import Booking 追加 + 重复跳过 + Resolver 缓存
**做了什么**:
- **Import Booking 追加而非覆盖** — `_link_import_to_cartage` 改为 `_link_imports_to_cartage`
  - 先读取 Op-Cartage 现有 Import Booking → 合并新 record_ids → 去重 → 写回
  - 使用 `extract_link_record_ids` 统一处理 Bitable link 字段的不同读取格式
- **重复 Container Number 跳过** — 不再 raise DuplicateContainerError 中止全部
  - 遍历所有柜号，检查重复，跳过重复的，只录入不重复的
  - 全部重复时不创建 Op-Cartage
  - 新增 `SkippedContainer` schema，记录被跳过的柜号、原因和已有 record_id
  - 移除 `DuplicateContainerError` 类
- **LinkFieldResolver 内存缓存** — 同一请求内，相同 lookup+value+filter_expr 只查一次 Bitable
  - 多柜共享同一 Vessel Schedule 时，第 2-5 个柜直接命中缓存
  - 缓存 key 包含 target_table_id + search_field + value + rendered filter_expr
- **Export Booking 追加** — 同 Import Booking，改为 `_link_exports_to_cartage` 批量追加

**E2E 验证** (使用 SHEXP26030118 TLX.PDF — 5个进口柜):
- 5 个 Op-Import 全部创建: Container Number ✅, Container Type=20GP ✅, Commodity=GEN ✅, Weight ✅
- Import Booking: 5 条关联全部追加 ✅
- Vessel Schedule: 只创建 1 条 (FENG NIAN 361/276S, Base Node=PORT OF SYDNEY) — 缓存命中 ✅
- 重复提交: 5 个柜全部跳过，不创建空 Cartage ✅

---

### [2026-04-14] 1-to-1 Cartage-Import 重构 + is_direct_link 修复
**做了什么**:
- **1-to-1 关系重构** — 每个柜号创建独立的 Op-Cartage + Op-Import，不再共享一个 Op-Cartage
  - `writeback.py` 完全重写: `_writeback_import()` 改为逐柜循环，每个柜号独立创建 Op-Cartage 再创建 Op-Import
  - `writeback_schemas.py`: `cartage: WritebackRecordRef | None` → `cartage_refs: list[WritebackRecordRef]`
  - 移除 `_link_imports_to_cartage` / `_link_exports_to_cartage` (1-to-1 时由双向关联自动回填)
  - Export 流程同样重构为 1-to-1
- **is_direct_link 修复** — Op-Cartage 的 Consingnee Name 和 Deliver Config 写入失败
  - 根因: 旧配置用 `LinkLookup` 搜索 enrichment 已解析出的 record_id (如 `recvfDQTsLGCuR`)，把 record_id 当 Name 搜索，自然找不到
  - 修复: `WritebackFieldRule` 新增 `is_direct_link: bool = False` 字段
  - Consingnee Name 和 Deliver Config 改为 `is_direct_link=True`，直接写入 `[record_id]`
  - `_build_fields()` 新增 `is_direct_link` 分支，优先于 `link_lookup` 处理
- **测试脚本修复** — `scripts/test_auto_order_entry.py` 适配 `cartage_refs` 字段

**E2E 验证** (使用 SHEXP26030118 TLX.PDF — 5个进口柜):
- 5 个 Op-Cartage 全部创建 ✅, 每个 Booking Reference=SHEXP26030118
- 5 个 Op-Import 全部创建 ✅, 每个 Container Number/Type/Commodity/Weight 正确
- 每个 Op-Cartage 有且仅有 1 条 Import Booking (1-to-1) ✅
- Consingnee Name = HF IMPERIAL INTERNATIONAL ✅ (之前为空)
- Deliver Config = UNIT 3/222 Woodpark Rd, Smithfield NSW 2164 (STD) ✅ (之前为空)
- Vessel Schedule: 缓存命中，5 个 Op-Import 共享同一条 ✅

---

### [2026-04-14] Export 出口柜写回实现
**做了什么**:
- **新增 OP_CARTAGE_EXPORT_RULES** — Op-Cartage (Export) 写入配置: Booking Reference + Consingnee Name (direct_link) + Deliver Config (direct_link)，Consingee/Deliver Config 非必填（出口柜可能无地址匹配）
- **新增 OP_EXPORT_RULES** — Op-Export 写入配置:
  - Booking Reference (必填)
  - Container Number (可选，展开后可能无)
  - Release Qty (数字)
  - FULL Vessel Name (关联 Op-Vessel Schedule，同 Import 的 Vessel Name+Voyage+Base Node 三字段查找)
  - Container Type (单选)
  - Commodity (单选)
- **重写 `_writeback_export()`** — 与 Import 完全对齐:
  - 先 expand_export_bookings (release_qty>1 展开为多条)
  - 重复检查: 按 Container Number 查 Op-Export，有则跳过
  - 1-to-1: 每条展开后的 booking 独立创建 Op-Cartage + Op-Export
  - 使用 `_build_fields(OP_CARTAGE_EXPORT_RULES)` 和 `_build_fields(OP_EXPORT_RULES)` 配置驱动
- **expand_export_bookings 逻辑** — release_qty>1 时，Booking Reference 保持原值不变，Container Number 加 `-序号` 后缀 (如 RSG20811-1, RSG20811-2)，release_qty 改为 1

**E2E 验证** (使用 03288201...pdf — 出口柜 RSG20811, release_qty=2):
- 2 个 Op-Cartage 全部创建 ✅: BR=RSG20811 (不变), Consingnee=Ocean & Air Cargo Services ✅, Deliver Config=28 Jones Rd Brooklyn (SDL) ✅
- 2 个 Op-Export 全部创建 ✅: BR=RSG20811, CN=RSG20811-1/RSG20811-2, Release Qty=1, Container Type=20GP, Commodity=EMPTY ✅
- 1-to-1: 每个 Cartage 恰好 1 条 Export Booking ✅

---

### [2026-04-14] 线上版触发流程 — 从 Op-Cartage 记录触发写回
**做了什么**:
- **writeback_from_record() 新方法** — 从已有 Op-Cartage 行触发写回:
  - 第一个非重复柜号: UPDATE 原行（填入 Booking Reference, Consingee, Deliver Config, Record Status, Source Cartage）
  - 后续非重复柜号: CREATE 新行（Source Cartage → 指向原行）
  - 重复柜号: CREATE 新行（Record Status = Duplicate Entry Failed）
  - 全部重复时: UPDATE 原行标记 Duplicate Entry Failed
- **Record Status 字段** — select 类型，两个选项: Entry Successful / Duplicate Entry Failed
- **Source Cartage 字段** — 单向关联，原始行自关联，衍生行关联原始行
- **CartageRepository.download_attachment()** — 通过 Drive API 下载 Bitable 附件
- **extract_attachment_file_tokens()** — 从附件字段值提取 file_token
- **POST /cartage/trigger** 端点 — 传入 record_id，自动下载附件 → 解析 → 匹配 → 写回
- **lark_tables.py** — Op-Cartage 新增 record_status, source_cartage, completed_confirm 字段映射

**设计决策**:
- 原始行 Source Cartage 自关联 → 按 Source Cartage 筛选/分组时原始行和衍生行在同一组
- 第一个柜重复时用第二个非重复柜填原行（避免出现有附件但数据为空的行）
- 不复制附件到衍生行，通过 Source Cartage 关联查看原始行附件

---

*最后更新: 2026-04-14*

### [2026-04-15] Trigger 端点 404 修复 + 附件下载 + 链接字段写回修复
**做了什么**:
- **修复 POST /cartage/trigger 返回 404** — 根因: `router.include_router(cartage_router)` 在 `llm.py` 第 17 行执行，此时 `cartage_router` 的路由装饰器尚未执行，导致子路由为空
  - 修复: 将 `router.include_router()` 调用移到文件末尾（所有装饰器之后）
  - data controller 不受影响（它从独立文件 import 子 router，装饰器已执行完毕）
- **修复附件下载 `_token_manager` 报错** — `lark.Client` builder 模式不暴露 `_token_manager`
  - 修复: 新增 `_get_tenant_token()` 方法，直接调用 auth API 获取 tenant_access_token
  - Drive media 下载 URL 修正为 `/drive/v1/medias/{file_token}/download`（需 `/download` 后缀）
- **修复 is_direct_link/link_lookup 字段写入 "TBC" 到 duplex link** — 当 `consingee_id` 为 None 时，`_build_fields` 的 fallback 分支将 "TBC" 字符串写入链接字段，触发 Bitable 1254074 错误
  - 修复: `is_direct_link` 和 `link_lookup` 规则的 `continue` 不再依赖 `value` 有值，value 为空时直接 skip 该字段，不写 fallback

**E2E 验证** (使用 recvgMkopfDD5n — 5个进口柜 SHEXP26030118):
- 5 个 Op-Cartage 创建 ✅: 第一个 UPDATE 原行，其余 4 个 CREATE
- 5 个 Op-Import 创建 ✅: Container Number/Type/Commodity/Weight 正确
- Record Status = Entry Successful ✅, Source Cartage 正确指向原行 ✅
- Vessel Schedule (FENG NIAN 361/276S/PORT OF SYDNEY) 新建并链接 ✅
- 测试数据已清理

### [2026-04-15] 幂等保护 + AI 解析稳定性修复
**做了什么**:
- **幂等保护** — `trigger_cartage_from_record` 现在检查 Record Status，已处理的记录直接拒绝（`ValueError`）
  - `trigger_pending_cartage_records` 的筛选逻辑也改为 `extract_cell_text(r.get("Record Status"))` 处理 select 字段的各种读取格式
  - 防止同一条记录被重复触发（之前可无限重复创建）
- **AI 解析稳定性** — `temperature` 从 0.1 降为 0.0（ZhipuAI glm-5v-turbo thinking 模式支持）
  - Prompt 加强 vessel_name/voyage 提取约束：user_hint 新增 "CRITICAL: vessel_name and voyage are REQUIRED"
  - system prompt 新增 "VESSEL NAME AND VOYAGE ARE CRITICAL" 规则

**E2E 验证**:
- 5 个进口柜全部稳定提取 vessel_name=FENG NIAN 361, voyage=276S ✅
- 第二次 trigger 正确拒绝: "Record recvgMkopfDD5n already processed" ✅

### [2026-04-15] EDO 解析+匹配+写回完整实现
**做了什么**:
- **EDO 解析增强** — EdoEntry 新增 empty_park_address 字段; EdoDictValues 动态从 Bitable 构建（Shipping Line + Empty Park 列表含别名）
  - Prompt 注入 Shipping Line 和 Empty Park 列表，AI 输出精确 Bitable 名
  - EdoParser 适配 EdoDictValues 注入，system_prompt 改为 property
- **EDO 匹配** — EdoEnrichmentService（Shipping Line 精确+Short Name fallback; Empty Park 精确名→别名→模糊名+地址三层匹配）
  - MD-Empty Park Alias 字段支持（分号分隔的别名列表）
  - lark_tables.py MD-Empty Park 新增 alias 字段映射 (fldNWhSkie)
- **EDO 领域服务** — EdoService（Shipping Line / Empty Park 带缓存查询 + build_dict_values）
  - CacheFactory 扩展 EdoMatchingCacheKey (SHIPPING_LINES, EMPTY_PARKS)
  - ShippingLineRepository 新增
- **EDO 写回** — EdoWritebackService：按 Container Number 查找 Op-Import → UPDATE
  - EdoWritebackSchemas (EdoWritebackResult + EdoWritebackEntryRef)
  - ImportRepository 新增 download_attachment
  - lark_tables.py Op-Import 新增 record_status (fldEwvsGtt) + source_edo (fldgijIfl5) 字段映射
  - LLMService 新增 trigger_edo_from_record + trigger_pending_edo_records
  - Controller 新增 POST /edo/process, /edo/process-text, /edo/trigger, /edo/clear-cache
- **Cartage 地址匹配验证** — 确认地址匹配逻辑正常（score=1.0 精确匹配 UNIT 3/222 Woodpark Rd），之前报告的 Consingee/Deliver Config 丢失是暂时性问题

**本地测试结果**:
- EDO PDF 解析+匹配: Shipping Line / Empty Park 正确匹配 ✅
- EDO trigger E2E: 解析+匹配+写回逻辑正确 ✅
- Cartage 地址匹配: UNIT 3/222 Woodpark Rd → score=1.0, Consingee=HF IMPERIAL INTERNATIONAL, Deliver Config=STD ✅

### [2026-04-16] 同事合并 — Writeback 移入 Service + 码头爬虫 Provider + RelationLoader
**变更来源**: 同事 3 个 commit (e62350d, 51989c6, 69a2103)

**架构调整**:
- **Writeback 从 llm_service 移入 CartageService** — `CartageWritebackService` 整类删除，逻辑 (+322 行) 合并到 `app/service/cartage.py`
  - `writeback_config.py` → `app/service/model/cartage_writeback_config.py`
  - `writeback_schemas.py` → `app/service/model/cartage_writeback_schemas.py`
  - `llm_service.py` 删除 `CartageWritebackService` 依赖，改为 `self._cartage.writeback()` / `self._cartage.writeback_from_record()`
  - CartageService 用 `TYPE_CHECKING` 延迟 import `CartageProcessResult` 规避循环依赖

**新增文件**:
- `app/common/relation_loader.py` — `RelationLoader` + `RelationConfig`，批量关联字段解析，消除 N+1 串行调用
- `app/component/VbsSearchProvider.py` (679 行) — VBS 码头查询爬虫 (集装箱可用性/ETA/Storage Date)
- `app/component/HutchisonPortsProvider.py` (489 行) — Hutchison Ports 爬虫 (import availability/match pin)
- `app/component/OneStopProvider.py` (361 行) — 1-Stop 爬虫 (集装箱信息/海关货物状态/空箱归还)
- `app/component/ContainerChainProvider.py` (334 行) — ContainerChain 爬虫 (import/export 集装箱信息)
- `app/component/__init__.py`
- `app/service/model/__init__.py`

**其他**:
- `CLAUDE.MD` 新增规则: "使用中文回复 代码注释也使用中文"

**待关注问题**:
1. CartageService import CartageProcessResult（来自 llm_service 子包）造成逻辑上的反向依赖，TYPE_CHECKING 只是编译期规避
2. 4 个 Component Provider 无统一基类/接口，各自独立实现
3. ContainerChainProvider 硬编码账号密码 (第 48-49 行)
4. 新增依赖 (beautifulsoup4, lxml, pytz) 可能未在 pyproject.toml 声明

### [2026-04-17] VesselSync Controller 更新 + OneStopProvider load_terminal_mapping 修复
**做了什么**:
- **Controller 更新** — `app/controller/sync/vessel.py` 替换旧的 `sync_pending()` 为新的声明式端点:
  - `GET /sync/vessel/conditions` — 列出所有可用的批量同步条件
  - `POST /sync/vessel/batch` — 接受 `VesselBatchSyncRequest` 请求体 (condition/base_node/limit)
  - `POST /sync/vessel/single` — 单条同步 (保留不变)
- **修复 OneStopProvider 缺失函数** — `_parse_match_containers_info` 引用 `load_terminal_mapping` 但该函数不存在
  - 新增 `app/common/relation_loader.py:load_terminal_mapping()` — 从 MD-Terminal 加载 {Terminal Full Name: {"Depot": depot}} 映射，模块级缓存
  - `_parse_match_containers_info` 改为接受 `terminal_mapping` 参数，不再内部 import
  - `match_containers_info_by_list` 在调用前预加载 terminal_mapping 并传入

**下一步**:
- 批量同步 E2E 测试 (sync_batch 各种 condition)
- 更多 Component 爬虫集成 (VBS/Hutchison/ContainerChain service + controller)
- Provider 统一接口抽象
- 账号密码配置化

### [2026-04-19] 港口数据同步 (Port Data Sync) + Bug 修复
**做了什么**:
- **HutchisonPortsProvider 代理修复** — `_PROXY` 从 `"http://127.0.0.1:7890"` 改为 `None`（用户本地无代理）
- **ContainerSyncService.sync 改为 batch_update_records** — 原来 `sync` 方法逐条 `update_record`，现改为批量查 record_id + `batch_update_records` + 回退逐条，与 `sync_batch` 对齐
- **Op-Import 缺失字段补齐** — lark_tables.py 新增 5 个字段映射:
  - `on_board_vessel` (fldMoSJMeC, ON_BOARD_VESSEL)
  - `discharge` (fld1RJa0Ji, DISCHARGE)
  - `gateout` (fldELjpWia, GATEOUT)
  - `quarantine` (fldLWaEpR3, Quarantine)
  - `clear_status` (fld7OEef4K, Clear Status)
- **PortDataSyncService 完整实现** — 港口数据同步服务，支持 3 个 Provider 数据源:
  - `sync_customs()` — 1-Stop customs_cargo_status_search → Clear Status + Quarantine
  - `sync_hutchison()` — HutchisonPorts container_enquiry_by_list → Clear Status + ISO + Gross Weight + Quarantine
  - `sync_all()` — 合并所有 Provider，同字段取第一个有值的
  - 声明式 `PortDataFieldMapping` 配置驱动，与 ContainerSyncService 同模式
  - batch_update_records + 回退逐条写回
- **Controller 端点**:
  - `POST /sync/customs` — 清关状态同步
  - `POST /sync/hutchison` — Hutchison 集装箱查询同步
  - `POST /sync/port-data` — 合并所有 Provider 同步
- **Gross Weight number 修复** — ContainerSyncService 的 Gross Weight 映射缺少 `field_type="number"`，导致字符串写入 number 字段；`_build_update_fields` 新增 `number` 分支

**E2E 验证**:
- Hutchison sync: OOCU9024853 → Clear Status=RELEASED, ISO=45G0, Gross Weight=10.92, Quarantine=Not Found ✅
- Port-data (合并): TGBU4369245 → 4 个字段写回成功 ✅
- Bitable 数据确认: Clear Status / ISO / Gross Weight / Quarantine 均正确持久化 ✅

**待完成**:
- VbsSearchProvider / ContainerChainProvider 集成
- 4 个 Provider 统一接口抽象
- 账号密码配置化

### [2026-04-20] Clear 模块重构 + 批量同步 + Sync 规范固化
**做了什么**:
- **PortData → Clear 重构** — 删除 3 个旧端点 (customs/hutchison/port-data)，合并为单一 `POST /sync/clear`
  - 请求体: `{ container_numbers, terminal_full_name }`
  - `terminal_full_name` 为空 → 先 1-Stop customs，无数据 fallback Hutchison
  - 非 HUTCHISON PORTS - PORT BOTANY → 只调 1-Stop customs
  - HUTCHISON PORTS - PORT BOTANY → 只调 Hutchison
  - 返回中含 `provider` 字段标识数据来源
- **Clear 批量同步** — `POST /sync/clear/batch`
  - 声明式 `ClearBatchCondition`：`pending`（Terminal 不为空 + Clear Status 非终态）/ `all`
  - 终态列表: `CLEAR`, `UNDERBOND APPROVAL`, `RELEASED`
  - `sync_batch` 按 Provider 分组：Hutchison 码头记录一组，其他码头记录一组，各组独立查+写回
- **Sync Module 三步模式固化** — 写入 AGENTS.md 和 architecture.md，作为后续所有爬虫同步模块的强规范
  - 步骤 1: 数据来源（手动传入 / 声明式 BatchCondition 自动筛选）
  - 步骤 2: 调 Provider 拿数据（单 Provider / 多 Provider 路由）
  - 步骤 3: 批量写回 Bitable（batch_update_records + 回退逐条 + 声明式 FieldMapping）
  - 文件结构模板: `service/sync/{module}.py` + `service/sync/model/{module}_schemas.py` + `controller/sync/{module}.py`

**E2E 验证**:
- Hutchison terminal: OOCU9024853 → provider=Hutchison, Clear Status+Quarantine ✅
- 非 Hutchison terminal: → provider=1-Stop customs ✅
- 空 terminal fallback: → provider=Hutchison (1-Stop 无数据后 fallback) ✅
- 批量 pending: 4 条记录，3 条 1-Stop + 1 条 Hutchison，全部同步成功 ✅

### [2026-04-20] BitableQuery 统一重构 — 去除 filter_fn 双轨制
**做了什么**:
- **重写 BitableQuery** — 每个子句同时存储 `filter_expr`(服务端) 和 `predicate`(客户端)
  - `build()` → 生成服务端 filter_expr（预筛选，减少数据拉取）
  - `filter(records)` → 客户端 Python 精筛（保证正确性，处理 Bitable 无法表达的条件如 `ETA < now()`）
  - 新增 `.client_filter(predicate)` — 纯客户端筛选条件（无服务端 filter_expr 对应）
  - 新增 `.raw(expr, predicate?)` — 支持附带可选客户端判断
  - 新增 `.has_client_filter()` — 判断是否存在客户端筛选
  - 所有链式方法（eq/ne/not_empty/is_empty/not_in/in_list/gt/gte/lt/lte）同时生成 expr + predicate
- **重构 BatchCondition** — 去掉 `filter_fn` 字段，BitableQuery 成为唯一条件定义机制
  - 新增 `query_fn: Callable[[], BitableQuery]` — 动态工厂，用于需要运行时值（如 `now()`）的条件
  - `query`(静态) 和 `query_fn`(动态) 二选一，`query_fn` 优先
  - 新增 `get_query()` 方法统一获取 BitableQuery
- **更新 VesselSyncService**:
  - `pending_arrival` 改用 `raw('OR(NOT CurrentValue.[Actual Arrival], AND(...))')` 正确处理空值
  - 删除 `_actual_arrival_not_confirmed` 函数和 `filter_fn` 字段
  - `sync_batch` 改为 `query = cond.get_query()` + `query.filter(all_records)`
- **更新 ContainerSyncService**:
  - `discharge` 和 `gateout` 改用 `query_fn` 工厂 + `.client_filter(_eta_passed_predicate)`
  - 删除 `_has_text` / `_not_has_text` / `_discharge_check` / `_gateout_check` 函数和 `filter_fn` 字段
  - `sync_batch` 统一用 `query.filter(all_records)`
- **更新 ClearSyncService**:
  - `ClearBatchCondition` 对齐新结构（新增 query_fn + get_query）
  - `sync_batch` 统一用 `query.filter(all_records)`
- **更新 AGENTS.md** — Sync Module 关键约束重写，明确禁止 `filter_fn` 双轨制

**设计原则**:
- 服务端 filter_expr 是"尽力预筛"——减少数据拉取量，但不保证 100% 精确（如空值处理差异）
- 客户端 filter 是"精确保证"——对所有返回记录做最终验证
- `not_in("Clear Status", [...])` 的 filter_expr 不匹配空值，但 client predicate 包含空值——两阶段互补

### [2026-04-20] BitableQuery 实测 + NOT 语法修复 + Controller conditions 端点
**做了什么**:
- **重大发现：Bitable 不支持 `NOT` 运算符** — `NOT CurrentValue.[Field]` 返回 `InvalidFilter`
  - "为空"必须用 `CurrentValue.[Field]=""`
  - "非空"必须用 `CurrentValue.[Field]!=""`
- **修正 BitableQuery**:
  - `is_empty` → `CurrentValue.[Field]=""`（原来用 `NOT CurrentValue.[Field]`）
  - `not_empty` → `CurrentValue.[Field]!=""`（原来用 `CurrentValue.[Field]`，部分场景返回 0 记录）
  - `not_in` / `in_list` 的 predicate 修复 None 安全（`extract_cell_text` 可能返回 None）
- **修正所有 raw() 表达式** — Container 的 `basic`/`terminal`/`vessel_schedule` 中 `NOT CurrentValue.[X]` 改为 `CurrentValue.[X]=""`
- **修正 Vessel `pending_arrival`** — `OR(NOT ...)` 改为 `OR(CurrentValue.[Actual Arrival]="", AND(...))`
- **新增 3 个 conditions 端点** — `GET /sync/vessel/conditions`, `GET /sync/container/conditions`, `GET /sync/clear/conditions`

**E2E 测试结果（全部通过）**:

| 端点 | 条件 | total | synced | errors |
|------|------|-------|--------|--------|
| `POST /sync/vessel/batch` | pending_arrival | 0 | 0 | 0 |
| `POST /sync/vessel/batch` | missing_eta | 0 | 0 | 0 |
| `POST /sync/vessel/batch` | all | 4 | 4 | 0 |
| `POST /sync/container/batch` | basic | 8 | 8 | 0 |
| `POST /sync/container/batch` | terminal | 0 | 0 | 0 |
| `POST /sync/container/batch` | vessel_schedule | 0 | 0 | 0 |
| `POST /sync/container/batch` | discharge | 0 | 0 | 0 |
| `POST /sync/container/batch` | gateout | 0 | 0 | 0 |
| `POST /sync/container/batch` | all | 8 | 8 | 0 |
| `POST /sync/clear/batch` | pending | 1 | 1 | 0 |
| `POST /sync/clear/batch` | all | 8 | 8 | 0 |
| `POST /sync/vessel` (单条) | recvh3COKI3bzQ | - | 1 | 0 |
| `POST /sync/container` (单条) | OOCU9024853 | 1 | 1 | 0 |
| `POST /sync/clear` (单条) | OOCU9024853 Hutchison | 1 | 1 | 0 |

**Bitable filter_expr 语法备忘**:
- ✅ `CurrentValue.[Field]="value"` / `CurrentValue.[Field]!="value"`
- ✅ `CurrentValue.[Field]=""` (为空) / `CurrentValue.[Field]!=""` (非空)
- ✅ `AND(...)`, `OR(...)` 嵌套
- ❌ `NOT CurrentValue.[Field]` — InvalidFilter
- ❌ `CurrentValue.[Field] = null` / `is null` — InvalidFilter

### [2026-04-20] BitableQuery 统一重构 — 语义化 + 去除 query_fn/raw
**做了什么**:
- **BitableQuery 新增组合条件方法**:
  - `any_empty(fields)` — 任一字段为空 → `OR(f1="", f2="", ...)`
  - `not_in_or_empty(field, values)` — 字段为空或不在列表中 → `OR(field="", AND(field!="v1", ...))`
- **统一 BatchCondition 结构** — 三个 sync service 一致: `name + description + query + required_fields`
  - 去掉 `query_fn`（`client_filter` 的 lambda 延迟执行，不需要工厂）
  - 去掉 `raw()` 调用（全部用 `any_empty` / `not_in_or_empty` 语义化方法）
  - 去掉 `get_query()` 方法（直接用 `cond.query`）
- **Container 条件复用提取** — `_vessel_info_present()` / `_terminal_info_present()` 工厂函数
- **Clear pending 改用 `not_in_or_empty`** — 服务端 filter 正确包含 Clear Status 为空的记录
- **修复模块级 BitableQuery 共享可变状态** — 改为工厂函数，每次创建新实例

**E2E 测试结果（全部通过）**:

| 端点 | 条件 | total | synced | errors |
|------|------|-------|--------|--------|
| `POST /sync/vessel/batch` | pending_arrival | 4 | 4 | 0 |
| `POST /sync/vessel/batch` | missing_eta | 0 | 0 | 0 |
| `POST /sync/vessel/batch` | all | 4 | 4 | 0 |
| `POST /sync/container/batch` | basic | 8 | 8 | 0 |
| `POST /sync/container/batch` | terminal | 0 | 0 | 0 |
| `POST /sync/container/batch` | vessel_schedule | 0 | 0 | 0 |
| `POST /sync/container/batch` | discharge | 0 | 0 | 0 |
| `POST /sync/container/batch` | gateout | 0 | 0 | 0 |
| `POST /sync/container/batch` | all | 8 | 8 | 0 |
| `POST /sync/clear/batch` | pending | 7 | 7 | 0 |
| `POST /sync/clear/batch` | all | 8 | 8 | 0 |

### [2026-04-20] Sync 三模块统一 — BatchCondition write_fields 重构完成
**做了什么**:
- **VesselSyncService 重构** — `BatchCondition` 改为 `name + description + query + write_fields`，去掉 `required_fields`
  - 每个条件配独立 `write_fields: list[FieldMapping]`，不同条件写回不同字段集
  - 写回字段按语义分组: `_DATETIME_FIELDS`(6个时间字段) + `_ACTUAL_ARRIVAL`(text) + `_TERMINAL_NAME`(link)
  - 条件定义加中文注释: 筛选规则 + 写回字段
- **ContainerSyncService 重构** — 同样结构，6个条件每个配独立 `write_fields`
  - 写回字段按语义分组: `_VESSEL_INFO` / `_TERMINAL_INFO` / `_SCHEDULE_INFO` / `_CARGO_INFO` / `_ON_BOARD` / `_DISCHARGE` / `_GATEOUT`
  - basic=全量 / terminal=去船舶 / vessel_schedule=去码头 / discharge=仅卸船+提柜 / gateout=仅提柜 / all=全量
  - `sync()` 手动触发也使用 `cond.write_fields`（用 "all" 条件的字段集）
- **ClearSyncService 重构** — `ClearBatchCondition` 新增 `write_fields: dict[str, list[ClearFieldMapping]]`
  - 清关特点：不同 Provider 返回不同字段，所以 `write_fields` 按 Provider 名称分组
  - 1-Stop customs → Clear Status + Quarantine
  - Hutchison → Clear Status + Quarantine + ISO + Gross Weight (number)
  - `sync_batch` 按 Terminal 分组后，从 `cond.write_fields[provider_name]` 取对应的字段映射
  - `sync()` 手动触发也使用 `CLEAR_BATCH_CONDITIONS["all"].write_fields`
  - 去掉 `required_fields`，`list_all_records` 不再限制 `field_names`（与 vessel/container 一致）
  - 删除顶层 `ONESTOP_CUSTOMS_MAPPINGS` / `HUTCHISON_CLEAR_MAPPINGS` 常量（已内聚到条件定义中）

**E2E 测试结果（全部通过）**:

| 端点 | 条件 | total | synced | errors |
|------|------|-------|--------|--------|
| `POST /sync/vessel/batch` | all | 4 | 4 | 0 |
| `POST /sync/container/batch` | basic | 8 | 8 | 0 |
| `POST /sync/clear/batch` | pending | 0 | 0 | 0 |
| `POST /sync/clear/batch` | all | 8 | 3 | 0 |

**三个 Sync 模块现已完全统一**:
- `BatchCondition(name, description, query, write_fields)` — Clear 的 `write_fields` 是 `dict[str, list]`（按 Provider 分组），Vessel/Container 是 `list`（单 Provider）
- 每个条件一眼看出"筛什么"+"写什么"
- 中文注释覆盖所有条件定义

### [2026-04-20] Sync 全面重构 — 全局字段类型 + LinkConfig + 共享逻辑
**做了什么**:
- **新增 `app/common/bitable_fields.py`** — 全局 Bitable 字段类型注册表
  - 每个字段类型只定义一次，所有模块共享
  - `get_field_type(field_name)` 自动解析类型
  - FieldMapping 不再需要 `field_type` 参数，从注册表自动推导
- **新增 `app/service/sync/base.py`** — Sync 模块共享类型与逻辑
  - `LinkConfig(table, search_field)` — 关联字段配置，只需指定目标表 + 搜索字段，自动查找 record_id
  - `LinkResolver` — 通用关联字段解析器，缓存 + 自动查找，复用 DynamicRepo 模式
  - `FieldMapping(provider_key, bitable_field, link=)` — link 非空时自动解析，field_type 强制为 "link"
  - `BatchCondition` / `MultiProviderBatchCondition` — 统一条件类型
  - `build_update_fields()` — 共享字段构建，自动处理 text/number/datetime/link/select
  - `batch_write_back()` — 共享批量写回 + 逐条回退
  - `parse_datetime_to_timestamp()` — 共享日期解析
- **重构 vessel_sync.py**:
  - Terminal Name 改用 `LinkConfig(table=T.md_terminal, search_field="Terminal Full Name")`，删除自定义 `_find_terminal_by_full_name`
  - 删除本地 `FieldMapping` / `BatchCondition` 定义，改用 base 共享类型
  - 删除本地 `_build_update_fields` / `_batch_write_back` / `_parse_datetime_to_timestamp`
  - 删除 `TerminalRepository` 依赖（LinkResolver 自动处理）
- **重构 container_sync.py**:
  - 删除本地 `FieldMapping` / `BatchCondition` 定义，改用 base 共享类型
  - 删除本地 `_build_update_fields` / `_batch_write_back` / `_parse_datetime_to_timestamp`
- **重构 clear_sync.py**:
  - 删除本地 `ClearFieldMapping` / `ClearBatchCondition` 定义，改用 base 的 `FieldMapping` / `MultiProviderBatchCondition`
  - 删除本地 `_build_update_fields` / `_batch_write_back`

**核心设计**:
1. **字段类型全局注册** — `bitable_fields.py` 一个地方定义所有字段类型，FieldMapping 不再重复声明 field_type
2. **LinkConfig 配置驱动** — 只需 `LinkConfig(table=T.md_terminal, search_field="Terminal Full Name")`，不再写自定义查询代码
3. **三个模块共享 build_update_fields + batch_write_back** — 不再每个 service 重复实现

**E2E 测试结果（全部通过）**:

| 端点 | 条件 | total | synced | errors |
|------|------|-------|--------|--------|
| `POST /sync/vessel/batch` | all | 4 | 4 | 0 |
| `POST /sync/container/batch` | basic | 10 | 8 | 0 |
| `POST /sync/clear/batch` | all | 10 | 3 | 0 |

### [2026-04-21] OverwritePolicy — 字段覆盖策略
**做了什么**:
- **OverwritePolicy 枚举** — `base.py` 新增三种覆盖策略:
  - `ALWAYS` — Provider 有值就覆盖（适合会变化的字段如 Status）
  - `NON_EMPTY` — Provider 返回空值时不覆盖（默认，安全策略）
  - `ONCE` — Bitable 已有值就不覆盖（适合"一旦确定就不变"的字段如日期），需传 `existing_fields`
- **FieldMapping 新增 `overwrite` 字段** — 默认 `NON_EMPTY`
- **build_update_fields 支持三种策略**:
  - ONCE: 检查 `existing_fields` 中该字段是否已有值，有值跳过
  - NON_EMPTY: Provider 返回空值时跳过
  - ALWAYS: 即便空值也写入
- **所有 sync 模块字段暂配 NON_EMPTY** — 后续可按字段语义调整（如 Clear Status 用 ALWAYS，日期类用 ONCE）

### [2026-04-21] VBS 同步服务 — VbsSyncService
**做了什么**:
- **VbsSyncService 完整实现** — VBS 集装箱可用性同步，按 Terminal Full Name 路由到 VBS operation
  - Terminal 路由映射 `_TERMINAL_TO_OPERATION`: DP WORLD NS/DP WORLD VI/PATRICK NS/PATRICK VI/VICTORIA INTERNATIONAL → 5 个 VBS operation
  - `sync(container_numbers, terminal_full_name)` — 手动触发
  - `sync_batch(condition)` — 批量触发，按 operation 分组后各组独立查+写回
- **MultiProviderBatchCondition** — VBS 按 operation 分组写回字段（结构相同，按 operation 分组是为了支持多 Provider 扩展）
  - `pending`: GATEOUT_Time 为空 + Terminal 可路由 → EstimatedArrival + ImportAvailability + StorageStartDate
  - `all`: 全部可路由记录
- **VBS Controller** — `POST /sync/vbs` + `POST /sync/vbs/batch` + `GET /sync/vbs/conditions`
- **VbsSearchProvider._PROXY = None** — 修复代理问题
- **VICTORIA INTERNATIONAL CONTAINER TERMINAL 映射修复** — 去掉 "LIMITED"

**E2E 验证** (pending 条件):
- 10 条待处理记录，9 条成功同步 (1 条 VBS 无数据) ✅
- EstimatedArrival / ImportAvailability / StorageStartDate 正确写入 Bitable ✅

### [2026-04-21] VBS Patrick VIC 字段适配
**做了什么**:
- **Patrick VIC VBS 页面使用不同 HTML 结构** — 字段在 `MovementDetailsForm` 前缀下（其他码头用 `ContainerVesselDetailsForm`）：
  - ImportAvailability → `MovementDetailsForm___CONTAINERAVAILABILITY`（Patrick VIC 叫 "Container Availability"）
  - StorageStartDate → `MovementDetailsForm___CONTAINERSTORAGESTART`（Patrick VIC 叫 "Storage Start"，依旧 -1 小时）
  - EstimatedArrival → `MovementDetailsForm___ESTIMATEDARRIVALDATE`（Patrick VIC 也在此前缀下）
- **`_CTNS_REGEX_PATTERNS` 多候选 pattern** — 每个字段按优先级配多个候选 regex：
  - EstimatedArrival: `ContainerVesselDetailsForm___ESTIMATEDARRIVALDATE` → `MovementDetailsForm___ESTIMATEDARRIVALDATE`
  - ImportAvailability: `ContainerVesselDetailsForm___IMPORTAVAILABILITY` → `MovementDetailsForm___CONTAINERAVAILABILITY`
  - StorageStartDate: `ContainerVesselDetailsForm___IMPORTSTORAGEDATE` → `MovementDetailsForm___CONTAINERSTORAGESTART`
- **`_normalize_ctn_dates` 支持带秒格式** — Patrick VIC 日期含秒（如 `19/04/2026 09:55:07`），之前 `strptime` 只匹配 `%d/%m/%Y %H:%M` 导致 ValueError→空字符串。改为依次尝试 `%d/%m/%Y %H:%M:%S` → `%d/%m/%Y %H:%M` → `%d/%m/%Y`

**E2E 验证** (5 个码头全部 3 字段完整):
- dpWorldNSW ✅ / patrickNSW ✅ / patrickVIC ✅ / dpWorldVIC ✅ / victVIC ✅
- Patrick VIC: EstimatedArrival=2026-04-18 12:00, ImportAvailability=2026-04-19 09:55, StorageStartDate=2026-04-23 09:00

**待完成**:
1. ContainerChainProvider 集成
2. 4 个 Provider 统一接口抽象
3. 账号密码配置化

---

### [2026-04-22] 远程仓库重大重构同步 — QueryWrapper/UpdateWrapper + SyncTemplate/SyncData
**变更来源**: 同事 2 个 commit (5d42a3c, bfaab75)

**架构调整**:

- **Repository 层 MyBatis-Plus 风格重构** — `BitableQuery` → `QueryWrapper` + `UpdateWrapper`
  - `QueryWrapper` 链式查询构建器：每个子句同时存储 `condition_node`(服务端) + `predicate`(客户端)
  - `UpdateWrapper` 链式更新构建器：`.eq().set().set_all().with_label()`
  - `BaseRepository` 统一接口：`findOne/updateOne/deleteOne` 都接收 Wrapper
  - `eq("record_id", rid)` / `in_list("record_id", ids)` 特殊处理：不走 search API，走直连 GET/batch_get
  - 删除 `app/common/bitable_query.py`

- **Sync 模板模式重构** — `base.py` → `SyncTemplate` + `SyncData` + 按职责分层
  - `SyncTemplate` 模板方法：`fetch_records → fetch_provider_data → build_update_wrappers → _persist`
  - `SyncData` Pydantic 基类：`alias` 声明字段映射，`to_update_wrapper()` 自动转换
  - `BatchSyncResult(total/synced/errors)` 统一结果
  - 目录分层：`workflow/`(骨架) + `scene/`(场景实现) + `constants/`(条件) + `utils/`(工具) + `request/`(请求) + `factory/`(策略工厂)
  - 删除 `service/sync/base.py` + `vessel_sync.py` + `container_sync.py` + `clear_sync.py` + `vbs_sync.py` + `model/*.py`
  - 新增 4 个 SyncTemplate 子类：`VesselSyncService`、`ContainerSyncService`、`ClearSyncService`、VBS 5 个码头各一个
  - 新增 `VbsSyncFactory` 策略工厂 + `VbsSyncService` 委托层
  - 新增 `LinkConfig` + `LinkResolver`(sync/utils/) — 通用关联字段解析
  - 新增 `safe_ts`(sync/utils/datetime_parser.py) — 共享时间戳转换

- **集合操作 + 断言工具提取到 common/** — `collection_utils.py` + `assert_utils.py`
  - `pluck/to_map/filter_by/group_by/partition` 消除重复集合操作
  - `assert_in/assert_not_blank/assert_not_none/assert_true` 消除重复断言
  - CLAUDE.md 新增「一.五、公共工具使用规范」章节

**文档同步**:
- AGENTS.md — 项目结构 + Sync 三步模式规范对齐
- .ai/architecture.md — 远程已更新
- .ai/decisions.md — 新增 3 条决策记录
- .ai/style-guide.md — 远程已更新

### [2026-04-23] 远程重构同步 + Sync 模块 E2E 测试修复
**做了什么**:
- **git pull 远程重构代码** — Fast-forward 合并，95 文件 +2419/-2117 行
- **修复 `extract_linked_ids` 不支持 `link_record_ids` dict 格式** — Bitable link 字段返回 `{"link_record_ids": ["recXXX"]}` 而非显示文本，原函数只处理 str/list
- **修复 Vessel `Base Node` link 字段解析** — `_record_to_dict` 解析后返回 `{'link_record_ids': [...]}`，新增 `_resolve_base_node()` 用 `RelationLoader` 批量解析
- **所有 constants 改为纯 `client_filter`** — vessel/container/clear/vbs 4 个 constants 文件，去掉服务端 filter（Bitable OR+嵌套AND 语法有坑），全拉客户端筛
- **修复 ContainerData 3 个 datetime 字段类型** — `on_board_vessel_time`/`discharge_time`/`gateout_time` 从 `str | None` 改为 `int | None`，`_parse` 方法从 `_str()` 改为 `safe_ts()`
- **修复 `container_constants._eta_passed` 不支持 int 时间戳** — `EstimatedArrival` 从 Bitable 读回为 int 毫秒时间戳，`_to_datetime()` 统一处理 int/str 两种格式
- **创建备份分支 `main-local-backup`**（指向 2e02edc）

**E2E 测试结果（4 个 Sync 模块全部通过）**:

| 模块 | 条件 | total | synced | errors |
|------|------|-------|--------|--------|
| Vessel | pending_arrival | 2 | 2 | 0 |
| Vessel | missing_eta | 0 | 0 | 0 |
| Vessel | all | 9 | 9 | 0 |
| Container | basic | 1 | 1 | 0 |
| Container | terminal | 2 | 2 | 0 |
| Container | vessel_schedule | 1 | 1 | 0 |
| Container | discharge | 1 | 1 | 0 |
| Container | gateout | 7 | 7 | 0 |
| Container | all | 17 | 17 | 0 |
| Clear | pending | 1 | 1 | 0 |
| Clear | all | 15 | 15 | 0 |
| VBS | pending | 11 | 11 | 0 |
| VBS | all | 11 | 11 | 0 |

### [2026-04-23] _resolve_base_node 重构 — 去除内联 Repo + 不发明方法原则
**做了什么**:
- **删除 `_resolve_base_node` 中的内联 `_BaseNodeRepo` 类** — 违反"一表一文件"铁律，方法内动态创建 Repository 绕过了正常的依赖管理
- **新建 `app/repository/base_node.py`** — 正规的 `BaseNodeRepository(BaseRepository)`，与其他 repo 保持一致
- **重写 `_resolve_base_node`** — 用已有工具链：`extract_link_record_ids`(提取 record_id) + `BaseNodeRepository.list(in_list("record_id", ids))`(批量查) + `to_map`(构建映射)，不再用 `RelationLoader` + 手动 pop/覆盖
- **构造函数注入 `BaseNodeRepository`** — 通过参数注入，可测试、可替换
- **删除 `RelationLoader`/`RelationConfig` import** — 不再需要
- **AGENTS.md 新增"不发明方法"铁律** — 5 条规则写进 Sync 模块关键约束
- **decisions.md 新增 3 条决策记录** — 禁止内联 Repo + constants 暂用纯 client_filter + 不发明方法原则

**E2E 验证**: Vessel/Container/Clear/VBS 全部 0 errors

### [2026-04-23] Op-Import 新增 Full Vessel In + PortOfDischarge 改 link
**做了什么**:
- **lark_tables.py** — Op-Import 新增 `full_vessel_in`(fldxqMZLHT, "Full Vessel In")；`PortOfDischarge` 已从 text 改为 link（Bitable 侧用户已改）
- **container_data.py** — `port_of_discharge` 从 `str | None` 改为 `list[str] | None`（link → MD-Base Node）；新增 `full_vessel_in: list[str] | None`（link → Op-Vessel Schedule）
- **container_sync.py** — `fetch_provider_data` 新增 link 解析：
  - `PortOfDischarge` 文本 → `LinkResolver` + `LinkConfig(table=T.md_base_node)` 解析为 MD-Base Node record_id
  - `Full Vessel In` 文本 → `_build_vessel_schedule_map()` 构建 `(Vessel Name|Voyage|Base Node) → record_id` 映射，按三字段精确匹配 Op-Vessel Schedule
  - Vessel Schedule 的 Base Node 是 link 字段，用 `extract_link_record_ids` + `BaseNodeRepository.list(in_list)` + `to_map` 解析为文本
- **构造函数注入** `VesselScheduleRepository` + `BaseNodeRepository`

**E2E 验证**: Container sync all=17/17, 0 errors

### [2026-04-23] 多选字段修复 + build_select_field_map 提取 + First Free / Last Free
**做了什么**:
- **`_record_to_dict` 保留原始 list** — 多选字段（纯字符串 list）不再拼成逗号字符串，直接返回 `list[str]`，从源头解决多选值含逗号（如 `"DP WORLD, VI, WEST SWANSON"`）被错误拆分的问题
- **新增 `extract_select_text()`** — `core/lark_bitable_value.py`，统一 `list[str]`/`str`/`None` → 字符串转换，供 `.strip().upper()` 场景使用
- **新增 `build_select_field_map()`** — `service/sync/utils/link_resolver.py`，通用「A表文本值 → B表多选字段匹配 → record_id」工具函数，自动处理 `list[str]` 和旧格式 `str`
- **container_sync.py** — 删除 3 个 `_build_xxx_map` 方法，替换为一行 `await build_select_field_map(repo, field)` 调用
- **vessel_sync.py** — 删除 `_build_terminal_full_name_map`，替换为 `build_select_field_map`
- **修复 5 个 VBS 文件 + Clear sync** — `(r.get("Terminal Full Name") or "").strip()` → `extract_select_text(r.get("Terminal Full Name")).strip()`
- **修复 3 个 constants 文件** — `_fv()` 函数适配 `list[str]` 类型
- **修复 `relation_loader.load_terminal_mapping`** — 多选 TFN 值逐个注册到映射
- **container_data.py** — `ImportAvailability → First Free`, `StorageStartDate → Last Free` 双字段同步写入

**修复验证**:
- VICT VIC: Terminal Full Name 双值多选 → Terminal Name 正确链接 ✅
- DP WORLD, VI, WEST SWANSON: 含逗号的多选值 → Terminal Name 正确链接 ✅
- PATRICK, VI, EAST SWANSON: 含逗号的多选值 → Terminal Name 正确链接 ✅

**E2E 验证**: vessel 9/9, container 17/17, clear 15/15, vbs 8/8, 0 errors

### [2026-04-23] Terminal Name link + FULL Vessel Name link + ETA datetime
**做了什么**:
- **lark_tables.py** — Op-Import 新增 `terminal_name`(fld6cJPAxN, "Terminal Name", link → MD-Terminal)、`eta`(fldvsf9koU, "ETA", datetime)
- **container_data.py** — 新增 `terminal_name: list[str] | None`（link → MD-Terminal）、`eta: int | None`（datetime 毫秒时间戳）、`full_vessel_name: list[str] | None`（link → Op-Vessel Schedule，与 full_vessel_in 相同值）
- **container_sync.py**:
  - 新增 `_build_terminal_full_name_map()` — 从 MD-Terminal 读取 Terminal Full Name（多选字段拆分后逐个注册），构建 `TFN → record_id` 映射
  - `_parse` 新增 `terminal_name` 解析（TFN 文本 → MD-Terminal record_id）
  - `full_vessel_name = full_vessel_in`（两个 link 字段指向同一 Op-Vessel Schedule 记录）
  - `eta = estimated_arrival`（同一时间戳写入两个 datetime 字段）
  - 构造函数注入 `TerminalRepository`

**验证**:
- Terminal Name link 正确指向 MD-Terminal（DP WORLD NS PORT BOTANY → recvg0Y7DBJs4k = "Dp World NSW"）✅
- FULL Vessel Name link 正确指向 Op-Vessel Schedule ✅
- ETA datetime 正确写入 ✅

**E2E 验证**: 4 个 Sync 模块全部通过 (vessel 9/9, container 17/17, clear 15/15, vbs 9/9, 0 errors)

### [2026-04-23] Commodity link + Container Weight 重写
**做了什么**:
- **lark_tables.py** — 新增 `dt_commodity` 表定义（tblKYHYftSjvnKq8），字段：Commodity(文本) + CommodityIn(多选)
- **repository/dt_commodity.py** — 新建 `DTCommodityRepository`
- **container_data.py** — `commodity: list[str] | None`（link → DT-Commodity），`container_weight: float | None`
- **container_sync.py** — `_build_commodity_in_to_commodity_map()` 构建 `CommodityIn → record_id` 映射；`container_weight = gross_weight` 同步写入

**E2E 验证**: Container sync all=17/17, 0 errors

### [2026-04-23] Container Type link — ISO → DT-Container Type 映射
**做了什么**:
- **lark_tables.py** — 新增 `dt_container_type` 表定义（tblvJAVKWL3OMoNV），字段：ISO(多选) + Container Type(文本)
- **repository/dt_container_type.py** — 新建 `DTContainerTypeRepository`
- **container_data.py** — `container_type` 从 `str | None` 改为 `list[str] | None`（link → DT-Container Type）
- **container_sync.py** — `_build_iso_to_container_type_map()` 构建 `ISO → record_id` 映射，ISO 多选字段拆分后逐个注册；构造函数注入 `DTContainerTypeRepository`

**映射结果**: ISO 2200/2210/22G0 → 20GP, ISO 4500/4511/45G0 → 40HC, 其余 ISO 无匹配留空

**E2E 验证**: Container sync all=17/17, 0 errors
