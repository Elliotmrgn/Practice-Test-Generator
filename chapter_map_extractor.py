import re
import PySimpleGUI as sg

# TODO: Fix naming convention
# TODO: Look into using regex match instead of findall for spillover case

def extract_chapter_map(doc):
    """
    This function is used to build a map of the pdfs chapters that contain questions.
    It finds chapters that contain questions and builds a DICT of chapter number, chapter title, starting page,
    ending page, and the total number of questions for the chapter.
    Then it finds chapters that contain the answers to the questions and adds to the DICT an answer starting page, and
    answer ending page

    :param doc:
    :return chapter_map:
    """

    # Get the table of contents from the document
    tableofcontents = doc.get_toc()
    # Initialize an empty list to store chapter information
    chapter_map = []
    # Initialize variables to match answer chapters to corresponding question chapter
    answer_chapter_match = 0
    is_answer_section = False

    # Iterate through the table of contents
    for i, chapter in enumerate(tableofcontents):
        # If not in an answer section and the chapter starts with "Chapter "
        if not is_answer_section and chapter[1].startswith("Chapter "):
            # Extract information for a regular chapter and append it to chapter_map
            chapter_map.append(question_chapter_info_extract(doc, tableofcontents, i, chapter))
        # Checks if the current chapter marks the beginning of an answer section. (needed for some books)
        elif chapter[1].startswith("Appendix Answers") or chapter[1].startswith("Answers"):
            is_answer_section = True
        # If a chapter is an answer chapter or an answer section
        elif chapter[1].startswith("Answers to Chapter ") or (is_answer_section and chapter[1].startswith("Chapter")):
            # Extract info for a chapter containing answers
            answer_chapter_info_extract(doc, tableofcontents, i, chapter_map, answer_chapter_match, chapter)
            answer_chapter_match += 1

    return chapter_map


def question_chapter_info_extract(doc, toc, i, chapter):

    # Regex with 3 capture groups [0] = question number, [1] = question text, [2] = question choices
    regex_question_and_choices = \
        r"^([\d|\s\d][\d' ']*)\.\s(.*(?:\r?\n(?![\s]*[A-Z]\.\s)[^\n]*|)*)(.*(?:\r?\n(?![\d|\s\d][\d' ']*\.\s)[^\n]*|)*)"
    # Regex checking if the page starts with choices. Used in case the last question's choices spill over to next page
    regex_choice_spillover = r"^[A-Z]*\.\s(?:.*(?:\r?\n(?!\d[\d\s]*\.\s)[^\n]*|)*)"
    # Get the starting page from the table of contents
    start_page_check = chapter[2] - 1
    # Get the ending page by checking the starting page of the next chapter and subtracting 1
    end_page_check = toc[i + 1][2] - 2

    # Initialize total questions and a special case if the question spills over to the next page
    total_questions = 0
    spillover_case = False

    # Loop until all info for the chapter is found
    while True:
        # Attempts to extract questions from the starting page
        question_check = re.findall(regex_question_and_choices, doc[start_page_check].get_text(), re.MULTILINE)

        # If the starting page contains a question and if the choices are on the same page
        if question_check and question_check[0][2]:
            # Attempts to match questions from the page
            last_page_text = re.findall(regex_question_and_choices, doc[end_page_check].get_text(), re.MULTILINE)
            # Attempts to match spillover choices if the page starts with choices
            last_page_spillover_case = re.findall(regex_choice_spillover, doc[end_page_check].get_text(), re.MULTILINE)
            # If questions were found
            if last_page_text:
                # Stores final question number as total questions
                total_questions = int(last_page_text[-1][0])
                # If choices spill over add a page to the ending page
                if spillover_case:
                    end_page_check += 1
                break
            # If spillover questions were found go back a page (ensures last question number is still found)
            elif last_page_spillover_case and not last_page_text:
                spillover_case = True
                end_page_check -= 1
            # If no matches found go back a page
            else:
                end_page_check -= 1
                # Break case if something goes wrong and the end page catches up to the start page
                if end_page_check <= start_page_check:
                    break
        # If no questions were found go forward a page
        else:
            start_page_check += 1
            # Break case if something goes wrong and the start page catches up to the end page
            if start_page_check >= end_page_check:
                break

    # Return dictionary containing chapter information
    return {
        "number": int(chapter[1].split(" ")[1]),  # Extract chapter number from title
        "title": chapter[1],  # Chapter Title
        "question_start_page": start_page_check,  # First page questions were found
        "question_end_page": end_page_check,  # Last page questions were found
        "total_questions": total_questions  # Total number of questions
    }


def answer_chapter_info_extract(doc, toc, i, chapter_map, answer_chapter_match, chapter):
    # Regex to match a question number and answer
    regex_answer_nums = r"^[\d|\s\d][\d' ']*(?=\.[\s]*[A-Z])"
    # Adds the starting page of answers to the matching chapter
    chapter_map[answer_chapter_match]["answer_start_page"] = chapter[2] - 1
    # Pulls the ending page of answers from the next chapter's starting page - 1
    end_page_check = toc[i + 1][2] - 1

    while True:
        # Gets the text from the ending page
        doc_text = doc[end_page_check].get_text()
        # If the page has text and answers are found
        if doc_text and re.findall(regex_answer_nums, doc_text, re.MULTILINE):
            # Matches the answer numbers from the last page
            last_answer_page_data = re.findall(regex_answer_nums, doc_text, re.MULTILINE)
            last_answer_page_data = [number.replace(' ', '') for number in last_answer_page_data]
            #  If the last question from the chapter is found in the matched answer numbers
            if str(chapter_map[answer_chapter_match]["total_questions"]) in last_answer_page_data:
                # Set the end page for the answer chapter
                chapter_map[answer_chapter_match]["answer_end_page"] = end_page_check
                break
            # Check if the page being checked caught up to the answer page
            elif end_page_check == chapter_map[answer_chapter_match]["answer_start_page"]:
                sg.popup_error("ERROR FINDING ANSWER CHAPTERS")
                break
            # Decrement the end page for further checking
            else:
                end_page_check -= 1
        # Decrement the end page for further checking
        else:
            end_page_check -= 1
