import re
import PySimpleGUI as sg


def extract_questions(doc, chapter, chapter_num, page_text_rect):
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


def process_question(page_questions, chapter, chapter_num, question_bank, intentional_question_skip):

    # Loop over each question found
    for question in page_questions:
        # Check if the question text contains words that indicate it will have a graphic and skip the question
        # TODO: expand to skip other words that indicate the question will have graphics
        # TODO: Figure out method to extract graphics to display and remove the need to skip questions

        if 'match' in question[1].strip().lower():
            # Remove 1 from the chapters total questions
            chapter["total_questions"] -= 1
            # Indicate a question was skipped
            # TODO: Bug fix- If the last question processed is skipped the boolean flip is reverted.
            intentional_question_skip = True
            continue

        # Get the question number
        question_num = int(question[0])

        # Checks if the previous question is not found in the question bank
        # This indicates a question was unintentionally skipped.
        # Skips check on the first question, and skips if the question was skipped intentionally
        if question_num > 1 and question_num - 1 not in question_bank and not intentional_question_skip:
            # Allows user to input the question manually if desired
            handle_skipped_question(chapter, chapter_num, question_bank, question_num)

        # If a question was skipped, reset the flag
        if intentional_question_skip:
            intentional_question_skip = False

        # Clean up the format of the choices and add the question to the bank
        choices = choice_cleanup(question[2].strip())

        question_bank[question_num] = {
            "question_num": question_num,
            "question": question[1].strip(),
            "choices": choices,
            "chapter_number": chapter_num
        }



def handle_skipped_question(chapter, chapter_num, question_bank, question_num):
    # TODO: Needs to be redone with better input options
    # TODO: allow the user to check if the inputted question is correct and edit
    # TODO: create the ability to check if the next question is properly formatted as well
    # Prompts the user if they would like to input the skipped question manually
    user_input_yes_no = sg.popup_yes_no(
        f"Error adding chapter {chapter_num} question {question_num - 1}. Would you like to input it manually?")
    if user_input_yes_no == 'Yes':
        # Popup allowing user to input the question text
        user_input_question_text = sg.popup_get_text("Enter the question text")
        if user_input_question_text:
            while True:
                user_input_question_choices = sg.popup_get_text("Enter the choices")
                if user_input_question_choices:
                    # Passes inputted choices for formatting
                    user_input_question_choices = choice_cleanup(user_input_question_choices)
                    break
            # Add the question to the bank
            question_bank[question_num - 1] = {
                "question_num": question_num - 1,
                "question": user_input_question_text.strip(),
                "choices": user_input_question_choices,
                "chapter_number": chapter_num
            }
        # If no text is entered, skip the question
        else:
            chapter["total_questions"] -= 1
    # If user chooses no, skip the question
    else:
        chapter["total_questions"] -= 1


def choice_cleanup(unclean_choices):
    # Choices come out with lots of new lines, this cleans them up and matches them together
    choice_text = re.split('(^[a-zA-Z]\. +)', unclean_choices, flags=re.MULTILINE)
    choice_text = [choice.strip() for choice in choice_text if choice.strip()]
    clean_choices = [[choice_text[i][0], choice_text[i + 1]] for i in range(0, len(choice_text), 2)]

    return clean_choices
