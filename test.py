import re
import PySimpleGUI as sg
from Chapter import Chapter
class Book:
    def __init__(self, doc):
        self.title = doc.metadata["title"]
        self.chapters = self.build_list_of_chapters(doc)
    def build_list_of_chapters(self, doc):
        tableofcontents = doc.get_toc()
        list_of_chapters = []
        answer_chapter_match = 0
        is_answer_section = False
        for i, chapter in enumerate(tableofcontents):
            if not is_answer_section and chapter[1].startswith("Chapter "):
                chapter_obj = self.question_chapter_info_extract(doc, tableofcontents, i, chapter)
            elif chapter[1].startswith("Appendix Answers") or chapter[1].startswith("Answers"):
                is_answer_section = True
            elif chapter[1].startswith("Answers to Chapter ") or (is_answer_section and chapter[1].startswith("Chapter")):
                end_page_check = tableofcontents[i + 1][2] - 1
                self.answer_chapter_info_extract(doc, end_page_check, chapter, chapter_obj)
                answer_chapter_match += 1

        return list_of_chapters
    def question_chapter_info_extract(self, doc, toc, i, chapter):
        regex_question_and_choices = \
            r"^([\d|\s\d][\d' ']*)\.\s(.*(?:\r?\n(?![\s]*[A-Z]\.\s)[^\n]*|)*)(.*(?:\r?\n(?![\d|\s\d][\d' ']*\.\s)[^\n]*|)*)"
        regex_choice_spillover = r"^[A-Z]*\.\s(?:.*(?:\r?\n(?!\d[\d\s]*\.\s)[^\n]*|)*)"
        start_page_check = chapter[2] - 1
        end_page_check = toc[i + 1][2] - 2
        total_questions = 0
        spillover_case = False
        while True:
            question_check = re.findall(regex_question_and_choices, doc[start_page_check].get_text(), re.MULTILINE)
            if question_check and question_check[0][2]:
                last_page_text = re.findall(regex_question_and_choices, doc[end_page_check].get_text(), re.MULTILINE)
                last_page_spillover_case = re.findall(regex_choice_spillover, doc[end_page_check].get_text(), re.MULTILINE)
                if last_page_text:
                    total_questions = int(last_page_text[-1][0])
                    if spillover_case:
                        end_page_check += 1
                    break
                elif last_page_spillover_case and not last_page_text:
                    spillover_case = True
                    end_page_check -= 1
                else:
                    end_page_check -= 1
                    if end_page_check <= start_page_check:
                        break
            else:
                start_page_check += 1
                if start_page_check >= end_page_check:
                    break
        chapter_num = int(chapter[1].split(" ")[1]),
        chapter_title = chapter[1],
        return Chapter(chapter_num, chapter_title, start_page_check, end_page_check, total_questions)
    def answer_chapter_info_extract(self, doc, end_page_check, chapter, chapter_obj):
        regex_answer_nums = r"^[\d|\s\d][\d' ']*(?=\.[\s]*[A-Z])"
        chapter_obj.answer_start_page = chapter[2] - 1

        while True:
            doc_text = doc[end_page_check].get_text()
            if doc_text and re.findall(regex_answer_nums, doc_text, re.MULTILINE):
                last_answer_page_data = re.findall(regex_answer_nums, doc_text, re.MULTILINE)
                last_answer_page_data = [number.replace(' ', '') for number in last_answer_page_data]
                if str(chapter_obj.total_questions) in last_answer_page_data:
                    chapter_obj.answer_end_page = end_page_check
                    break
                elif end_page_check == chapter_obj.answer_start_page:
                    sg.popup_error("ERROR FINDING ANSWER CHAPTERS")
                    break
                else:
                    end_page_check -= 1
            else:
                end_page_check -= 1
        self.chapters.append(chapter_obj)