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

---
*最后更新: 2026-04-10*
