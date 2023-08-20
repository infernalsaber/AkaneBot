"""
This is the module to make 3x3s or find Google Image results
"""
import json
import re
import typing as t
from typing import Optional

from aiohttp_client_cache import CachedSession
from bs4 import BeautifulSoup


def original_images(soup):
    """Return the original res images from the scrapped ones"""

    google_images = []

    all_script_tags = soup.select("script")

    matched_images_data = "".join(
        re.findall(r"AF_initDataCallback\(([^<]+)\);", str(all_script_tags))
    )

    matched_images_data_fix = json.dumps(matched_images_data)
    matched_images_data_json = json.loads(matched_images_data_fix)

    matched_google_image_data = re.findall(
        r"\"b-GRID_STATE0\"(.*)sideChannel:\s?{}}", matched_images_data_json
    )

    matched_google_image_thumbnails = ", ".join(
        re.findall(
            r"\[\"(https\:\/\/encrypted-tbn0\.gstatic\.com\/images\?.*?)\",\d+,\d+\]",
            str(matched_google_image_data),
        )
    ).split(", ")

    thumbnails = [
        bytes(bytes(thumbnail, "ascii").decode("unicode-escape"), "ascii").decode(
            "unicode escape"
        )
        for thumbnail in matched_google_image_thumbnails
    ]

    removed_matched_google_images_thumbnails = re.sub(
        r"\[\"(https\:\/\/encrypted-tbn0\.gstatic\.com\/images\?.*?)\",\d+,\d+\]",
        "",
        str(matched_google_image_data),
    )

    matched_google_full_resolution_images = re.findall(
        r"(?:'|,),\[\"(https:|http.*?)\",\d+,\d+\]",
        removed_matched_google_images_thumbnails,
    )

    full_res_images = [
        bytes(bytes(img, "ascii").decode("unicode-escape"), "ascii").decode(
            "unicode-escape"
        )
        for img in matched_google_full_resolution_images
    ]
    # print("Parsing shit")
    # print(full_res_images[0:2])
    for metadata, thumbnail, original in zip(
        soup.select(".isv-r.PNCib.MSM1fd.BUooTd"), thumbnails, full_res_images
    ):
        # start=1,
        # ):
        try:
            google_images.append(
                {
                    # "title": metadata.select_one(".VFACy.kGQAp.sMi44c.lNHeqe.WGvvNb")[
                    #     "title"
                    # ],
                    "link": metadata.select_one(".VFACy.kGQAp.sMi44c.lNHeqe.WGvvNb")[
                        "href"
                    ],
                    "source": metadata.select_one(".fxgdke").text,
                    "thumbnail": thumbnail,
                    "original": original,
                }
            )
        except Exception:
            print("Google is shit")
            google_images.append(
                {
                    "thumbnail": thumbnail,
                    "source": "Unknown",
                    "link": "Unknown",
                    "original": original,
                }
            )

    # print(google_images)
    return google_images


async def lookfor(
    query: str,
    session: CachedSession,
    *,
    num: t.Optional[int] = 9,
    recent: Optional[str] = None,
) -> list:
    """Return images and corresponding data of the search query

    Args:
        query (str): The query to search for
        num (int, optional): The number of images to search for. Defaults to 9.

    Returns:
        list: The list of images alongwith thumbnail, source and link if possible
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    }
    params = {
        "q": query,  # Query to search for
        "tbm": "isch",  # to display image search results
        "h1": "en",  # language for the query
        "gl": "us",  # country to fetch results from
        "ijn": "0",
    }

    if recent:
        params["tbs"] = f"qdr:{recent}"
    # req = requests.session()
    async with session.get(
        "https://www.google.com/search", params=params, headers=headers, timeout=30
    ) as html:
        # html = req.get("https://www.google.com/search",params=params,headers=headers,timeout=30)
        # print("Fetched g search")
        soup = BeautifulSoup(await html.text(), "lxml")
    return original_images(soup)[:num]


# import time
