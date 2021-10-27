import PySimpleGUI as sg
import chess
import chess.pgn
import io
import threading
from subprocess import Popen, PIPE, STDOUT
from queue import Queue
import traceback
import copy

enginePath = r"Chess.exe"
whiteColour = "#e8e8ed"
blackColour = "#3c3c53"
imgDir = "img/"  # Folder with images in
blankImg = imgDir + "blank.png"  # Empty square
imgs = ["pawn", "knight", "bishop", "rook", "queen", "king"]  # File names of pieces
diffs = ["Easy", "Medium", "Hard", "Impossible"]  # Difficulties


def main():
    engine = Engine()  # Creates Engine
    game = Game(board=chess.Board(None))  # Create game
    layout = create_layout()  # Creates Layout
    window = sg.Window("Chess", [layout, [engine.output.button]])  #Setups GUI
    lastPressed = None
    while True:  # Event Loop
        event, values = window.read()  # Gets event
        #print(event, values)
        if event == sg.WIN_CLOSED or event == 'Exit':  #Closes GUI
            break
        elif event == "From Start":  # Creates new game from start
            game = Game()
        elif event == "From PGN":  # Creates game from PGN
            gameIn = Game(board=get_pgn())
            if gameIn:  # If PGN worked
                game = gameIn
        elif event == "From FEN":  # Creates game from FEN
            gameIn = get_fen()
            if gameIn:
                game = gameIn
        elif type(event) is tuple:  # If it was a click on a square
            lastPressed = game.check_move(event, lastPressed, engine)
        elif event in diffs:  # Change in difficulty
            engine.difficulty = diffs.index(event)  # Sets difficulty
            window.find_element("diff").update(event)  # Changes the display difficulty
        elif event == "engine_output":
            game.make_engine_move(engine)
            # If the engine has outputed something it is checked if it is a move and then played
        update_window(window, game)
    engine.engine.kill() # Ends the engine process


def update_window(window, game):
    update_board(window, game.board)
    update_movelist(window, game)


def update_movelist(window, game):
    window["moves"].update(value = game.get_move_list())  # Sets new move list


def create_layout():  # Creates layout of GUI
    sg.theme("BluePurple")
    menuDef = [["New Game", ["From Start", "From PGN", "From FEN"]],
               ["Difficulty", diffs],
               ["Export", ["FEN"]],
               ["Mode", ["Competitive", "Training", "Analysis"]]]  # The menu along the top
    menu = [sg.Menu(menuDef)]
    board = create_board()  #The board with squares
    info = [[sg.Text("Mode:", size=(8, 1)), sg.Text("Competitive", size=(30, 1), relief=sg.RELIEF_GROOVE)],
            [sg.Text("Difficulty:", size=(8, 1)), sg.Text("Impossible", size=(30, 1), relief=sg.RELIEF_GROOVE, key="diff")],
            [sg.Text("White: ", size=(8, 1)), sg.Text("Human", size=(30, 1), relief=sg.RELIEF_GROOVE)],
            [sg.Text("Black: ", size=(8, 1)), sg.Text("Computer", size=(30, 1), relief=sg.RELIEF_GROOVE)]]
            # The info under the board
    timers = [sg.Text("5:00", relief=sg.RELIEF_RAISED, font=10), sg.Text("5:00", relief=sg.RELIEF_RAISED, font=10)] # TODO: make work or remove
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
                #print(line)
                self.responses.put(line)
                self.button.click()



class Engine:
    def __init__(self):
        self.commandPositions = Queue()
        self.engine = Popen(enginePath,  stdin=PIPE, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
        self.output = EngineOutput(self.engine.stdout)
        self.output.start()
        self.difficulty = 3;

    def send(self, command):
        #print(command)
        self.engine.stdin.write(command)
        self.engine.stdin.write("\n")
        self.engine.stdin.flush()

    def set_position(self, board, startFen):
        command = "position fen "
        command += startFen + " "
        board2 = chess.Board(startFen)
        command += "moves"
        for move in board.move_stack:
            moveStr = board2.uci(move)
            command += " " + moveStr
            board2.push(move)
        self.send(command)

    def search(self):
        if self.difficulty == 3:
            self.send("go")
        else:
            self.send("go diff " + str(self.difficulty))

    def get_best_move(self, board, startFen):
        self.commandPositions.put(board.fen())
        self.set_position(board, startFen)
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
            return response[response.find("bestmove")+9:]
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
        game = Game(board = chess.Board(fen))
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
                    return Game(board=board)
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
            self.startBoard = copy.deepcopy(board)
            self.moves = board.move_stack.copy()
            while len(self.startBoard.move_stack) > 0:
                self.startBoard.pop()
        else:
            self.board = chess.Board()
            self.startBoard = chess.Board()
            self.moves = []
        self.human = humanColour

    def get_move_list(self):
        return self.startBoard.variation_san(self.moves)

    def check_move(self, pressed, lastPressed, engine):
        if self.board.turn == self.human:
            if lastPressed:
                startSquare = chess.square(lastPressed[1], lastPressed[0])
                if self.board.piece_at(startSquare).piece_type == chess.PAWN and (pressed[0]in(7, 0)):
                    promo = self.get_promotion()
                else:
                    promo = None
                move = chess.Move(startSquare, chess.square(pressed[1], pressed[0]), promotion=promo)
                if move in self.board.legal_moves:
                    self.make_move(move)
                    engine.get_best_move(self.board, self.startBoard.fen())
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

    def get_promotion(self):
        promoPieces = [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]
        layout = [[sg.Button(image_filename=get_piece_img(piece, self.human), key=piece) for piece in promoPieces]]
        popup = sg.Window("Promotion", layout)
        while True:
            event, values = popup.read()
            if event in promoPieces:
                return event


def get_piece_img(piece, colour):
    if colour:
        colourCode = "w_"
    else:
        colourCode = "b_"
    return imgDir + colourCode + imgs[piece - 1] + ".png"








main()