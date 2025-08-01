import json
from os import getenv

from dotenv import load_dotenv

load_dotenv()

TOKEN: str = getenv('TOKEN')
TEST_TOKEN: str = getenv('TEST_TOKEN')

WEBHOOK: str = getenv('WEBHOOK')
SUGGESTIONS_WEBHOOK_TOKEN: str = getenv('SUGGESTION_WEBHOOK')

DATABASE_CRED: str = getenv('POSTGRES_URI')

DEFAULT_PREFIX: str = getenv('DEFAULT_PREFIX')

OWNER_IDS: list[int] = json.loads(getenv('OWNER_IDS'))

TOPGG: str = getenv('TOPGG')
