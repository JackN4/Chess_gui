import PySimpleGUI as sg
import chess
import chess.pgn
import io
import threading
from subprocess import Popen, PIPE, STDOUT
from queue import Queue
import traceback

enginePath = r"Chess.exe"
whiteColour = "#e8e8ed"
blackColour = "#3c3c53"
imgDir = "img/"
blankImg = imgDir + "blank.png"
imgs = ["pawn", "knight", "bishop", "rook", "queen", "king"]
diffs = ["Easy", "Medium", "Hard", "Impossible"]


def main():
    try:
        engine = Engine()
        game = Game(board=chess.Board(None))
        layout = create_layout()
        window = sg.Window("Chess", [layout, [engine.output.button]])
        lastPressed = None
        diff = 3
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
                lastPressed = game.check_move(event, lastPressed, engine)
            elif event in diffs:
                diff = diffs.index(event)
                print(diff)
            elif event == "engine_output":
                game.make_engine_move(engine)
            update_window(window, game)
    except Exception as e:
        print(traceback.format_exc())
    engine.engine.kill()

def update_window(window, game):
    update_board(window, game.board)
    update_movelist(window, game)


def update_movelist(window, game):
    window["moves"].update(value = game.get_move_list())


def create_layout():
    sg.theme("BluePurple")
    menuDef = [["New Game", ["From Start", "From PGN", "From FEN"]],
               ["Difficulty", diffs],
               ["Export", ["FEN"]],
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


class EngineOutput(threading.Thread):
    def __init__(self, pipe):
        super(EngineOutput, self).__init__()
        self.pipe = pipe
        self.button = sg.Button(visible=False, key="engine_output")
        self.responses = Queue()
        self.setDaemon(True)

    def run(self):
        self.worker()

    def worker(self):
        while True:
            line = self.pipe.readline().strip()
            if line == '':
                break
            else:
                print(line)
                self.responses.put(line)
                self.button.click()



class Engine:
    def __init__(self):
        self.commandPositions = Queue()
        self.engine = Popen(enginePath,  stdin=PIPE, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
        self.output = EngineOutput(self.engine.stdout)
        self.output.start()

    def send(self, command):
        print(command)
        self.engine.stdin.write(command)
        self.engine.stdin.write("\n")
        self.engine.stdin.flush()

    def set_position(self, board):
        command = "position fen "
        command += board.starting_fen + " "
        board2 = chess.Board(board.starting_fen)
        command += "moves "
        for move in board.move_stack:
            moveStr = board2.uci(move)
            command += moveStr + " "
            board2.push(move)
        self.send(command)

    def search(self):
        self.send("go")

    def get_best_move(self, board):
        self.commandPositions.put(board.fen())
        self.set_position(board)
        self.search()

    def get_response(self, board): #TODO: Needs to be fixed if game changes
        while not self.output.responses.empty():
            response = self.output.responses.get()
            if "bestmove" in response:
                if self.commandPositions.get() == board.fen():
                    return response
        return None

    def get_move_response(self, board):
        response = self.get_response(board)
        if response:
            return response[9:]
        else:
            return None



def export_game(message, output):
    layout = [[sg.Text(message)], [sg.Multiline(default_text=output, key="input", disabled=True)]]
    popup = sg.Window("Export", layout)
    while True:
        event, values = popup.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            popup.close()


def export_fen(game):
    export_game("This is the current FEN for the game: ", game.board.fen())


def get_input(message):
    layout = [[sg.Text(message)], [sg.Multiline(key="input")], [sg.Button("Enter")]]
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
    def __init__(self, humanColour=True, board=None):
        if board:
            self.board = board
            self.moves = board.move_stack.copy()
        else:
            self.board = chess.Board()
            self.moves = []
        self.human = humanColour

    def get_move_list(self):
        board2 = chess.Board(self.board.starting_fen)
        return board2.variation_san(self.moves)

    def check_move(self, pressed, lastPressed, engine):
        if self.board.turn == self.human:
            if lastPressed:
                move = chess.Move(chess.square(lastPressed[1], lastPressed[0]), chess.square(pressed[1], pressed[0]))
                if move in self.board.legal_moves:
                    self.make_move(move)
                    engine.get_best_move(self.board)
                    return None
            else:
                if self.board.piece_at(chess.square(pressed[1], pressed[0])):
                    return pressed
                else:
                    return None
            return None
        return None

    def make_move(self, move):
        self.board.push(move)
        self.moves.append(move)

    def make_engine_move(self, engine):
        moveUci = engine.get_move_response(self.board)
        if moveUci:
            move = chess.Move.from_uci(moveUci)
            self.make_move(move)


def get_piece_img(piece, colour):
    if colour:
        colourCode = "w_"
    else:
        colourCode = "b_"
    return imgDir + colourCode + imgs[piece - 1] + ".png"








main()