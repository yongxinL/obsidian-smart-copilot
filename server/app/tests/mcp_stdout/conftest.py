# Deliberately empty — do NOT import from the main app/tests/conftest.py
# which sets up pytest-asyncio with session-scoped loop that corrupts
# the logging module for subprocess.run() children.