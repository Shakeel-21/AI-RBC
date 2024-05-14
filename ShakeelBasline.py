import chess
from reconchess import *
import chess.engine
from collections import Counter
import os
import random


class MyAgent(Player):
    def __init__(self):
        # setup agent as you see fit
        self.board = None
        self.color = None
        self.opponent = None
        self.possible_states = []
        self.engine = chess.engine.SimpleEngine.popen_uci('./opt/stockfish/stockfish', setpgrp=True)
        pass

    def handle_game_start(self, color, board, opponent_name):
        # function that is run when the game starts
        self.board = board
        self.color = color
        self.opponent = opponent_name
        self.possible_states = [board.fen()]
        pass

    def handle_opponent_move_result(self, captured_my_piece, capture_square):
        # feedback on whether the opponent captured a piece
        if captured_my_piece:
            self.possible_states = predict_next_states_with_captures(self.possible_states, capture_square)
        else:
            self.possible_states = [nextStatePrediction(state) for state in self.possible_states]
        pass

    def choose_sense(self, sense_actions, move_actions, seconds_left):
        # write code here to select a sensing move
        valid_sense_actions = [square for square in sense_actions if square not in [
            chess.A1, chess.A2, chess.A3, chess.A4, chess.A5, chess.A6, chess.A7, chess.A8,
            chess.B1, chess.B8,
            chess.C1, chess.C8,
            chess.D1, chess.D8,
            chess.E1, chess.E8,
            chess.F1, chess.F8,
            chess.G1, chess.G8,
            chess.H1, chess.H2, chess.H3, chess.H4, chess.H5, chess.H6, chess.H7, chess.H8
        ]]
        return random.choice(valid_sense_actions)

    def handle_sense_result(self, sense_result):
        window = ";".join(
            [f"{chess.SQUARE_NAMES[square]}:{piece.symbol() if piece else '?'}" for square, piece in sense_result])
        self.possible_states = [state for fen in self.possible_states for state in
                                nextStateWithSense(fen, window)]

    def choose_move(self, move_actions, seconds_left):
        # execute a chess move
        selected_move = select_common_move(self.possible_states, self.engine)
        return selected_move

    def handle_move_result(self, requested_move, taken_move, captured_opponent_piece, capture_square):
        # this function is called after your move is executed.
        if captured_opponent_piece:
            self.possible_states = predict_next_states_with_captures(self.possible_states, capture_square)
        else:
            self.possible_states = [execute_move(state, taken_move.uci()) for state in self.possible_states]
        pass

    def handle_game_end(self, winner_color, win_reason, game_history):
        # shut down everything at the end of the game
        self.engine.quit()
        pass


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
  list=[]
  for move in sorted(possible_moves, key=lambda move: move.uci()):
    list.append(move)
  return list



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
    lists=[]
    for position in next_positions:
        lists.append(position)
    return lists


def nextStateWithSense(lines, window):
    print(lines)
    print(window)
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
    return outputs


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


def select_common_move(fen_list,engine1):
    with engine1 as engine:
        move_counter = Counter()
        for fen in fen_list:
            board = chess.Board(fen)
            if board.is_checkmate():
                move = list(board.legal_moves)[0]
            else:
                result = engine.play(board, chess.engine.Limit(time=10/len(fen_list)))
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


def moveGeneration(line,engine):
    board = chess.Board(line)
    color = board.turn    

    if board.is_check():
        enemy_king_square = board.king(not color)
        attackers = board.attackers(color, enemy_king_square)
        if attackers:
            attacker_square = attackers.pop()
            return chess.Move(attacker_square, enemy_king_square)

    else:

        result = engine.play(board, chess.engine.Limit(time=0.35))
        return result.move.uci()


