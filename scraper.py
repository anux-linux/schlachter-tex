# -*- coding: utf-8 -*-
import requests
import codecs
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import bs4


class Webscraper:

    def __init__(self):
        self.base_url = "https://www.schlachterbibel.de"
        self.chapter = ""
        self.book = ""
        self.next_site = ""

    def get_book(self, soup):
        header = soup.find("h1")
        book = " ".join(header.text.split(" ")[:-1])
        return book

    def get_next_chapter(self, content):
        try:
            div = content.find_all("div", {"class": "chap_nav"})[0]
            href = div.find_all("a", string="Nächstes Kapitel >")
            return href
        except:
            print(content)
            raise

    def build_ref_string(self, hyperref):
        "\hyperref[1Mose:1-1]{Ps 104,2}; Ps 19,2}"
        if isinstance(hyperref, bs4.element.NavigableString):
            return hyperref
        else:
            url = hyperref["href"]
            splitted = url.split("/")
            verse = "1"
            if len(splitted) > 5:
                verse = splitted[5].split("?")[0].split("-")[0].split(".")[0]

            format_String = "\\hyperref[{0}:{1}-{2}]{{{3}}}".format(splitted[3], splitted[4].split("?")[0], verse,
                                                                    hyperref.text.strip())
            # print(format_String)
            return format_String

    def save_para(self, line, file, chapter, book_file, book_short):
        if isinstance(line, bs4.element.NavigableString):
            file.write(line.strip())
            # print(line)
        elif 'st' in line.attrs.get("class", ""):
            line_to_write = "\n\\superheding{{{}}}\n".format(line.text.strip())
            file.write(line_to_write)
            # print(line_to_write)
        elif 'sr' in line.attrs.get("class", ""):
            line_to_write = "\n\n\\suboverview{{{}}}\n\n\n".format(line.text.strip())
            file.write(line_to_write)
            # print(line_to_write)
        elif 'ct' in line.attrs.get("class", ""):
            try:
                if book_short == "Psalm":
                    full_text = line.text.strip()
                    if full_text.startswith("Psalm"):
                        split_chapter = full_text.split(" ")
                        self.chapter = split_chapter[1]
                        line_to_write = "\n\n\\subsection[{0}]{{Kapitel {0}}}\n\markboth{{{1} {0}}}{{}}\n\n".format(
                            self.chapter,
                            book_short)
                        file.write(line_to_write)
                    else:
                        line_to_write = "\n\\subtext{{{}}}\n".format(full_text)
                        file.write(line_to_write)
                else:
                    line_to_write = "\n\\subtext{{{}}}\n".format(line.text.strip())
                    file.write(line_to_write)
            except:
                # Special handling for Psalms
                print(line)
            # print(line_to_write)
        elif 'cr' in line.attrs.get("class", ""):
            ref_string = "\subref{"
            for hyperref in line:
                ref_string = ref_string + self.build_ref_string(hyperref)

            ref_string = ref_string + "}"
            # print(ref_string)
            file.write(ref_string)
            # print(line_to_write)
        elif 'versenum' in line.attrs.get("class", ""):
            # print(chapter)
            line_to_write = "\n\\paragraph{{{0}}}\\label{{{1}:{2}-{0}}}\n".format(line.text, book_file,
                                                                                  chapter)
            file.write(line_to_write)
            # print(line_to_write)
        elif 'footnote' in line.attrs.get("class", ""):
            footnote_string = line.text
            footnote_string = footnote_string.replace("[schließen]", "")

            footnote_string = re.sub(r"\[\d+\]", "", footnote_string)

            line_to_write = "\\footnote{{{}}} ".format(footnote_string.strip())
            file.write(line_to_write)
        elif 'smallcaps' in line.attrs.get("class", ""):
            smallcaps_string = line.text.strip()
            line_to_write = " \\textsl{{{}}} ".format(smallcaps_string)
            file.write(line_to_write)
        elif line.prettify().startswith("<i>"):
            content = line.prettify()
            content = content.replace("<i>", "")
            content = content.replace("</i>", "")
            content = content.strip()
            line_to_write = " \emph{{{}}} ".format(content)
            file.write(line_to_write)
        else:
            # print(line.attrs)
            # print(line)
            # print(line.text)
            return

    def save_line(self, line, file, book_short, book_file):
        if isinstance(line, bs4.element.NavigableString):
            if "XXXXX SELECT" in line:
                return
            file.write(line.strip())
            # print(line)
        elif not line.attrs:
            return
        elif 'breadcrumbs' in line.attrs.get("id", [""]):
            return
        elif 'book_nav' in line.attrs.get("class", [""]):
            return
        elif 'chap_num' in line.attrs.get("class", [""]):
            self.chapter = line.text
            line_to_write = "\n\n\n\\subsection[{0}]{{Kapitel {0}}}\n\markboth{{{1} {0}}}{{}}\n".format(self.chapter,
                                                                                                        book_short)
            file.write(line_to_write)
            #print(self.chapter)
            # print(line_to_write)
        elif 'para' in line.attrs.get("class", [""]):
            for para in line.contents:
                self.save_para(para, file, self.chapter, book_file, book_short)

    def start_scraping(self, book_short, book_long, book_file, start_chapter):
        with codecs.open("latex\\bible\\"+book_file + ".tex", 'w', "utf-8") as tex_file:

            self.next_site = urljoin(self.base_url, start_chapter)

            page = requests.get(self.next_site)
            soup = BeautifulSoup(page.content, "html.parser")
            content = soup.find(id="content")
            self.book = self.get_book(content)

            tex_file.truncate(0)
            tex_file.write(
                '\\section[{long}]{{{short}}}'.format(long=book_long, short=book_short) + '\n')

            relevant_content = content.contents
            for element in relevant_content:
                self.save_line(element, tex_file, book_short, book_file)

            print(self.chapter)
            next_chapter = self.get_next_chapter(content)
            if len(next_chapter) > 0:
                self.next_site = urljoin(self.base_url, next_chapter[0]["href"])

            while len(next_chapter) > 0:
                page = requests.get(self.next_site)
                soup = BeautifulSoup(page.content, "html.parser")
                content = soup.find(id="content")
                book = self.get_book(content)
                relevant_content = content.contents
                for element in relevant_content:
                    self.save_line(element, tex_file, book_short, book_file)
                    # tex_file.write(line + '\n')

                print(self.chapter)
                next_chapter = self.get_next_chapter(content)
                if len(next_chapter) > 0:
                    self.next_site = urljoin(self.base_url, next_chapter[0]["href"])


scraper = Webscraper()

book_list_AT = {"1. Mose": ["1. Mose (Genesis)", "1_mose", "/de/bibel/1_mose/1/"],
                "2. Mose": ["2. Mose (Exodus)", "2_mose", "/de/bibel/2_mose/1/"],
                "3. Mose": ["3. Mose (Leviticus)", "3_mose", "/de/bibel/3_mose/1/"],
                "4. Mose": ["4. Mose (Numeri)", "4_mose", "/de/bibel/4_mose/1/"],
                "5. Mose": ["5. Mose (Deuteronomium)", "5_mose", "/de/bibel/5_mose/1/"],
                "Josua": ["Josua", "josua", "/de/bibel/josua/1/"],
                "Richter": ["Richter", "richter", "/de/bibel/richter/1/"],
                "Ruth": ["Ruth", "ruth", "/de/bibel/ruth/1/"],
                "1. Samuel": ["1. Samuel", "1_samuel", "/de/bibel/1_samuel/1/"],
                "2. Samuel": ["2. Samuel", "2_samuel", "/de/bibel/2_samuel/1/"],
                "1. Könige": ["1. Könige", "1_koenige", "/de/bibel/1_koenige/1/"],
                "2. Könige": ["2. Könige", "2_koenige", "/de/bibel/2_koenige/1/"],
                "1. Chronik": ["1. Chronik", "1_chronik", "/de/bibel/1_chronik/1/"],
                "2. Chronik": ["2. Chronik", "2_chronik", "/de/bibel/2_chronik/1/"],
                "Esra": ["Esra", "esra", "/de/bibel/esra/1/"],
                "Nehemia": ["Nehemia", "nehemia", "/de/bibel/nehemia/1/"],
                "Esther": ["Esther", "esther", "/de/bibel/esther/1/"],
                "Hiob": ["Hiob", "hiob", "/de/bibel/hiob/1/"],
                "Psalm": ["Psalmen", "psalm", "/de/bibel/psalm/1/"],
                "Sprüche": ["Sprüche", "sprueche", "/de/bibel/sprueche/1/"],
                "Prediger": ["Prediger", "prediger", "/de/bibel/prediger/1/"],
                "Hoheslied": ["Hoheslied", "hoheslied", "/de/bibel/hoheslied/1/"],
                "Jesaja": ["Jesaja", "jesaja", "/de/bibel/jesaja/1/"],
                "Jeremia": ["Jeremia", "jeremia", "/de/bibel/jeremia/1/"],
                "Klagelieder": ["Klagelieder", "klagelieder", "/de/bibel/klagelieder/1/"],
                "Hesekiel": ["Hesekiel", "hesekiel", "/de/bibel/hesekiel/1/"],
                "Daniel": ["Daniel", "daniel", "/de/bibel/daniel/1/"],
                "Hosea": ["Hosea", "hosea", "/de/bibel/hosea/1/"],
                "Joel": ["Joel", "joel", "/de/bibel/joel/1/"],
                "Amos": ["Amos", "amos", "/de/bibel/amos/1/"],
                "Obadja": ["Obadja", "obadja", "/de/bibel/obadja/1/"],
                "Jona": ["Jona ", "jona", "/de/bibel/jona/1/"],
                "Micha": ["Micha", "micha", "/de/bibel/micha/1/"],
                "Nahum": ["Nahum", "nahum", "/de/bibel/nahum/1/"],
                "Habakuk": ["Habakuk", "habakuk", "/de/bibel/habakuk/1/"],
                "Zephanja": ["Zephanja", "zephanja", "/de/bibel/zephanja/1/"],
                "Haggai": ["Haggai", "haggai", "/de/bibel/haggai/1/"],
                "Sacharja": ["Sacharja", "sacharja", "/de/bibel/sacharja/1/"],
                "Maleachi": ["Maleachi", "maleachi", "/de/bibel/maleachi/1/"]}

book_list_NT = {"Matthäus": ["Matthäus", "matthaeus", "/de/bibel/matthaeus/1/"],
                "Markus": ["Markus", "markus", "/de/bibel/markus/1/"],
                "Lukas": ["Lukas", "lukas", "/de/bibel/lukas/1/"],
                "Johannes": ["Johannes", "johannes", "/de/bibel/johannes/1/"],
                "Apostelgeschichte": ["Apostelgeschichte", "apostelgeschichte", "/de/bibel/apostelgeschichte/1/"],
                "Römer": ["Römer", "roemer", "/de/bibel/roemer/1/"],
                "1. Korinther": ["1. Korinther ", "1_korinther", "/de/bibel/1_korinther/1/"],
                "2. Korinther": ["2. Korinther", "2_korinther", "/de/bibel/2_korinther/1/"],
                "Galater": ["galater", "galater", "/de/bibel/galater/1/"],
                "Epheser": ["epheser", "epheser", "/de/bibel/epheser/1/"],
                "Philipper": ["philipper", "philipper", "/de/bibel/philipper/1/"],
                "Kolosser": ["kolosser", "kolosser", "/de/bibel/kolosser/1/"],
                "1. Thessalonicher": ["1. Thessalonicher", "1_thessalonicher", "/de/bibel/1_thessalonicher/1/"],
                "2. Thessalonicher": ["2. Thessalonicher", "2_thessalonicher", "/de/bibel/2_thessalonicher/1/"],
                "1. Timotheus": ["1. Timotheus", "1_timotheus", "/de/bibel/1_timotheus/1/"],
                "2. Timotheus": ["2. Timotheus", "2_timotheus", "/de/bibel/2_timotheus/1/"],
                "Titus": ["titus", "titus", "/de/bibel/titus/1/"],
                "Philemon": ["philemon", "philemon", "/de/bibel/philemon/1/"],
                "Hebräer": ["hebraeer", "hebraeer", "/de/bibel/hebraeer/1/"],
                "Jakobus": ["jakobus ", "jakobus", "/de/bibel/jakobus/1/"],
                "1. Petrus": ["1. Petrus", "1_petrus", "/de/bibel/1_petrus/1/"],
                "2. Petrus": ["2. Petrus", "2_petrus", "/de/bibel/2_petrus/1/"],
                "1. Johannes": ["1. Johannes", "1_johannes", "/de/bibel/1_johannes/1/"],
                "2. Johannes": ["2. Johannes", "2_johannes", "/de/bibel/2_johannes/1/"],
                "3. Johannes": ["3. Johannes", "3_johannes", "/de/bibel/3_johannes/1/"],
                "Judas": ["Judas", "judas", "/de/bibel/judas/1/"],
                "Offenbarung": ["Offenbarung", "offenbarung", "/de/bibel/offenbarung/1/"]}


def scrap_AT():
    for book in book_list_AT:
        dic_content = book_list_AT[book]
        print("Start scraping " + book)
        scraper.start_scraping(book_short=book, book_long=dic_content[0], book_file=dic_content[1],
                               start_chapter=dic_content[2])


def scrap_NT():
    for book in book_list_NT:
        dic_content = book_list_NT[book]
        print("Start scraping " + book)
        scraper.start_scraping(book_short=book, book_long=dic_content[0], book_file=dic_content[1],
                               start_chapter=dic_content[2])


def scrap_all():
    scrap_AT()
    scrap_NT()


def scrap_specific(book):
    dic_content = book_list_AT[book]
    print("Start scraping " + book)
    scraper.start_scraping(book_short=book, book_long=dic_content[0], book_file=dic_content[1],
                           start_chapter=dic_content[2])

def print_include_data():
    for book in book_list_AT:
        print("\include{bible\\"+book_list_AT[book][1]+"}")
    print("\n\n")
    for book in book_list_NT:
        print("\include{"+book_list_NT[book][1]+"}")

#scrap_specific("Psalm")

#print_include_data()

import time
start_time = time.time()
scrap_all()
print("--- %s seconds ---" % (time.time() - start_time))
