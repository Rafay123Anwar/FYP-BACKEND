import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "UPDATE profiles "
                "SET linkedin = CONCAT('https://', linkedin) "
                "WHERE linkedin IS NOT NULL "
                "  AND linkedin NOT LIKE 'http%' "
                "  AND (linkedin LIKE 'linkedin.com%' OR linkedin LIKE 'www.linkedin.com%');"
            )
        )
        await session.execute(
            text(
                "UPDATE profiles "
                "SET github = CONCAT('https://', github) "
                "WHERE github IS NOT NULL "
                "  AND github NOT LIKE 'http%' "
                "  AND (github LIKE 'github.com%' OR github LIKE 'www.github.com%');"
            )
        )
        await session.commit()
        print("Existing profile URLs sanitized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
