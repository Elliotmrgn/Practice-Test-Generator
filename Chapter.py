class Chapter:
    def __init__(self, chapter_num, chapter_title, start_page_check, end_page_check, total_questions):
        self.number = chapter_num
        self.title = chapter_title
        self.question_start_page = start_page_check
        self.question_end_page = end_page_check
        self.answer_start_page = 0
        self.answer_end_page = 0
        self.total_questions = total_questions

    def extract_questions(self, doc, chapter, chapter_num, page_text_rect):
        """
        This function extracts all the question data from the chapters with questions and stores them in a DICT.
        It stores the pages of text until it finds a page that starts with a new question to avoid cases where parts of the
        question spill over to the next page.
        Once it finds the next instance of a page starting with a new question or the last page of the chapter, it processes
        the page data to extract the questions, question numbers, and choices.
        """
        # Regular expressions for matching questions and choices
        regex_question_and_choices = \
            r"^([\d|\s\d][\d' ']*)\.\s(.*(?:\r?\n(?![\s]*[a-zA-Z]\.\s)[^\n]*|)*)(.*(?:\r?\n(?![\d|\s\d][\d' ']*\.\s)[^\n]*|)*)"
        regex_question_num = r"^([\d|\s\d][\d' ']*)\.\s"

        # Initialize question bank and other variables
        question_bank = {}
        page_number = chapter["question_start_page"]
        multi_page_text = ""
        # Initialize check for if a question was skipped
        intentional_question_skip = False

        # Loop through pages in the chapter
        while page_number <= chapter["question_end_page"]:
            # Get text from the page
            doc_text = doc[page_number].get_textbox(page_text_rect)

            # Check if the page starts with a question number
            clean_page_check = re.match(regex_question_num, doc_text)

            # Condition to check when the stored page text will be processed to extract questions
            # Checks when the next clean page is found and if that pages starting question has already been stored (prevents chapter overlap)
            # Also skips the first page since no text has been stored yet and automatically triggers on the last page
            if (clean_page_check and int(clean_page_check[1]) not in question_bank and page_number != chapter[
                "question_start_page"]) or page_number == chapter["question_end_page"]:
                # Last page condition to add the final pages to the data
                if page_number == chapter["question_end_page"]:
                    multi_page_text += f"\n{doc_text}"

                # Extract question number, question text, and choices from the text
                page_questions = re.findall(regex_question_and_choices, multi_page_text, re.MULTILINE)

                # Process questions
                process_question(page_questions, chapter, chapter_num, question_bank, intentional_question_skip)

                # Reset multi-page text
                multi_page_text = ""

            # Add current page text to multi-page text
            multi_page_text += f"\n{doc_text}"

            # Move to the next page
            page_number += 1

        return question_bank
