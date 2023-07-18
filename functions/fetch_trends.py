"""The extension which fetches the AL data for the plot function"""
import datetime
from operator import itemgetter

import requests
import requests_cache

requests_cache.install_cache("my_cache", expire_after=3600)


async def search_it(search_query: str) -> dict | int:
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
    response = requests.post(
        "https://graphql.anilist.co",
        json={"query": query, "variables": {"search": search_query}},
        timeout=10,
    )
    if response.status_code == 200:
        print("Successfull connection")
        data = response.json()["data"]["Media"]
        al_id = data["id"]
        name = data["title"]["english"] or data["title"]["romaji"]
        lower_limit = datetime.datetime(
            data["startDate"]["year"],
            data["startDate"]["month"],
            data["startDate"]["day"],
            0,
            0,
        )

        if datetime.datetime.now() < lower_limit:
            print("Unaired stuff sir")
        lower_limit = lower_limit - datetime.timedelta(days=7)
        if data["endDate"]["year"]:
            upper_limit = datetime.datetime(
                data["endDate"]["year"],
                data["endDate"]["month"],
                data["endDate"]["day"],
                0,
                0,
            ) + datetime.timedelta(days=7)
        else:
            upper_limit = datetime.datetime.now()

    else:
        print(response.json()["errors"])
        return response.status_code

    """Fetching the trend values """
    req = requests.Session()
    # id = input("Enter id. ")
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

        response = req.post(
            "https://graphql.anilist.co", json={"query": query, "variables": variables}
        )

        if response.status_code == 200:
            # print(response.json())
            if not response.json()["data"]["Page"]["pageInfo"]["hasNextPage"]:
                flag = False
            else:
                counter = counter + 1

            for item in response.json()["data"]["Page"]["mediaTrends"]:
                trend_score.append(item)
        else:
            # print("ERROR")
            print(response.json()["errors"])
            return response.status_code

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
        dates2.append(datetime.datetime.fromtimestamp(value["date"]))

    for value in sorted(trend_score, key=itemgetter("date")):
        dates.append(datetime.datetime.fromtimestamp(value["date"]))
        trends.append(value["trending"])
        if value["averageScore"]:
            scores.append(value["averageScore"])

    # Sending the data back

    return {
        "name": name,
        "data": [dates, trends, dates2, trends2, dates[-len(scores) :], scores],
    }
