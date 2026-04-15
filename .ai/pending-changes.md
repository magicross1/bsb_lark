# Pending Changes

> 拉取协作者代码后需要重新应用的改动清单。
> 这些改动基于当前结构实现，拉取后需根据新结构适配。

---

## 1. Bug 修复 (shared/address.py)

### #4 HIGH — `_number_ranges_overlap` 修复
**问题**: `range(start, end+1, step=2)` 只生成奇/偶数，"10-18" vs "15-21" 判为不重叠
**修复**: 改用区间交集判断
```python
def _number_ranges_overlap(a: str, b: str) -> bool:
    def parse_range(s: str) -> range:
        s = re.sub(r"[A-Za-z]", "", s)
        if "-" in s:
            parts = s.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                return range(start, end + 1)
        if s.isdigit():
            n = int(s)
            return range(n, n + 1)
        return range(0)

    ra, rb = parse_range(a), parse_range(b)
    if not ra or not rb:
        return False
    latest_start = max(ra.start, rb.start)
    earliest_end = min(ra.stop, rb.stop)
    return latest_start < earliest_end
```

### #12 MEDIUM — `normalize_address` 双空格问题
**问题**: 删除 state/postcode 后残留双空格，导致无逗号地址的 suburb 检测失败
**修复**: 在 `normalize_address()` 中，删除 state/postcode 后、提取 unit 之前，加一行：
```python
s = s.strip().rstrip(",").strip()
s = re.sub(r"\s{2,}", " ", s)  # <-- 新增
```

---

## 2. 邮编匹配修复 (cartage/service.py)

### #5 MEDIUM — postcode 子串匹配误报
**问题**: `parsed.postcode in address_str` 是子串匹配，"2164" 会匹配 "12164 Something St"
**修复**: 改用词边界正则
```python
import re  # 在 service.py 顶部

# 在 _get_address_candidates 方法中：
if parsed.postcode:
    pc_pattern = re.compile(rf"\b{re.escape(parsed.postcode)}\b")
    postcode_candidates = [
        a for a in all_addresses if pc_pattern.search(str(a.get("Address", a.get("address", ""))))
    ]
    if postcode_candidates:
        filtered = postcode_candidates
```

---

## 3. Consingee 名字相似度匹配 (cartage/service.py)

### 新增功能 — 同地址多 Consingee 时按名字相似度选最佳
**问题**: `_find_consingee_by_address` 只返回第一个匹配地址的 consingee，忽略 `consingee_name`
**修复**:

3a. 新增辅助函数（在 `CartageService` 类外面）：
```python
_NOISE_WORDS_RE = re.compile(
    r"\b(?:CO\.?|PTY\.?|LTD\.?|PTD\.?|INC\.?|PTE\.?|LLC\.?|CORP\.?|LIMITED|COMPANY|INTERNATIONAL|TRADING|INDUSTRIES|GROUP|HOLDINGS|AUSTRALIA|AUST|AUS)\b",
    re.IGNORECASE,
)

def _normalize_name(name: str) -> str:
    s = name.upper()
    s = _NOISE_WORDS_RE.sub("", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return s.strip()

def _name_similarity(a: str, b: str) -> float:
    tokens_a = set(_normalize_name(a).split())
    tokens_b = set(_normalize_name(b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    return overlap / max(len(tokens_a), len(tokens_b))
```

3b. 修改 `_find_consingee_by_address` 签名和逻辑：
```python
async def _find_consingee_by_address(
    self,
    warehouse_address_id: str,
    consingee_name_hint: str | None = None,  # 新增参数
) -> dict[str, Any] | None:
    all_consingees = await self._load_consingees()
    matches = [
        c for c in all_consingees
        if self._link_contains_id(
            c.get("MD-Warehouse Address", c.get("warehouse_address")), warehouse_address_id
        )
    ]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    if not consingee_name_hint:
        return matches[0]

    scored = [
        (c, _name_similarity(consingee_name_hint, _extract_text(c.get("Name", c.get("name"))) or ""))
        for c in matches
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    if scored[0][1] > 0:
        logger.info(
            "Consingee name match: %r → %r (score=%.2f, %d candidates)",
            consingee_name_hint,
            _extract_text(scored[0][0].get("Name", scored[0][0].get("name"))),
            scored[0][1],
            len(matches),
        )
    return scored[0][0]
```

3c. 修改 `_match_deliver_address` 签名，透传 consingee_name_hint：
```python
async def _match_deliver_address(
    self,
    address_str: str,
    deliver_type: str | None = None,
    consingee_name_hint: str | None = None,  # 新增参数
) -> tuple[AddressMatch | None, bool]:
```
在方法内调用处改为：
```python
consingee = await self._find_consingee_by_address(best_record_id, consingee_name_hint)
```

3d. 在 `_enrich_parse_result` 中透传：
```python
if parse_result.deliver_address:
    address_match, address_needs_review = await self._match_deliver_address(
        parse_result.deliver_address,
        parse_result.deliver_type,
        parse_result.consingee_name,  # 新增
    )
```

**效果示例**:
- AI 解析出 `OTTOVO TRADING CO., PTY LTD` → 去噪声剩 `OTTOVO`
- Bitable `APLUS MATERIALS` → `APLUS MATERIALS` (score=0.0)
- Bitable `OTTOVO INTERNATIONAL` → `OTTOVO` (score=1.0) ← 正确匹配

---

## 4. Prompt 拆分到 prompts.py

### 架构改动 — prompt 和 parser 逻辑分离
**原则**: 每个 parser 模块的 AI 提示词从 `parser.py` 拆到独立 `prompts.py`

4a. 新建 `app/modules/operations/edo/prompts.py`：
```python
from __future__ import annotations

EDO_SYSTEM_PROMPT = """..."""  # 原 edo/parser.py 中的 EDO_SYSTEM_PROMPT 完整内容

EDO_USER_HINT = "Parse this EDO document. Extract ALL containers with their respective fields."
```

4b. 新建 `app/modules/operations/cartage/prompts.py`：
```python
from __future__ import annotations
from app.modules.operations.cartage.schemas import CartageDictValues

CARTAGE_USER_HINT = (
    "Parse this Cartage / Time Slot Request document."
    " Determine if it is Import or Export, then extract all containers or bookings."
)

def build_cartage_system_prompt(dv: CartageDictValues) -> str:
    return f"""..."""  # 原 cartage/parser.py 中 _build_cartage_prompt() 的完整内容
```

4c. 修改 `edo/parser.py`：
- 删除内联的 `EDO_SYSTEM_PROMPT`
- 改为 `from app.modules.operations.edo.prompts import EDO_SYSTEM_PROMPT, EDO_USER_HINT`
- `user_hint = EDO_USER_HINT`（原来是硬编码字符串）

4d. 修改 `cartage/parser.py`：
- 删除内联的 `CARTAGE_USER_HINT` 和 `_build_cartage_prompt()`
- 改为 `from app.modules.operations.cartage.prompts import CARTAGE_USER_HINT, build_cartage_system_prompt`
- `system_prompt` property 改为 `return build_cartage_system_prompt(self._dict_values)`

4e. `pyproject.toml` 加 per-file-ignores：
```toml
[tool.ruff.lint.per-file-ignores]
"**/parser.py" = ["E501"]
"**/prompts.py" = ["E501"]  # 新增
"**/router.py" = ["B008"]
```

---

## 5. Router 临时文件泄漏修复

### #7 MEDIUM — copyfileobj 异常时 tmp_path 未赋值
**修复**: 两个 router (cartage + edo) 都改为：
```python
tmp_path = None
try:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    result = await _service.xxx(tmp_path, model=model)
    return ApiResponse.ok(data=result.model_dump())
finally:
    if tmp_path:
        Path(tmp_path).unlink(missing_ok=True)
```

---

## 6. 其他小修复

### #8 MEDIUM — _load_addresses 精简字段
`_load_addresses` 只拉 `["Address"]`，不拉 `["Address", "Location", "Detail"]`

### #10 MEDIUM — EDO router 支持 .txt/.text
`allowed` 集合新增 `.txt` / `.text`

### #16 LOW — _validate_choice 日志
`_validate_choice` 返回 None 时加 `logger.warning()`
```python
_logger.warning("AI returned unrecognized value %r not in %s", value, valid[:5])
```
需要在 parser.py 顶部加 `import logging` 和 `_logger = logging.getLogger(__name__)`

### middleware.py 死代码清理
- 删除 `from typing import Callable`（未使用）
- 删除 `except AppError` 下的 `body = {...}` 赋值（未使用）

### 7 个文件补 `from __future__ import annotations`
`main.py`, `config/settings.py`, `master_data/repository.py`, `master_data/service.py`, `master_data/router.py`, `master_data/schemas.py`, `shared/enums.py`

### test_edo_parse.py 修复
- 删除 `from app.config.ai import get_ai_client`（未使用）
- `parser.parse_pdf()` → `parser.parse()`

---

*创建于: 2026-04-13*
