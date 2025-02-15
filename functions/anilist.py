import collections
from datetime import datetime, timedelta

import aiohttp_client_cache
import hikari as hk

from functions.models import ColorPalette
from functions.utils import verbose_timedelta


class AnilistBase:
    def __init__(self, name: str, id_: int) -> None:
        self.name = name
        self.id = id_

    @staticmethod
    def parse_description(description: str) -> str:
        """Parse Anilist descriptions into Discord friendly markdown

        Args:
            description (str): The description to parse

        Returns:
            str: The parsed description
        """

        description = (
            description.replace("<br>", "")
            .replace("~!", "||")
            .replace("!~", "||")
            .replace("#", "")
            .replace("<i>", "")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("</i>", "")
            .replace("<BR>", "")
        )

        if len(description) > 400:
            description = description[0:400]

            # If the trimmed description has a missing spoiler tag, add one
            if description.count("||") % 2:
                description = description + "||"

            description = description + "..."

        return description


class ALCharacter(AnilistBase):
    def __init__(
        self, name: str, id_: int, session: aiohttp_client_cache.CachedSession
    ) -> None:
        self.url = f"https://anilist.co/character/{id_}"
        self.session = session
        super().__init__(name, id_)

    @classmethod
    async def from_search(
        cls, query_: str, session: aiohttp_client_cache.CachedSession
    ):
        query = """
        query ($search: String) { # Define which variables will be used in the query
        Character (search: $search,  sort: FAVOURITES_DESC) { # Add var. to the query
            id
            name {
            full
            }
        }
        }
        """

        variables = {
            "search": query_
            # ,"sort": FAVOURITES_DESC
        }

        resp = await session.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
        )
        if not resp.ok:
            return await resp.json()
        resp_json = await resp.json()

        response = resp_json["data"]["Character"]

        title = response["name"]["full"]
        id_ = response["id"]

        return cls(title, id_, session)

    @classmethod
    async def from_id(cls, query_: int, session: aiohttp_client_cache.CachedSession):

        query = """
        query ($id: Int) { # Define which variables will be used in the query
        Character (id: $id,  sort: FAVOURITES_DESC) { # Add var. to the query
            id
            name {
            full
            }
        }
        }
        """

        variables = {
            "id": query_
            # ,"sort": FAVOURITES_DESC
        }

        resp = await session.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
        )
        if not resp.ok:
            return await resp.json()
        resp_json = await resp.json()

        response = resp_json["data"]["Character"]

        title = response["name"]["full"]
        id_ = response["id"]

        return cls(title, id_, session)

        # except Exception as e:
        # return e

    @classmethod
    async def is_birthday(cls, session: aiohttp_client_cache.CachedSession):
        # async with session.get()

        # self.session = session
        # try:
        query = """
        query ($var: Boolean) { # Define which variables will be used in the query
        Character (isBirthday: $var, sort: FAVOURITES_DESC) { # Add var. to the query
            id
            name {
            full
            }
        }
        }
        """

        variables = {
            "var": True
            # ,"sort": FAVOURITES_DESC
        }

        resp = await session.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
        )
        if not resp.ok:
            return await resp.json()
        resp_json = await resp.json()

        response = resp_json["data"]["Character"]

        title = response["name"]["full"]
        id_ = response["id"]

        return cls(title, id_, session)

    async def make_embed(self):
        query = """
query ($id: Int, $search: String) { # Define which variables will be used in the query
  Character (id: $id, search: $search,  sort: FAVOURITES_DESC) { # Add var. to the query
    id
    name {
      full
    }
    image {
      large
    }
    gender
    dateOfBirth {
        year
        month
        day
    }
    description (asHtml: false)
    media (sort: TRENDING_DESC, perPage: 3) {
        nodes {
            title {
                romaji
            }
            season
            seasonYear
            meanScore
            seasonInt
            episodes
            chapters
            source
            popularity
            tags {
              name
            }
        }
    }
    favourites #♥
    siteUrl
  }
}
"""
        try:
            variables = collections.defaultdict(list)

            variables["id"] = self.id

            resp = await self.session.post(
                "https://graphql.anilist.co",
                json={"query": query, "variables": variables},
            )
            if not resp.ok:
                return hk.Embed(
                    title="ERROR FETCHING DATA",
                    color=ColorPalette.ERROR,
                    description=(
                        "Failed to fetch data 😵"
                        "\nTry typing the full name of the character."
                    ),
                )
            resp_json = await resp.json()

            response = resp_json["data"]["Character"]

            response["name"]["full"]

            if response["dateOfBirth"]["month"] and response["dateOfBirth"]["day"]:
                dob = f"{response['dateOfBirth']['day']}/{response['dateOfBirth']['month']}"
                if response["dateOfBirth"]["year"]:
                    dob += f"/{response['dateOfBirth']['year']}"
            else:
                dob = "NA"

            if response["description"]:
                response["description"] = self.parse_description(
                    response["description"]
                )

            else:
                response["description"] = "NA"

            return (
                hk.Embed(
                    title=self.name,
                    url=self.url,
                    description="\n\n",
                    color=ColorPalette.ANILIST,
                    timestamp=datetime.now().astimezone(),
                )
                .add_field("Gender", response["gender"] or "Unknown")
                .add_field("DOB", dob, inline=True)
                .add_field("Favourites", f"{response['favourites']}❤", inline=True)
                .add_field("Character Description", response["description"])
                .set_thumbnail(response["image"]["large"])
                .set_footer(
                    text="Source: AniList",
                    icon="https://anilist.co/img/icons/android-chrome-512x512.png",
                )
            )

        except Exception as e:
            return hk.Embed(
                title="Failure",
                color=ColorPalette.ERROR,
                description=f"We encountered an error, `{e}`",
            )

    async def make_pages(self) -> list[hk.Embed]:
        query = """
query ($id: Int, $search: String) { # Define which variables will be used in the query
  Character (id: $id, search: $search,  sort: FAVOURITES_DESC) { # Add var. to the query
    id
    name {
      full
    }
    image {
      large
    }
    gender
    dateOfBirth {
        year
        month
        day
    }
    description (asHtml: false)
    media (sort: TRENDING_DESC, perPage: 3) {
        nodes {
            title {
                romaji
            }
            season
            seasonYear
            meanScore
            seasonInt
            episodes
            chapters
            source
            popularity
            tags {
              name
            }
        }
    }
    favourites #♥
    siteUrl
  }
}
"""

        try:
            variables = collections.defaultdict(list)

            variables["id"] = self.id

            resp = await self.session.post(
                "https://graphql.anilist.co",
                json={"query": query, "variables": variables},
            )

            if not resp.ok:
                return [
                    hk.Embed(
                        title="ERROR FETCHING DATA",
                        color=ColorPalette.ERROR,
                        description=(
                            "Failed to fetch data 😵"
                            "\nTry typing the full name of the character."
                        ),
                    )
                ]

            resp_json = await resp.json()

            response = resp_json["data"]["Character"]

            title = response["name"]["full"]

            if response["dateOfBirth"]["month"] and response["dateOfBirth"]["day"]:
                dob = f"{response['dateOfBirth']['day']}/{response['dateOfBirth']['month']}"
                if response["dateOfBirth"]["year"]:
                    dob += f"/{response['dateOfBirth']['year']}"
            else:
                dob = "NA"

            if response["description"]:
                response["description"] = self.parse_description(
                    response["description"]
                )

            else:
                response["description"] = "NA"

            series = ""

            for i, item in enumerate(response["media"]["nodes"]):
                series += (
                    f"```ansi\n{i+1}. \u001b[0;35m{item['title']['romaji']}"
                    f" \u001b[0;32m({item['meanScore']})```"
                )

            return [
                hk.Embed(
                    title=title,
                    url=response["siteUrl"],
                    description="\n\n",
                    color=ColorPalette.ANILIST,
                    timestamp=datetime.now().astimezone(),
                )
                .add_field("Gender", response["gender"] or "Unknown")
                .add_field("DOB", dob, inline=True)
                .add_field("Favourites", f"{response['favourites']}❤", inline=True)
                .add_field("Character Description", response["description"])
                .set_thumbnail(response["image"]["large"])
                .set_footer(
                    text="Source: AniList",
                    icon="https://anilist.co/img/icons/android-chrome-512x512.png",
                ),
                hk.Embed(
                    title=title,
                    url=response["siteUrl"],
                    color=ColorPalette.ANILIST,
                    timestamp=datetime.now().astimezone(),
                )
                .set_thumbnail(response["image"]["large"])
                .set_footer(
                    text="Source: AniList",
                    icon="https://anilist.co/img/icons/android-chrome-512x512.png",
                )
                .add_field("Appears in ", series),
            ]
        except Exception as e:
            return [
                hk.Embed(
                    title="Failure",
                    color=ColorPalette.ERROR,
                    description=f"We encountered an error, `{e}`",
                )
            ]


class ALAnime(AnilistBase):
    def __init__(
        self, name: str, id_: int, session: aiohttp_client_cache.CachedSession
    ) -> None:
        self.url = f"https://anilist.co/anime/{id_}"
        self.session = session
        super().__init__(name, id_)

    async def make_embed(self):
        query = """
query ($id: Int, $type: MediaType) { 
  media (id: $id, type: $type) { # The sort param was POPULARITY_DESC
    id
    idMal
    title {
        english
        romaji
    }
    duration
    type
    averageScore
    format
    meanScore
    episodes
    startDate {
        year
    }
    coverImage {
        large
    }
    studios (isMain: true) {
        nodes {
            name
            siteUrl
        }
    }
    bannerImage
    genres
    status
    description (asHtml: false)
    siteUrl
    trailer {
        id
        site
        thumbnail
    }
  }
  }
}

"""

        variables = {"id": self.id, "type": "ANIME"}

        response = await self.session.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
        )

        if not response.ok:
            # await ctx.respond(
            #     f"Failed to fetch data 😵, error `code: {response.status_code}`"
            # )
            return

        response = (await response.json())["data"]["Media"]

        title = response["title"]["english"] or response["title"]["romaji"]

        no_of_items = (
            response["episodes"]
            if response["episodes"] != 1
            else verbose_timedelta(timedelta(minutes=response["duration"]))
        )

        if response["description"]:
            response["description"] = self.parse_description(response["description"])

        else:
            response["description"] = "NA"

        # try:

        embed = (
            hk.Embed(
                title=title,
                url=response["siteUrl"],
                description="\n\n",
                color=ColorPalette.ANILIST,
                timestamp=datetime.now().astimezone(),
            )
            .add_field("Rating", response.get("meanScore", "NA"))
            .add_field("Genres", ", ".join(response["genres"][:4]))
            .add_field("Status", response["status"].replace("_", " "), inline=True)
            .add_field(
                "Episodes" if response["episodes"] != 1 else "Duration",
                no_of_items,
                inline=True,
            )
            .add_field("Studio", response["studios"]["nodes"][0]["name"], inline=True)
            .add_field("Summary", response["description"])
            .set_thumbnail(response["coverImage"]["large"])
            .set_image(response["bannerImage"])
            .set_footer(
                text="Source: AniList",
                icon="https://anilist.co/img/icons/android-chrome-512x512.png",
            )
        )

        if response["trailer"]:
            if response["trailer"]["site"] == "youtube":
                trailer = f"https://{response['trailer']['site']}.com/watch?v={response['trailer']['id']}"
            else:
                trailer = f"https://{response['trailer']['site']}.com/video/{response['trailer']['id']}"
        else:
            trailer = None

        return [embed, trailer]


#     @classmethod
#     async def from_search(
#         cls, query_: str, session: aiohttp_client_cache.CachedSession
#     ):
#         query = """
#         query ($search: String) { # Define which variables will be used in the query
#         Character (search: $search,  sort: FAVOURITES_DESC) { # Add var. to the query
#             id
#             name {
#             full
#             }
#         }
#         }
#         """

#         variables = {
#             "search": query_
#             # ,"sort": FAVOURITES_DESC
#         }

#         resp = await session.post(
#             "https://graphql.anilist.co",
#             json={"query": query, "variables": variables},
#
#         )
#         if not resp.ok:
#             return await resp.json()
#         resp_json = await resp.json()

#         response = resp_json["data"]["Character"]

#         title = response["name"]["full"]
#         id_ = response["id"]

#         return cls(title, id_, session)

#     @classmethod
#     async def from_id(cls, query_: int, session: aiohttp_client_cache.CachedSession):
#         # async with session.get()

#         # self.session = session
#         # try:
#         query = """
#         query ($id: Int) { # Define which variables will be used in the query
#         Character (id: $id,  sort: FAVOURITES_DESC) { # Add var. to the query
#             id
#             name {
#             full
#             }
#         }
#         }
#         """

#         variables = {
#             "id": query_
#             # ,"sort": FAVOURITES_DESC
#         }

#         response = await session.post(
#             "https://graphql.anilist.co",
#             json={"query": query, "variables": variables},
#
#         )
#         if not response.ok:
#             return await response.json()
#         response = await response.json()

#         response = response["data"]["Character"]

#         title = response["name"]["full"]
#         id_ = response["id"]

#         return cls(title, id_, session)

#         # except Exception as e:
#         # return e

#     async def make_embed(self):
#         query = """
# query ($id: Int, $search: String) { # Define which variables will be used in the query
#   Character (id: $id, search: $search,  sort: FAVOURITES_DESC) { # Add var. to the query
#     id
#     name {
#       full
#     }
#     image {
#       large
#     }
#     gender
#     dateOfBirth {
#         year
#         month
#         day
#     }
#     description (asHtml: false)
#     media (sort: TRENDING_DESC, perPage: 3) {
#         nodes {
#             title {
#                 romaji
#             }
#             season
#             seasonYear
#             meanScore
#             seasonInt
#             episodes
#             chapters
#             source
#             popularity
#             tags {
#               name
#             }
#         }
#     }
#     favourites #♥
#     siteUrl
#   }
# }
# """
#         # await ctx.respond("In")
#         try:
#             variables = collections.defaultdict(list)

#             # if id_:
#             variables["id"] = self.id

#             # elif character:
#             # variables["search"] = character

#             # else:
#             # raise lb.NotEnoughArguments

#             resp = await self.session.post(
#                 "https://graphql.anilist.co",
#                 json={"query": query, "variables": variables},
#
#             )
#             if not resp.ok:
#                 return hk.Embed(
#                     title="ERROR FETCHING DATA",
#                     color=ColorPalette.ERROR,
#                     description=(
#                         "Failed to fetch data 😵"
#                         "\nTry typing the full name of the character."
#                     ),
#                 )
#                 # return
#             resp_json = await resp.json()

#             response = resp_json["data"]["Character"]

#             response["name"]["full"]

#             if response["dateOfBirth"]["month"] and response["dateOfBirth"]["day"]:
#                 dob = f"{response['dateOfBirth']['day']}/{response['dateOfBirth']['month']}"
#                 if response["dateOfBirth"]["year"]:
#                     dob += f"/{response['dateOfBirth']['year']}"
#             else:
#                 dob = "NA"

#             if response["description"]:
#                 # response["description"] = parse_description(response["description"])\
#                 response["description"] = self.parse_description(
#                     response["description"]
#                 )

#             else:
#                 response["description"] = "NA"

#             return (
#                 hk.Embed(
#                     title=self.name,
#                     url=self.url,
#                     description="\n\n",
#                     color=ColorPalette.ANILIST,
#                     timestamp=datetime.now().astimezone(),
#                 )
#                 .add_field("Gender", response["gender"])
#                 .add_field("DOB", dob, inline=True)
#                 .add_field("Favourites", f"{response['favourites']}❤", inline=True)
#                 .add_field("Character Description", response["description"])
#                 .set_thumbnail(response["image"]["large"])
#                 # .set_author(url=response["siteUrl"], name=title)
#                 .set_footer(
#                     text="Source: AniList",
#                     icon="https://anilist.co/img/icons/android-chrome-512x512.png",
#                 )
#             )

#         except Exception as e:
#             return hk.Embed(
#                 title="Failure",
#                 color=ColorPalette.ERROR,
#                 description=f"We encountered an error, `{e}`",
#             )

#     async def make_pages(self) -> list[hk.Embed]:
#         query = """
# query ($id: Int, $search: String) { # Define which variables will be used in the query
#   Character (id: $id, search: $search,  sort: FAVOURITES_DESC) { # Add var. to the query
#     id
#     name {
#       full
#     }
#     image {
#       large
#     }
#     gender
#     dateOfBirth {
#         year
#         month
#         day
#     }
#     description (asHtml: false)
#     media (sort: TRENDING_DESC, perPage: 3) {
#         nodes {
#             title {
#                 romaji
#             }
#             season
#             seasonYear
#             meanScore
#             seasonInt
#             episodes
#             chapters
#             source
#             popularity
#             tags {
#               name
#             }
#         }
#     }
#     favourites #♥
#     siteUrl
#   }
# }
# """

#         try:
#             variables = collections.defaultdict(list)

#             variables["id"] = self.id

#             resp = await self.session.post(
#                 "https://graphql.anilist.co",
#                 json={"query": query, "variables": variables},
#
#             )

#             if not resp.ok:
#                 return [
#                     hk.Embed(
#                         title="ERROR FETCHING DATA",
#                         color=ColorPalette.ERROR,
#                         description=(
#                             "Failed to fetch data 😵"
#                             "\nTry typing the full name of the character."
#                         ),
#                     )
#                 ]

#             resp_json = await resp.json()

#             response = resp_json["data"]["Character"]

#             title = response["name"]["full"]

#             if response["dateOfBirth"]["month"] and response["dateOfBirth"]["day"]:
#                 dob = f"{response['dateOfBirth']['day']}/{response['dateOfBirth']['month']}"
#                 if response["dateOfBirth"]["year"]:
#                     dob += f"/{response['dateOfBirth']['year']}"
#             else:
#                 dob = "NA"

#             if response["description"]:
#                 response["description"] = self.parse_description(
#                     response["description"]
#                 )

#             else:
#                 response["description"] = "NA"

#             series = ""

#             for i, item in enumerate(response["media"]["nodes"]):
#                 series += (
#                     f"```ansi\n{i+1}. \u001b[0;35m{item['title']['romaji']}"
#                     f" \u001b[0;32m({item['meanScore']})```"
#                 )

#             return [
#                 hk.Embed(
#                     title=title,
#                     url=response["siteUrl"],
#                     description="\n\n",
#                     color=ColorPalette.ANILIST,
#                     timestamp=datetime.now().astimezone(),
#                 )
#                 .add_field("Gender", response["gender"] or "Unknown")
#                 .add_field("DOB", dob, inline=True)
#                 .add_field("Favourites", f"{response['favourites']}❤", inline=True)
#                 .add_field("Character Description", response["description"])
#                 .set_thumbnail(response["image"]["large"])
#                 .set_footer(
#                     text="Source: AniList",
#                     icon="https://anilist.co/img/icons/android-chrome-512x512.png",
#                 ),
#                 hk.Embed(
#                     title=title,
#                     url=response["siteUrl"],
#                     color=ColorPalette.ANILIST,
#                     timestamp=datetime.now().astimezone(),
#                 )
#                 .set_thumbnail(response["image"]["large"])
#                 .set_footer(
#                     text="Source: AniList",
#                     icon="https://anilist.co/img/icons/android-chrome-512x512.png",
#                 )
#                 .add_field("Appears in ", series),
#             ]
#         except Exception as e:
#             return [
#                 hk.Embed(
#                     title="Failure",
#                     color=ColorPalette.ERROR,
#                     description=f"We encountered an error, `{e}`",
#                 )
#             ]


# class VNDBBase:
#     def __init__(self, name: str, id_: int) -> None:
#         self.name = name
#         self.id = id_


#     @staticmethod
#     def parse_vndb_desciption(description: str) -> str:
#         """Parse a VNDB description into a Discord friendly Markdown"""
#         description = (
#             description.replace("[spoiler]", "||")
#             .replace("[/spoiler]", "||")
#             .replace("#", "")
#             .replace("[i]", "")
#             .replace("[b]", "")
#             .replace("[/b]", "")
#             .replace("[/i]", "")
#         )

#         pattern = r"\[url=(.*?)\](.*?)\[/url\]"

#         # Replace BBCode links with Markdown links in the text
#         description = re.sub(pattern, _replace_bbcode_with_markdown, description)

#         if len(description) > 300:
#             description = description[0:300]

#             if description.count("||") % 2:
#                 description = description + "||"

#             description = description + "..."

#         return description

#     @staticmethod
#     def _replace_bbcode_with_markdown(match: re.Match) -> str:
#         """Make a markdown-link string from a re Match object"""
#         url = match.group(1)
#         link_text = match.group(2)
#         markdown_link = f"[{link_text}]({url})"
#         return markdown_link


# class VNDBChara(VNDBBase):
#     ...


# class ALAnime:
#     ...


# class ALManga:
#     ...


# class ALNovel:
#     ...


# # class Genshin:
# #     def __init__(self, character: str = None):
# #         ...
