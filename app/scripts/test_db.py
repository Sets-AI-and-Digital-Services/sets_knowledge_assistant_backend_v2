import asyncio
from app.core.db import get_db

async def main():
    db = get_db()
    print("Connected DB:", db.name)
    print("Collections:", await db.list_collection_names())

if __name__ == "__main__":
    asyncio.run(main())
