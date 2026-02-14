import asyncio

from db.init_db import init_db


def main() -> None:
    asyncio.run(init_db())


if __name__ == "__main__":
    main()
