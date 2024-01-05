import json
from pathlib import Path
from .nodms import NoDMs

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot):
    cog = NoDMs(bot)
    await cog.initialize()
    await bot.add_cog(cog)
