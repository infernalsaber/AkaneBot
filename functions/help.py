import collections
import typing as t
from datetime import datetime

import hikari as hk
import miru

# if t.TYPE_CHECKING:
from lightbulb import commands
from lightbulb import context as context_
from lightbulb import errors, plugins
from lightbulb.help_command import BaseHelpCommand

from functions.components import SimpleTextSelect
from functions.views import SelectView


async def filter_commands(
    cmds: t.Sequence[commands.base.Command], ctx: context_.base.Context
) -> t.Sequence[commands.base.Command]:
    """
    Evaluates the checks for each command provided, removing any that the checks fail for.
    This effectively removes any commands from the given collection that could not be
    invoked under the given context. This will also remove any commands with
    the ``hidden`` attribute set to ``True``.

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
        for plugin, cmd_list in cmds.items():
            pages[plugin].append(f"== {header} Commands")
            for cmd in set(cmd_list):
                pages[plugin].append(f"- {cmd.name} - {cmd.description}")

    async def send_bot_help(self, ctx: context_.base.Context) -> None:
        pages = {}

        try:
            main_embed = (
                hk.Embed(
                    title="Akane Bot Help Menu",
                    color=0x000000,
                    description=("An animanga search and sauce bot \n\n" "### Plugins"),
                    timestamp=datetime.now().astimezone(),
                )
                .set_thumbnail(
                    (
                        "https://media.discordapp.net/attachments/980479966389096460"
                        "/1125810202277597266/rubyhelp.png?width=663&height=662"
                    )
                )
                .set_image("https://i.imgur.com/LJ1t4wD.png")
            )

            p_commands = await self._get_command_plugin_map(
                self.app._prefix_commands, ctx
            )
            s_commands = await self._get_command_plugin_map(
                self.app._slash_commands, ctx
            )

            plugin_pages: t.MutableMapping[
                t.Optional[plugins.Plugin], t.List[str]
            ] = collections.defaultdict(list)
            self._add_cmds_to_plugin_pages(plugin_pages, p_commands, "Prefix")
            self._add_cmds_to_plugin_pages(plugin_pages, s_commands, "Slash")

            for plugin, _ in plugin_pages.items():
                if not plugin or not plugin.d.help:
                    continue
                # if plugin.d.help is not True:
                # continue

                main_embed.add_field(plugin.name, plugin.description)

                p_cmds, s_cmds = [], []
                all_commands = await filter_commands(plugin._all_commands, ctx)
                for cmd in all_commands:
                    if isinstance(cmd, commands.prefix.PrefixCommand):
                        p_cmds.append(cmd)
                    elif isinstance(cmd, commands.slash.SlashCommand):
                        s_cmds.append(cmd)

                cmds: t.List[t.Tuple[t.Sequence[commands.base.Command], str]] = [
                    (p_cmds, "Prefix"),
                    (s_cmds, "Slash"),
                ]

                embed = hk.Embed(
                    color=0x000000,
                    title=f"{plugin.name} Help",
                    description=f"{plugin.description or 'No additional details provided.'}\n",
                    timestamp=datetime.now().astimezone(),
                )

                for cmd_list, header in cmds:
                    desc = ""
                    if cmd_list:
                        for cmd in set(cmd_list):
                            desc += f"`{cmd.name: <14}` {cmd.description} \n"

                        embed.add_field(f"{header} Commands", desc)

                embed.set_image(plugin.d.help_image)
                pages[plugin.name.replace(" ", "_")] = embed

            view = SelectView(user_id=ctx.author.id, pages=pages)
            options = []
            for plugin, _ in plugin_pages.items():
                if not plugin:
                    continue
                if plugin.d.help is not True:
                    continue
                options.append(
                    miru.SelectOption(
                        label=plugin.name, value=plugin.name, emoji=plugin.d.help_emoji
                    )
                )

            view.add_item(
                SimpleTextSelect(options=options, placeholder="Select Plugin")
            )
            resp = await ctx.respond(content=None, embed=main_embed, components=view)
            await view.start(resp)
            await view.wait()

        except Exception as exp:
            await ctx.respond(f"Initializing help command failed: `{exp}`")

    async def send_command_help(
        self, ctx: context_.base.Context, command: commands.base.Command
    ) -> None:
        long_help = command.get_help(ctx).replace("[p]", ctx.prefix)
        prefix = (
            ctx.prefix
            if isinstance(command, commands.prefix.PrefixCommand)
            else "/"
            if isinstance(command, commands.slash.SlashCommand)
            else "🖱️"
        )

        if len(command.aliases) > 0:
            aliases = f"Aliases: {', '.join(command.aliases)}\n\n"
        else:
            aliases = ""

        if len(ctx.responses) == 0:
            await ctx.respond(
                embed=hk.Embed(
                    color=0x000000,
                    title="Command Help",
                    description=(
                        f"**{command.name}** \n"
                        f"{command.description} \n\n"
                        f"Usage: `{prefix}{command.signature}` \n\n"
                        f"{aliases}"
                        f"{long_help or ''}"
                    ),
                )
            )
        else:
            await ctx.edit_last_response(
                content=None,
                embed=hk.Embed(
                    color=0x000000,
                    title="Command Help",
                    description=(
                        f"**{command.name}** \n"
                        f"{command.description} \n\n"
                        f"Usage: `{prefix}{command.signature}` \n\n"
                        f"{aliases}"
                        f"{long_help or ''}"
                    ),
                ),
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
                    f"{prefix}{group.signature}"
                    if isinstance(group, commands.prefix.PrefixCommand)
                    else None,
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

    async def send_plugin_help(
        self, ctx: context_.base.Context, plugin: plugins.Plugin
    ) -> None:
        p_cmds, s_cmds = [], []
        all_commands = await filter_commands(plugin._all_commands, ctx)
        for cmd in all_commands:
            if isinstance(cmd, commands.prefix.PrefixCommand):
                p_cmds.append(cmd)
            elif isinstance(cmd, commands.slash.SlashCommand):
                s_cmds.append(cmd)

        # Message and User commands are not included in the Plugin Help
        cmds: t.List[t.Tuple[t.Sequence[commands.base.Command], str]] = [
            (p_cmds, "Prefix"),
            (s_cmds, "Slash"),
        ]

        embed = hk.Embed(
            color=0x000000,
            title=f"{plugin.name} Help",
            description=f"{plugin.description or 'No additional details provided.'}\n",
            timestamp=datetime.now().astimezone(),
        )

        for cmd_list, header in cmds:
            desc = ""
            if cmd_list:
                for cmd in set(cmd_list):
                    desc += f"`{cmd.name: <14}` {cmd.description} \n"

                embed.add_field(f"{header} Commands", desc)

        embed.set_image(plugin.d.help_image)
        await ctx.respond(embed)
