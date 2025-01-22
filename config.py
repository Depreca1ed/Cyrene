import json
from os import getenv

from dotenv import load_dotenv

load_dotenv()

TOKEN: str = getenv('TOKEN')

WAIFU_TOKEN: str = getenv('WAIFU_TOKEN')

WEBHOOK: str = getenv('WEBHOOK')

DATABASE_CRED: str = getenv('POSTGRES_URI')

DEFAULT_PREFIX: str = getenv('DEFAULT_PREFIX')

OWNERS_ID: list[int] = json.loads(getenv('OWNER_IDS'))

TOPGG: str = getenv("TOPGG")