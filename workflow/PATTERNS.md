---
gmd: "0.1"
id: PATTERNS
title: "Code Patterns"
tags: [reference]
metadata:
  node_type: doc
---

# Code Patterns {#root}

Common patterns used throughout the codebase. Copy-paste these to avoid re-reading source files.

## Ground Rules {#ground-rules}

1. **No mocks in production code** — all `src/` code must be fully concrete. No stubs, no
   `NotImplementedError`, no placeholder logic. If it can't be real, it doesn't exist yet.
2. **Mocks only in tests** — `tests/` may mock external services (databases, APIs, hardware).
3. **Tech stack** — see `TECH_STACK_DECISIONS.md` for approved libraries and rationale.

## Testing Patterns {#testing-patterns}

### Pytest Async Test {#pytest-async-test}
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Pytest Fixture {#pytest-fixture}
```python
import pytest

@pytest.fixture
def sample_config():
    return {"key": "value", "enabled": True}
```

### FastAPI Test Client {#fastapi-test-client}
```python
from httpx import ASGITransport, AsyncClient

@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

## FastAPI Patterns {#fastapi-patterns}

### Dependency Injection {#dependency-injection}
```python
from fastapi import Depends
from typing import Annotated

async def get_db(request: Request) -> DatabasePool:
    return request.app.state.db_pool

DB = Annotated[DatabasePool, Depends(get_db)]

@app.get("/items")
async def list_items(db: DB):
    return await db.fetch_all("SELECT * FROM items")
```

### Error Responses {#error-responses}
```python
from fastapi import HTTPException

def not_found(resource: str, id: str):
    raise HTTPException(
        status_code=404,
        detail={"error": "not_found", "resource": resource, "id": id}
    )
```

## Async Patterns {#async-patterns}

### Retry with Backoff {#retry-with-backoff}
```python
import asyncio
from functools import wraps

def retry_async(max_attempts: int = 3, backoff: float = 1.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(backoff * (2 ** attempt))
            raise last_error
        return wrapper
    return decorator
```

---

*Update this file when new patterns emerge. Keep examples minimal and copy-paste ready.*
