import PySimpleGUI as sg


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
    ]

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