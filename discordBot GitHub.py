from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

import aiohttp
import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("live-notifier")

# Config

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DISCORD_CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])

TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")

# Twitch Streamers
# Insert streamers into the "", followed by a comma 
TWITCH_STREAMERS = [
    "alexmeisteer", # thats me xD
    "",
]

# Messagetemplate
# Feel free to customize it however you want
MESSAGE_TEMPLATE = (
    "**{name}** is streaming!\n"
    "{title}\n"
    "They are streaming: **{game}**\n"
    "Link to the stream: {url}\n"
)

# Poll-Intervall
POLL_SECONDS = 60

# Twitch Client
@dataclass
class TwitchStreamInfo:
    user_name: str
    title: str
    game_name: str
    url: str

class TwitchHelix:
    def __init__(self, session: aiohttp.ClientSession, client_id: str, client_secret: str):
        self.session = session
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def _fetch_app_token(self) -> None:
        # Client Credentials Grant (App Access Token)
        token_url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        async with self.session.post(token_url, params=params) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(f"Twitch token error {resp.status}: {data}")

        self._access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 0))
        # 60 seconds buffer
        self._token_expires_at = time.time() + max(0, expires_in - 60)
        log.info("Fetched Twitch app token (expires in %ss).", expires_in)

    async def _ensure_token(self) -> str:
        if not self._access_token or time.time() >= self._token_expires_at:
            await self._fetch_app_token()
        return self._access_token

    async def get_live_stream(self, user_login: str) -> Optional[TwitchStreamInfo]:
        token = await self._ensure_token()
        url = "https://api.twitch.tv/helix/streams"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {token}",
        }
        
        params = {"user_login": user_login}

        async with self.session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(f"Twitch helix error {resp.status}: {data}")

        items = data.get("data", [])
        if not items:
            return None

        s0 = items[0]
        # Stream-URL is stable for login
        stream_url = f"https://twitch.tv/{user_login}"
        title = s0.get("title") or "Live"
        game_name = s0.get("game_name") or "Unknown"
        user_name = s0.get("user_name") or user_login

        return TwitchStreamInfo(
            user_name=user_name,
            title=title,
            game_name=game_name,
            url=stream_url,
        )

# Discord Bot
class LiveNotifierBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # Just sending message
        super().__init__(command_prefix="!", intents=intents)
        self._sent_online_message = False

        self.http_session: Optional[aiohttp.ClientSession] = None
        self.twitch: Optional[TwitchHelix] = None

        # From offline -> live, post message
        self._twitch_live_state: Dict[str, bool] = {}

    async def setup_hook(self) -> None:
        self.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

        if TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET:
            self.twitch = TwitchHelix(self.http_session, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)

        poll_live.start()

    async def close(self) -> None:
        poll_live.cancel()
        if self.http_session:
            await self.http_session.close()
        await super().close()


bot = LiveNotifierBot()


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user)

def format_message(name: str, url: str, title: str, game: str) -> str:
    return MESSAGE_TEMPLATE.format(name=name, url=url, title=title, game=game)


@tasks.loop(seconds=POLL_SECONDS)
async def poll_live():
    await bot.wait_until_ready()

    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(DISCORD_CHANNEL_ID)

    assert isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel, discord.GroupChannel))

    # Twitch
    if bot.twitch is not None:
        for login in TWITCH_STREAMERS:
            try:
                info = await bot.twitch.get_live_stream(login)
                is_live = info is not None
                was_live = bot._twitch_live_state.get(login, False)

                if is_live and not was_live:
                    msg = format_message(info.user_name, info.url, info.title, info.game_name)
                    await channel.send(msg)


                bot._twitch_live_state[login] = is_live

            except Exception as e:
                log.warning("Twitch check failed for %s: %s", login, e)


@poll_live.before_loop
async def before_poll_live():
    await bot.wait_until_ready()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)