"""Loads .env once for the whole test session, same pattern as reliable-agents-labs.

Chapter 21: triage-app's first real psycopg connection in this test
suite hits the same Windows `ProactorEventLoop` incompatibility
reorder-app's chapter 7 and pkgintel-app's chapter 15 already found,
confirmed live a third time. Setting the policy here, before
pytest-asyncio builds its own loop, is sufficient for pytest (a real
interactive server would still need its own `scripts/run_dev_server.py`,
chapter 22's concern, not this one).
"""

import asyncio
import sys

from dotenv import load_dotenv

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()
