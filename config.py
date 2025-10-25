import json
from os import getenv

from dotenv import load_dotenv

load_dotenv()

TOKEN: str = getenv('TOKEN')
TEST_TOKEN: str = getenv('TEST_TOKEN')

DEFAULT_WEBHOOK: str = getenv('WEBHOOK')

DEFAULT_PREFIX: str = getenv('DEFAULT_PREFIX')

OWNER_IDS: list[int] = json.loads(getenv('OWNER_IDS'))

DATABASE_CRED: str = getenv('POSTGRES_URI')
