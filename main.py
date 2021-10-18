import PySimpleGUI as sg
import chess
import chess.pgn
import io

whiteColour = "#e8e8ed"
blackColour = "#3c3c53"
imgDir = "img/"
blankImg = imgDir + "blank.png"
imgs = ["pawn", "knight", "bishop", "rook", "queen", "king"]
diffs = ["Easy", "Medium", "Hard", "Impossible"]

def main():
    layout = create_layout()
    window = sg.Window("Chess", layout)
    game = Game(board = chess.Board(None))
    lastPressed = None
    while True:
        event, values = window.read()
        print(event, values)
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
        elif event == "From Start":
            game = Game()
        elif event == "From PGN":
            gameIn = Game(board=get_pgn())
            if gameIn:
                game = gameIn
        elif event == "From FEN":
            gameIn = get_fen()
            if gameIn:
                game = gameIn
        elif type(event) is tuple:
            lastPressed = game.check_move(event, lastPressed)
        elif event in diffs

        update_window(window, game)

def update_window(window, game):
    update_board(window, game.board)
    update_movelist(window, game)


def update_movelist(window, game):
    window["moves"].update(value = game.get_move_list())


def create_layout():
    sg.theme("BluePurple")
    menuDef = [["New Game", ["From Start", "From PGN", "From FEN"]],
               ["Difficulty", diffs],
               ["Export", ["FEN", "PNG"]],
               ["Mode", ["Competitive", "Training", "Analysis"]]]
    menu = [sg.Menu(menuDef)]
    board = create_board()
    info = [[sg.Text("Mode:", size=(8, 1)), sg.Text("Competitive", size=(30, 1), relief=sg.RELIEF_GROOVE)],
            [sg.Text("Difficulty:", size=(8, 1)), sg.Text("Impossible", size=(30, 1), relief=sg.RELIEF_GROOVE)],
            [sg.Text("White: ", size=(8, 1)), sg.Text("Human", size=(30, 1), relief=sg.RELIEF_GROOVE)],
            [sg.Text("Black: ", size=(8, 1)), sg.Text("Computer", size=(30, 1), relief=sg.RELIEF_GROOVE)]]
    timers = [sg.Text("5:00", relief=sg.RELIEF_RAISED, font=10), sg.Text("5:00", relief=sg.RELIEF_RAISED, font=10)]
    moveList = [[sg.Text("Move list:", font=10)],
                [sg.Multiline( size=(50, 7), auto_refresh=True, no_scrollbar=True, disabled=True, key="moves")],
                [sg.Button("<-", key="previous"), sg.Button("->", key="next")]]
    layout = [menu, board, timers, info,  moveList]
    return layout



def get_input(text):
    layout = [[sg.Text(text)],[sg.Multiline(key="input")], [sg.Button("Enter")]]
    popup = sg.Window("Input", layout)
    while True:
        event, values = popup.read()
        if event == "Enter":
            result = popup["input"].get()
            popup.close()
            return result
        if event == sg.WIN_CLOSED or event == 'Exit':
            popup.close()
            return ""


def show_error(message):
    popup = sg.Window("ERROR", [[sg.Text(message)]])
    while True:
        event, values = popup.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            popup.close()
            return

def get_fen():
    fen = get_input("Please enter the FEN")
    try:
        game = Game(chess.Board(fen))
        return game
    except ValueError:
        show_error("You entered an incorrect FEN")



def get_pgn():
    pgn = get_input("Please enter the PGN:")
    try:
        if pgn:
            pgnIo = io.StringIO(pgn)
            game = chess.pgn.read_game(pgnIo)
            if len(game.errors) == 0:
                board = game.board()
                for move in game.mainline_moves():
                    board.push(move)
                if board.fen() != chess.STARTING_FEN:
                    return board
    except ValueError:
        pass
    show_error("The PGN you entered was incorrect")


def create_board():
    boardSg = []
    for rowNum in range(8):
        row = []
        for colNum in range(8):
            if (rowNum+colNum) % 2 == 0:
                colour = whiteColour
            else:
                colour = blackColour
            row.append(sg.Button(image_filename=blankImg, button_color=colour, pad=(0,0), border_width=0, key=(7 - rowNum, colNum)))
        boardSg.append(row)
    return boardSg

def update_board(window, board):
    for rowNum in range(8):
        for colNum in range(8):
            piece = board.piece_at(chess.square(colNum, rowNum))
            if piece:
                imgFile = get_piece_img(piece.piece_type, piece.color)

            else:
                imgFile = blankImg
            window[(rowNum, colNum)].Update(image_filename=imgFile)


class Game:
    def __init__(self, board=None):
        if board:
            self.board = board
            self.moves = board.move_stack
        else:
            self.board = chess.Board()
            self.moves = []


    def get_move_list(self):
        board2 = chess.Board(self.board.starting_fen)
        return board2.variation_san(self.moves)


    def check_move(self, pressed, lastPressed):
        if lastPressed:
            move = chess.Move(chess.square(lastPressed[1], lastPressed[0]), chess.square(pressed[1], pressed[0]))
            if move in self.board.legal_moves:
                self.board.push(move)
                self.moves.append(move)
                return None
        else:
            if self.board.piece_at(chess.square(pressed[1], pressed[0])):
                return pressed
            else:
                return None




def get_piece_img(piece, colour):
    if colour:
        colourCode = "w_"
    else:
        colourCode = "b_"
    return imgDir + colourCode + imgs[piece - 1] + ".png"








main()