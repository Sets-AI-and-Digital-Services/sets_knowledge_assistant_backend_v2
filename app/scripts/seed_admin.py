import asyncio
from datetime import datetime
from passlib.hash import bcrypt
from app.core.db import col_users

async def main():
    email = "admin@example.com"
    password = "admin123"   # change this
    existing = await col_users().find_one({"email": email})
    if existing:
        print("Admin already exists")
        return
    await col_users().insert_one({
        "name": "Admin",
        "email": email,
        "password_hash": bcrypt.hash(password),
        "role": "admin",
        "created_at": datetime.utcnow(),
    })
    print(f"Admin created with email={email}, password={password}")

if __name__ == "__main__":
    asyncio.run(main())
