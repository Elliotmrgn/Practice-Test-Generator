import re
import os.path
from Chapter import Chapter


class Book:
    def __init__(self, doc):
        self.title = doc.metadata["title"]
        self.chapters = self._build_chapters(doc)


    def _build_chapters(self, doc):
        toc = doc.get_toc()  # gets able of contents
        chapters = []
        match_answer_chapter_to_question_chapter = 0  # matches answer chapter to corresponding question chapter
        is_answer_section = False  # indicator if started answer chapters

        for index, entry in enumerate(toc):
            # entry[0] = chapter depth, entry[1] = chapter title, entry[2] = starting page number
            title = entry[1]
            # subtract 1 from the starting page number to match the list index of pages
            start_page = entry[2] - 1
            # check the next chapter starting page and subtract 2 to get last page of the previous chapter

            end_page = toc[index + 1][2] - 2
            # Check if the chapter title indicates it will be a chapter with questions
            if self._is_question_chapter(title, is_answer_section):
                # Create chapter object with info extracted
                chapter = self._extract_question_chapter_info(doc, title, start_page, end_page)
                chapters.append(chapter)
            # Special case needed when answers chapters start the same as question chapters
            elif self._starts_answer_section(title):
                is_answer_section = True
            # Check if the chapter title indicates it will be a chapter with answers
            elif self._is_answer_chapter(title, is_answer_section):
                # Add answer data to chapter (end page needs to check start page of next chapter in case they overlap)
                self._extract_answer_info(doc, chapters[match_answer_chapter_to_question_chapter], start_page,
                                          end_page + 1)
                match_answer_chapter_to_question_chapter += 1
                # Once last chapter gets its answer data, stop checking
                if len(chapters) == match_answer_chapter_to_question_chapter:
                    break
        # Returns list of chapter objects
        return chapters

    def _is_question_chapter(self, title, is_answer_section):
        return not is_answer_section and title.startswith("Chapter ")

    def _starts_answer_section(self, title):
        return title.startswith("Appendix") or title.startswith("Answers to the ")

    def _is_answer_chapter(self, title, is_answer_section):
        return title.startswith("Answers to Chapter ") or (is_answer_section and title.startswith("Chapter"))

    def _extract_question_chapter_info(self, doc, title, start_page, end_page):
        # Grab the chapter number from the chapter title
        chapter_num = int(title.split(" ")[1])
        # Validate the start page is where questions begin
        start_page = self._validate_chapter_start_page(doc, start_page, end_page, False)
        # Validate the end page is where questions end
        end_page = self._validate_chapter_end_page(doc, start_page, end_page, False)
        total_questions = self._find_total_questions(doc, end_page)

        return Chapter(doc, chapter_num, title, start_page, end_page, total_questions)

    def _extract_page_data(self, doc, page_number, is_answer_section):
        # Extracts either questions from page or answer numbers
        page_text = doc[page_number].get_text()
        if page_text:
            if not is_answer_section:
                question_regex = r"^([\d|\s\d][\d' ']*)\.\s(.*(?:\r?\n(?![\s]*[A-Z]\.\s)[^\n]*|)*)(.*(?:\r?\n(?![\d|\s\d][\d' ']*\.\s)[^\n]*|)*)"
                page_questions = re.findall(question_regex, page_text, re.MULTILINE)
                return page_questions
            elif is_answer_section:
                answer_regex = r"^[\d|\s\d][\d' ']*(?=\.[\s]*[A-Z])"
                page_answers = re.findall(answer_regex, page_text, re.MULTILINE)
                return page_answers

    def _validate_chapter_start_page(self, doc, start_page, end_page, is_answer_section):
        # Checks which page is the actual starting page
        while start_page <= end_page:
            page_data = self._extract_page_data(doc, start_page, is_answer_section)
            # If a match is found return the starting page
            if page_data:
                return start_page
            # Otherwise check next page
            start_page += 1

    def _validate_chapter_end_page(self, doc, start_page, end_page, is_answers_section, total_questions=None):
        # Checks which page is the actual end page
        while start_page <= end_page:
            page_data = self._extract_page_data(doc, end_page, is_answers_section)
            if page_data:
                # When validating answer end pages make sure the last question is found
                if is_answers_section:
                    page_data = [int(question_num.replace(' ', '')) for question_num in page_data]
                    if max(page_data) == total_questions:
                        return end_page
                else:
                    return end_page

            end_page -= 1

    def _find_total_questions(self, doc, end_page):
        # Grabs the questions on the last page
        page_data = self._extract_page_data(doc, end_page, False)
        # Makes a list of the question numbers
        question_numbers = [int(questions[0].replace(' ', '')) for questions in page_data]
        # Returns the highest question
        return max(question_numbers)

    def _extract_answer_info(self, doc, chapter, start_page, end_page):
        chapter.answer_start_page = self._validate_chapter_start_page(doc, start_page, end_page, True)
        chapter.answer_end_page = self._validate_chapter_end_page(doc, start_page, end_page, True, chapter.total_questions)

    def print_chapters(self):
        for chapter in self.chapters:
            print(chapter)
            print()

    def __str__(self):
        book_str = f"Book Title: {self.title}\nChapters:\n"
        for i, chapter in enumerate(self.chapters, 1):
            book_str += f"\nChapter {i}:\n{chapter}\n"
        return book_str
