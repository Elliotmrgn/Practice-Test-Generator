import json
import os
import random
import re
import string

import fitz
import pickle

import PySimpleGUI as sg

# TODO: Add 'Match The Following' Questions
# TODO: Manual editing of questions
# TODO: Image processing or manual adding

from chapter_map_extractor import extract_chapter_map
from question_extractor import extract_questions
from answer_extractor import extract_answers
from GUI_windows import nav_window, quiz_window, score_window


def pdf_processing(file_path):
    """Function to open and process the selected PDF file"""
    # Open the pdf
    doc = fitz.open(file_path)
    # Store the title of the pdf

    title = doc.metadata["title"]

    # If there is a title make it the file name
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
    chapter_map = extract_chapter_map(doc)

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
    x = 0
    for _ in range(total_questions):
        while True:
            x+=1
            random_chapter = random.randint(0, total_chapters - 1)
            # add 1 if chosen random chapters value is less than the total number of questions for that chapter

            if questions_per_chapter[random_chapter] < pdf_questions[random_chapter]["total_questions"]:
                questions_per_chapter[random_chapter] += 1
                break


    for i in range(total_chapters):
        if questions_per_chapter[i]:
            try:
                chosen_questions[i].extend(random.sample(list(pdf_questions[i]["question_bank"].values()), questions_per_chapter[i]))
            except ValueError:
                for o in range(total_chapters):
                    print(f'LENGTH OF CHAPTER {o+1}: {len(list(pdf_questions[o]["question_bank"].values()))}')
                    print(f'TOTAL QUESTIONS: {questions_per_chapter[o]}')
                    print()
                quit()


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

def main():
    # Main function to create and run the GUI

    sg.set_options(font=('Arial Bold', 24))
    filelist = load_previous_pdfs()
    quiz = None
    nav = nav_window(filelist)

    # Nav screen loop
    while True:
        event, values = nav.read()
        # Window closed
        if event == sg.WINDOW_CLOSED:
            break

        # ADD BUTTON ------------------------------------------------
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

        # PDF LIST ITEM SELECTION ------------------------------------------------
        if event == '-LIST-' and nav["-LIST-"].get():
            try:
                # Clear the length input
                nav['quiz-len'].update('')

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

        # Quiz length input validation -------------------------------------------
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

        # Start Quiz Button ---------------------------------------------
        if event == "Start":
            # Check that everything is entered to begin the quiz
            if values['quiz-len'] and (values['test'] or values['practice']):
                if not quiz and pdf_questions:
                    nav.disable()
                    nav.hide()

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
                                    if score_event == sg.WINDOW_CLOSED:
                                        score_screen = None
                                        break
                                    if score_event.startswith("Chapter"):
                                        if current_list and current_list != score_event:
                                            score_screen[current_list].update(set_to_index=[])
                                        current_list = score_event
                                        selected_question = wrong_questions[int(score_event.split(' ')[1]) - 1][score_screen[score_event].get_indexes()[0]]

                                        score_screen['question-details'].update(f"QUESTION:\n{selected_question['question']}\n\n EXPLANATION:\n{selected_question['explanation']}")
                                        score_screen['question-details'].update(visible=True)

                                    if score_event == "Show Details":
                                        score_screen['details-col'].update(visible=True)

                    nav.enable()
                    nav.un_hide()
            else:
                sg.popup_ok("Select quiz type and length before beginning")

    # Close the window
    nav.close()
    if quiz:
        quiz.close()


if __name__ == "__main__":
    main()
