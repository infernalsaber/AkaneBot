"""The extension which fetches the AL data for the plot function"""
from datetime import datetime, timedelta
from operator import itemgetter


async def search_it(search_query: str, session) -> dict | int:
    """Search for the anime"""

    # Here we define our query as a multi-line string
    query = """
query ($id: Int, $search: String) { 
    Media (id: $id, search: $search, type: ANIME, sort: POPULARITY_DESC) { 
        id
        title {
            english
            romaji
        }
        averageScore
        startDate {
            year
            month
            day
        }
        endDate {
            year
            month
            day
        }
        coverImage {
            large
        }
        status

    }
}

    """

    # Make the HTTP Api request
    # try:
    response = await session.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": {"search": search_query}},
        timeout=10,
    )
    if response.ok:
        # print("Successfull connection")
        data = (await response.json())["data"]["Media"]
        al_id = data["id"]
        name = data["title"]["english"] or data["title"]["romaji"]
        lower_limit = datetime(
            data["startDate"]["year"],
            data["startDate"]["month"],
            data["startDate"]["day"],
            0,
            0,
        )

        if datetime.now() < lower_limit:
            print("Unaired stuff sir")
        lower_limit = lower_limit - timedelta(days=7)
        if data["endDate"]["year"]:
            upper_limit = datetime(
                data["endDate"]["year"],
                data["endDate"]["month"],
                data["endDate"]["day"],
                0,
                0,
            ) + timedelta(days=7)
        else:
            upper_limit = datetime.now()

    else:
        print((await response.json())["errors"])
        return response.status

    # Fetching the trend values

    trend_score = []
    flag = True
    counter = 1

    while flag:
        query = """
        query ($id: Int, $page: Int, $perpage: Int, $date_greater: Int, $date_lesser: Int) {
        Page (page: $page, perPage: $perpage) { 
            pageInfo {
                total
                hasNextPage
            }
            mediaTrends (mediaId: $id, date_greater: $date_greater, date_lesser: $date_lesser) {
            mediaId
            date
            trending
            averageScore
            episode
            }
            }
        }
        """

        variables = {
            "id": al_id,
            "page": counter,
            "perpage": 50,
            "date_greater": lower_limit.timestamp(),
            "date_lesser": int(upper_limit.timestamp()),
        }

        response = await session.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": variables},
            timeout=2,
        )

        if response.ok:
            if not (await response.json())["data"]["Page"]["pageInfo"]["hasNextPage"]:
                flag = False
            else:
                counter = counter + 1

            for item in (await response.json())["data"]["Page"]["mediaTrends"]:
                trend_score.append(item)
        else:
            print((await response.json())["errors"])
            return response.status

    # Parsing the values

    dates = []
    trends = []
    scores = []

    episode_entries = []
    trends2 = []
    dates2 = []

    for value in trend_score:
        if value["episode"]:
            episode_entries.append(value)

    for value in sorted(episode_entries, key=itemgetter("date")):
        trends2.append(value["trending"])
        dates2.append(datetime.fromtimestamp(value["date"]))

    for value in sorted(trend_score, key=itemgetter("date")):
        dates.append(datetime.fromtimestamp(value["date"]))
        trends.append(value["trending"])
        if value["averageScore"]:
            scores.append(value["averageScore"])

    # Sending the data back

    return {
        "name": name,
        "data": {
            "activity": {"dates": dates, "values": trends},
            "episodes": {"dates": dates2, "values": trends2},
            "scores": {"dates": dates[-len(scores) :], "values": scores},
        },
        # [dates, trends, dates2, trends2, dates[-len(scores) :], scores],
    }
