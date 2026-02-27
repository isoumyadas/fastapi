## URLs/Endpoints

- https://techwithdorian.net/about?video=123&page=2

  - https://techwithdorian.net -> Domain 
  - /about -> Path/Endpoint
  - ?video=123&page=2 -> Query Parameter

## Request & Response

- Request components
  - Type/Method
  - Path
  - Body
  - Headers

- Response Components
  - Status Code
  - Body
  - Headers

### Uvicorn => is a web server in python that allows us to serve our fast api application.

### uv run main.py  => To run the main.py file

## DB
1. Create a db.py file
2. Import all the dependencies
3. Set up DB_URL

=> Note, understand about db config and connection properly. (you can refer the SQLalchemy fastapi & the github starred repo)

### What is I/O?
- Any operation where your code `talks to something outside tye CPU`.
  - Database queries
  - HTTP API calls
  - Reading files from disk
  - Redis calls
  - Anything over a network

BLOCKING (requests library):
Request 1 → [===========WAITING===========] → Response
Request 2 →                                  [=========WAITING=========] → Response
Thread:      BUSY BUSY BUSY BUSY BUSY          BUSY BUSY BUSY BUSY BUSY

NON-BLOCKING (httpx async):
Request 1 → [await...]
Request 2 →           [await...]
Request 3 →                     [await...]
Thread:      FREE  FREE  FREE  FREE  FREE (handles all 3 nearly simultaneously)

### When to use `async def` in FastAPI?

Is your function doing I/O? (DB, HTTP, file, Redis)
├── YES
│   ├── Is the library you're using async? (asyncpg, httpx, aiofiles, aioredis)
│   │   ├── YES → use async def + await ✅
│   │   └── NO  → use def (regular) and FastAPI handles it in a thread ✅
│   
└── NO (just CPU work, calculations)
    └── use def (regular) ✅

### Running Blocking Code in Threads
#### Why This Is Needed

Event Loop (the brain):
  - Runs all your async code
  - Is SINGLE THREADED
  - If anything blocks it → EVERYTHING stops

Solution: Offload blocking work to a THREAD POOL
  - Thread pool = a set of worker threads
  - Blocking code runs THERE, not on event loop
  - Event loop stays free


- Method 1 : Fast API's Built-In (Just use def)
  - This automatically runs regular def endpoints in a thread pool

```python
@app.get("/sync-endpoint")
def sync_endpoint():
    # This runs in a separate thread automatically
    # Event loop is NOT blocked
    result = some_blocking_library_call()
    return result
```

- Method 2 : `run_in_executor` for async contexts
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

# A blocking function (imagine this is a legacy library)
def blocking_task(n: int):
    time.sleep(n)  # Simulates slow sync work
    return f"Done after {n}s"


# Custom thread pool (optional, can use default)
executor = ThreadPoolExecutor(max_workers=4)

@app.get("/with-blocking-task")
async def endpoint_with_blocking():
    loop = asyncio.get_event_loop()
    
    # run_in_executor → runs blocking_task in thread pool
    # await → waits without blocking the event loop
    result = await loop.run_in_executor(executor, blocking_task, 3)
    return {"result": result}
```
- Method 3 : Cleanest way `asyncio.to_thread`

```python

import asyncio

def cpu_heavy_or_blocking(data: str) -> str:
    time.sleep(2)  # blocking work
    return data.upper()


@app.get("/modern-way")
async def modern_endpoint():
    # Cleanest modern approach
    result = await asyncio.to_thread(cpu_heavy_or_blocking, "hello")
    return {"result": result}

```
- When to use what?
┌─────────────────────────────────────────────────────────┐
│ Situation                    │ Solution                  │
├─────────────────────────────────────────────────────────┤
│ Endpoint uses sync lib       │ Just use def              │
│ Async endpoint needs sync    │ asyncio.to_thread()       │
│ Need custom thread control   │ run_in_executor(executor) │
│ CPU-heavy work               │ ProcessPoolExecutor       │
└─────────────────────────────────────────────────────────┘

### What is connection pool?

- Instead of opening and closing a new database connection for every request, your app reuses a pool of already-open connections.

WITHOUT Pool:
  Request → Open DB Connection → Query → Close Connection
  Request → Open DB Connection → Query → Close Connection
  Request → Open DB Connection → Query → Close Connection
          ↑ Opening/closing connections is EXPENSIVE (50-100ms each time)

WITH Pool:
  At startup: Open 10 connections, keep them ready

  Request 1 → Borrow conn #1 → Query → Return conn #1
  Request 2 → Borrow conn #2 → Query → Return conn #2
  Request 3 → Borrow conn #1 (reused!) → Query → Return
              ↑ No open/close overhead. Fast!

- Pool Exhaustion - What Goes Wrong

    Pool size = 5 connections

    Request 1 → Takes conn #1 (pool: 4 left)
    Request 2 → Takes conn #2 (pool: 3 left)
    Request 3 → Takes conn #3 (pool: 2 left)
    Request 4 → Takes conn #4 (pool: 1 left)
    Request 5 → Takes conn #5 (pool: 0 left)
    Request 6 → ⏳ WAITING... pool is exhausted
    Request 7 → ⏳ WAITING...
    Request 8 → ⏳ WAITING...

    If requests 1-5 are slow (complex queries), requests 6-8 time out.
    Your API appears "down" even though the server is fine.

1. Connection Pool Setup
