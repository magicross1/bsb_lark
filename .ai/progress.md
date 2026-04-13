# Progress

> 项目开发进度日志。AI 从这里知道"做到哪了"。

## Current Sprint / Phase
架构审计 + 铁律融入完成，待集成测试

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

---

*最后更新: 2026-04-13*
