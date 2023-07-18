"""Make cool plot charts"""
import os

import hikari as hk
import lightbulb as lb
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from functions.fetch_trends import search_it

plot_plugin = lb.Plugin(
    "plot", "A set of commands that are used to plot anime's trends"
)


@plot_plugin.command
@lb.add_cooldown(15, 2, lb.ChannelBucket)
@lb.add_cooldown(3, 1, lb.GuildBucket)
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

    # print(os.listdir("./pictures/"))
    print("\n\n\n")
    if f"{query}.png" in os.listdir("./pictures/"):
        # await ctx.respond("Found")
        await ctx.respond(
            embed=hk.Embed(
                title=f"Popularity Chart: {query}", color=0x7DF9FF
            ).set_image(hk.File(f"pictures/{query.upper()}.png"))
            # , attachments = None
        )

        return
    series = query.split("vs")
    if not len(series) in [1, 2]:
        await ctx.respond("The command only works for one or two series.")
        return

    async with ctx.bot.rest.trigger_typing(ctx.event.channel_id):
        if len(series) == 1:
            data = await search_it(series[0])

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
                # title=f'Series Trends: {data["name"]}',
                xaxis_title="Dates",
                yaxis_title="Trend Value",
                template="plotly_dark",
            )
            embed_title = f'Popularity Trends: {data["name"]}'
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
                    name=f"Trends {series[0][0:15]}",
                    line={"color": "MediumTurquoise", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data["data"][2],
                    y=data["data"][3],
                    mode="markers",
                    name=f"Episodes {series[0][0:15]}",
                    line={"color": "DarkTurquoise", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data["data"][4],
                    y=data["data"][5],
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
                    x=data2["data"][0],
                    y=data2["data"][1],
                    mode="lines",
                    name=f"Trends {series[1][0:15]}",
                    line={"color": "MediumSlateBlue", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data2["data"][2],
                    y=data2["data"][3],
                    mode="markers",
                    name=f"Episodes {series[1][0:15]}",
                    line={"color": "MediumSlateBlue", "width": 2.5},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data2["data"][4],
                    y=data2["data"][5],
                    line={"color": "DarkOrchid"},
                    name=f"Scores {series[1][0:15]}",
                    mode="lines",
                    line_shape="spline",
                ),
                secondary_y=True,
            )
            fig.update_layout(
                # title=f'Trends Comparision: {data["name"]} vs {data2["name"]}',
                xaxis_title="Dates",
                yaxis_title="Trend Value",
                template="plotly_dark",
            )
            embed_title = f'Popularity Comparision: {data["name"]} vs {data2["name"]}'

        fig.update_yaxes(title_text="Score", secondary_y=True)
        # img_bytes = fig.to_image(format="png")
        # Image.open(io.BytesIO(img_bytes)).save(f"pictures/{query}.png")
        fig.write_image(f"pictures/{query}.png")
        # image_to_send = hk.File(f"pictures/{query}.png")
        await ctx.respond(
            embed=hk.Embed(title=embed_title, color=0x7DF9FF).set_image(
                hk.File(f"pictures/{query}.png")
            ),
            attachments=[],
        )


def load(bot: lb.BotApp) -> None:
    """Load the plugin"""
    bot.add_plugin(plot_plugin)


def unload(bot: lb.BotApp) -> None:
    """Unload the plugin"""
    bot.remove_plugin(plot_plugin)
