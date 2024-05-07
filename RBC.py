import chess
from reconchess import utilities, is_illegal_castle
import chess.engine
from collections import Counter
import os

def boardRepresentation(line):
    board = chess.Board(line)
    print(board)


def nextMovePrediction(line):
  board = chess.Board(line)
  possible_moves = list(board.pseudo_legal_moves) + [chess.Move.null()]

  if board.castling_rights:
    for move in utilities.without_opponent_pieces(board).generate_castling_moves():
      possible_moves.append(move) if not is_illegal_castle(board, move) else None

  possible_moves = list(set(possible_moves))
  for move in sorted(possible_moves, key=lambda move: move.uci()):
    print(move)



def nextStatePrediction(line):
    board = chess.Board(line)
    moves = list(board.pseudo_legal_moves) + [chess.Move.null()]
    next_positions = []

    if board.castling_rights:
        for move in utilities.without_opponent_pieces(board).generate_castling_moves():
            moves.append(move) if not is_illegal_castle(board, move) else None

    for move in moves:
        temp_board = board.copy()
        temp_board.push(move)
        next_positions.append(temp_board.fen())
    next_positions.sort()

    for position in next_positions:
        print(position)


def nextStateWithSense(lines, window):
    entries = []
    # this is where lines are extracted and labeled
    for i, line in enumerate(lines):
        rows = line.split('/')
        rows[len(rows) - 1] = rows[len(rows) - 1].split()[0]
        # converts numbers to ?s
        expandedRows = []
        for row in rows:
            modified_row = ''
            for char in row:
                if char.isdigit():
                    modified_row += '?' * int(char)
                else:
                    modified_row += char
            expandedRows.append(modified_row)
        # adds converted rows and their labeles
        entries.append([expandedRows, i])

    # splits the window into the squares
    view = window.split(';')
    pairs = []
    for square in view:
        pairs.append(square.split(':'))

    # gets the coords from the suares and finds match in the FEN
    for pair in pairs:
        location = pair[0]
        piece = pair[1]
        letter = location[0]
        number = location[1]

        for line in entries:
            row = line[0][abs(int(number) - 8)]
            if row[ord(letter) - ord('a')] != piece:
                entries.remove(line)

    # saves the equivalent original string from the labels
    outputs = []
    for s in entries:
        outputs.append(lines[s[1]])
    outputs.sort()
    for s in outputs:
        print(s)


# Used to allow the function to take in the correct parameters while still only adding one line of code
def getInput():
    num = input()
    lines = []
    for i in range(int(num)):
        line = input()
        lines.append(line)
    window = input()
    # where the actual function is called
    nextStateWithSense(lines, window)


def predict_next_states_with_captures(fen, capture_square):
    board = chess.Board(fen)
    capture_moves = []

    for move in board.legal_moves:
        if move.to_square == chess.parse_square(capture_square) and board.is_capture(move):
            board.push(move)
            capture_moves.append(board.fen())
            board.pop()

    capture_moves.sort()
    return capture_moves


def select_common_move(fen_list):
    engine_path = '/opt/stockfish/stockfish'  # Adjust this path as necessary

    # Check if Stockfish executable exists at the specified path
    if not os.path.exists(engine_path):
        raise FileNotFoundError(f"Stockfish engine not found at {engine_path}")

    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        move_counter = Counter()
        for fen in fen_list:
            board = chess.Board(fen)
            if board.is_checkmate():
                move = list(board.legal_moves)[0]
            else:
                result = engine.play(board, chess.engine.Limit(time=0.5))
                move = result.move
            move_counter[move.uci()] += 1

    most_common_move = sorted(move_counter.items(), key=lambda x: (-x[1], x[0]))[0][0]
    return most_common_move


def execute_move(fen, move):
    # Create a board from the given FEN string
    board = chess.Board(fen)

    # Create a move object from the UCI string
    chess_move = chess.Move.from_uci(move)

    # Check if the move is legal and execute it
    if chess_move in board.legal_moves:
        board.push(chess_move)
        return board.fen()
    else:
        return "Illegal move"


def moveGeneration(line):
    board = chess.Board(line)
    color = board.turn    

    if board.is_check():
        enemy_king_square = board.king(not color)
        attackers = board.attackers(color, enemy_king_square)
        if attackers:
            attacker_square = attackers.pop()
            print(chess.Move(attacker_square, enemy_king_square))

    else:
        engine = chess.engine.SimpleEngine.popen_uci('/opt/stockfish/stockfish', setpgrp=True)        
        result = engine.play(board, chess.engine.Limit(time=0.5))
        print(result.move.uci())
        engine.quit()

line=input()
moveGeneration(line)