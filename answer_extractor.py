import re
import PySimpleGUI as sg


def extract_answers(doc, chapter, page_text_rect):
    """
    This function extracts the answers and explanations from the document and adds them to the matching question
    """
    regex_answers = r"^([\d|\s\d][\d' ']*)\.\s*((?:[A-Z][,\s]*[\sand\s]*[\sor\s]*)*[A-Z])\.\s*((?:.*(?:\r?\n(?![\d|\s\d][\d\s]*\.\s)[^\n]*)*))"
    regex_answer_num = r"^([\d|\s\d][\d' ']*)\.\s[A-Z]"
    multi_page = ""
    page_number = chapter["answer_start_page"]

    # Loops through pages until last page is hit
    while page_number <= chapter["answer_end_page"]:
        doc_text = doc[page_number].get_textbox(page_text_rect)

        # Check if the first line on the page is an answer. Skips 1st page and runs on last page
        # This is to extract the answers when there is no overflow
        if (re.match(regex_answer_num, doc_text.strip()) and page_number != chapter["answer_start_page"]) or page_number == chapter["answer_end_page"]:
            if page_number == chapter["answer_end_page"]:
                # Checks if the next chapters answers start on the same page
                if f"Chapter {chapter['number'] + 1}" in doc_text:
                    # Splits the text into lines to remove the next chapters answers
                    lines = doc_text.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith(f"Chapter {chapter['number'] + 1}"):
                            # Keeps only text from current chapter
                            doc_text = '\n'.join(lines[:i])
                            break
                multi_page += f"\n{doc_text}"

            # Finds all answers and explanations
            answer_data = re.findall(regex_answers, multi_page, re.MULTILINE)
            # Cycles through each answer
            for answer in answer_data:
                question_num = int(answer[0].replace(' ', ''))
                # Skips answers for questions that were skipped and not added to the question bank
                if question_num not in chapter["question_bank"]:
                    continue

                
                # check if the current question is not 1 and this chapters question 1 doesn't exist then skip
                # Ensures that answers are starting at question 1
                if question_num != 1 and "answer" not in chapter["question_bank"][1]:
                    continue
                # check if there is already an answer built for the current question then break
                elif "answer" in chapter["question_bank"][question_num]:
                    break
                # otherwise build the answer
                else:
                    # Check if there is an error adding an answer due to formatting
                    # Skips the first question since there is no previous question, then checks if the previous question
                    # exists in the bank and if the answer is missing from it.
                    if question_num > 1 and question_num - 1 in chapter["question_bank"] and 'answer' not in chapter["question_bank"][question_num - 1]:
                        handle_skipped_answer(chapter, question_num)

                    all_answers = answer[1]
                    
                    # Check for multiple answers
                    if ',' in answer[1] or 'and' in answer[1]:
                        all_answers = answer[1].replace(',', '').replace(' ', '').replace('and', '').replace('or', '')

                    chapter["question_bank"][question_num]["answer"] = list(all_answers)
                    chapter["question_bank"][question_num]["explanation"] = answer[2]

            multi_page = ""

        multi_page += f"\n{doc_text}"
        page_number += 1

def handle_skipped_answer(chapter, question_num):
    # Catches if an answer was skipped and allows user input

    chapter_num = chapter['question_bank'][question_num - 1]['chapter_number']
    # Prompt the user if they want to enter the answer manually if not remove the question from the bank
    user_input_yes_no = sg.popup_yes_no(
        f"Error adding answer for chapter {chapter_num} question {question_num - 1}. Would you like to add it manually?")
    # Yes input allows the user to submit the answer manually
    if user_input_yes_no == 'Yes':
        while True:
            # Prompt to enter answers
            user_error_answer = sg.popup_get_text(
                f"Enter the correct answer to chapter {chapter_num} question {question_num - 1}")
            # removes commas and spaces from input
            user_error_answer = user_error_answer.strip().replace(' ', '').replace(',', '')
            # Keeps prompt up until an answer is submitted
            if user_error_answer:
                break
        while True:
            # Prompt to enter answer explanation
            user_error_explanation = sg.popup_get_text(
                f"Enter the explanation to chapter {chapter_num} question {question_num - 1}")
            # Keeps prompt up until an explanation is submitted
            if user_error_explanation:
                break
        # Adds the answer and explanation to the missed question
        chapter["question_bank"][question_num - 1]["answer"] = list(user_error_answer)
        chapter["question_bank"][question_num - 1]["explanation"] = user_error_explanation
    # No input will remove the question missing the answer and subtract one from the total questions
    else:
        chapter["total_questions"] -= 1
        del (chapter["question_bank"][question_num - 1])
    