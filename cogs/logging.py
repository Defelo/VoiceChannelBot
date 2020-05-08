from datetime import datetime
from typing import Optional

from discord import (
    TextChannel,
    Guild,
    Message,
    Embed,
    RawMessageDeleteEvent,
)
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread
from models.settings import Settings
from translations import translations
from util import permission_level, calculate_edit_distance


def add_field(embed: Embed, name: str, text: str):
    first = True
    while text:
        embed.add_field(name=["\ufeff", name][first], value=text[:1024], inline=False)
        text = text[1024:]
        first = False


class LoggingCog(Cog, name="Logging"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_logging_channel(self, event: str) -> Optional[TextChannel]:
        channel_id = await run_in_thread(Settings.get, int, "logging_" + event, -1)
        return self.bot.get_channel(channel_id) if channel_id != -1 else None

    async def on_message_edit(self, before: Message, after: Message) -> bool:
        edit_channel: Optional[TextChannel] = await self.get_logging_channel("edit")
        mindiff: int = await run_in_thread(Settings.get, int, "logging_edit_mindiff", 1)
        if edit_channel is None or calculate_edit_distance(before.content, after.content) < mindiff:
            return True

        embed = Embed(title=translations.message_edited, color=0xFFFF00, timestamp=datetime.utcnow())
        embed.add_field(name=translations.channel, value=before.channel.mention)
        embed.add_field(name=translations.author_title, value=before.author.mention)
        embed.add_field(name=translations.url, value=before.jump_url, inline=False)
        add_field(embed, translations.old_content, before.content)
        add_field(embed, translations.new_content, after.content)
        await edit_channel.send(embed=embed)

        return True

    async def on_raw_message_edit(self, channel: TextChannel, message: Optional[Message]) -> bool:
        edit_channel: Optional[TextChannel] = await self.get_logging_channel("edit")
        if edit_channel is None:
            return True

        embed = Embed(title=translations.message_edited, color=0xFFFF00, timestamp=datetime.utcnow())
        embed.add_field(name=translations.channel, value=channel.mention)
        if message is not None:
            embed.add_field(name=translations.author_title, value=message.author.mention)
            embed.add_field(name=translations.url, value=message.jump_url, inline=False)
            add_field(embed, translations.new_content, message.content)
        await edit_channel.send(embed=embed)

        return True

    async def on_message_delete(self, message: Message) -> bool:
        delete_channel: Optional[TextChannel] = await self.get_logging_channel("delete")
        if delete_channel is None:
            return True

        embed = Embed(title=translations.message_deleted, color=0xFF0000, timestamp=(datetime.utcnow()))
        embed.add_field(name=translations.channel, value=message.channel.mention)
        embed.add_field(name=translations.author_title, value=message.author.mention)
        add_field(embed, translations.old_content, message.content)
        if message.attachments:
            out = []
            for attachment in message.attachments:
                size = attachment.size
                for unit in "BKMG":
                    if size < 1000:
                        break
                    size /= 1000
                out.append(f"{attachment.filename} ({size:.1f} {unit})")
            embed.add_field(name=translations.attachments, value="\n".join(out), inline=False)
        await delete_channel.send(embed=embed)

        return True

    async def on_raw_message_delete(self, event: RawMessageDeleteEvent) -> bool:
        delete_channel: Optional[TextChannel] = await self.get_logging_channel("delete")
        if delete_channel is None:
            return True

        embed = Embed(title=translations.message_deleted, color=0xFF0000, timestamp=datetime.utcnow())
        channel: Optional[TextChannel] = self.bot.get_channel(event.channel_id)
        if channel is not None:
            embed.add_field(name=translations.channel, value=channel.mention)
            embed.add_field(name=translations.message_id, value=event.message_id, inline=False)
        await delete_channel.send(embed=embed)

        return True

    @commands.group(name="logging", aliases=["log"])
    @permission_level(1)
    @guild_only()
    async def logging(self, ctx: Context):
        """
        view and change logging settings
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                await ctx.send_help(self.logging)
            return

        guild: Guild = ctx.guild
        edit_id = await run_in_thread(Settings.get, int, "logging_edit", -1)
        delete_id = await run_in_thread(Settings.get, int, "logging_delete", -1)
        changelog_id = await run_in_thread(Settings.get, int, "logging_changelog", -1)
        edit_channel: Optional[TextChannel] = guild.get_channel(edit_id) if edit_id != -1 else None
        delete_channel: Optional[TextChannel] = guild.get_channel(delete_id) if delete_id != -1 else None
        changelog_channel: Optional[TextChannel] = guild.get_channel(changelog_id) if changelog_id != -1 else None
        out = [translations.logging_channels_header]
        if edit_channel is not None:
            mindiff: int = await run_in_thread(Settings.get, int, "logging_edit_mindiff", 1)
            out.append(" - " + translations.f_msg_edit_on(edit_channel.mention, mindiff))
        else:
            out.append(" - " + translations.msg_edit_off)
        if delete_channel is not None:
            out.append(" - " + translations.f_msg_delete_on(delete_channel.mention))
        else:
            out.append(" - " + translations.msg_delete_off)
        if changelog_channel is not None:
            out.append(" - " + translations.f_changelog_on(changelog_channel.mention))
        else:
            out.append(" - " + translations.changelog_off)
        await ctx.send("\n".join(out))

    @logging.group(name="edit", aliases=["e"])
    async def edit(self, ctx: Context):
        """
        change settings for edit event logging
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.edit)

    @edit.command(name="mindiff", aliases=["md"])
    async def edit_mindiff(self, ctx: Context, mindiff: int):
        """
        change the minimum difference between the old and new content of the message to be logged
        """

        if mindiff <= 0:
            raise CommandError(translations.min_diff_gt_zero)

        await run_in_thread(Settings.set, int, "logging_edit_mindiff", mindiff)
        await ctx.send(translations.f_edit_mindiff_updated(mindiff))

    @edit.command(name="channel", aliases=["ch", "c"])
    async def edit_channel(self, ctx: Context, channel: TextChannel):
        """
        change logging channel for edit events
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.log_not_changed_no_permissions)

        await run_in_thread(Settings.set, int, "logging_edit", channel.id)
        await ctx.send(translations.f_log_edit_updated(channel.mention))

    @edit.command(name="disable", aliases=["d"])
    async def edit_disable(self, ctx: Context):
        """
        disable edit event logging
        """

        await run_in_thread(Settings.set, int, "logging_edit", -1)
        await ctx.send(translations.log_edit_disabled)

    @logging.group(name="delete", aliases=["d"])
    async def delete(self, ctx: Context):
        """
        change settings for delete event logging
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.delete)

    @delete.command(name="channel", aliases=["ch", "c"])
    async def delete_channel(self, ctx: Context, channel: TextChannel):
        """
        change logging channel for delete events
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.log_not_changed_no_permissions)

        await run_in_thread(Settings.set, int, "logging_delete", channel.id)
        await ctx.send(translations.f_log_delete_updated(channel.mention))

    @delete.command(name="disable", aliases=["d"])
    async def delete_disable(self, ctx: Context):
        """
        disable delete event logging
        """

        await run_in_thread(Settings.set, int, "logging_delete", -1)
        await ctx.send(translations.log_delete_disabled)

    @logging.group(name="changelog", aliases=["cl", "c", "change"])
    async def changelog(self, ctx: Context):
        """
        change settings for internal changelog
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.changelog)

    @changelog.command(name="channel", aliases=["ch", "c"])
    async def changelog_channel(self, ctx: Context, channel: TextChannel):
        """
        change changelog channel
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.log_not_changed_no_permissions)

        await run_in_thread(Settings.set, int, "logging_changelog", channel.id)
        await ctx.send(translations.f_log_changelog_updated(channel.mention))

    @changelog.command(name="disable", aliases=["d"])
    async def changelog_disable(self, ctx: Context):
        """
        disable changelog
        """

        await run_in_thread(Settings.set, int, "logging_changelog", -1)
        await ctx.send(translations.log_changelog_disabled)
