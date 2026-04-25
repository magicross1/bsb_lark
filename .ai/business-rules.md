# Business Rules

> 业务规则与数据模型。AI 从这里理解"业务怎么跑的"。

## 核心业务域

### 1. Cartage（短驳委托）— AI 自动录入
- Cartage Advise 附件 → AI 解析 → 地址匹配 → 写回 Bitable
- 进口：1 Container = 1 Op-Cartage + 1 Op-Import（1:1 关系）
- 出口：release_qty > 1 时展开为多条，每条独立 Op-Cartage + Op-Export
- 地址匹配三步：normalize → 粗筛(postcode/street) → 评分(阈值 0.6/0.8)
- Consingee 匹配：同地址多候选时按名字相似度排序
- 幂等保护：Record Status 已有值的记录拒绝重复触发
- 重复 Container Number 跳过而非中止全部

### 2. EDO（Empty Delivery Order）— AI 解析写回
- 从 EDO PDF 提取 container_number / edo_pin / shipping_line / empty_park
- 按 Container Number 查找 Op-Import → UPDATE（不是 CREATE）
- Shipping Line 匹配：精确名 → Short Name fallback
- Empty Park 匹配：精确名 → 别名（分号分隔）→ 模糊名+地址

### 3. Sync（码头数据同步）— 爬虫定时同步
- **Vessel Schedule**：船期同步（ETA/ETD/Cutoff/Actual Arrival 等）
- **Container Status**：集装箱状态同步（Terminal/Vessel/Discharge/Gateout 等）
- **Clear Status**：清关状态同步（1-Stop customs + Hutchison Ports）
- **VBS**：码头可用性同步（5 个码头：DP World NSW/VIC, Patrick NSW/VIC, VICT VIC）

### 4. Master Data（主数据）— 9 个表 CRUD
- MD-Warehouse Address / Deliver Config / Consingee / Suburb
- MD-Shipping Line / Empty Park / Terminal / Base Node
- MD-Driver / Vehicle / Contractor / Sub Carrier 等

## 关键业务规则

### Cartage 写回规则
- Op-Cartage 的 Consingnee Name / Deliver Config 是 direct_link（record_id 已知，直接写入）
- Op-Import 的 FULL Vessel Name 是 link_lookup（Vessel Name + Voyage + Base Node 三字段联合查找，找不到则创建）
- link 字段 value 为空时跳过（不写 "TBC" 到 duplex link，否则 Bitable 报 1254074 错误）
- Trigger 模式：第一个非重复柜 UPDATE 原行，后续柜 CREATE 新行，Source Cartage 自关联

### Sync Provider 路由规则
- **Clear**：Terminal 空 → 1-Stop fallback Hutchison；HUTCHISON PORTS - PORT BOTANY → 只 Hutchison；其他 → 只 1-Stop
- **VBS**：按 Terminal Full Name 路由到 5 个 operation（dpWorldNSW/dpWorldVIC/patrickNSW/patrickVIC/victVIC）
- **Container**：PortOfDischarge → MD-Base Node link；Full Vessel In → Op-Vessel Schedule link（三字段匹配）
- Container Type 通过 ISO 码映射到 DT-Container Type（ISO 多选字段拆分匹配）
- Commodity 通过 CommodityIn 多选字段映射到 DT-Commodity

### Bitable 数据类型规则
- datetime 字段 → 毫秒时间戳 `int(dt.timestamp() * 1000)`
- number 字段 → `float()`
- link 字段写入格式 `["recXXX"]`
- 多选字段读回为 `list[str]`，含逗号的值不能用逗号拆分
- Bitable 不支持 `NOT` → 为空用 `=""`，非空用 `!=""`

### VBS Patrick VIC 特殊规则
- HTML 使用 `MovementDetailsForm` 前缀（其他码头用 `ContainerVesselDetailsForm`）
- ImportAvailability → ContainerAvailability
- StorageStartDate → ContainerStorageStart
- 日期含秒（`%d/%m/%Y %H:%M:%S`），需多格式尝试

## 数据模型关系

```
Op-Cartage ──1:1──→ Op-Import ──N:1──→ Op-Vessel Schedule ──N:1──→ MD-Base Node
     │                  │                                              │
     │                  ├──→ MD-Terminal                               │
     │                  ├──→ DT-Container Type (via ISO)              │
     │                  ├──→ DT-Commodity (via CommodityIn)           │
     │                  └──→ MD-Shipping Line (EDO 流程)              │
     │                                                                │
     ├──→ MD-Consingee ──→ MD-Warehouse Address                      │
     └──→ MD-Warehouse Deliver Config ──→ MD-Warehouse Address        │

Op-Cartage ──1:1──→ Op-Export ──N:1──→ Op-Vessel Schedule
```

---
*创建于: 2026-04-25*
