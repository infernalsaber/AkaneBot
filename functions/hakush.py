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
        # pg = [
        if agent_info['Name'] == agent_info['PartnerInfo']['FullName']:
            display_name = agent_info['PartnerInfo']['FullName']
        else:
            display_name = f"{agent_info['PartnerInfo']['FullName']} ({agent_info['Name']})" 
        # display_name = agent_info['PartnerInfo']['FullName']
        thumbnail = f"{self.cdn}/zzz/UI/{agent_info['Icon']}.webp"
        
        pages['Story'] = (
            hk.Embed(
                title=display_name,
                url=f"https://zzz.hakush.in/character/{self.id}",
                # description=thumbnail
                # description="**Profile Info**" + agent_info['PartnerInfo']['TrustLv']['1'][:200]
            )
            .set_image(thumbnail)
            .add_field("Birthday", agent_info['PartnerInfo']['Birthday'], inline=True)
            .add_field("Camp", agent_info['PartnerInfo']['Race'], inline=True)
            .add_field("\u200b", "\u200b")
            .add_field("Profile Info", agent_info['PartnerInfo']['TrustLv']['1'][:400] + "...")
            .set_footer("Via: zzz.hakush.in", icon='https://zzz.hakush.in/_app/immutable/assets/hakushin.Dy6InycZ.svg')
            
        )
        
        pages['Stats'] = (
            hk.Embed(
                title=display_name,
                url=f"https://zzz.hakush.in/character/{self.id}",
                description=(
                    f"**Base HP: ** {agent_info['Stats']['HpMax']}\n"
                    f"**Base ATK: ** {agent_info['Stats']['Attack']}\n"
                    f"**Impact: ** {agent_info['Stats']['BreakStun']}\n"
                    f"**Crit. Rate: ** {agent_info['Stats']['Crit']/100}%\n"
                    f"**Crit. DMG: ** {agent_info['Stats']['CritDamage']/100}%\n"
                    f"**Anomaly Prof: ** {agent_info['Stats']['ElementAbnormalPower']}\n"
                    f"**Anomaly Mastery: ** {agent_info['Stats']['ElementMystery']}\n"                    
                )
            )
            .set_image(thumbnail)
            .set_footer("Via: zzz.hakush.in")
        )
        
        pages['Mindscape'] = (    
            hk.Embed(
                title="Mindscape Cinema Lv.3"
            )
            .set_image(f"{self.cdn}/zzz/UI/Mindscape_{self.id}_3.webp")
            .set_footer("Via: zzz.hakush.in")
        )
        
        
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