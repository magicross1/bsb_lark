# Style Guide

> 项目的代码风格指南。AI 会遵守这些约定保持一致性。

## Code Conventions

### Naming
- Files: snake_case (`lark_repository.py`, `container_sync.py`)
- Classes: PascalCase (`BaseRepository`, `ContainerSyncService`)
- Functions/Methods: snake_case (`find_one`, `fetch_records`)；Repository 层用 camelCase (`findOne`, `createOne`, `updateOne`, `deleteOne`)
- Constants: UPPER_SNAKE_CASE (`MAX_PAGE_SIZE`, `_HUTCHISON_TERMINAL`)
- Private: 前缀 `_`（`_CONDITIONS`, `_batch_get`）

### Project Structure Conventions
- Repository 一表一文件，继承 `BaseRepository`，只绑定 `table_id`
- Service 一个业务域一个文件
- Controller 一个入口域一个文件，只做参数接收 + 调 service + 返回 response
- 公共工具放 `app/common/`，跨模块复用

### 查询/更新规范
- 所有 Bitable 查询必须用 `QueryWrapper` 链式构建
- 所有 Bitable 更新必须用 `UpdateWrapper` 链式构建
- `record_id` 查询走 `QueryWrapper().eq("record_id", rid)` — 内部自动路由到直连 API
- 集合操作用 `collection_utils`（`pluck` / `to_map` / `filter_by`）
- 断言用 `assert_utils`（`assert_in` / `assert_not_blank`）
- 时间戳转换用 `safe_ts`

### Error Handling
- Custom error classes extending base `AppError`
- Always include HTTP status code in error responses
- Log errors with context (function name, params)
- 断言失败抛 `ValueError`（由全局异常处理统一返回）

### API Response Format
```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

### Do / Don't
| Do | Don't |
|----|-------|
| `QueryWrapper` 链式查询 | 手动拼 filter dict |
| `UpdateWrapper` 链式更新 | 直接构造 `AppTableRecord` |
| `pluck(records, field)` | `[v for r in records if (v := r.get(field))]` |
| `to_map(records, key, value)` | `{r.get(k): r[v] for r in records if ...}` |
| `assert_in(k, d, msg)` | `if x is None: raise ValueError(...)` |
| `safe_ts(raw, key)` | 每个模块定义 `_ts()` |
| `from __future__ import annotations` | 裸类型引用 |
| Early returns | Deep nesting |
| Descriptive names | Abbreviations |
| 中文注释 | 英文注释 |

---
*最后更新: 2026-04-22*
