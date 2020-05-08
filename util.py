from discord import Member
from discord.ext.commands import check, Context, CheckFailure

from database import run_in_thread, db
from models.authorized_roles import AuthorizedRoles


def make_error(message) -> str:
    return f":x: Error: {message}"


async def check_access(member: Member) -> int:
    if member.id == 370876111992913922:
        return 3

    if member.guild_permissions.administrator:
        return 2

    roles = set(role.id for role in member.roles)
    for authorization in await run_in_thread(db.query, AuthorizedRoles, server=member.guild.id):
        if authorization.role in roles:
            return 1
    return 0


def permission_level(level: int):
    @check
    async def admin_only(ctx: Context):
        if await check_access(ctx.author) < level:
            raise CheckFailure("You are not allowed to use this command.")

        return True

    return admin_only


def calculate_edit_distance(a: str, b: str) -> int:
    dp = [[max(i, j) for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            dp[i][j] = min(dp[i - 1][j - 1] + (a[i - 1] != b[j - 1]), dp[i - 1][j] + 1, dp[i][j - 1] + 1,)
    return dp[len(a)][len(b)]
