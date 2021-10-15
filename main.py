import PySimpleGUI as sg

def main():
    sg.theme("BluePurple")
    menuDef = [["New Game", ["From Start", "From PGN"]],
               ["Difficulty", ["Easy", "Medium", "Hard", "Impossible"]],
               ["Export", ["FEN", "PNG"]],
               ["Mode", ["Competitive", "Training", "Analysis"]]]
    Menu = [sg.Menu(menuDef)]
    Timers = [sg.Text("5:00", relief=sg.RELIEF_RAISED, font=10), sg.Text("5:00", relief=sg.RELIEF_RAISED, font=10)]
    MoveList = [[sg.Text("Move list:", font= 10)],
                [sg.Multiline(size=(50,7),  auto_refresh=True, no_scrollbar=True, disabled=True)],
                [sg.Button("<-"), sg.Button("->")]]
    layout =[Menu, Timers, MoveList]
    window = sg.Window("Chess", layout)
    while True:
        event, values = window.read()
        print(event, values)
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

main()