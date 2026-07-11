import asyncio
import os
import sys

# Ensure the submodules can be imported correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline import VideoPipelineAsync

async def main():
    print("Initializing SRVS V4 Asynchronous Pipeline Test...")
    pipeline = VideoPipelineAsync()
    await pipeline.run_all()
    print("Test Completed Successfully.")

if __name__ == "__main__":
    asyncio.run(main())
