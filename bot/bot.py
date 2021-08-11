from typing import Iterable

import sentry_sdk
from discord import Intents, Message, Guild
from discord.ext.commands import Bot, Context, CommandError, CommandNotFound, UserInputError, CommandInvokeError

from PyDrocsid.cog import load_cogs
from PyDrocsid.command import reply, make_error
from PyDrocsid.database import db
from PyDrocsid.environment import TOKEN
from PyDrocsid.events import listener
from PyDrocsid.logger import get_logger
from PyDrocsid.prefix import get_prefix
from PyDrocsid.translations import t
from cogs.library.general.auto_reaction import AutoreactionCog
from cogs.custom import CustomBotInfoCog, CustomServerInfoCog
from cogs.library import *
from cogs.library.information.help.cog import send_help
from cogs.library.moderation.mod.cog import UserCommandError
from cogs.library.pubsub import send_alert

logger = get_logger(__name__)

t = t.g


async def fetch_prefix(_, msg: Message) -> Iterable[str]:
    prefix = [await get_prefix(), f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "]

    if msg.guild is None:
        prefix.append("")

    return prefix


bot = Bot(command_prefix=fetch_prefix, case_insensitive=True, intents=(Intents.all()))
bot.remove_command("help")


@listener
async def on_ready():
    logger.info(f"\033[1m\033[36mLogged in as {bot.user}\033[0m")


@bot.event
async def on_error(*_, **__):
    sentry_sdk.capture_exception()
    raise  # skipcq: PYL-E0704


@listener
async def on_command_error(ctx: Context, error: CommandError):
    if isinstance(error, CommandInvokeError):
        if not isinstance(error.original, PermissionError):
            await reply(ctx, embed=make_error(t.internal_error))
        raise error.original

    if isinstance(error, CommandNotFound) and ctx.guild is not None and ctx.prefix == await get_prefix():
        return
    if isinstance(error, UserInputError):
        await send_help(ctx, ctx.command)
    elif isinstance(error, UserCommandError):
        await reply(ctx, embed=make_error(str(error), error.user))
    else:
        await reply(ctx, embed=make_error(str(error)))


@listener
async def on_permission_error(guild: Guild, error: str):
    await send_alert(guild, error)


# fmt: off
load_cogs(
    bot,

    # Administration
    RolesCog(),
    PermissionsCog(),
    SettingsCog(),
    SudoCog(),

    # Moderation
    ModCog(),
    LoggingCog(),
    MessageCog(),
    MediaOnlyCog(),
    InvitesCog(),
    AutoClearCog(),
    AutoModCog(),
    AutoRoleCog(),
    RoleNotificationsCog(),
    VerificationCog(),
    SpamDetectionCog(),
    UserNoteCog(),

    # Information
    CustomBotInfoCog(),
    HeartbeatCog(),
    HelpCog(),
    CustomServerInfoCog(),
    UserInfoCog(),
    InactivityCog(),

    # Integrations
    AdventOfCodeCog(),
    DiscordpyDocumentationCog(),
    RedditCog(),
    RunCodeCog(),

    # General
    BeTheProfessionalCog(),
    CustomCommandsCog(),
    DiscordBotTokenDeleterCog(),
    PollsCog(team_roles=["team"]),
    ReactionPinCog(),
    ReactionRoleCog(),
    RemindMeCog(),
    UtilsCog(),
    VoiceChannelCog(team_roles=["team"]),
    AutoreactionCog(),
)
# fmt: on


def run():
    bot.loop.run_until_complete(db.create_tables())

    logger.debug("logging in")
    bot.run(TOKEN)
