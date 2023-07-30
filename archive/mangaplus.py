import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By  # test
from selenium.webdriver.support import expected_conditions as EC  # test
from selenium.webdriver.support.ui import WebDriverWait  # test

string = re.compile(r"Chapter (\d+): ([^\(]+)")


# link = "https://mangaplus.shueisha.co.jp/titles/100037"


# link = "https://mangaplus.shueisha.co.jp/titles/100191"
def get_chapter(link: str, latest_chapter: int = 0):
    driver = webdriver.Firefox()

    driver.get(link)

    wait = WebDriverWait(driver, 10)  # Wait for a maximum of 10 seconds
    wait.until(
        EC.presence_of_element_located(
            (By.CLASS_NAME, "ChapterListItem-module_chapterListItem_ykICp")
        )
    )

    page_source = driver.page_source
    print(page_source)

    para_class = "ChapterListItem-module_title_3Id89"
    link_class = "ChapterListItem-module_commentContainer_1P6qt"
    testing_shit_out = "TitleDetail-module_topAd_MtvCi"

    para_class = "ChapterListItem-module_title_3Id89"
    link_class = "ChapterListItem-module_commentContainer_1P6qt"
    testing_shit_out = "TitleDetail-module_topAd_MtvCi"

    soup = BeautifulSoup(page_source)

    # elements = soup.find_all(class_=link_class)  # Replace 'your-class-name' with the actual class name you want to find
    # # print(elements)
    # chapters = (list(link['href'].split('/')[-1] for link in elements))
    # print(chapters)

    # elements = soup.find_all(class_=para_class)  # Replace 'your-class-name' with the actual class name you want to find
    # wp_text = ""
    # for element in elements:
    #     wp_text += element.text
    #     wp_text += "("
    # print(element.text)

    # print()

    chapter_names = string.findall(wp_text)
    print(chapter_names)

    ans = {}

    # for i, chapter_num, chapter_name in enumerate(chapter_names):
    #     if chapter_num > latest chapter:
    #         ans['chapter'] = chapter_num
    #         ans['chapter_name'] = chapter_name
    #         ans['chapter_id'] =

    elements = soup.find_all(class_=("ChapterListItem-module_chapterListItem_ykICp"))
    string = re.compile(r"Chapter (\d+): ([^\(]+)")

    for element in elements:
        chapter = element.find("p", class_="ChapterListItem-module_title_3Id89").text
        print(chapter)
        # print(string.findall(chapter))
        chapter_num, chapter_name = string.findall(chapter)[0]
        if int(chapter_num) <= latest_chapter:
            continue
        ans["num"] = chapter_num
        ans["name"] = chapter_name
        ans["thumbnail"] = element.find(
            "img", class_="ChapterListItem-module_thumbnail_1w6kS"
        )["data-src"]
        ans["id"] = element.find(
            "a", class_="ChapterListItem-module_commentContainer_1P6qt"
        )["href"].split("/")[-1]

    driver.quit()
    return ans


if __name__ == "__main__":
    print(get_chapter("https://mangaplus.shueisha.co.jp/titles/100037", 123))
