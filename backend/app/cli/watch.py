"""CLI tool for watching directory"""

import asyncio
import argparse
import logging

from app.ingestion.watcher import FileWatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main CLI function"""
    
    parser = argparse.ArgumentParser(description="Watch directory for log files")
    parser.add_argument("--directory", "-d", help="Directory to watch")
    
    args = parser.parse_args()
    
    watcher = FileWatcher(directory=args.directory)
    await watcher.start()


if __name__ == "__main__":
    asyncio.run(main())
