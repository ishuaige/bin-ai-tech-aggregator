"""seed 脚本命令行入口。"""

import asyncio

from db.session import SessionLocal
from db.seed import seed_db


async def run() -> None:
    """打开一个数据库会话并执行 seed 流程。"""
    async with SessionLocal() as session:
        await seed_db(session)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
