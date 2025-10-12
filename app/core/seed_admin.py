
import asyncio
from app.core.db import get_database
from app.core.security import hash_password

async def seed_admin():
    db = await get_database()
    users = db["users"]

    # ✅ Only create if no admin exists
    existing = await users.find_one({"email": "admin@example.com"})
    if existing:
        print("✅ Admin already exists, skipping seeding.")
        return

    admin = {
        "email": "admin@example.com",
        "password_hash": hash_password("admin123"),
        "role": "admin",
        "created_at": "auto",
    }

    await users.insert_one(admin)
    print("✅ Admin user created successfully.")

if __name__ == "__main__":
    asyncio.run(seed_admin())
