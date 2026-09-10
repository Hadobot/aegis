import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.seed_data import seed_all


async def main():
    print("Starting Aegis seed process...")
    await seed_all()
    print("Seed process complete!")


if __name__ == "__main__":
    asyncio.run(main())
