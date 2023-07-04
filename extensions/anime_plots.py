"""Make cool plot charts"""
import io
from PIL import Image

import hikari as hk
import lightbulb as lb


import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

from functions.fetch_trends import search_it


plot_plugin = lb.Plugin(
    "plot", "A set of commands that are used to plot anime's trends"
)


# @plot_plugin.command
# @lb.add_cooldown(10, 1, lb.UserBucket)
# @lb.add_cooldown(15, 2, lb.ChannelBucket)
# @lb.command("plot", "Make a series' trends' graph when it aired", aliases=["p"])
# @lb.implements(lb.PrefixCommandGroup, lb.SlashCommandGroup)
# async def plt_grp(ctx: lb.Context) -> None:
#     """Base ftn to plot a graph"""


# @plt_grp.child
# @lb.option(
#     "series",
#     "The series whose trends to look for",
#     modifier=lb.commands.OptionModifier.CONSUME_REST,
# )
# @lb.command(
#     "trend",
#     "Plot some trendz",
#     pass_options=True,
#     auto_defer=True,
#     aliases=["t", "trends"],
# )
# @lb.implements(lb.PrefixSubCommand, lb.SlashSubCommand)
# async def plot_airing_trend(ctx: lb.Context, series: str) -> None:
#     """Plot the popularity of an anime when it aired
#     Args:
#         ctx (lb.Context): The event context (irrelevant to the user)
#         series (str): Name of the series
#     """
#     data = await search_it(series)

#     if isinstance(data, int):
#         await ctx.respond(f"An error occurred, `code: {data}` ")
#         return
#     print(type(data))

#     pio.renderers.default = "notebook"
#     fig = make_subplots(specs=[[{"secondary_y": True}]])
#     fig.add_trace(
#         go.Scatter(
#             x=data["data"][0],
#             y=data["data"][1],
#             mode="lines",
#             name="Trends",
#             line={"color": "MediumTurquoise", "width": 2.5},
#         )
#     )
#     fig.add_trace(
#         go.Scatter(
#             x=data["data"][2],
#             y=data["data"][3],
#             mode="markers",
#             name="Episodes",
#             line={"color": "MediumTurquoise", "width": 2.5},
#         )
#     )
#     fig.add_trace(
#         go.Scatter(
#             x=data["data"][4],
#             y=data["data"][5],
#             line={"color": "DeepPink"},
#             name="Scores",
#             mode="lines",
#             line_shape="spline",
#         ),
#         secondary_y=True,
#     )
#     fig.update_layout(
#         title=f'Series Trends: {data["name"]}',
#         xaxis_title="Dates",
#         yaxis_title="Trend Value",
#         template="plotly_dark",
#     )

#     fig.update_yaxes(title_text="Score", secondary_y=True)
#     img_bytes = fig.to_image(format="png")
#     Image.open(io.BytesIO(img_bytes)).save(f"pictures/{series}.png")
#     await ctx.respond(
#         content=hk.Emoji.parse("<:nerd2:1060639499505377320>"),
#         attachment=f"pictures/{series}.png",
#     )


@plot_plugin.command
@lb.add_cooldown(10, 1, lb.UserBucket)
@lb.add_cooldown(15, 2, lb.ChannelBucket)
@lb.option(
    "query",
    "The names of the series(') to plot",
    modifier=lb.commands.OptionModifier.CONSUME_REST,
)
@lb.command(
    "plot", "Plot some trendz", pass_options=True, auto_defer=True, aliases=["p"]
)
@lb.implements(lb.PrefixCommand)
async def compare_trends(ctx: lb.Context, query: str) -> None:
    """Compare the popularity and ratings of two different anime
    Args:
        ctx (lb.Context): The event context (irrelevant to the user)
        query (str): The name of the two anime (seperated by "vs")
    """

    series = query.split("vs")
    if not len(series) in [1, 2]:
        await ctx.respond("The command only works for one or two series.")
        return

    async with ctx.bot.rest.trigger_typing(ctx.event.channel_id):
        if len(series) == 1:
            data = await search_it(series)

            if isinstance(data, int):
                await ctx.respond(f"An error occurred, `code: {data}` ")
                return
            print(type(data))

            pio.renderers.default = "notebook"
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Scatter(
                    x=data["data"][0],
                    y=data["data"][1],
                    mode="lines",
                    name="Trends",
                    line={"color": "MediumTurquoise", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data["data"][2],
                    y=data["data"][3],
                    mode="markers",
                    name="Episodes",
                    line={"color": "MediumTurquoise", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data["data"][4],
                    y=data["data"][5],
                    line={"color": "DeepPink"},
                    name="Scores",
                    mode="lines",
                    line_shape="spline",
                ),
                secondary_y=True,
            )
            fig.update_layout(
                title=f'Series Trends: {data["name"]}',
                xaxis_title="Dates",
                yaxis_title="Trend Value",
                template="plotly_dark",
            )
        else:    
            data = await search_it(series[0])
            # from pprint import pprint
            data2 = await search_it(series[1])


            pio.renderers.default = "notebook"
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Scatter(
                    x=data["data"][0],
                    y=data["data"][1],
                    mode="lines",
                    name=f"Trends {series[0]}",
                    line={"color": "MediumTurquoise", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data["data"][2],
                    y=data["data"][3],
                    mode="markers",
                    name=f"Episodes {series[0]}",
                    line={"color": "DarkTurquoise", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data["data"][4],
                    y=data["data"][5],
                    line={"color": "DeepPink"},
                    name=f"Scores {series[0]}",
                    mode="lines",
                    line_shape="spline",
                ),
                secondary_y=True,
            )

            # Second series
            fig.add_trace(
                go.Scatter(
                    x=data2["data"][0],
                    y=data2["data"][1],
                    mode="lines",
                    name=f"Trends {series[1]}",
                    line={"color": "MediumSlateBlue", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data2["data"][2],
                    y=data2["data"][3],
                    mode="markers",
                    name=f"Episodes {series[1]}",
                    line={"color": "MediumSlateBlue", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data2["data"][4],
                    y=data2["data"][5],
                    line={"color": "DarkOrchid"},
                    name=f"Scores {series[1]}",
                    mode="lines",
                    line_shape="spline",
                ),
                secondary_y=True,
            )
            fig.update_layout(
                title=f'Trends Comparision: {data["name"]} vs {data2["name"]}',
                xaxis_title="Dates",
                yaxis_title="Trend Value",
                template="plotly_dark",
            )

        fig.update_yaxes(title_text="Score", secondary_y=True)
        img_bytes = fig.to_image(format="png")
        Image.open(io.BytesIO(img_bytes)).save(f"pictures/{query}.png")
        await ctx.respond(
            content=hk.Emoji.parse("<:nerd2:1060639499505377320>"),
            attachment=f"pictures/{query}.png",
        )



def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(plot_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(plot_plugin)