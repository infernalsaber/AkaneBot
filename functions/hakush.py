"""
In broad what this module aims to do:
Dropdown: Story, Stats, Ascension, Skills, Mindscape (a navigator having lvl1,2,3 images)

Story: lvl1 trust (rest spoilered), gender, birthdate, height
Stats: try for image
Ascension: try for emotes of everything
Skills: a list for now
Mindscape

"""

import asyncio
import collections
from random import shuffle

import hikari as hk
import miru
from aiohttp_client_cache import CachedSession
from rapidfuzz import process
from rapidfuzz.utils import default_process


class HakushCharacter:
    def __init__(self, id, name, session) -> None:
        self.id = id
        self.name = name
        self.session = session
        self.cdn = "https://api.hakush.in"

    @classmethod
    async def from_search(cls, query: str, service: str, session: CachedSession):
        response = await session.get(
            f"https://api.hakush.in/{service}/data/character.json"
        )  # Can be hsr, gi, zzz, ww

        resp_json: dict = await response.json()

        chara_codes = list(resp_json.keys())
        name_code_mapping = {}

        for code in chara_codes:
            name_code_mapping.update(
                {resp_json[code].get("EN") or resp_json[code]["en"]: code}
            )

        closest_match, *_ = process.extractOne(
            query,
            name_code_mapping.keys(),
            processor=default_process,
        )

        return cls(name_code_mapping[closest_match], closest_match, session)

    async def get_character_info(self, service):
        resp = await self.session.get(
            f"https://api.hakush.in/{service}/data/en/character/{self.id}.json"
        )
        r_json = await resp.json()
        return r_json

    @staticmethod
    async def get_gallery_images(name, session, max_imgs=10, searchword=""):
        response = await session.get(
            f"https://danbooru.donmai.us/tags.json?search[name_matches]={name}*"
        )
        if not response.ok or not (await response.json()):
            return None

        tags = await response.json()
        tags = sorted(tags, key=lambda x: x["post_count"], reverse=True)
        tag = tags[0]["name"]
        for tag_search in tags:
            if searchword in tag_search["name"]:
                tag = tag_search["name"]
                break

        response = await session.get(
            f"https://danbooru.donmai.us/posts.json?tags={tag}+rating%3Ageneral+&z=5"
        )
        if not response.ok or not (await response.json()):
            return None

        images = await response.json()
        shuffle(images)

        return [
            {
                "url": img["file_url"],
                "source": img.get("source", "https://danbooru.donmai.us"),
                "artist": img.get("tag_string_artist", "UNKNOWN ARTIST"),
            }
            for img in (images)[:max_imgs]
        ]

class PrydwenCharacter:
    # Currently only for ZZZ
    def __init__(self, slug, name, session) -> None:
        self.slug = slug #store slug here
        self.name = name
        self.session = session
        self.cdn = "https://www.prydwen.gg/"

    @classmethod
    async def from_search(cls, query: str, service: str, session: CachedSession):
        response = await session.get(
            f"https://www.prydwen.gg/page-data/sq/d/2231396699.json"
        ) 

        resp_json: dict = await response.json()

        chara_nodes = resp_json['data']['allContentfulZzzCharacter']['nodes']
        name_code_mapping = {}

        for node in chara_nodes:
            name_code_mapping.update(
                {node['name']: node['slug']}
            )

        closest_match, *_ = process.extractOne(
            query,
            name_code_mapping.keys(),
            processor=default_process,
        )

        return cls(name_code_mapping[closest_match], closest_match, session)

    async def get_character_info(self, service):
        resp = await self.session.get(
            f"https://www.prydwen.gg/page-data/zenless/characters/{self.slug}/page-data.json"
        )
        r_json = await resp.json()
        return r_json

class ZZZCharacter(HakushCharacter):
    def __init__(self, id, name, session) -> None:
        super().__init__(id, name, session)

    @classmethod
    async def from_search(cls, query: str, session: CachedSession):
        return await super().from_search(query, "zzz", session)

    async def make_pages(self):
        agent_info = await self.get_character_info("zzz")

        pages = collections.defaultdict(list)
        options = []
        if agent_info.get("Name") == agent_info.get("PartnerInfo", {}).get("FullName"):
            display_name = agent_info.get("PartnerInfo", {}).get("FullName")
        else:
            display_name = f"{agent_info.get('PartnerInfo', {}).get('FullName')} ({agent_info.get('Name')})"
        thumbnail = f"{self.cdn}/zzz/UI/{agent_info.get('Icon')}.webp"

        pages["Story"] = [
            hk.Embed(
                title=display_name, url=f"https://zzz.hakush.in/character/{self.id}"
            )
            .set_image(thumbnail)
            .add_field(
                "Birthday",
                agent_info.get("PartnerInfo", {}).get("Birthday", "NA"),
                inline=True,
            )
            .add_field(
                "Camp", agent_info.get("PartnerInfo", {}).get("Race", "NA"), inline=True
            )
            .add_field("\u200b", "\u200b")
            .add_field(
                "Profile Info",
                agent_info.get("PartnerInfo", {}).get("TrustLv", {}).get("1", "")[:400]
                + "...",
            )
            .set_footer("Via: zzz.hakush.in", icon="https://hakush.in/bangboo.png")
        ]

        pages["Stats"] = [
            hk.Embed(
                title=display_name,
                url=f"https://zzz.hakush.in/character/{self.id}",
                description=(
                    f"**Base HP: ** {agent_info.get('Stats', {}).get('HpMax')}\n"
                    f"**Base ATK: ** {agent_info.get('Stats', {}).get('Attack')}\n"
                    f"**Impact: ** {agent_info.get('Stats', {}).get('BreakStun')}\n"
                    f"**Crit. Rate: ** {agent_info.get('Stats', {}).get('Crit', 0.1)/100}%\n"
                    f"**Crit. DMG: ** {agent_info.get('Stats', {}).get('CritDamage', 0.1)/100}%\n"
                    f"**Anomaly Prof: ** {agent_info.get('Stats', {}).get('ElementAbnormalPower')}\n"
                    f"**Anomaly Mastery: ** {agent_info.get('Stats', {}).get('ElementMystery')}\n"
                ),
            )
            .set_image(thumbnail)
            .set_footer("Via: zzz.hakush.in", icon="https://hakush.in/bangboo.png")
        ]

        pages["Mindscape"] = [
            hk.Embed(title=f"Mindscape Cinema Lv.{i}")
            .set_image(f"{self.cdn}/zzz/UI/Mindscape_{self.id}_{i}.webp")
            .set_footer("Via: zzz.hakush.in", icon="https://hakush.in/bangboo.png")
            for i in [2, 3, 1]
        ]

        character_images = await self.get_gallery_images(
            agent_info.get("PartnerInfo", {}).get("FullName"),
            self.session,
            searchword="zenless",
        )
        if character_images:
            total = len(character_images)
            pages["Gallery"] = [
                hk.Embed(title=f"{self.name} Image Gallery", url=img["source"])
                .set_image(img["url"])
                .set_author(name=img["artist"])
                .set_footer(
                    f"Via: Danbooru | Page {i+1}/{total}",
                    icon="https://danbooru.donmai.us/packs/static/danbooru-logo-128x128-ea111b6658173e847734.png",
                )
                for i, img in enumerate(character_images)
            ]

        for key in pages.keys():
            options.append(miru.SelectOption(label=key, value=key))

        return pages, options

class HSRCharacter(HakushCharacter):
    def __init__(self, id, name, session) -> None:
        super().__init__(id, name, session)

    @classmethod
    async def from_search(cls, query: str, session: CachedSession):
        return await super().from_search(query, "hsr", session)

    async def make_pages(self):
        chara_info = await self.get_character_info("hsr")
        pages = collections.defaultdict(list)
        options = []

        thumbnail = f"{self.cdn}/hsr/UI/avatardrawcard/{self.id}.webp"
        rarity_map = {
            "CombatPowerAvatarRarityType5": "★★★★★",
            "CombatPowerAvatarRarityType4": "★★★★",
            "NA": "NA",
        }


        pages["Story"] = [
            hk.Embed(
                title=chara_info.get("Name") or "NA", url=f"https://hsr.hakush.in/character/{self.id}"
            )
            .set_image(thumbnail)
            .add_field(
                "Rarity",
                rarity_map[chara_info.get("Rarity") or "NA"],
                inline=True,
            )
            .add_field(
                "Element", chara_info.get("DamageType") or "NA",
                inline=True
            )
            .add_field("\u200b", "\u200b")
            .add_field(
                "Character Info",
                chara_info.get("Desc", "")[:400]
                + "...",
            )
            .set_footer("Via: hsr.hakush.in", icon="https://hakush.in/silverwolf.png")
        ]
        
        pages["Stats"] = [
            hk.Embed(
                title=chara_info.get("Name", "NA"),
                url=f"https://hsr.hakush.in/character/{self.id}",
                description=(
                    f"**Base HP: ** {chara_info.get('Stats', {}).get('0', {}).get('HPBase')}\n"
                    f"**Base ATK: ** {chara_info.get('Stats', {}).get('0', {}).get('AttackBase')}\n"
                    f"**Base DEF: ** {chara_info.get('Stats', {}).get('0', {}).get('DefenceBase')}\n"
                    f"**Speed: ** {chara_info.get('Stats', {}).get('SpeedBase')}\n"
                    f"**Taunt: ** {chara_info.get('Stats', {}).get('BaseAggro')}\n"
                    f"**Max. Energy: ** {chara_info.get('SPNeed')}\n"
                ),
            )
            .set_image(thumbnail)
            .set_footer("Via: hsr.hakush.in", icon="https://hakush.in/silverwolf.png")

        ]
        
        
        pages["Eidolons"] = [
            hk.Embed(
                title=f"Eidolon Rank {i}: {chara_info.get('Ranks', {}).get(str(i), {}).get('Name', 'NA')}",
                )
            .set_image(f"{self.cdn}/hsr/UI/rank/_dependencies/textures/{self.id}/{self.id}_Rank_{i}.webp")
            .set_footer("Via: hsr.hakush.in", icon="https://hakush.in/silverwolf.png")
            for i in [1,2,3,4,5,6]
        ]
        
        character_images = await self.get_gallery_images(
            chara_info.get("Name"),
            self.session,
            searchword="honkai",
        )
        
        if character_images:
            total = len(character_images)
            pages["Gallery"] = [
                hk.Embed(title=f"{self.name} Image Gallery", url=img["source"])
                .set_image(img["url"])
                .set_author(name=img["artist"])
                .set_footer(
                    f"Via: Danbooru | Page {i+1}/{total}",
                    icon="https://danbooru.donmai.us/packs/static/danbooru-logo-128x128-ea111b6658173e847734.png",
                )
                for i, img in enumerate(character_images)
            ]
        
        for key in pages.keys():
            options.append(miru.SelectOption(label=key, value=key))
        
        return pages, options

class WuwaCharacter(HakushCharacter):
    def __init__(self, id, name, session) -> None:
        super().__init__(id, name, session)

    @classmethod
    async def from_search(cls, query: str, session: CachedSession):
        return await super().from_search(query, "ww", session)

    async def make_pages(self):
        chara_info = await self.get_character_info("ww")
        pages = collections.defaultdict(list)
        options = []

        thumbnail = f"{self.cdn}/{chara_info.get('Background').replace('/Game/Aki', 'ww').split('.')[0]}.webp"
        rarity_map = {
            5: "★★★★★",
            4: "★★★★",
            "NA": "NA",
        }
        pages["Story"] = [
            hk.Embed(
                title=chara_info.get("Name") or "NA", url=f"https://ww.hakush.in/character/{self.id}"
            )
            .set_image(thumbnail)
            .add_field(
                "Rarity",
                rarity_map[chara_info.get("Rarity") or "NA"],
                inline=True,
            )
            .add_field(
                "Affiliation",
                chara_info.get("CharaInfo", {}).get("Influence", "NA"), inline=True
            )
            .add_field("\u200b", "\u200b")
            .add_field(
                "Info",
                chara_info.get("CharaInfo", {}).get("Info", "NA")[:400]
                + "...",
            )
            .set_footer("Via: ww.hakush.in", icon="https://hakush.in/yangyang.png")
        ]
        


        
        character_images = await self.get_gallery_images(
            chara_info.get("Name"),
            self.session,
            searchword="wuthering",
        )
        
        if character_images:
            total = len(character_images)
            pages["Gallery"] = [
                hk.Embed(title=f"{self.name} Image Gallery", url=img["source"])
                .set_image(img["url"])
                .set_author(name=img["artist"])
                .set_footer(
                    f"Via: Danbooru | Page {i+1}/{total}",
                    icon="https://danbooru.donmai.us/packs/static/danbooru-logo-128x128-ea111b6658173e847734.png",
                )
                for i, img in enumerate(character_images)
            ]
        
        
        for key in pages.keys():
            options.append(miru.SelectOption(label=key, value=key))
        
        return pages, options
        


async def main():
    session = CachedSession()

    # ccc = await ZZZCharacter.from_search("caesar", session)
    # ccc = await PrydwenCharacter.from_search("qingyi", "zzz", session)
    # ci = await ccc.get_character_info('zzz')
    
    ccc = await WuwaCharacter.from_search("qingyi", session)
    # ci = await ccc.get_character_info('ww')
    # pgs, opts = await ccc.make_pages()
    
    
    import ipdb; ipdb.set_trace()
    await session.close()
    import ipdb

    ipdb.set_trace()


if __name__ == "__main__":
    asyncio.run(main())
