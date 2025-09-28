# config.py

from environs import Env

env = Env()
env.read_env(path=".env") # read .env file if it exists

BOT_TOKEN = env.str("BOT_TOKEN")  # Bot token from @BotFather
ADMIN_ID = env.int("ADMIN_ID")    # Your Telegram ID
