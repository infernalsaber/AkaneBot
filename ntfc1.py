from curl_cffi import requests
from bs4 import BeautifulSoup

cookies = {
    # 'cf_clearance': 'UeG.pHOocjA9LmiS1flvDnoQ3geGmioNh4DfGEzFp9I-1758745617-1.2.1.1-0HeO9XROfygQG9bCQFcsJhcdqKxd.oNa6FjXpSx.n.rpZc2zlTf2vwf9oOoct0f2EE0W5ZltIN3jZlxs1vAyk2A6rwk_pZvj6uyz4hVSHTAcQ.u5m9aFV9312d1HmIVJNdu9BP9hlWYn.UET6viA6oMvDF50uOA4vNxG.qzFFVgxk3mEWL6DhpNjoelOCRFIyV9a77twZP6LPHJ.5tqAtevw6W2jD0YHAlvSSIEFwOM',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.6',
    'cache-control': 'no-cache',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://www.novelupdates.com',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'referer': 'https://www.novelupdates.com/series-finder/?sf=1&sh=re%3Azero&sort=sdate&order=desc',
    'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'sec-gpc': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    # 'cookie': 'cf_clearance=UeG.pHOocjA9LmiS1flvDnoQ3geGmioNh4DfGEzFp9I-1758745617-1.2.1.1-0HeO9XROfygQG9bCQFcsJhcdqKxd.oNa6FjXpSx.n.rpZc2zlTf2vwf9oOoct0f2EE0W5ZltIN3jZlxs1vAyk2A6rwk_pZvj6uyz4hVSHTAcQ.u5m9aFV9312d1HmIVJNdu9BP9hlWYn.UET6viA6oMvDF50uOA4vNxG.qzFFVgxk3mEWL6DhpNjoelOCRFIyV9a77twZP6LPHJ.5tqAtevw6W2jD0YHAlvSSIEFwOM',
}

data = [
    ('releases_mm', 'min'),
    ('rk_releases', ''),
    ('releases_mm', 'max'),
    ('rk_rfreq', ''),
    ('releases_mm', 'min'),
    ('rk_rreviews', ''),
    ('releases_mm', 'min'),
    ('rk_sr', ''),
    ('releases_mm', 'min'),
    ('rk_rcount', ''),
    ('releases_mm', 'min'),
    ('rk_sread', ''),
    ('releases_mm', 'min'),
    ('ardate_first', ''),
    ('releases_mm', 'min'),
    ('ardate', ''),
    ('releases_mm', 'and'),
    ('releases_mm', 'or'),
    ('releases_mm', 'exclude'),
    ('storystatus', '1'),
    ('argroup', ''),
    ('argroup', ''),
    ('argroup', ''),
    ('seriescontains', 're:zero'),
    ('series_text', 're:zero'),
    ('sortmyresults', 'sread'),
    ('sortmyorder', 'desc'),
]

response = requests.post(
    'https://www.novelupdates.com/series-finder/?sf=1&sh=re:zero&sort=sread&order=desc',
    cookies=cookies,
    headers=headers,
    data=data,
)

with open('test.html', 'w+', encoding='utf-8') as f:
    f.write(response.text)
import ipdb; ipdb.set_trace()