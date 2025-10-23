"""CLI tool for one-off ingestion"""

import asyncio
import argparse
import logging
from pathlib import Path

from app.ingestion.worker import IngestionWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main CLI function"""
    
    parser = argparse.ArgumentParser(description="Ingest log files")
    parser.add_argument("--directory", "-d", help="Directory containing log files")
    parser.add_argument("--file", "-f", help="Single file to ingest")
    parser.add_argument("--batch-size", "-b", type=int, default=1000, help="Batch size")
    
    args = parser.parse_args()
    
    worker = IngestionWorker()
    worker.batch_size = args.batch_size
    
    if args.file:
        # Ingest single file
        await worker.ingest_file(args.file, incremental=False)
    
    elif args.directory:
        # Ingest all files in directory
        directory = Path(args.directory)
        
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return
        
        files = list(directory.rglob("*.log")) + list(directory.rglob("*.txt"))
        logger.info(f"Found {len(files)} log files")
        
        for file_path in files:
            await worker.ingest_file(str(file_path), incremental=False)
    
    else:
        logger.error("Must specify --directory or --file")
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
