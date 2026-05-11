from pathlib import Path
from tortoise import Tortoise


async def init_db():
    root_dir = Path(__file__).parent.parent
    db_path = root_dir / "kiuf_bot.db"

    await Tortoise.init(
        db_url=f"sqlite:///{db_path.absolute()}",
        modules={"models": ["models.user", "models.schedule"]},
    )
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()
