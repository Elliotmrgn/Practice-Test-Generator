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

from GUI_windows import nav_window, quiz_window, score_window
from Book import Book

class ExamScribe:
    def __init__(self):
        self.current_book_total_questions = 0
        self.active_quiz = None

    def pdf_processing(self, file_path, file_name):
        # Open the pdf
        doc = fitz.open(file_path)
        # Create the Book obj that builds the chapter map
        book = Book(doc)
        all_questions = []
        # Cycle through all the chapters to build a full question bank
        for chapter in book.chapters:
            chapter.build_question_bank(doc)
            all_questions.append(chapter.question_bank)

        book.get_total_questions()
        # TODO: Output all_questions to a json file
        self._write_questions_to_json_file(all_questions, file_name)

    def _write_questions_to_json_file(self, all_questions, file_name):
        with open(f'./json/{file_name}', 'w') as file:
            json.dump(all_questions, file, indent=4)

    def _read_questions_from_json_file(self, file_name):
        with open(f'./json/{file_name}', 'r') as file:
            all_questions = json.load(file)
        return all_questions

    def _get_total_questions(self, all_questions):
        total_questions = 0
        for chapter_question in all_questions:
            total_questions += len(chapter_question)
        return total_questions
    def load_previous_pdfs(self):
        filelist = []
        folder_path = './json'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            return filelist

        for file in os.listdir('./json'):
            filelist.append(file)

        return filelist

    def handle_add_button(self, nav):
        nav['add-browser'].update(visible=True)

    def new_pdf_ok_button(self, nav, file_path):
        if file_path:
            # extract file name from path
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            # Check if file exists
            if os.path.exists(f'./json/{file_name}'):
                overwrite_prompt = sg.popup_ok_cancel(f"'{file_name}' already exists. Do you want to overwrite it?")
                if overwrite_prompt == 'Cancel':
                    return
            # Extract the pdf data and create a file for use
            self.pdf_processing(file_path, file_name)

            # Reload the list elements
            nav['-LIST-'].update(self.load_previous_pdfs())
            nav['add-browser'].update(visible=False)
            nav['input_path'].update('')

        else:
            sg.popup_error("Please enter or select a PDF file path.")

    def select_pdf_from_list(self, nav):

        # Clear the length input
        nav['quiz-len'].update('')

        # Get data from binary file

        self.current_book_total_questions = self._get_total_questions(self._read_questions_from_json_file(nav["-LIST-"].get()[0]))
        # Display the total questions
        nav["max-questions"].update(f"{self.current_book_total_questions} )")
        # Shows settings column
        nav["settings-col"].update(visible=True)

    def handle_quiz_length_input(self, nav, quiz_length_value):
        # Doesn't allow inputting non numbers and a number larger than total questions
        if quiz_length_value and quiz_length_value[-1] not in '0123456789':
            nav['quiz-len'].update(quiz_length_value[:-1])
        elif quiz_length_value and int(quiz_length_value) > self.current_book_total_questions:
            nav['quiz-len'].update(quiz_length_value[:-1])

    def handle_remove_button(self, nav):
        # Ensure a pdf has been selected
        if nav["-LIST-"].get():
            del_validate = sg.popup_ok_cancel('Are you sure you want to delete this pdf data?')
            if del_validate == "OK":
                try:
                    # Remove pdf binary
                    os.remove(f'./json/{nav["-LIST-"].get()[0]}')
                    nav['-LIST-'].update(self.load_previous_pdfs())
                    nav['settings-col'].update(visible=False)

                except FileNotFoundError:
                    sg.popup_error("Something went wrong")
        else:
            sg.popup_ok("Please select a PDF to remove")

    def handle_start_button(self, nav, values):
        # TODO: REFACTOR THIS
        if values['quiz-len'] and (values['test'] or values['practice']):
            all_questions = self._read_questions_from_json_file(nav["-LIST-"].get()[0])
            if not self.active_quiz and all_questions:
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
                quiz_questions = question_randomizer(all_questions, quiz_total_questions)

                current_question = 0
                score = 0
                closed = False
                wrong_questions = [[] for _ in range(len(all_questions))]

                if quiz_questions:
                    while current_question + 1 <= quiz_total_questions:
                        # Break on close
                        if closed:
                            self.active_quiz = None
                            break

                        # Build quiz window everytime a question is submitted
                        self.active_quiz = quiz_window(current_question + 1, quiz_questions[current_question], quiz_type,
                                           score)
                        while True:
                            quiz_event, quiz_values = self.active_quiz.read()

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
                                        wrong_questions[quiz_questions[current_question]['chapter_number'] - 1].append(
                                            quiz_questions[current_question])

                                current_question += 1
                                self.active_quiz.close()
                                break
                    else:
                        self.active_quiz = None
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
                                    selected_question = wrong_questions[int(score_event.split(' ')[1]) - 1][
                                        score_screen[score_event].get_indexes()[0]]

                                    score_screen['question-details'].update(
                                        f"QUESTION:\n{selected_question['question']}\n\n EXPLANATION:\n{selected_question['explanation']}")
                                    score_screen['question-details'].update(visible=True)

                                if score_event == "Show Details":
                                    score_screen['details-col'].update(visible=True)

                nav.enable()
                nav.un_hide()
        else:
            sg.popup_ok("Select quiz type and length before beginning")
    def _build_nav_gui(self):
        sg.set_options(font=('Arial Bold', 24))
        filelist = self.load_previous_pdfs()
        nav = self.nav_window(filelist)
        return nav

    def nav_window(self, filelist):
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


def question_randomizer(pdf_questions, total_questions=100):
    # TODO: REFACTOR THIS
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


def main():
    exam_scribe = ExamScribe()
    filelist = exam_scribe.load_previous_pdfs()
    nav = exam_scribe.nav_window(filelist)
    # Nav screen loop
    while True:
        event, values = nav.read()
        if event == sg.WINDOW_CLOSED:
            break

        # ADD BUTTON ------------------------------------------------
        if event == "-ADD-":
            exam_scribe.handle_add_button(nav)

        # OK BUTTON FOR ADDING NEW PDF ------------------------------
        if event == 'add-OK':
            file_path = values["input_path"]
            exam_scribe.new_pdf_ok_button(nav, file_path)

        # CLICKING ON LIST ITEM -------------------------------------
        if event == '-LIST-' and nav["-LIST-"].get():
            exam_scribe.select_pdf_from_list(nav)

        # HADNLE TYPING IN QUIZ LENGTH ------------------------------
        if event == 'quiz-len':
            exam_scribe.handle_quiz_length_input(nav, values['quiz-len'])

        # REMOVE BUTTON ---------------------------------------------
        if event == "Remove":
            exam_scribe.handle_remove_button(nav)

        # START QUIZ -------------------------------------------------
        if event == "Start":
            exam_scribe.handle_start_button(nav, values)

    nav.close()
    if exam_scribe.active_quiz:
        exam_scribe.active_quiz.close()


if __name__ == "__main__":
    main()
