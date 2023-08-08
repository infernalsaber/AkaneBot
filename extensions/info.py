"""Get information about a role, server, user, bot etc."""
import typing as t

import hikari as hk
import lightbulb as lb
import psutil
import subprocess
from datetime import datetime

from math import floor

from functions.views import CustomView, CustomNavi
from functions.buttons import GenericButton, KillButton, SwapButton
from functions.utils import iso_to_timestamp


info_plugin = lb.Plugin("Utility", "Utility and info commands", include_datastore=True)
info_plugin.d.help = True
info_plugin.d.help_emoji =  "⚙️"
info_plugin.d.help_image = "https://i.imgur.com/nsg3lZJ.png"


@info_plugin.command
@lb.set_help(
    "Find the list of users in a role"
)
@lb.option(
    "role",
    "The role",
    modifier=lb.OptionModifier.CONSUME_REST
)
@lb.command("inrole", "List of users in role", pass_options=True)
@lb.implements(lb.PrefixCommand)
async def inrole_cmd(ctx: lb.Context, role: t.Union[hk.Role, hk.ScheduledEvent]) -> None:
    

    try:
        role = int(role)
    except ValueError:
        pass

    if not isinstance(role, hk.Role):

        if isinstance(role, int):
            for role_ in (await ctx.bot.rest.fetch_roles(ctx.guild_id)):
                if role == role_.id:
                    role = role_
                    break
        elif role[0] == "<":
            for role_ in (await ctx.bot.rest.fetch_roles(ctx.guild_id)):
                if role == role_.mention:
                    role = role_
                    break
        else:
            for role_ in (await ctx.bot.rest.fetch_roles(ctx.guild_id)):
                if role == role_.name:
                    role = role_
                    break
    
    if isinstance(role, hk.Role):
        try:    

            d1, d2 = "", ""

            counter: int = 0

            pages = []


            for member_id in ctx.get_guild().get_members():
                member = ctx.get_guild().get_member(member_id)
                if role.id in member.role_ids:
                    d1 += f"`{member.id: <20}`\n"
                    d2 += f"{member.username}\n"
                    counter +=1


            basic_embed = (
                hk.Embed(
                title=f"List of users in {role.name} role ({counter})",
                timestamp=datetime.now().astimezone(),
                color=role.color or 0xFFFFFF
                )
                .set_thumbnail(role.icon_url)
            )

            if counter == 0:
                await ctx.respond(basic_embed)
                return


            mem_ids = [d1.split("\n")[i: i+20] for i in range(0, len(d1.split("\n")), 20)]
            mem_names = [d2.split("\n")[i: i+20] for i in range(0, len(d2.split("\n")), 20)]

            for i, item in enumerate(mem_ids):
                pages.append(
                    basic_embed
                    .add_field("UID", "\n".join(item), inline=True)
                    .add_field("Name", "\n".join(mem_names[i]), inline=True)
                )
            
            

            if len(pages) == 1:
                await ctx.respond(pages[0])
                return


            await ctx.respond('made pages')


            view = CustomNavi(
                pages=pages, user_id=ctx.author.id,
            )

            await ctx.respond('okokok pages')
            await view.send(ctx.channel_id)
            return
        except Exception as e:
            await ctx.respond(e)
            return
    try:
        event_ = None
        events = await ctx.bot.rest.fetch_scheduled_events(ctx.guild_id)
        if isinstance(role, int):
            for event in events:
                if role == event.id:
                    event_ = event
                    break
        else:
            for event in events:
                if role == event.name:
                    event_ = event
                    break
        
        if not event_:
            return
        
        event_members = []
        await ctx.respond(f"{ctx.guild_id}, {event_.id}")
        members = list(await ctx.bot.rest.fetch_scheduled_event_users(ctx.guild_id, event_))
        for member in members:
            if member.member:
                event_members.append(member.member.username)


        paginated_members = [event_members[i:i + 20] for i in range(0, len(event_members), 20)]
        pages = []

        base_embed= (
            hk.Embed(
            title=f"List of users interested in {event.name} ({len(event_members)})",
            timestamp=datetime.now().astimezone(),
            color=0x43408A
            )
            .set_image(event.image_url)
        )

        if len(event_members) == 0:
            await ctx.respond(base_embed)
            return

        for item in paginated_members:
            pages.append(
                base_embed
                .add_field("​", "\n".join(item))
            )

        if len(pages) == 1:
            await ctx.respond(pages[0])
            return

        view = CustomNavi(
            pages=pages, user_id=ctx.author.id,
        )
        await view.send(ctx.channel_id)
    
    except Exception as e:
        await ctx.respond(e)

@info_plugin.command
@lb.add_checks(lb.owner_only)
@lb.command("guilds", "See the servers the bot's in")
@lb.implements(lb.PrefixCommand)
async def guilds(ctx: lb.Context) -> None:
    pages = []
    buttons = [CustomPrevButton(), KillNavButton(), CustomNextButton()]
    for gld in list([guild for guild in ctx.bot.cache.get_guilds_view().values()]):
        pages.append(
            hk.Embed(
                color=0xF4EAE9,
                title=f"Server: {gld.name}",
                description=f"Server ID: `{gld.id}`",
                timestamp=datetime.datetime.now().astimezone(),
            )
            .add_field("Owner", await gld.fetch_owner(), inline=True)
            .add_field(
                "Server Created",
                f"<t:{int(gld.created_at.timestamp())}:R>",
                inline=True,
            )
            .add_field("Member Count", gld.member_count)
            .add_field("Boosts", gld.premium_subscription_count or "NA", inline=True)
            .add_field("Boost Level", gld.premium_tier or "NA", inline=True)
            .set_thumbnail(gld.icon_url)
            .set_image(gld.banner_url)
        )

    navigator = CustomNavi(pages=pages, buttons=buttons, user_id=ctx.author.id)
    await navigator.send(ctx.channel_id)



@info_plugin.command
@lb.add_cooldown(10, 1, lb.UserBucket)
@lb.add_cooldown(15, 2, lb.ChannelBucket)
@lb.command("botinfo", "Get general info about the bot", aliases=["info"])
@lb.implements(lb.PrefixCommand)
async def botinfo(ctx: lb.Context) -> None:
    """Get info about the bot"""

    try:
        user = info_plugin.bot.get_me()
        data = await info_plugin.bot.rest.fetch_application()
        guilds = list(await info_plugin.bot.rest.fetch_my_guilds())

        member = 0
        for guild in list(info_plugin.bot.cache.get_members_view()):
            guild_obj = info_plugin.bot.cache.get_guild(guild)
            member = member + guild_obj.member_count


        process = subprocess.Popen(
            "git rev-list --count main", text=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        num_commits, _ = process.communicate()

        try:
            num_commits = int(num_commits)
        except ValueError:
            return


        process = subprocess.Popen(
            'git log -5 --format="<t:%at:D> %s"', text=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        changes, _ = process.communicate()

        

        version = f"{floor(num_commits/1000)}.{floor(num_commits/100)}.{floor(num_commits/10)}"

        pages = [
            hk.Embed(
                color=0x43408A,
                description="A multi-purpose discord bot \
                    written in hikari-py.",
            )
            .add_field("Name", user)
            .add_field("No of Servers", len(guilds), inline=True)
            .add_field("No of Members", member, inline=True)
            .add_field("Version", version)
            .add_field(
                "Alive since", f"<t:{int(user.created_at.timestamp())}:R>", inline=True
            )
            .add_field(
                "Up since",
                f"<t:{int(info_plugin.bot.d.timeup.timestamp())}:R>",
                inline=True,
            )
            .add_field(
                "System Usage",
                f"RAM: {psutil.virtual_memory()[2]}% (of 512MB) \nCPU: {psutil.cpu_percent(4)}%",
            )
            .set_author(name=f"{user.username} Bot")
            .set_thumbnail(user.avatar_url)
            .set_footer(f"Made by: {data.owner}", icon=data.owner.avatar_url),

            hk.Embed(
                description=changes, color=0x43408A
            )
            .set_author(name="Bot Changelog (Recent)")
        ]


        view = CustomView(user_id=ctx.author.id)
        view.add_item(
            SwapButton(
                label1="Changelogs", label2="Info",
                emoji1=hk.Emoji.parse("<:MIU_changelog:1108056158377349173>"),
                emoji2=hk.Emoji.parse("ℹ️"),
                original_page=pages[0], swap_page=pages[1]
            )
        )
        
        choice = await ctx.respond(
            embed=pages[0],
            components=view,
        )
        await view.start(choice)
        await view.wait()

        if hasattr(view, "answer"):
            pass
        else:
            await ctx.edit_last_response(components=[])
    except Exception as e:
        await ctx.respond(e)

@info_plugin.command
@lb.add_checks(
    lb.has_guild_permissions(hk.Permissions.MANAGE_EMOJIS_AND_STICKERS),
)
@lb.command("stickerinfo", "Get info about a sticker", aliases=["sticker"])
@lb.implements(lb.PrefixCommand)
async def sticker_info(ctx: lb.Context) -> None:
    
    resp_embed = []
    if not ctx.event.message.stickers:
        await ctx.respond("No sticker in your message, I'm afraid")
        return

    stickers = []

    for sticker in ctx.event.message.stickers:
        try:
            sticker = await ctx.bot.rest.fetch_sticker(sticker.id)
            stickers.append(sticker)
        except hk.NotFoundError:
            resp_embed.append(
                hk.Embed(
                    color=0x000000,
                    title=f"Sticker: {sticker.name}",
                    timestamp=datetime.now().astimezone()
                )
                .add_field("Sticker ID: ", f"`{sticker.id}`")
                .add_field("Created at" ,f"<t:{int(sticker.created_at.timestamp())}:R>")
                .set_image(sticker.image_url)
            )
        else:
            resp_embed.append(
                hk.Embed(
                    color=0x43408A,
                    title=f"Sticker: {sticker.name}",
                    timestamp=datetime.now().astimezone()
                )
                .add_field("Sticker ID: ", f"`{sticker.id}`")
                .add_field("Created at" ,f"<t:{int(sticker.created_at.timestamp())}:R>", inline=True)
                .add_field("Type", sticker.type, inline=True)
                .add_field("Tag", sticker.tag)
                .set_thumbnail(ctx.get_guild().icon_url)
                .set_image(sticker.image_url)
            )

        
    await ctx.respond(embeds=resp_embed)

@info_plugin.command
@lb.command("emoteinfo", "Get info about an emote", aliases=["emote"], pass_options=True)
@lb.implements(lb.PrefixCommand)
async def emote_info(
    ctx: lb.Context, 
    ) -> None:

    emotes = []
    for word in ctx.event.message.content.split(" "):
        try:
            emote = hk.Emoji.parse(word)
            if isinstance(emote, hk.CustomEmoji):
                emotes.append(emote)
                print(emote.url)
        except:
            continue
    print(emotes, "\n\n\n\n\n")
    if len(emotes) == 0:
        await ctx.respond('No emotes found')
        return
    elif len(emotes) > 5:
        await ctx.respond('Too many emotes, taking the first 5 into account')
    
    resp_embed = []
    for emote in emotes[:5]:
        resp_embed.append(
            hk.Embed(
                title=f"Emoji: {emote.name}"
            )
            .add_field("Raw", f"`{emote.mention}`")
            .set_thumbnail(emote.url)
        )

    await ctx.respond(
        embeds=resp_embed, 
    )


@info_plugin.command
@lb.add_checks(
    lb.bot_has_guild_permissions(hk.Permissions.MANAGE_EMOJIS_AND_STICKERS),
    lb.has_guild_permissions(hk.Permissions.ADMINISTRATOR)
)
@lb.command("re", "Remove emote or multiple, simple as that", aliases=["remote"], pass_options=True, hidden=True)
@lb.implements(lb.PrefixCommand)
async def emote_removal(
    ctx: lb.Context, 
    # emotes: t.Sequence[hk.Emoji]
    ) -> None:
    words = ctx.event.message.content.split(" ")
    if len(words) == 1:
        await ctx.respond(hk.Embed(
            title="Remove emote help",
            description= (
                "Remove an emote or multiple, simple as that (upto 5)"
                "\n\n"
                "Usage: `-re <emote1> <emote2>....`"
            )
        ))
    emotes = []
    for word in words:
        try:
            # hk.Emoji.
            emote = hk.Emoji.parse(word)
            emote = await ctx.bot.rest.fetch_emoji(ctx.guild_id, emoji=emote)
            # if isinstance(emote, hk.KnownCustomEmoji):
                
            emotes.append(emote)
                # print(emote.url)
        except:
            continue
    # print(emotes, "\n\n\n\n\n")
    if len(emotes) == 0:
        await ctx.respond('No emotes found')
        return
    
    if len(emotes) > 5:
        await ctx.respond('Too many emotes, removing the first five at once')
    

    for emote in emotes[:5]:
        try:
            await ctx.author.send(
                content= (
                    "## EMOTE REMOVAL NOTIFICATION\n"
                    f"Emote `{emote.name}` removed from `{ctx.get_guild()}`"
                ),
                attachment=emote
            )
            await ctx.bot.rest.delete_emoji(ctx.guild_id, emote)
        except Exception as e:
            await ctx.respond(f"Error: {e}")


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(info_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(info_plugin)
