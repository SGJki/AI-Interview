"""
Database Initialization Script

Creates database tables and enables pgvector extension.
Run this script before starting the application for the first time.

Usage:
    uv run python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.db.database import get_database_manager
from src.db.models import Base


async def init_database():
    """Initialize database with tables and extensions"""
    print("Initializing database...")

    db = get_database_manager()

    try:
        # Enable pgvector extension
        print("Enabling pgvector extension...")
        async with db.engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("  ✓ pgvector extension enabled")

        # Create tables
        print("Creating database tables...")
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("  ✓ Tables created")

        # Verify tables
        print("\nVerifying tables...")
        async with db.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            for table in tables:
                print(f"  ✓ {table}")

        print("\nDatabase initialization complete!")
        return True

    except Exception as e:
        print(f"\nError initializing database: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)
