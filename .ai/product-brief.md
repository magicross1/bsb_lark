# Product Brief

> AI 每次新对话都会读取此文件，这是项目的"灵魂文档"。

## 项目名称
BSB Lark

## 一句话描述
基于 Lark Open API 的后端服务，用于管理和操作飞书多维表格（Bitable）及其他 Lark 资源

## 目标用户
BSB 团队内部成员，需要通过程序化管理飞书多维表格数据

## 核心问题
手动操作飞书多维表格效率低、易出错，需要通过 API 自动化数据管理和业务流程

## 核心功能
1. 飞书多维表格（Bitable）数据读写操作
2. Lark 事件订阅与自动响应
3. 数据同步与转换
4. 权限管理与审批流程集成
5. 定时任务与自动化工作流

## 设计调性
简洁、可靠、高效的后端服务，注重错误处理和日志记录

## 技术约束
- 必须使用 Lark 官方 SDK (@larksuiteoapi/node-sdk)
- 遵守 Lark API 调用频率限制
- 所有敏感信息通过环境变量管理
- Node.js >= 20

## 参考产品/设计
- Lark Open Platform: https://open.larksuite.com
- Lark Bitable API: https://open.larksuite.com/document/ukTMukTMukTM/uUDN04yM1QjL2EDN

---
*最后更新: 2026-04-10*
