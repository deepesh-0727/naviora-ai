"""Print missing or type-mismatched model columns in the public database schema."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.schema_diff import inspect_database  # noqa: E402


async def main() -> None:
    differences = await inspect_database()
    if not differences:
        print("No model/database column differences found.")
        return
    print("Model/database column differences:")
    for difference in differences:
        print(f"- {difference}")


if __name__ == "__main__":
    asyncio.run(main())
