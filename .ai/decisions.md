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

---
*最后更新: 2026-04-15*
