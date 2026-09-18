"""Same real, already-proven fix reorder-app's chapter 7 and
pkgintel-app's chapter 15 both needed: a bare `uvicorn triage_app.api:app`
CLI invocation resets the event loop policy via its own `asyncio.run()`,
regardless of what `api.py`'s own module-level fix already set. Building
the loop directly and handing `uvicorn.Server.serve()` to it bypasses
that reset entirely.
"""

import asyncio
import sys

import uvicorn

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    config = uvicorn.Config("triage_app.api:app", host="127.0.0.1", port=8020)
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())
