import typing as t

import hikari as hk
import lightbulb as lb
from rapidfuzz import process

from functions.help import BotHelpCommand

helper = lb.Plugin("Help", "Slash impl of help", include_datastore=True)
helper.d.help = False


@helper.command
@lb.option("query", "The object to get help for", required=False, autocomplete=True)
@lb.command("help", "See this message duh", pass_options=True)
@lb.implements(lb.SlashCommand)
async def help_slash_command(ctx: lb.Context, query: t.Optional[str]) -> None:
    # Your code in here
    try:
        helper = BotHelpCommand(ctx.bot)

        await helper.send_help(context=ctx, obj=query)
    except Exception as e:
        await ctx.respond(e)


@help_slash_command.autocomplete("query")
async def help_autocomplete(
    option: hk.CommandInteractionOption, interaction: hk.AutocompleteInteraction
):
    commands_and_plugins = []

    all_cmds = [
        *interaction.app.prefix_commands.items(),
        *interaction.app.slash_commands.items(),
        *interaction.app.message_commands.items(),
        *interaction.app.user_commands.items(),
    ]
    # self.app.plugins

    for cmd_name, cmd in all_cmds:
        if not cmd.hidden:
            commands_and_plugins.append(cmd_name)

    close_matches: t.Optional[t.Tuple[str, int]] = process.extract(
        option.value, commands_and_plugins, score_cutoff=85, limit=None
    )

    possible_commands: t.Sequence = []

    if close_matches:
        possible_commands = [f"{i}" for i, _, _ in close_matches]

    return possible_commands


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.d.old_help_command = bot.help_command
    bot.help_command = BotHelpCommand(bot)
    bot.add_plugin(helper)


def unload(bot):
    bot.help_command = bot.d.old_help_command
    del bot.d.old_help_command
    bot.remove_plugin(helper)


# def unload(bot: lb.BotApp) -> None:
# """Unload the plugin"""
