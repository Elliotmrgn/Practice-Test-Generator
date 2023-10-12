import json
import os
import random
import re
import string

import fitz
import pickle

import PySimpleGUI as sg

# TODO: Manual editing of questions
# TODO: Image processing or manual adding

def extract_chapter_map(doc, page_text_rect):
    toc = doc.get_toc()
    chapter_map = []
    answer_chapter_match = 0
    for i, chapter in enumerate(toc):
        if chapter[0] == 1 and chapter[1].startswith("Chapter "):
            regex_question_and_choices = r"^[\d|\s\d][\d\s]*\.\s(?:.*(?:\r?\n(?![\d|\s\d][\d\s]*\.\s)[^\n]*|)*)"
            regex_choice_spillover = r"^[A-Z]*\.\s(?:.*(?:\r?\n(?!\d[\d\s]*\.\s)[^\n]*|)*)"
            start_page_check = chapter[2] - 1
            end_page_check = toc[i + 1][2] - 2

            total_questions = 0
            spillover_case = False
            while True:
                # Goes through pages to see if they have questions to find real start and end page
                if re.findall(regex_question_and_choices, doc[start_page_check].get_text(), re.MULTILINE):
                    # Once start page is found checks for end page
                    last_page_text = re.findall(regex_question_and_choices, doc[end_page_check].get_text(),
                                                re.MULTILINE)
                    last_page_spillover_case = re.findall(regex_choice_spillover, doc[end_page_check].get_text(),
                                                          re.MULTILINE)
                    if last_page_text:
                        regex_question_num = r"^[\d|\s\d][\d' ']*(?=\.\s)"
                        total_questions = int(re.findall(regex_question_num, last_page_text[-1], re.MULTILINE)[0])
                        if spillover_case:
                            end_page_check += 1
                        break
                    elif last_page_spillover_case and not last_page_text:
                        # Check if there is a page at the end that is just choices
                        spillover_case = True
                        end_page_check -= 1
                    else:
                        end_page_check -= 1
                        if end_page_check <= start_page_check:  # incase it checks all chapter pages and nothing found
                            break
                else:
                    start_page_check += 1
                    if start_page_check >= end_page_check:  # incase it checks all chapter pages and nothing found
                        break

            chapter_map.append({
                "number": int(chapter[1][8]),
                "title": chapter[1],
                "question_start_page": start_page_check,
                "question_end_page": end_page_check,
                "total_questions": total_questions

            })
        elif chapter[1].startswith("Answers to Chapter ") or (chapter[0] == 2 and chapter[1].startswith("Chapter ")):
            regex_answers = r"^(\d[\d' ']*)\.\s*((?:[A-Z],\s*)*[A-Z])\.\s*((?:.*(?:\r?\n(?!\d[\d\s]*\.\s)[^\n]*|)*))"
            regex_answer_nums = r"^[\d|\s\d][\d' ']*(?=\.[\s]*[A-Z])"
            chapter_map[answer_chapter_match]["answer_start_page"] = chapter[2] - 1
            end_page_check = toc[i + 1][2] - 1
            x = 0
            while True:
                doc_text = doc[end_page_check].get_text()

                if doc_text and re.findall(regex_answer_nums, doc_text, re.MULTILINE):
                    last_answer_page_data = re.findall(regex_answer_nums, doc_text, re.MULTILINE)
                    last_answer_page_data = [number.replace(' ', '') for number in last_answer_page_data]
                    print(last_answer_page_data)
                    if str(chapter_map[answer_chapter_match]["total_questions"]) in last_answer_page_data:
                        chapter_map[answer_chapter_match]["answer_end_page"] = end_page_check
                        break
                    elif end_page_check == chapter_map[answer_chapter_match]["answer_start_page"]:
                        sg.popup_error("ERROR FINDING ANSWER CHAPTERS")
                        break
                    else:
                        end_page_check -= 1
                else:
                    end_page_check -= 1

            answer_chapter_match += 1

    print(json.dumps(chapter_map, indent=2))

    return chapter_map


def extract_questions(doc, chapter, chapter_num, page_text_rect):
    def choice_cleanup(unclean_choices):
        # Choices come out with lots of new lines, this cleans them up and matches them together
        choice_text = re.split('(^[a-zA-Z]\. +)', unclean_choices, flags=re.MULTILINE)
        choice_text = [choice.strip() for choice in choice_text if choice.strip()]
        clean_choices = [[choice_text[i][0], choice_text[i + 1]] for i in range(0, len(choice_text), 2)]
        return clean_choices

    # -------------------------------------------------
    regex_question_and_choices = r"^([\d|\s\d][\d' ']*)\.\s(.*(?:\r?\n(?![\s]*[a-zA-Z]\.\s)[^\n]*|)*)(.*(?:\r?\n(?![\d|\s\d][\d' ']*\.\s)[^\n]*|)*)"
    regex_question_num = r"^[\d|\s\d][\d' ']*\.\s"
    regex_choice_spillover = r"^[A-Z]*\.\s(?:.*(?:\r?\n(?!\d[\d\s]*\.\s)[^\n]*|)*)"
    question_bank = {}
    page_number = chapter["question_start_page"]

    multi_page = ""

    while page_number <= chapter["question_end_page"]:

        doc_text = doc[page_number].get_textbox(page_text_rect)

        if (re.match(regex_question_num, doc_text) and page_number != chapter["question_start_page"]) or page_number == \
                chapter["question_end_page"]:
            if page_number == chapter["question_end_page"]:
                multi_page += f"\n{doc_text}"

            # Splits questions into 3 groups: [0] is question number, [1] is question text and [2] is choices
            page_questions = re.findall(regex_question_and_choices, multi_page, re.MULTILINE)

            for question in page_questions:
                question_num = int(question[0])
                try:
                    choices = choice_cleanup(question[2].strip())
                except IndexError:
                    print(json.dumps(question_bank, indent=2))
                    print(multi_page)
                    # print(json.dumps(question, indent=2))
                    quit()

                question_bank[question_num] = {
                    "question_num": question_num,
                    "question": question[1].strip(),
                    "choices": choices,
                    "chapter_number": chapter_num
                }

            multi_page = ""

        multi_page += f"\n{doc_text}"
        page_number += 1

    return question_bank


def extract_answers(doc, chapter, page_text_rect):
    regex_answers = r"^([\d|\s\d][\d' ']*)\.\s*((?:[A-Z],\s*)*[A-Z]|(?:[A-Z]\sand\s[A-Z]))\.\s*((?:.*(?:\r?\n(?![\d|\s\d][\d\s]*\.\s)[^\n]*|)*))"
    regex_answer_num = r"^[\d|\s\d][\d' ']*\.\s[A-Z]"

    multi_page = ""
    page_number = chapter["answer_start_page"]
    # print(doc[281].get_textbox(page_text_rect))
    # quit()
    while page_number <= chapter["answer_end_page"]:

        doc_text = doc[page_number].get_textbox(page_text_rect)

        if (re.match(regex_answer_num, doc_text.strip()) and page_number != chapter["answer_start_page"]) or page_number == \
                chapter["answer_end_page"]:
            if page_number == chapter["answer_end_page"]:
                # Checks if the next chapters answers start on the same page
                if f"Chapter {chapter['number'] + 1}" in doc_text:
                    lines = doc_text.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith(f"Chapter {chapter['number'] + 1}"):
                            # Keeps only text from current chapter
                            doc_text = '\n'.join(lines[:i])
                            break
                multi_page += f"\n{doc_text}"

            answer_data = re.findall(regex_answers, multi_page, re.MULTILINE)
            for answer in answer_data:

                question_num = int(answer[0].replace(' ', ''))

                # check if the current question is not 1 and this chapters question 1 doesn't exist then skip
                if question_num != 1 and "answer" not in chapter["question_bank"][1]:
                    continue
                # check if there is already an answer built for the current question then break
                elif "answer" in chapter["question_bank"][question_num]:
                    break
                # otherwise build the answer
                else:
                    all_answers = answer[1]
                    # Check for multiple answers
                    if ',' in answer[1]:
                        all_answers = answer[1].split(', ')
                    elif 'and' in answer[1]:
                        all_answers = answer[1].split(' and ')
                    chapter["question_bank"][question_num]["answer"] = all_answers
                    chapter["question_bank"][question_num]["explanation"] = answer[2]

            multi_page = ""

        multi_page += f"\n{doc_text}"
        page_number += 1

# Function to open and process the selected PDF file
def pdf_processing(file_path):
    doc = fitz.open(file_path)
    title = doc.metadata["title"]
    if title:
        title = sanitize_file_name(doc.metadata["title"])
    else:
        title = sanitize_file_name(os.path.splitext(os.path.basename(file_path))[0])

    # Check if the file already exists before overwriting
    if os.path.exists(f'./bins/{title}'):
        # file_exist_ans = 'OK' or 'Cancel'
        file_exists_ans = sg.popup_ok_cancel(f"'{title}' already exists. Do you want to overwrite it?")
        if file_exists_ans == 'Cancel':
            return

    # create rect to remove header
    page_text_rect = (0, 60, doc[0].rect.width, doc[0].rect.height)

    # processes the mapping of chapters
    chapter_map = extract_chapter_map(doc, page_text_rect)

    # extract all questions and answers for each chapter
    for chapter_num, chapter in enumerate(chapter_map):
        chapter["question_bank"] = extract_questions(doc, chapter, chapter_num + 1, page_text_rect)
        extract_answers(doc, chapter, page_text_rect)
    # save the data to a binary file for later use
    with open(f'./bins/{title}', 'wb') as file:
        pickle.dump(chapter_map, file)


def sanitize_file_name(file_name):
    # Define a translation table to remove characters that are not allowed in file names
    # We'll keep all letters, digits, and some common file name-safe characters like '-', '_', and '.'
    file_name = file_name.replace(' ', '-')
    allowed_characters = string.ascii_letters + string.digits + "-_."

    # Create a translation table that maps all characters not in the allowed set to None (removes them)
    translation_table = str.maketrans('', '', ''.join(c for c in string.printable if c not in allowed_characters))

    # Use translate() to remove disallowed characters from the file name
    sanitized_name = file_name.translate(translation_table)

    # Remove leading and trailing dots and spaces (common file name issues)
    sanitized_name = sanitized_name.strip('. ')

    return sanitized_name


def question_randomizer(pdf_questions, total_questions=100):
    # Choose which questions will be on the test and randomize their order
    total_chapters = len(pdf_questions)
    questions_per_chapter = [0 for _ in range(total_chapters)]
    chosen_questions = [[] for _ in range(total_chapters)]

    for _ in range(total_questions):
        while True:
            random_chapter = random.randint(0, total_chapters - 1)
            # add 1 if chosen random chapters value is less than the total number of questions for that chapter
            if questions_per_chapter[random_chapter] < pdf_questions[random_chapter]["total_questions"]:
                questions_per_chapter[random_chapter] += 1
                break

    for i in range(total_chapters):
        if questions_per_chapter[i]:
            chosen_questions[i].extend(
                random.sample(list(pdf_questions[i]["question_bank"].values()), questions_per_chapter[i]))

    # flattens list to be randomized
    chosen_questions = [question for chapter in chosen_questions for question in chapter]

    # Randomize 5 times
    for _ in range(5):
        random.shuffle(chosen_questions)

    return chosen_questions


def load_previous_pdfs():
    filelist = []
    for file in os.listdir('./bins'):
        filelist.append(file)
    return filelist


def nav_window(filelist):
    layout = [
        [sg.Text("PDF Titles:")],
        [sg.Column([
            [sg.Listbox(filelist, size=(60, 8), expand_y=True, enable_events=True, key="-LIST-")],

        ], pad=0),
        sg.Column([
            [sg.Button(key="-ADD-", button_text="Add")],
            [sg.Button('Remove')],
        ])],
        [sg.pin(
            sg.Column([
                [sg.InputText(key="input_path"),
                 sg.FileBrowse("Browse", key="browse_button", file_types=(("PDF files", "*.pdf"),)),
                 sg.OK(key="add-OK")]
            ], key="add-browser", pad=(0, 0), visible=False)
        )],
        # [sg.Text("Select a PDF:")],


        [sg.pin(
            sg.Column([
                [sg.Text("Quiz Type:"), sg.Radio("Test", "quiz_type", key="test", enable_events=True),
                 sg.Radio("Practice", "quiz_type", key="practice", enable_events=True)],
                [sg.Text(f"Total questions? (max"), sg.Text(key="max-questions"),
                 sg.InputText(key="quiz-len", size=5, enable_events=True)],
                [sg.Button("Start")]
            ], key="settings-col", pad=(0, 0), visible=False)
        )],
    ]
    # starting window to add, remove, or select quiz
    # Define the layout of the GUI
    # Create the window
    return sg.Window("PDF Reader", layout)


def quiz_window(question_number, current_question, quiz_type, score):
    # generates quiz window and dynamically adds choices
    layout = [
        [sg.Frame(f'Question {question_number}: ', [[sg.Text(f"{current_question['question']}")]])],
        # [sg.Text(f'Question {question_number}: ')],
        # [sg.Text(f"{current_question['question']}")],
    ]
    try:
        len(current_question['answer'])
    except KeyError:
        print(json.dumps(current_question, indent=2))
        quit()
    if len(current_question['answer']) == 1:
        choice_buttons = [[sg.Radio(choice[1], question_number, key=choice[0])] for choice in
                          current_question['choices']]
    else:
        choice_buttons = [[sg.Checkbox(choice[1], key=choice[0])] for choice in current_question['choices']]
    layout.append(choice_buttons)
    layout.append([sg.Button("Submit"), sg.Text(size=(10, 1))])
    if quiz_type == 'practice' and question_number - 1 > 0:
        layout.append(
            [sg.Text(f"Score: {score} / {question_number - 1}  -  {score / (question_number - 1) * 100:.2f}")])

    return sg.Window("Quiz", layout)


def score_window(score, quiz_total_questions, wrong_questions):
    show_detail_display = []
    for i, chapter in enumerate(wrong_questions):
        if chapter:
            y_size = 0
            no_scroll = True
            show_detail_display.append([sg.Text(f"Chapter {i+1}:", key=f"Chapter {i+1}")])
            wrong_question_list = []
            for question in chapter:
                wrong_question_list.append(f'Question {question["question_num"]}')
                y_size += 1
            if y_size > 10:
                y_size = 10
                no_scroll = False
            show_detail_display.append([sg.Listbox(wrong_question_list, size=(14, y_size), expand_y=True,no_scrollbar=no_scroll, enable_events=True, key=f"Chapter {i+1} List")])
            # for question in chapter:
            #     wrong_questions_display.append()
        # wrong_questions_display.append()
        print(show_detail_display)

    layout = [
        [sg.Text(f"Final Score: {score} / {quiz_total_questions}  -  {score / quiz_total_questions * 100:.2f}", key="final-score")],
        [sg.Button("Show Details")],
        [sg.pin(
            sg.Column(show_detail_display,key="details-col", pad=(0, 0), visible=False)
        ), sg.pin(
            sg.Column([
                [sg.Multiline(size=(30, 12), key='question-details', visible=False, pad=0)]
            ])
        )]
    ]

    return sg.Window("Score", layout)


def main():
    # Main function to create and run the GUI

    sg.set_options(font=('Arial Bold', 16))
    filelist = load_previous_pdfs()
    quiz = None

    nav = nav_window(filelist)
    # Nav screen loop
    while True:
        event, values = nav.read()
        print(event)
        # Window closed
        if event == sg.WINDOW_CLOSED:
            break

        # Add new pdf
        if event == "-ADD-":
            nav['add-browser'].update(visible=True)
        if event == 'add-OK':
            file_path = values["input_path"]
            if file_path:
                # Extract the pdf data and create a file for use
                pdf_processing(file_path)
                # Reload the list elements
                nav['-LIST-'].update(load_previous_pdfs())
                nav['add-browser'].update(visible=False)
                nav['input_path'].update('')

            else:
                sg.popup_error("Please enter or select a PDF file path.")
        # Select valid PDF
        if event == '-LIST-' and nav["-LIST-"].get():
            try:
                # Get data from binary file
                with open(f'./bins/{nav["-LIST-"].get()[0]}', 'rb') as file:
                    try:
                        pdf_questions = pickle.load(file)
                    except EOFError:
                        sg.popup_error("Error! Data is corrupted")
                        continue
                # Calculate total questions in pdf
                total_questions = 0
                for chapter in pdf_questions:
                    total_questions += len(chapter["question_bank"])
                nav["max-questions"].update(f"{total_questions} )")
                nav["settings-col"].update(visible=True)
            # Error if the file doesn't exist
            except FileNotFoundError:
                sg.popup_error("File Not Found! Try adding it again if this error persists.")

        # Quiz length input validation
        if event == 'quiz-len':
            if values['quiz-len'] and values['quiz-len'][-1] not in '0123456789':
                nav['quiz-len'].update(values['quiz-len'][:-1])
            elif values['quiz-len'] and int(values['quiz-len']) > total_questions:
                nav['quiz-len'].update(values['quiz-len'][:-1])

        # Remove Button
        if event == "Remove":
            # Ensure a pdf has been selected
            if nav["-LIST-"].get():
                del_validate = sg.popup_ok_cancel('Are you sure you want to delete this pdf data?')
                if del_validate == "OK":
                    try:
                        # Remove pdf binary
                        os.remove(f'./bins/{nav["-LIST-"].get()[0]}')
                        nav['-LIST-'].update(load_previous_pdfs())
                        nav['settings-col'].update(visible=False)

                    except FileNotFoundError:
                        sg.popup_error("Something went wrong")
            else:
                sg.popup_ok("Please select a PDF to remove")

        # Start Quiz

        if event == "Start":
            print(values)
            # Check that everything is entered to begin the quiz
            if values['quiz-len'] and values['test'] or values['practice']:
                if not quiz and pdf_questions:

                    # Set quiz type
                    if values['test']:
                        quiz_type = 'test'
                    elif values['practice']:
                        quiz_type = 'practice'

                    # Set quiz length
                    quiz_total_questions = int(values['quiz-len'])

                    # Choose and randomize the questions that will be used
                    quiz_questions = question_randomizer(pdf_questions, quiz_total_questions)

                    current_question = 0
                    score = 0
                    closed = False
                    wrong_questions = [[] for _ in range(len(pdf_questions))]

                    if quiz_questions:
                        while current_question + 1 <= quiz_total_questions:
                            # Break on close
                            if closed:
                                quiz = None
                                break

                            # Build quiz window everytime a question is submitted
                            quiz = quiz_window(current_question + 1, quiz_questions[current_question], quiz_type,
                                               score)
                            while True:
                                quiz_event, quiz_values = quiz.read()

                                # Break on close
                                if quiz_event == sg.WINDOW_CLOSED:
                                    closed = True
                                    break

                                # Question Submission
                                if quiz_event == "Submit":
                                    selected_answer = [choice for choice, value in quiz_values.items() if value]

                                    # Correct Answer
                                    if quiz_questions[current_question]["answer"] == selected_answer:
                                        score += 1
                                        if values['practice']:
                                            explain = quiz_questions[current_question]['explanation'].replace(f'\n', ' ')
                                            sg.popup_ok(f"Good Job!\n\n{explain}")

                                    else:
                                        if values['practice']:
                                            explain = quiz_questions[current_question]['explanation'].replace(f'\n', ' ')
                                            sg.popup_ok(f"Wrong!\n\n{explain}")
                                        elif values['test']:
                                            wrong_questions[quiz_questions[current_question]['chapter_number'] - 1].append(quiz_questions[current_question])


                                    current_question += 1
                                    quiz.close()
                                    break
                        else:
                            quiz = None
                            if values['test']:
                                # Show score at end of test
                                current_list = ''
                                score_screen = score_window(score, quiz_total_questions, wrong_questions)
                                while True:
                                    score_event, score_values = score_screen.read()
                                    print("EVENT", score_event)
                                    print("VALUES", score_values)
                                    if score_event == sg.WINDOW_CLOSED:
                                        score_screen = None
                                        break
                                    if score_event.startswith("Chapter"):
                                        if current_list and current_list != score_event:
                                            score_screen[current_list].update(set_to_index=[])
                                        current_list = score_event
                                        print(score_screen[score_event].get_indexes())
                                        print("******")
                                        print(wrong_questions[int(score_event.split(' ')[1]) - 1][score_screen[score_event].get_indexes()[0]])
                                        selected_question = wrong_questions[int(score_event.split(' ')[1]) - 1][score_screen[score_event].get_indexes()[0]]

                                        score_screen['question-details'].update(f"QUESTION:\n{selected_question['question']}\n\n EXPLANATION:\n{selected_question['explanation']}")
                                        score_screen['question-details'].update(visible=True)

                                    if score_event == "Show Details":
                                        print(json.dumps(wrong_questions))
                                        score_screen['details-col'].update(visible=True)

                                # sg.popup_ok(f"Final Score: {score} / {quiz_total_questions}  -  {score / (quiz_total_questions) * 100:.2f}")

            else:
                sg.popup_ok("Select quiz type and length before beginning")

    # Close the window
    nav.close()
    if quiz:
        quiz.close()


if __name__ == "__main__":
    main()
