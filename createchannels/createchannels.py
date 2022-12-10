"""
MIT License

Copyright (c) 2021-present Obi-Wan3

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import time
import typing
import asyncio

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import humanize_list


class CreateChannels(commands.Cog):
    """Create Text & Voice Channels Using Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14000605, force_registration=True)
        default_guild = {
            "voice": {
                "timeout": 60,
                "category": None,
                "maximum": 10,
                "roles": [],
                "userlimit": 3,
                "active": [],
                "role_req_msg": "You do not have any of the required roles!",
                "toggle": False
            },
            "text": {
                "category": None,
                "maximum": 10,
                "roles": [],
                "userlimit": 3,
                "active": [],
                "role_req_msg": "You do not have any of the required roles!",
                "toggle": False
            }
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener("on_voice_state_update")
    async def _voice_listener(self, member: discord.Member, before, after):
        if before.channel is not None and after.channel is None:
            vc = member.guild.get_channel(before.channel.id)
            if not vc.permissions_for(member.guild.me).manage_channels:
                return
            async with self.config.guild(member.guild).voice.active() as active:
                timeout = await self.config.guild(member.guild).voice.timeout()
                try:
                    ind = [a[0] for a in active].index(vc.id)
                    if not vc.members and time.time() > active[ind][2] + timeout:
                        await vc.delete(reason="CreateVoice: inactive VC")
                        active.pop(ind)
                except ValueError:
                    pass
        return

    @commands.Cog.listener("on_guild_channel_delete")
    async def _deletion_listener(self, channel):
        async with self.config.guild(channel.guild).voice.active() as active:
            try:
                ind = [a[0] for a in active].index(channel.id)
                active.pop(ind)
            except ValueError:
                pass
        async with self.config.guild(channel.guild).text.active() as active:
            try:
                ind = [a[0] for a in active].index(channel.id)
                active.pop(ind)
            except ValueError:
                pass

    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    @commands.command(name="createvoice")
    async def _createvoice(self, ctx: commands.Context, name: str, max_users: typing.Optional[int] = None):
        """Create a Voice Channel"""

        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send("I don't have the permissions to create a channel!")

        if not await self.config.guild(ctx.guild).voice.toggle(): return

        role_req = await self.config.guild(ctx.guild).voice.roles()
        if role_req and not bool(set(role_req) & {r.id for r in ctx.author.roles}):
            return await ctx.send(await self.config.guild(ctx.guild).voice.role_req_msg())

        active = await self.config.guild(ctx.guild).voice.active()
        active_author = [c for c in active if c[1] == ctx.author.id]
        maximum = await self.config.guild(ctx.guild).voice.maximum()

        for c in active_author:
            ch = self.bot.get_channel(c[0])
            if not ch.members:
                async with self.config.guild(ctx.guild).voice.active() as active:
                    try:
                        ind = [a[0] for a in active].index(ch.id)
                        active.pop(ind)
                    except ValueError:
                        pass
                await ch.delete(reason="CreateVoice: inactive VC")
                break

        userlimit = await self.config.guild(ctx.guild).voice.userlimit()
        if len(active) >= maximum:
            return await ctx.send(f"There are already {maximum} active VCs!")
        if len(active_author) >= userlimit:
            return await ctx.send(f"You already have {userlimit} active VCs!")

        category = self.bot.get_channel(await self.config.guild(ctx.guild).voice.category())
        overwrite = category.overwrites
        overwrite[ctx.author] = overwrite.get(ctx.author, discord.PermissionOverwrite())
        overwrite[ctx.author].update(manage_channels=True)
        if max_users is None:
            new = await ctx.guild.create_voice_channel(name=name, category=category, overwrites=overwrite)
        elif not(99 >= max_users >= 1):
            return await ctx.send("The user limit should be between 1 and 99 users!")
        else:
            new = await ctx.guild.create_voice_channel(name=name, category=category, overwrites=overwrite, user_limit=max_users)
        async with self.config.guild(ctx.guild).voice.active() as a:
            a.append((new.id, ctx.author.id, time.time()))

        await ctx.tick()
        await asyncio.sleep(await self.config.guild(ctx.guild).voice.timeout())

        if not new.members:
            async with self.config.guild(ctx.guild).voice.active() as active:
                try:
                    await new.delete(reason="CreateVoice: VC inactive after creation")
                    try:
                        ind = [a[0] for a in active].index(new.id)
                        active.pop(ind)
                    except ValueError:
                        pass
                except discord.NotFound:
                    pass

        return

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group()
    async def createvoiceset(self, ctx: commands.Context):
        """Settings for VoiceCreate"""

    @createvoiceset.command(name="toggle")
    async def _voice_toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether users can use `[p]createvoice` in this server."""
        await self.config.guild(ctx.guild).voice.toggle.set(true_or_false)
        return await ctx.tick()

    @createvoiceset.command(name="timeout")
    async def _voice_timeout(self, ctx: commands.Context, interval: int):
        """Set the VC timeout (and deletion) interval in seconds (default 60s)."""
        await self.config.guild(ctx.guild).voice.timeout.set(interval)
        return await ctx.tick()

    @createvoiceset.command(name="category")
    async def _voice_category(self, ctx: commands.Context, category: discord.CategoryChannel):
        """Set the VC category."""
        await self.config.guild(ctx.guild).voice.category.set(category.id)
        return await ctx.tick()

    @createvoiceset.command(name="maxchannels")
    async def _voice_maxchannels(self, ctx: commands.Context, maximum: int):
        """Set the maximum amount of total VCs that can be created."""
        await self.config.guild(ctx.guild).voice.maximum.set(maximum)
        return await ctx.tick()

    @createvoiceset.command(name="roles")
    async def _voice_roles(self, ctx: commands.Context, *roles: discord.Role):
        """Set the roles allowed to use `[p]createvoice`."""
        await self.config.guild(ctx.guild).voice.roles.set([r.id for r in roles])
        return await ctx.tick()

    @createvoiceset.command(name="userlimit")
    async def _voice_userlimit(self, ctx: commands.Context, limit: int):
        """Set the maximum amount of VCs users can create."""
        await self.config.guild(ctx.guild).voice.userlimit.set(limit)
        return await ctx.tick()

    @createvoiceset.command(name="rolereqmsg")
    async def _voice_rolereqmsg(self, ctx: commands.Context, *, message: str):
        """Set the message displayed when a user does not have any of the required roles."""
        await self.config.guild(ctx.guild).voice.role_req_msg.set(message)
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @createvoiceset.command(name="view")
    async def _voice_view(self, ctx: commands.Context):
        """View the current CreateVoice settings."""
        settings = await self.config.guild(ctx.guild).voice()

        roles = []
        for role in settings["roles"]:
            if r := ctx.guild.get_role(role):
                roles.append(r.name)

        return await ctx.send(embed=discord.Embed(
            title="CreateVoice Settings",
            color=await ctx.embed_color(),
            description=f"""
            **Toggle:** {settings["toggle"]}
            **Timeout:** {settings["timeout"]} seconds
            **Category:** {"None" if settings["category"] is None else ctx.guild.get_channel(settings["category"]).name}
            **MaxChannels:** {settings["maximum"]} channels
            **Roles:** {humanize_list(roles) or None}
            **UserLimit:** {settings["userlimit"]} channels
            **Active:** {humanize_list([ctx.guild.get_channel(c[0]) for c in settings["active"]]) or None}
            **Role Req Msg**: {settings["role_req_msg"]}
            """
        ))

    @createvoiceset.command(name="clear")
    async def _voice_clear(self, ctx: commands.Context):
        """Clear & reset the current CreateVoice settings."""
        await self.config.guild(ctx.guild).voice.clear()
        return await ctx.tick()

    @commands.bot_has_permissions(manage_channels=True)
    @commands.guild_only()
    @commands.command(name="createtext")
    async def _createtext(self, ctx: commands.Context, name: str):
        """Create a Text Channel"""

        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send("I don't have the permissions to create a channel!")

        if not await self.config.guild(ctx.guild).text.toggle(): return

        role_req = await self.config.guild(ctx.guild).text.roles()
        if role_req and not bool(set(role_req) & {r.id for r in ctx.author.roles}):
            return await ctx.send(await self.config.guild(ctx.guild).text.role_req_msg())

        active = await self.config.guild(ctx.guild).text.active()
        active_author = [c for c in active if c[1] == ctx.author.id]
        maximum = await self.config.guild(ctx.guild).text.maximum()

        userlimit = await self.config.guild(ctx.guild).text.userlimit()
        if len(active) >= maximum:
            return await ctx.send(f"There are already {maximum} active text channels!")
        if len(active_author) >= userlimit:
            return await ctx.send(f"You already have {userlimit} active text channels!")

        category = self.bot.get_channel(await self.config.guild(ctx.guild).text.category())
        overwrite = category.overwrites
        overwrite[ctx.author] = overwrite.get(ctx.author, discord.PermissionOverwrite())
        overwrite[ctx.author].update(manage_channels=True)
        new = await ctx.guild.create_text_channel(name=name, category=category, overwrites=overwrite)
        async with self.config.guild(ctx.guild).text.active() as a:
            a.append((new.id, ctx.author.id, time.time()))

        return await ctx.tick()

    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.group()
    async def createtextset(self, ctx: commands.Context):
        """Settings for CreateText"""

    @createtextset.command(name="toggle")
    async def _text_toggle(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether users can use `[p]createtext` in this server."""
        await self.config.guild(ctx.guild).text.toggle.set(true_or_false)
        return await ctx.tick()

    @createtextset.command(name="category")
    async def _text_category(self, ctx: commands.Context, category: discord.CategoryChannel):
        """Set the text channel category."""
        await self.config.guild(ctx.guild).text.category.set(category.id)
        return await ctx.tick()

    @createtextset.command(name="maxchannels")
    async def _text_maxchannels(self, ctx: commands.Context, maximum: int):
        """Set the maximum amount of total text channels that can be created."""
        await self.config.guild(ctx.guild).text.maximum.set(maximum)
        return await ctx.tick()

    @createtextset.command(name="roles")
    async def _text_roles(self, ctx: commands.Context, *roles: discord.Role):
        """Set the roles allowed to use `[p]createtext`."""
        await self.config.guild(ctx.guild).text.roles.set([r.id for r in roles])
        return await ctx.tick()

    @createtextset.command(name="userlimit")
    async def _text_userlimit(self, ctx: commands.Context, limit: int):
        """Set the maximum amount of text channels users can create."""
        await self.config.guild(ctx.guild).text.userlimit.set(limit)
        return await ctx.tick()

    @createtextset.command(name="rolereqmsg")
    async def _text_rolereqmsg(self, ctx: commands.Context, *, message: str):
        """Set the message displayed when a user does not have any of the required roles."""
        await self.config.guild(ctx.guild).text.role_req_msg.set(message)
        return await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @createtextset.command(name="view")
    async def _text_view(self, ctx: commands.Context):
        """View the current CreateText settings."""
        settings = await self.config.guild(ctx.guild).text()

        roles = []
        for role in settings["roles"]:
            if r := ctx.guild.get_role(role):
                roles.append(r.name)

        return await ctx.send(embed=discord.Embed(
            title="CreateText Settings",
            color=await ctx.embed_color(),
            description=f"""
            **Toggle:** {settings["toggle"]}
            **Category:** {"None" if settings["category"] is None else ctx.guild.get_channel(settings["category"]).name}
            **MaxChannels:** {settings["maximum"]} channels
            **Roles:** {humanize_list(roles) or None}
            **UserLimit:** {settings["userlimit"]} channels
            **Active:** {humanize_list([ctx.guild.get_channel(c[0]) for c in settings["active"]]) or None}
            **Role Req Msg**: {settings["role_req_msg"]}
            """
        ))

    @createtextset.command(name="clear")
    async def _text_clear(self, ctx: commands.Context):
        """Clear & reset the current CreateText settings."""
        await self.config.guild(ctx.guild).text.clear()
        return await ctx.tick()
