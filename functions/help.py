import typing as t
from lightbulb.help_command import BaseHelpCommand
from datetime import datetime
import hikari as hk

import abc
import collections
import typing as t

from lightbulb import commands
from lightbulb import errors

# if t.TYPE_CHECKING:
from lightbulb import app as app_
from lightbulb import context as context_
from lightbulb import plugins

import miru

from functions.components import HelpTextSelect
from functions.views import SelectView
        # except Exception as e:
            # await ctx.respond(e)
        # await ctx.respond("Test")



    # async def get_text(self, select: miru.TextSelect, ctx: miru.Context) -> None:
    #     """Create the selection menu"""
    #     print(select)
    #     await ctx.respond("I exist")
    #     self.answer = select.values[0]
    
    # async def callback(self, ctx: miru.ViewContext):
    #     await ctx.respond("this that badabing badabong")
        

# class AnimalView(miru.View):
#     """The view class for the animals command"""

#     def __init__(self, author: hk.User) -> None:
#         self.author = author
#         super().__init__(timeout=60*5)

#     @miru.text_select(
#         # custom_id="animal_select",
#         placeholder="Choose The Plugin",
#         options=[
#             miru.SelectOption("Dog", value="dog", emoji="🐶"),
#             miru.SelectOption("Bird", value="bird", emoji="🐦"),
#             miru.SelectOption("Koala", value="koala", emoji="🐨"),
#             miru.SelectOption("Panda", value="panda", emoji="🐼"),
#             miru.SelectOption("Cat", value="cat", emoji="🐱"),
#             miru.SelectOption("Racoon", value="racoon", emoji="🦝"),
#             miru.SelectOption(
#                 "Red Panda",
#                 value="red_panda",
#                 emoji=hk.Emoji.parse("<:RedPanda:1060649685934674001>"),
#             ),
#         ],
#     )
#     async def select_menu(self, select: miru.TextSelect, ctx: miru.Context) -> None:
#         """Create the selection menu"""
#         print(select)
#         animal = select.values[0]
#         async with ctx.bot.d.aio_session.get(
#             f"https://some-random-api.ml/animal/{animal}"
#         ) as res:
#             if res.ok:
#                 res = await res.json()

#                 await ctx.edit_response(
#                     f"Here's a {animal.replace('_', ' ')} for you!!",
#                     components=[],
#                     embed=hk.Embed(
#                         title="",
#                         description=res["fact"],
#                         color=0xF4EAE9,
#                         timestamp=datetime.now().astimezone(),
#                     )
#                     .set_image(res["image"])
#                     .set_footer(
#                         f"Requested by: {ctx.author}", icon=ctx.author.avatar_url
#                     ),
#                 )
#             else:
#                 await ctx.edit_response(
#                     f"API error, `code:{res.status}`", components=[]
#                 )

#     async def on_timeout(self) -> None:
#         await self.message.edit("Timed out", components=[])

#     async def view_check(self, ctx: miru.Context) -> bool:
#         return ctx.user.id == self.author.id


async def filter_commands(
    cmds: t.Sequence[commands.base.Command], ctx: context_.base.Context
) -> t.Sequence[commands.base.Command]:
    """
    Evaluates the checks for each command provided, removing any that the checks fail for. This effectively
    removes any commands from the given collection that could not be invoked under the given context. This will
    also remove any commands with the ``hidden`` attribute set to ``True``.

    Args:
        cmds (Sequence[:obj:`~.commands.base.Command`]): Commands to filter.
        ctx (:obj:`~.context.base.Context`): Context to filter the commands under.

    Returns:
        Sequence[:obj:`~.commands.base.Command`]: Filtered commands.
    """
    new_cmds = []
    for cmd in cmds:
        if cmd.hidden:
            continue
        try:
            await cmd.evaluate_checks(ctx)
        except errors.CheckFailure:
            continue
        new_cmds.append(cmd)
    return new_cmds

class BotHelpCommand(BaseHelpCommand):
    """
    An implementation of the :obj:`~BaseHelpCommand` but prettier and useful
    """

    @staticmethod
    async def _get_command_plugin_map(
        cmd_map: t.Mapping[str, commands.base.Command], ctx: context_.base.Context
    ) -> t.Dict[t.Optional[plugins.Plugin], t.List[commands.base.Command]]:
        out = collections.defaultdict(list)
        for cmd in cmd_map.values():
            if await filter_commands([cmd], ctx):
                out[cmd.plugin].append(cmd)
        return out

    @staticmethod
    def _add_cmds_to_plugin_pages(
        pages: t.MutableMapping[t.Optional[plugins.Plugin], t.List[str]],
        cmds: t.Mapping[t.Optional[plugins.Plugin], t.List[commands.base.Command]],
        header: str,
    ) -> None:
        for plugin, cmds in cmds.items():
            pages[plugin].append(f"== {header} Commands")
            for cmd in set(cmds):
                pages[plugin].append(f"- {cmd.name} - {cmd.description}")


    async def send_bot_help(self, ctx: context_.base.Context) -> None:
        pages = {}
        # lines = [
        #     ">>> ```adoc",
        #     "Akane Bot Help Menu",
        #     "",
        #     f"For more information: {context.prefix}help [command|category]",
        #     "",
        #     "==== Categories ====",
        # ]
        try:
            main_embed = ( 
                hk.Embed(
                title="Akane Bot Help Menu",
                color=0x000000,
                description=(
                    "An animanga search and sauce bot \n\n"
                    "### Plugins"
                    ),
                timestamp=datetime.now().astimezone()
            )
            .set_thumbnail(
                (
                    "https://media.discordapp.net/attachments/980479966389096460"
                    "/1125810202277597266/rubyhelp.png?width=663&height=662"
                )
            )
            .set_image("https://i.imgur.com/LJ1t4wD.png") )
            # import os

            p_commands = await self._get_command_plugin_map(self.app._prefix_commands, ctx)
            s_commands = await self._get_command_plugin_map(self.app._slash_commands, ctx)
            # m_commands = await self._get_command_plugin_map(self.app._message_commands, context)
            # u_commands = await self._get_command_plugin_map(self.app._user_commands, context)

            plugin_pages: t.MutableMapping[t.Optional[plugins.Plugin], t.List[str]] = collections.defaultdict(list)
            self._add_cmds_to_plugin_pages(plugin_pages, p_commands, "Prefix")
            self._add_cmds_to_plugin_pages(plugin_pages, s_commands, "Slash")
            # self._add_cmds_to_plugin_pages(plugin_pages, m_commands, "Message")
            # self._add_cmds_to_plugin_pages(plugin_pages, u_commands, "User")

            for plugin, page in plugin_pages.items():
                if not plugin: 
                    continue
                if not plugin.d.help == True:
                        continue
                # if plugin:
                main_embed.add_field(plugin.name, plugin.description)
                # """Start of tragedy"""
                p_cmds, s_cmds = [], []
                all_commands = await filter_commands(plugin._all_commands, ctx)
                for cmd in all_commands:
                    if isinstance(cmd, commands.prefix.PrefixCommand):
                        p_cmds.append(cmd)
                    elif isinstance(cmd, commands.slash.SlashCommand):
                        s_cmds.append(cmd)
                # elif isinstance(cmd, commands.message.MessageCommand):
                #     m_cmds.append(cmd)
                # elif isinstance(cmd, commands.user.UserCommand):
                #     u_cmds.append(cmd)

                cmds: t.List[t.Tuple[t.Sequence[commands.base.Command], str]] = [
                    (p_cmds, "Prefix"),
                    (s_cmds, "Slash"),
                    # (m_cmds, "Message"),
                    # (u_cmds, "User"),
                ]
                embed = hk.Embed(
                    color=0x000000, title=f"{plugin.name} Help", 
                    description=f"{plugin.description or 'No additional details provided.'}\n",
                    timestamp=datetime.now().astimezone()
                    )

            # embed.add_field("")
                for cmd_list, header in cmds:
                    # field1 = ""
                    # field2 = ""
                    # field3 = ""
                    desc = ""
                    if cmd_list:
                        # embed.add_field(f"{header} Commands", "\u200B")
                        for cmd in set(cmd_list):
                            desc += f"`{cmd.name}"
                            # print(" "*14-len(cmd.name))
                            desc += ' '*(14-len(cmd.name))
                            desc += f"` {cmd.description} \n"
                            # lines.append(f"- {cmd.name} - {cmd.description}, {cmd.aliases}")
                            # field1 += f"```{cmd.name}```"
                            # field2 += f"```{cmd.description}```"
                            # field3 += f"```{', '.join(cmd.aliases) or ' '}```"
                        embed.add_field(f"{header} Commands", desc)
                        # embed.add_field("\u200B", field2, inline=True)
                    # if isinstance(cmd_list[0], commands.prefix.PrefixCommand):
                    #     embed.add_field("\u200B", field3, inline=True)
                    # else:
                    #     embed.add_field("\u200B", "\u200B", inline=True)
                    
                embed.set_image(plugin.d.help_image)   
                pages[plugin.name.replace(" ", "_")] = embed
                # )
                
                    # "\n".join(
                    #     [
                    #         ">>> ```adoc",
                    #         f"==== {plugin.name if plugin is not None else 'Uncategorised'} ====",
                    #         (f"{plugin.description}\n" if plugin.description else "No description provided\n")
                    #         if plugin is not None
                    #         else "",
                    #         *page,
                    #         "```",
                    #     ]
                    # )
                
        # lines.append("```")
        # pages.insert(0, "\n".join(lines))
        # try:
            view = SelectView(user_id=ctx.author.id, pages=pages)
            options = []
            for plugin, _ in plugin_pages.items():
                if not plugin: 
                    continue
                if not plugin.d.help == True:
                    continue
                options.append(
                    miru.SelectOption(
                        label=plugin.name, value=plugin.name, emoji=plugin.d.help_emoji
                    )
                )
            # selector = 
            view.add_item(HelpTextSelect(options=options, placeholder="Select Plugin"))
            resp = await ctx.respond(embed=main_embed, components=view)
            

            # print("\n\n", pages, "\n\n")
            await view.start(resp)
            await view.wait()

            # print("Selector")
            # print(dir(selector))
            # print("\n\n\n\n\n")
            # print(dir(view))
            # # await ctx.respond(dir(resp))
            # # await context.respond(pages)
            # print(dir(resp), "\n\n\n\n\n\n\n")
            
            # if hasattr(view, "answer"):  # Check if there is an answer
            #     print(f"Received an answer! It is: {view.answer}")
            #     await context.edit_last_response(embeds=[pages[view.answer]], components=view)

        except Exception as e:
            await ctx.respond(e)
        # navigator = nav.ButtonNavigator(pages)
        # await navigator.run(context)



    async def send_command_help(self, ctx: context_.base.Context, command: commands.base.Command) -> None:
        long_help = command.get_help(ctx)
        prefix = (
            ctx.prefix
            if isinstance(command, commands.prefix.PrefixCommand)
            else "/"
            if isinstance(command, commands.slash.SlashCommand)
            else "🖱️"
        )


        # embed = (
            
        # )
        # lines = [
        #     ">>> ```adoc",
        #     "==== Command Help ====",
        #     f"{command.name} - {command.description}",
        #     "",
        #     f"Usage: {prefix}{command.signature}",
        #     "",
        #     long_help if long_help else "No additional details provided.",
        #     "```",
        # ]
        await ctx.respond(
            embed=hk.Embed(
                color=0x000000, title="Command Help",
                description= (
                    f"**{command.name}** \n"
                    f"{command.description} \n\n"
                    f"Usage: `{prefix}{command.signature}` \n\n"

                    f"Aliases: {', '.join(command.aliases)}\n\n"
                    f"{long_help or ''}"
                )
            )
        )



    async def send_group_help(
        self,
        ctx: context_.base.Context,
        group: t.Union[
            commands.prefix.PrefixCommandGroup,
            commands.prefix.PrefixSubGroup,
            commands.slash.SlashCommandGroup,
            commands.slash.SlashSubGroup,
        ],
    ) -> None:

        long_help = group.get_help(ctx)
        prefix = (
            ctx.prefix
            if isinstance(group, commands.prefix.PrefixCommand)
            else "/"
            if isinstance(group, commands.slash.SlashCommand)
            else hk.Emoji.parse("🖱️")
        )

        usages = list(
            filter(
                None,
                [
                    f"{prefix}{group.signature}" if isinstance(group, commands.prefix.PrefixCommand) else None,
                    f"{prefix}{group.qualname} [subcommand]",
                ],
            )
        )
        usages[0] = f"Usage: {usages[0]}"
        if len(usages) > 1:
            usages[1] = f"Or: {usages[1]}"

        lines = [
            ">>> ```adoc",
            "==== Group Help ====",
            f"{group.name} - {group.description}",
            "",
            "\n".join(usages),
            "",
            long_help if long_help else "No additional details provided.",
            "",
        ]
        if group._subcommands:
            subcommands = await filter_commands(group._subcommands.values(), ctx)  # type: ignore
            lines.append("== Subcommands")
            for cmd in set(subcommands):
                lines.append(f"- {cmd.name} - {cmd.description}")
        lines.append("```")
        await ctx.respond("\n".join(lines))



    async def send_plugin_help(self, ctx: context_.base.Context, plugin: plugins.Plugin) -> None:
        # lines = [
        #     ">>> ```adoc",
        #     "==== Category Help ====",
        #     f"{plugin.name} - {plugin.description or 'No description provided'}",
        #     "",
        # ]
        try:
            p_cmds, s_cmds, m_cmds, u_cmds = [], [], [], []
            all_commands = await filter_commands(plugin._all_commands, ctx)
            for cmd in all_commands:
                if isinstance(cmd, commands.prefix.PrefixCommand):
                    p_cmds.append(cmd)
                elif isinstance(cmd, commands.slash.SlashCommand):
                    s_cmds.append(cmd)
                # elif isinstance(cmd, commands.message.MessageCommand):
                #     m_cmds.append(cmd)
                # elif isinstance(cmd, commands.user.UserCommand):
                #     u_cmds.append(cmd)

            cmds: t.List[t.Tuple[t.Sequence[commands.base.Command], str]] = [
                (p_cmds, "Prefix"),
                (s_cmds, "Slash"),
                # (m_cmds, "Message"),
                # (u_cmds, "User"),
            ]
            embed = hk.Embed(
                color=0x000000, title=f"{plugin.name} Help", 
                description=f"{plugin.description or 'No additional details provided.'}\n",
                timestamp=datetime.now().astimezone()
                )

            # embed.add_field("")
            for cmd_list, header in cmds:
                # field1 = ""
                # field2 = ""
                # field3 = ""
                desc = ""
                if cmd_list:
                    # embed.add_field(f"{header} Commands", "\u200B")
                    for cmd in set(cmd_list):
                        desc += f"`{cmd.name}"
                        # print(" "*14-len(cmd.name))
                        desc += ' '*(14-len(cmd.name))
                        desc += f"` {cmd.description} \n"
                        # lines.append(f"- {cmd.name} - {cmd.description}, {cmd.aliases}")
                        # field1 += f"```{cmd.name}```"
                        # field2 += f"```{cmd.description}```"
                        # field3 += f"```{', '.join(cmd.aliases) or ' '}```"
                    embed.add_field(f"{header} Commands", desc)
                    # embed.add_field("\u200B", field2, inline=True)
                    # if isinstance(cmd_list[0], commands.prefix.PrefixCommand):
                    #     embed.add_field("\u200B", field3, inline=True)
                    # else:
                    #     embed.add_field("\u200B", "\u200B", inline=True)
                    
            embed.set_image(plugin.d.help_image)            
            # lines.append("```")
            await ctx.respond(embed)
        except Exception as e:
            await ctx.respond(e)