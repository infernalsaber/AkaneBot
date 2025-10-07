"""Make cool plot charts"""

import io
from collections import Counter

import hikari as hk
import lightbulb as lb
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from functions.fetch_trends import search_it
from functions.models import ColorPalette as colors

plot_plugin = lb.Plugin(
    "Plots",
    "A set of commands that are used to plot anime's trends",
    include_datastore=True,
)
plot_plugin.d.help_image = "https://i.imgur.com/dTvGa1t.png"
plot_plugin.d.help = True
plot_plugin.d.help_emoji = "📈"


@plot_plugin.command
@lb.set_help(
    "Plot the activity of a series at airtime or compare multiple. \n"
    "- For example, doing `[p]plot bocchi the rock` will return the activity "
    "of Bocchi the Rock series during its airtime. \n"
    "- To compare two series, you should seperate them with a 'vs' like so: \n"
    "`[p]plot helck vs horimiya piece`\n"
    "- To compare series across seasons, add a --autoscale flag at the end for eg."
    "`[p]plot bocchi vs kaguya --autoscale` \n\n"
    "Note: You should type out the full name of the series to avoid false matches"
)
@lb.add_cooldown(300, 1, lb.GlobalBucket)
@lb.option(
    "query",
    "The names of the series(') to plot",
    modifier=lb.commands.OptionModifier.GREEDY,
)
@lb.command(
    "plot",
    "Chart the airtime popularity of upto two anime",
    pass_options=True,
    auto_defer=True,
    aliases=["p"],
)
@lb.implements(lb.PrefixCommand)
async def compare_trends(ctx: lb.PrefixContext, query: list[str]) -> None:
    """Compare the popularity and ratings of two different anime
    Args:
        ctx (lb.Context): The event context (irrelevant to the user)
        query (list[str]): The name of the two anime (seperated by "vs")
    """
    # list.remove()
    try:
        if Counter(query)["vs"] > 1:
            await ctx.respond("The command only works for one or two series.")
            return
        # if "--autoscale" in query:
        autoscale = True if "--autoscale" in query else False
        query.remove("--autoscale") if "--autoscale" in query else ...

        series = ("\n".join(query)).split("vs")
        if len(series) not in [1, 2]:
            await ctx.respond("The command only works for one or two series.")
            return

        async with ctx.bot.rest.trigger_typing(ctx.event.channel_id):
            if len(series) == 1:
                data = await search_it(series[0], ctx.bot.d.aio_session)

                if isinstance(data, int):
                    await ctx.respond(f"An error occurred, `code: {data}` ")
                    return

                # pio.renderers.default = "notebook"
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(
                    go.Scatter(
                        x=data["data"]["activity"]["dates"],
                        y=data["data"]["activity"]["values"],
                        mode="lines",
                        name="Trends",
                        line={"color": "MediumTurquoise", "width": 2.5},
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=data["data"]["episodes"]["dates"],
                        y=data["data"]["episodes"]["values"],
                        mode="markers",
                        name="Episodes",
                        line={"color": "MediumTurquoise", "width": 2.5},
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=data["data"]["scores"]["dates"],
                        y=data["data"]["scores"]["values"],
                        line={"color": "DeepPink"},
                        name="Scores",
                        mode="lines",
                        line_shape="spline",
                    ),
                    secondary_y=True,
                )
                fig.update_layout(
                    xaxis_title="Dates",
                    yaxis_title="Trend Value",
                    template="plotly_dark",
                )
                embed_title = f'Popularity Trends: {data["name"]}'
            else:
                data = await search_it(series[0], ctx.bot.d.aio_session)
                data2 = await search_it(series[1], ctx.bot.d.aio_session)

                if isinstance(data, int) or isinstance(data2, int):
                    await ctx.respond("An error occurred")
                    return

                if autoscale:
                    gap = (
                        data["data"]["activity"]["dates"][0]
                        - data2["data"]["activity"]["dates"][0]
                    )
                    if (
                        data["data"]["activity"]["dates"][0]
                        > data2["data"]["activity"]["dates"][0]
                    ):
                        data["data"]["activity"]["dates"] = [
                            item - gap for item in data["data"]["activity"]["dates"]
                        ]
                        data["data"]["episodes"]["dates"] = [
                            item - gap for item in data["data"]["episodes"]["dates"]
                        ]
                        data["data"]["scores"]["dates"] = [
                            item - gap for item in data["data"]["scores"]["dates"]
                        ]

                    else:
                        data2["data"]["activity"]["dates"] = [
                            item + gap for item in data2["data"]["activity"]["dates"]
                        ]
                        data2["data"]["episodes"]["dates"] = [
                            item + gap for item in data2["data"]["episodes"]["dates"]
                        ]
                        data2["data"]["scores"]["dates"] = [
                            item + gap for item in data2["data"]["scores"]["dates"]
                        ]

                # pio.renderers.default = "notebook"
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(
                    go.Scatter(
                        x=data["data"]["activity"]["dates"],
                        y=data["data"]["activity"]["values"],
                        mode="lines",
                        name=f"Trends {series[0][0:15]}",
                        line={"color": "MediumTurquoise", "width": 2.5},
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=data["data"]["episodes"]["dates"],
                        y=data["data"]["episodes"]["values"],
                        mode="markers",
                        name=f"Episodes {series[0][0:15]}",
                        line={"color": "DarkTurquoise", "width": 2.5},
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=data["data"]["scores"]["dates"],
                        y=data["data"]["scores"]["values"],
                        line={"color": "DeepPink"},
                        name=f"Scores {series[0][0:15]}",
                        mode="lines",
                        line_shape="spline",
                    ),
                    secondary_y=True,
                )

                # Second series
                fig.add_trace(
                    go.Scatter(
                        x=data2["data"]["activity"]["dates"],
                        y=data2["data"]["activity"]["values"],
                        mode="lines",
                        name=f"Trends {series[1][0:15]}",
                        line={"color": "MediumSlateBlue", "width": 2.5},
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=data2["data"]["episodes"]["dates"],
                        y=data2["data"]["episodes"]["values"],
                        mode="markers",
                        name=f"Episodes {series[1][0:15]}",
                        line={"color": "MediumSlateBlue", "width": 2.5},
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=data2["data"]["scores"]["dates"],
                        y=data2["data"]["scores"]["values"],
                        line={"color": "DarkOrchid"},
                        name=f"Scores {series[1][0:15]}",
                        mode="lines",
                        line_shape="spline",
                    ),
                    secondary_y=True,
                )
                fig.update_layout(
                    xaxis_title="Dates",
                    yaxis_title="Trend Value",
                    template="plotly_dark",
                )
                embed_title = (
                    f'Popularity Comparision: {data["name"]} vs {data2["name"]}'
                )

    except Exception as e:
        await ctx.respond(e)

    try:
        fig.update_yaxes(title_text="Score", secondary_y=True)

        await ctx.respond(
            embed=hk.Embed(title=embed_title, color=colors.ELECTRIC_BLUE).set_image(
                hk.Bytes(io.BytesIO(fig.to_image(format="png")), "plot.png")
            ),
        )

    except Exception as e:
        await ctx.respond(e)


@plot_plugin.command
@lb.add_cooldown(30, 3, lb.GlobalBucket)
@lb.set_max_concurrency(2, lb.GlobalBucket)
@lb.option(
    "series",
    "The series to get the watch order for",
    modifier=lb.commands.OptionModifier.CONSUME_REST,
)
@lb.command(
    "watch-order",
    "Time investment needed by a series and watch order",
    aliases=["timeto", "watchorder", "wo"],
    pass_options=True,
)
@lb.implements(lb.PrefixCommand, lb.SlashCommand)
async def watch_order(ctx: lb.Context, series: str) -> None:
    await ctx.respond(f"{get_random_quote()} {hk.Emoji.parse(emotes.LOADING.value)}")
    with requests.Session() as session:
        anime_id = int(get_anime_data(session, anime=series)["data"]["Media"]["id"])
        try:
            series_list = format_chronological_order(session, anime_id=anime_id)
        except Exception as e:
            return await ctx.respond(f"An error occurred: {e}")
        if not series_list:
            return await ctx.respond("Could not generate watch order")
    order = " -> ".join(str(entry) for entry in series_list)
    total_time_investment = sum(
        [series.episodes * series.duration for series in series_list]
    )
    series_name = find_series_name(
        [series.title.lower() for series in series_list]
    ).title()

    hours, mins = divmod(total_time_investment, 60)
    time = f"{hours} hours, {mins} minutes" if hours else f"{mins} minutes"

    await ctx.edit_last_response(
        f"The time investment required for the `{series_name}` series is {time}.\n\nThe suggested watch order, based on release date is as follows:\n{order}",
        flags=hk.MessageFlag.SUPPRESS_EMBEDS,
    )
    


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(plot_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(plot_plugin)
