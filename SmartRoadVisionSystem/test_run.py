import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pipeline import VideoPipelineAsync

async def main():
    pipeline = VideoPipelineAsync()
    await pipeline.run_all()

if __name__ == "__main__":
    asyncio.run(main())
