# Progress

> 项目开发进度日志。AI 从这里知道"做到哪了"。

## Current Sprint / Phase
EDO AI 解析已完成，准备接入 API 端点和更多文档类型

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

---
*最后更新: 2026-04-10*
