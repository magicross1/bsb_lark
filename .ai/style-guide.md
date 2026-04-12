# Style Guide

> 项目的视觉和代码风格指南。AI 会遵守这些约定保持一致性。

## Code Conventions

### Naming
- Files: kebab-case (`lark-client.ts`, `bitable-service.ts`)
- Classes: PascalCase (`LarkClient`, `BitableService`)
- Functions/Methods: camelCase (`getRecord`, `updateTable`)
- Constants: UPPER_SNAKE_CASE (`MAX_PAGE_SIZE`, `DEFAULT_TIMEOUT`)
- Types/Interfaces: PascalCase with descriptive suffix (`LarkConfig`, `BitableRecord`)

### Project Structure Conventions
- One service per file, filename matches service name
- Controllers in `api/`, business logic in `services/`
- Shared types in `types/`, domain types alongside services
- Config in `config/`, constants in `constants/`

### Error Handling
- Custom error classes extending base `AppError`
- Always include HTTP status code in error responses
- Log errors with context (function name, params, correlation ID)
- Never expose internal errors to API consumers

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
| Named exports | Default exports |
| `interface` for objects | `type` for simple objects |
| Early returns | Deep nesting |
| Descriptive names | Abbreviations |
| Validate inputs with zod | Trust external input |
| Log with context | Console.log raw data |
| Rate limit API calls | Spam Lark endpoints |

---
*最后更新: 2026-04-10*
