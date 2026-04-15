# Progress

> 项目开发进度日志。AI 从这里知道"做到哪了"。

## Current Sprint / Phase
EDO 解析+匹配+写回完成，Cartage trigger 地址匹配验证通过

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
