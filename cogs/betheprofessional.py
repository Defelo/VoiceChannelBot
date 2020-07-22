import string
from typing import List

from discord import Role, Guild, Member
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, UserInputError

from database import run_in_thread, db
from models.btp_role import BTPRole
from permission import Permission
from translations import translations
from util import permission_level, calculate_edit_distance, send_to_changelog


def split_topics(topics: str) -> List[str]:
    return [topic for topic in map(str.strip, topics.replace(";", ",").split(",")) if topic]


async def parse_topics(guild: Guild, topics: str, author: Member) -> List[Role]:
    roles: List[Role] = []
    all_topics: List[Role] = await list_topics(guild)
    for topic in split_topics(topics):
        for role in guild.roles:
            if role.name.lower() == topic.lower():
                if role in all_topics:
                    break
                if not role.managed and role >= guild.me.top_role:
                    raise CommandError(translations.f_youre_not_the_first_one(topic, author.mention))
        else:
            if all_topics:
                best_match = min(
                    [r.name for r in all_topics], key=lambda a: calculate_edit_distance(a.lower(), topic.lower())
                )
                raise CommandError(translations.f_topic_not_found_did_you_mean(topic, best_match))
            raise CommandError(translations.f_topic_not_found(topic))
        roles.append(role)
    return roles


async def list_topics(guild: Guild) -> List[Role]:
    roles: List[Role] = []
    for btp_role in await run_in_thread(db.all, BTPRole):
        if (role := guild.get_role(btp_role.role_id)) is None:
            await run_in_thread(db.delete, btp_role)
        else:
            roles.append(role)
    return roles


class BeTheProfessionalCog(Cog, name="Self Assignable Topic Roles"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="?")
    @guild_only()
    async def list_roles(self, ctx: Context):
        """
        list all registered topics
        """

        out = [role.name for role in await list_topics(ctx.guild)]
        out.sort(key=str.lower)
        if out:
            await ctx.send(translations.available_topics_header + "\n```\n" + ", ".join(out) + "```")
        else:
            await ctx.send(translations.no_topics_registered)

    @commands.command(name="+")
    @guild_only()
    async def add_role(self, ctx: Context, *, topics: str):
        """
        add one or more topics (comma separated) you are interested in
        """

        member: Member = ctx.author
        roles: List[Role] = [r for r in await parse_topics(ctx.guild, topics, ctx.author) if r not in member.roles]

        await member.add_roles(*roles)
        if len(roles) > 1:
            await ctx.send(translations.f_cnt_topics_added(len(roles)))
        elif len(roles) == 1:
            await ctx.send(translations.topic_added)
        else:
            await ctx.send(translations.no_topic_added)

    @commands.command(name="-")
    @guild_only()
    async def remove_roles(self, ctx: Context, *, topics: str):
        """
        remove one or more topics (use * to remove all topics)
        """

        member: Member = ctx.author
        if topics.strip() == "*":
            roles: List[Role] = await list_topics(ctx.guild)
        else:
            roles: List[Role] = await parse_topics(ctx.guild, topics, ctx.author)
        roles = [r for r in roles if r in member.roles]

        await member.remove_roles(*roles)
        if len(roles) > 1:
            await ctx.send(translations.f_cnt_topics_removed(len(roles)))
        elif len(roles) == 1:
            await ctx.send(translations.topic_removed)
        else:
            await ctx.send(translations.no_topic_removed)

    @commands.command(name="*")
    @permission_level(Permission.btp_manage)
    @guild_only()
    async def register_role(self, ctx: Context, *, topics: str):
        """
        register one or more new topics
        """

        guild: Guild = ctx.guild
        names = split_topics(topics)
        if not names:
            raise UserInputError

        valid_chars = set(string.ascii_letters + string.digits + " !#$%&'()+-./:<=>?[\\]^_`{|}~")
        to_be_created: List[str] = []
        roles: List[Role] = []
        for topic in names:
            if any(c not in valid_chars for c in topic):
                raise CommandError(translations.f_topic_invalid_chars(topic))

            for role in guild.roles:
                if role.name.lower() == topic.lower():
                    break
            else:
                to_be_created.append(topic)
                continue

            if await run_in_thread(db.get, BTPRole, role.id) is not None:
                raise CommandError(translations.f_topic_already_registered(topic))
            if role >= ctx.me.top_role:
                raise CommandError(translations.f_topic_not_registered_too_high(role, ctx.me.top_role))
            if role.managed:
                raise CommandError(translations.f_topic_not_registered_managed_role(role))
            roles.append(role)

        for name in to_be_created:
            roles.append(await guild.create_role(name=name, mentionable=True))

        for role in roles:
            await run_in_thread(BTPRole.create, role.id)

        if len(roles) > 1:
            await ctx.send(translations.f_cnt_topics_registered(len(roles)))
            await send_to_changelog(
                ctx.guild, translations.log_these_topics_registered + " " + ", ".join(f"`{r}`" for r in roles)
            )
        elif len(roles) == 1:
            await ctx.send(translations.topic_registered)
            await send_to_changelog(ctx.guild, translations.f_log_topic_registered(roles[0]))

    @commands.command(name="/")
    @permission_level(Permission.btp_manage)
    @guild_only()
    async def unregister_role(self, ctx: Context, *, topics: str):
        """
        delete one or more topics
        """

        guild: Guild = ctx.guild
        roles: List[Role] = []
        btp_roles: List[BTPRole] = []
        names = split_topics(topics)
        if not names:
            raise UserInputError

        for topic in names:
            for role in guild.roles:
                if role.name.lower() == topic.lower():
                    break
            else:
                raise CommandError(translations.f_topic_not_registered(topic))
            if (btp_role := await run_in_thread(db.get, BTPRole, role.id)) is None:
                raise CommandError(translations.f_topic_not_registered(topic))

            roles.append(role)
            btp_roles.append(btp_role)

        for role, btp_role in zip(roles, btp_roles):
            await run_in_thread(db.delete, btp_role)
            await role.delete()
        if len(roles) > 1:
            await ctx.send(translations.f_cnt_topics_unregistered(len(roles)))
            await send_to_changelog(
                ctx.guild, translations.log_these_topics_unregistered + " " + ", ".join(f"`{r}`" for r in roles)
            )
        elif len(roles) == 1:
            await ctx.send(translations.topic_unregistered)
            await send_to_changelog(ctx.guild, translations.f_log_topic_unregistered(roles[0]))
