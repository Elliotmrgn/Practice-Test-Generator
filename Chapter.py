import re, json

# TODO: clean answer and explanation
#   build json exporter
class Chapter:
    def __init__(self, doc, chapter_num, chapter_title, start_page_check, end_page_check, total_questions):
        self.number = chapter_num
        self.title = chapter_title
        self.question_start_page = start_page_check
        self.question_end_page = end_page_check
        self.answer_start_page = 0
        self.answer_end_page = 0
        self.total_questions = total_questions
        self.question_bank = []


    def _extract_page_data(self, doc, page_number):
        return doc[page_number].get_textbox((0, 60, doc[0].rect.width, doc[0].rect.height))

    def _extract_chapter_text(self, doc, start_page, end_page):
        # Builds a string of all text from the chapter
        chapter_text = ""
        for page in range(start_page, end_page+1):
            chapter_text += self._extract_page_data(doc, page)
            chapter_text += '\n'

        return chapter_text

    def _extract_questions(self, doc):
        regex_questions = r"^([\d|\s\d][\d' ']*)\.\s(.*(?:\r?\n(?![\s]*[a-zA-Z]\.\s)[^\n]*|)*)(.*(?:\r?\n(?![\d|\s\d][\d' ']*\.\s)[^\n]*|)*)"
        question_chapter_text = self._extract_chapter_text(doc, self.question_start_page, self.question_end_page)
        chapter_questions = re.findall(regex_questions, question_chapter_text, re.MULTILINE)
        return chapter_questions

    def _extract_answers(self, doc):
        regex_answers = r"^([\d|\s\d][\d' ']*)\.\s*((?:[A-Z][,\s]*[\sand\s]*[\sor\s]*)*[A-Z])\.\s*((?:.*(?:\r?\n(?![\d|\s\d][\d\s]*\.\s)[^\n]*)*))"
        answer_chapter_text = self._extract_chapter_text(doc, self.answer_start_page, self.answer_end_page)
        chapter_answers = re.findall(regex_answers, answer_chapter_text, re.MULTILINE)
        chapter_answers = self._remove_answer_overflow(chapter_answers)

        return chapter_answers

    def build_question_bank(self, doc):
        question_bank = []
        # Extracts all questions and answers from the chapter
        chapter_questions = self._extract_questions(doc)
        chapter_answers = self._extract_answers(doc)
        # Matches and combines the data
        combined_data = self._combine_questions_and_answers(chapter_questions, chapter_answers)
        # Iterates through each item and builds a dictionary of questions
        for entry in combined_data:
            question_number = self._clean_matched_number(entry[0])
            question_text = self._clean_quesiton_text(entry[1])
            choices = self._clean_choices(entry[2])
            correct_answer = entry[3]
            answer_explanation = entry[4]

            question_bank.append({
                "question_number": question_number,
                "question_text": question_text,
                "choices": choices,
                "correct_answer": correct_answer,
                "answer_explanation": answer_explanation
            })

        self.question_bank = question_bank

    def _clean_matched_number(self, question_number):
        # Strips question number and removes spaces
        if isinstance(question_number, str):
            question_number = int(question_number.strip().replace(' ', ''))
        return question_number

    def _clean_quesiton_text(self, question_text):
        question_text = question_text.strip().replace('\n', ' ').replace('  ', ' ')
        return question_text

    def _clean_choices(self, choices):
        choices = re.split('(^[a-zA-Z]\. +)', choices, flags=re.MULTILINE)
        choices = [choice.strip() for choice in choices if choice.strip()]
        choices = [[choices[i][0], choices[i + 1]] for i in range(0, len(choices), 2)]
        return choices

    def _remove_answer_overflow(self, chapter_answers):
        # Removes answers from the beginning and end of the matches to remove overflow from other chapters
        while chapter_answers and self._clean_matched_number(chapter_answers[0][0]) != 1:
            del (chapter_answers[0])
        while chapter_answers and self._clean_matched_number(chapter_answers[-1][0]) != self.total_questions:
            del (chapter_answers[-1])

        return chapter_answers

    def _combine_questions_and_answers(self, chapter_questions, chapter_answers):
        matched_data = []
        question_index = 0
        answer_index = 0
        while question_index < len(chapter_questions) and answer_index < len(chapter_answers):
            question_number = self._clean_matched_number(chapter_questions[question_index][0])
            answer_number = self._clean_matched_number(chapter_answers[answer_index][0])
            if question_number == answer_number:
                # Match found
                question_text = chapter_questions[question_index][1]
                choices = chapter_questions[question_index][2]
                correct_answer = chapter_answers[answer_index][1]
                answer_explanation = chapter_answers[answer_index][2]
                # Create tuple with matched data
                matched_data.append((question_number, question_text, choices, correct_answer, answer_explanation))
                question_index += 1
                answer_index += 1
            elif question_number < answer_number:
                question_index += 1
                self.total_questions -= 1
            else:
                answer_index += 1
                self.total_questions -= 1

        return matched_data

    def json_output(self):
        with open("chapter_map", "w") as json_file:
            json.dump(self.question_bank, json_file)

    def __str__(self):
        return (f"Chapter {self.number}: {self.title}\n"
                f"Questions: Pages {self.question_start_page}-{self.question_end_page}\n"
                f"Answers: Pages {self.answer_start_page}-{self.answer_end_page}\n"
                f"Total Questions: {self.total_questions}")
