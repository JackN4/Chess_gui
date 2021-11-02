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
                #This lists the moves from the game
    layout = [menu, board, timers, info,  moveList] #Collates all the parts
    return layout


class EngineOutput(threading.Thread): #This is a threaded worker that waits for and recieves any output from the engine
    
    def __init__(self, pipe):
        super(EngineOutput, self).__init__()
        self.pipe = pipe
        self.button = sg.Button(visible=False, key="engine_output") #The button that is triggered when there is output from the engine
        self.responses = Queue() #The output of the engine is added to this queue
        self.daemon = True

    def run(self):
        self.worker()

    def worker(self):
        while True:
            line = self.pipe.readline().strip() #Gets engine output
            if line == '': #If engine has closed
                break
            else:
                self.responses.put(line) #Adds output to responses queue
                self.button.click() #Triggers the button



class Engine: #Handles communication with the egine
    def __init__(self):
        self.commandPositions = Queue() #The board positions for each command sent to engine
        self.engine = Popen(enginePath,  stdin=PIPE, stdout=PIPE, stderr=STDOUT, universal_newlines=True) #Opens the engine exe
        self.output = EngineOutput(self.engine.stdout) #Makes the output worker
        self.output.start()
        self.difficulty = 3; #Sets default difficulty

    def send(self, command): #Sends commands to engine
        self.engine.stdin.write(command)
        self.engine.stdin.write("\n")
        self.engine.stdin.flush()

    def set_position(self, board, startFen): #Sends a position command to engine
        command = "position fen "
        command += startFen + " "  #Sets the fen before moves are made
        board2 = chess.Board(startFen) #Makes a board with the fen
        command += "moves"
        for move in board.move_stack: #Iterates through the moves
            moveStr = board2.uci(move) #Gets the uci version of the move
            command += " " + moveStr #Adds it to commamd
            board2.push(move) #Makes move on board
        self.send(command) #Sends command to engine

    def search(self): #Gets engine to search for best move
        if self.difficulty == 3:
            self.send("go")
        else:
            self.send("go diff " + str(self.difficulty)) #Search with difficulty level attached

    def get_best_move(self, board, startFen): #Finds bestmove
        self.commandPositions.put(board.fen()) #Adds current position to queue
        self.set_position(board, startFen) #Sets position within engine to current position
        self.search() #Searches

    def get_response(self, board): #TODO: Needs to be fixed if game changes
        while not self.output.responses.empty():
            response = self.output.responses.get() #Gets next response 
            if "bestmove" in response and self.commandPositions.get() == board.fen(): #If it contains bestmove and the command was from the current board
                    return response 
        return None #Was no correct response

    def get_move_response(self, board): #Returns the move from the response
        response = self.get_response(board)
        if response:
            return response[response.find("bestmove")+9:]
        else:
            return None



def export_game(message, output): #Creates a window that displays text to user allowing the game to be exported in different ways
    layout = [[sg.Text(message)], [sg.Multiline(default_text=output, key="input", disabled=True)]]
    popup = sg.Window("Export", layout)
    while True:
        event, values = popup.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            popup.close()


def export_fen(game): #Exports current board fen
    export_game("This is the current FEN for the game: ", game.board.fen())


def get_input(message): #Creates a windows that gets a returns input from the user
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


def show_error(message): #Creates a window that displays an error message
    popup = sg.Window("ERROR", [[sg.Text(message)]])
    while True:
        event, values = popup.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            popup.close()
            return


def get_fen(): #Gets a fen from user input and makes board from it
    fen = get_input("Please enter the FEN")
    try:
        game = Game(board = chess.Board(fen))
        return game
    except ValueError: #IF there was an error while parsing the fen
        show_error("You entered an incorrect FEN")


def get_pgn(): #Gets a PGN from user input and creates board from it
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
                    return Game(board=board) #PGN was correct and board is made
    except ValueError:
        pass
    show_error("The PGN you entered was incorrect") #PGN was not correct


def create_board(): #Creates board for GUI
    boardSg = [] #Board list
    for rowNum in range(8):
        row = [] #Row list
        for colNum in range(8):
            if (rowNum+colNum) % 2 == 0: #Finds whether current square is white or black
                colour = whiteColour
            else:
                colour = blackColour
            row.append(sg.Button(image_filename=blankImg, button_color=colour, pad=(0,0), border_width=0, key=(7 - rowNum, colNum))) #Adds square to row
        boardSg.append(row) #Adds row to board
    return boardSg


def update_board(window, board): #Updates the board
    for rowNum in range(8):
        for colNum in range(8):#Iterates through every square on board
            piece = board.piece_at(chess.square(colNum, rowNum)) #Gets piece at square
            if piece:
                imgFile = get_piece_img(piece.piece_type, piece.color) #Gets image for piece
            else:
                imgFile = blankImg #Or blank image
            window[(rowNum, colNum)].Update(image_filename=imgFile) #Updates square with image


class Game: #Class that holds the board info and moves
    def __init__(self, humanColour=True, board=None):
        if board:
            self.board = board
            self.startBoard = copy.deepcopy(board)
            self.moves = board.move_stack.copy()
            while len(self.startBoard.move_stack) > 0:
                self.startBoard.pop() #This creates a board that exists at the start of the move list
        else:
            self.board = chess.Board()
            self.startBoard = chess.Board()
            self.moves = []
        self.human = humanColour

    def get_move_list(self): #Gets list of moves in short algebraic notation
        return self.startBoard.variation_san(self.moves)

    def check_move(self, pressed, lastPressed, engine): #Proccesses a click on a square
        if self.board.turn == self.human: #If it is human's turn
            if lastPressed: #If a square has been pressed previously
                startSquare = chess.square(lastPressed[1], lastPressed[0]) #Gets the square at start of move
                if self.board.piece_at(startSquare).piece_type == chess.PAWN and (pressed[0]in(7, 0)): #Checks if there is promotion
                    promo = self.get_promotion()
                else:
                    promo = None
                move = chess.Move(startSquare, chess.square(pressed[1], pressed[0]), promotion=promo) #Creates move
                if move in self.board.legal_moves: #Checks if move is legal
                    self.make_move(move) #Makes move
                    engine.get_best_move(self.board, self.startBoard.fen()) #Sets engine to find best response
                    return None
            else:
                if self.board.piece_at(chess.square(pressed[1], pressed[0])):
                    return pressed #Returns current square pressed so user can click another square
                else:
                    return None
            return None
        return None

    def make_move(self, move): #Makes a move
        self.board.push(move) #Makes move on board
        self.moves.append(move) #Adds move to list of moves

    def make_engine_move(self, engine):
        moveUci = engine.get_move_response(self.board) #Gets move
        if moveUci:
            move = chess.Move.from_uci(moveUci) #Makes move object from string
            self.make_move(move) #Makes move

    def get_promotion(self): #Creates window to allow user to pick what piece they want to promote their pawn to
        promoPieces = [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]
        layout = [[sg.Button(image_filename=get_piece_img(piece, self.human), key=piece) for piece in promoPieces]] #Creates four buttons each with the piece on
        popup = sg.Window("Promotion", layout)
        while True:
            event, values = popup.read()
            if event in promoPieces:
                return event #Returns piece


def get_piece_img(piece, colour): #Gets the file name for image of piece of specific colour
    if colour:
        colourCode = "w_"
    else:
        colourCode = "b_"
    return imgDir + colourCode + imgs[piece - 1] + ".png"








main()
