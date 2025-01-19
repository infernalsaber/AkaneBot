"""
In broad what this module aims to do:
Dropdown: Story, Stats, Ascension, Skills, Mindscape (a navigator having lvl1,2,3 images)

Story: lvl1 trust (rest spoilered), gender, birthdate, height
Stats: try for image
Ascension: try for emotes of everything
Skills: a list for now
Mindscape

"""

from rapidfuzz import process
from rapidfuzz.utils import default_process
from aiohttp_client_cache import CachedSession
import asyncio
import hikari as hk
import miru
import collections

class HakushCharacter:
    
    def __init__(self, id, name, session) -> None:
        self.id = id
        self.name = name
        self.session = session
        self.cdn = "https://api.hakush.in"
    
    @classmethod
    async def from_search(cls, query: str, service: str, session: CachedSession):
        response = await session.get(f"https://api.hakush.in/{service}/data/character.json") # Can be hsr, gi, zzz, ww

        resp_json: dict = await response.json()

        chara_codes = list(resp_json.keys())
        name_code_mapping = {}
                
        for code in chara_codes:
            name_code_mapping.update({resp_json[code].get('EN') or resp_json[code]['en']: code})
        
        closest_match, *_ = process.extractOne(
            query,
            name_code_mapping.keys(),
            processor=default_process,
        )
        
        return cls(name_code_mapping[closest_match], closest_match, session)

    async def get_character_info(self, service):
        return await (await self.session.get(f"https://api.hakush.in/{service}/data/en/character/{self.id}.json")).json()
    
    @staticmethod
    async def get_gallery_images(name, session, max_imgs=10):
        response = await session.get(f"https://danbooru.donmai.us/tags.json?search[name_matches]={name}")
        if not response.ok or not (await response.json()):
            return None
                
        tag = (await response.json())[0]['name']
        
        response = await session.get(f"https://danbooru.donmai.us/posts.json?tags={tag}+rating%3Ageneral+&z=5")
        if not response.ok or not (await response.json()):
            return None
        
        return [img['file_url'] for img in (await response.json())[:max_imgs]]

class ZZZCharacter(HakushCharacter):
    
    def __init__(self, id, name, session) -> None:
        super().__init__(id, name, session)
    
    @classmethod
    async def from_search(cls, query: str, session: CachedSession):
        return await super().from_search(query, 'zzz', session)
    
    async def make_pages(self):
        agent_info = await self.get_character_info('zzz')
        
        pages = collections.defaultdict(list)
        options = []
        if agent_info.get('Name') == agent_info.get('PartnerInfo', {}).get('FullName'):
            display_name = agent_info.get('PartnerInfo', {}).get('FullName')
        else:
            display_name = f"{agent_info.get('PartnerInfo', {}).get('FullName')} ({agent_info.get('Name')})" 
        thumbnail = f"{self.cdn}/zzz/UI/{agent_info.get('Icon')}.webp"
        
        pages['Story'] = [
            hk.Embed(
                title=display_name,
                url=f"https://zzz.hakush.in/character/{self.id}"
            )
            .set_image(thumbnail)
            .add_field("Birthday", agent_info.get('PartnerInfo', {}).get('Birthday'), inline=True)
            .add_field("Camp", agent_info.get('PartnerInfo', {}).get('Race'), inline=True)
            .add_field("\u200b", "\u200b")
            .add_field("Profile Info", agent_info.get('PartnerInfo', {}).get('TrustLv', {}).get('1', '')[:400] + "...")
            .set_footer("Via: zzz.hakush.in", icon='https://hakush.in/bangboo.png')
            
        ]
        
        pages['Stats'] = [
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
                )
            )
            .set_image(thumbnail)
            .set_footer("Via: zzz.hakush.in", icon='https://hakush.in/bangboo.png')
        ]
        
        pages['Mindscape'] = [    
            hk.Embed(
                title=f"Mindscape Cinema Lv.{i}"
            )
            .set_image(f"{self.cdn}/zzz/UI/Mindscape_{self.id}_{i}.webp")
            .set_footer("Via: zzz.hakush.in", icon='https://hakush.in/bangboo.png')
            for i in [2,3,1]
        ]
        
        
        character_images = await self.get_gallery_images(
            agent_info.get('PartnerInfo', {}).get('FullName'), self.session
        )
        if character_images:
            pages["Gallery"] = [
                hk.Embed(
                    title=f"{self.name} Image Gallery"
                )
                .set_image(img)
                .set_footer("Via: Danbooru", icon="https://danbooru.donmai.us/packs/static/danbooru-logo-128x128-ea111b6658173e847734.png") 
                for img in character_images
            ]
        
        for key in pages.keys():
            options.append(
                miru.SelectOption(
                    label=key,
                    value=key
                )
            )
        
        return pages, options
        



async def main():
    session = CachedSession()

    ccc = await ZZZCharacter.from_search("lucy", session)
    ci = await ccc.get_character_info('zzz')

    pgs, opts = await ccc.make_pages()
    import ipdb; ipdb.set_trace()

if __name__ == "__main__":
    asyncio.run(main())