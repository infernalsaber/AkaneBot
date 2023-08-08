class YTVideo:
    """YouTube search video class"""

    def __init__(self, search_results: dict, i: int) -> None:
        """Initializing the class"""
        self.vid_name: str = search_results["items"][i]["snippet"]["title"]
        self.vid_id: str = search_results["items"][i]["id"]["videoId"]
        self.vid_thumb: str = search_results["items"][i]["snippet"]["thumbnails"][
            "high"
        ][
            "url"
        ]  # make it medium later
        self.vid_channel: str = search_results["items"][i]["snippet"]["channelTitle"]
        self.vid_duration: str = ""
        # pprint(search_results["items"][i])

    def get_link(self) -> str:
        """Getting a link to the vid"""
        return f"https://www.youtube.com/watch?v={self.vid_id}"

    def set_duration(self, req) -> str:
        """Make an API call and set the duration property"""
        ytapi2 = req.get(
            (
                f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2Ccontent"
                f"Details%2Cstatistics&id={self.vid_id}&regionCode=US&key={YT_KEY}"
            )
        )
        ytapi2 = ytapi2.json()
        self.vid_duration = str(
            isodate.parse_duration(ytapi2["items"][0]["contentDetails"]["duration"])
        )
        if self.vid_duration.startswith("0:"):
            self.vid_duration = str(
                isodate.parse_duration(ytapi2["items"][0]["contentDetails"]["duration"])
            )[2:]
            return self.vid_duration[2:]
        return self.vid_duration

    def get_duration_secs(self) -> int:
        """Get the duration in seconds"""
        ytapi2 = requests.get(
            (
                f"https://youtube.googleapis.com/youtube/v3/videos?part=snippet%2Ccontent"
                f"Details%2Cstatistics&id={self.vid_id}&regionCode=US&key={YT_KEY}"
            ),
            timeout=10,
        )
        ytapi2 = ytapi2.json()
        return int(
            isodate.parse_duration(
                (ytapi2["items"][0]["contentDetails"]["duration"])
            ).total_seconds()
        )


# class Genshin:
#     def __init__(self, character: str = None):
#         ...
