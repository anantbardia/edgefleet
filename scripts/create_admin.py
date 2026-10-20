"""CLI tool to create or update an administrator account."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from app.core.security import get_password_hash
from app.database.session import async_session_factory, init_db
from app.models.user import User


async def create_or_update_admin(email: str, password: str, role: str = "admin"):
    await init_db()
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            print(f"User {email} already exists. Updating password and role to {role}...")
            user.hashed_password = get_password_hash(password)
            user.role = role
            user.is_active = True
        else:
            print(f"Creating new admin user {email}...")
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                role=role,
                is_active=True,
            )
            db.add(user)

        await db.commit()
        print(f"Success: User {email} has been saved with role '{role}'.")


def main():
    parser = argparse.ArgumentParser(description="Create an admin user for EdgeFleet.")
    parser.add_argument("--email", default="admin@edgefleet.local", help="Admin email address")
    parser.add_argument("--password", default="admin123", help="Admin password")
    parser.add_argument("--role", default="admin", choices=["admin", "operator", "viewer"], help="User role")

    args = parser.parse_args()
    asyncio.run(create_or_update_admin(args.email, args.password, args.role))


if __name__ == "__main__":
    main()
