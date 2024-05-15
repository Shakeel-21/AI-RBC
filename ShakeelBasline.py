import chess
from reconchess import *
import chess.engine
from collections import Counter
import os
import random


class MyAgent(Player):
    def __init__(self):
        self.board = None
        self.color = None
        self.opponent = None
        self.possible_states = []
        self.engine = chess.engine.SimpleEngine.popen_uci('./opt/stockfish/stockfish', setpgrp=True)

    def handle_game_start(self, color, board, opponent_name):
        self.board = board
        self.color = color
        self.opponent = opponent_name
        self.possible_states = [board.fen()]

    def handle_opponent_move_result(self, captured_my_piece, capture_square):
        if captured_my_piece:
            capture_square_name = chess.SQUARE_NAMES[capture_square]
            self.possible_states = predict_next_states_with_captures(self.possible_states, capture_square_name)
        else:
            self.possible_states = [next_state for state in self.possible_states for next_state in
                                    nextStatePrediction(state)]

    def choose_sense(self, sense_actions, move_actions, seconds_left):
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
        max_states = 1000  # Limit the number of states to consider
        if len(self.possible_states) > max_states:
            self.possible_states = random.sample(self.possible_states, max_states)

        move_counter = Counter()
        for fen in self.possible_states:
            board = chess.Board(fen)
            if board.is_checkmate():
                move = list(board.legal_moves)[0]
            else:
                try:
                    # Adjust the time limit based on the number of states and remaining time
                    time_limit = min(1, seconds_left / len(self.possible_states))
                    result = self.engine.play(board, chess.engine.Limit(time=time_limit), info=chess.engine.INFO_SCORE)
                    move = result.move
                except chess.engine.EngineTerminatedError:
                    # Handle engine termination gracefully
                    move = random.choice(list(board.legal_moves))
            move_counter[move.uci()] += 1

        valid_moves = [move for move in move_counter if chess.Move.from_uci(move) in move_actions]

        if valid_moves:
            most_common_move = max(valid_moves, key=move_counter.get)
            return chess.Move.from_uci(most_common_move)
        else:
            # If no valid moves are found, choose a random move from the legal moves
            return random.choice(move_actions)
    def handle_move_result(self, requested_move, taken_move, captured_opponent_piece, capture_square):
        if captured_opponent_piece:
            capture_square_name = chess.SQUARE_NAMES[capture_square]
            self.possible_states = predict_next_states_with_captures(self.possible_states, capture_square_name)
        else:
            if taken_move:
                self.possible_states = [execute_move(state, taken_move.uci()) for state in self.possible_states]
            else:
                self.possible_states = [state for state in self.possible_states if state == self.board.fen()]

    def handle_game_end(self, winner_color, win_reason, game_history):
        self.engine.quit()
        if winner_color == self.color:
            print("Game Over. I won!")
        elif winner_color is None:
            print("Game Over. It was a draw.")
        else:
            print("Game Over. I lost.")


def nextStatePrediction(fen):
    board = chess.Board(fen)
    next_positions = []

    for move in board.legal_moves:
        temp_board = board.copy()
        temp_board.push(move)
        next_positions.append(temp_board.fen())

    next_positions.sort()
    return next_positions


def nextStateWithSense(fen, window):
    board = chess.Board(fen)
    rows = fen.split('/')
    rows[-1] = rows[-1].split()[0]

    expanded_rows = []
    for row in rows:
        expanded_row = ''
        for char in row:
            if char.isdigit():
                expanded_row += '?' * int(char)
            else:
                expanded_row += char
        expanded_rows.append(expanded_row)

    view = window.split(';')
    pairs = [square.split(':') for square in view]

    for pair in pairs:
        location = pair[0]
        piece = pair[1]
        letter = location[0]
        number = location[1]
        row = expanded_rows[abs(int(number) - 8)]
        if row[ord(letter) - ord('a')] != piece:
            return []

    return [fen]


def predict_next_states_with_captures(fen_list, capture_square):
    capture_moves = []
    for fen in fen_list:
        board = chess.Board(fen)
        try:
            capture_square_index = chess.parse_square(capture_square)
            for move in board.legal_moves:
                if move.to_square == capture_square_index and board.is_capture(move):
                    board.push(move)
                    capture_moves.append(board.fen())
                    board.pop()
        except ValueError:
            # Handle invalid capture_square gracefully
            pass
    capture_moves.sort()
    return capture_moves


def execute_move(fen, move):
    board = chess.Board(fen)
    chess_move = chess.Move.from_uci(move)
    if chess_move in board.legal_moves:
        board.push(chess_move)
        return board.fen()
    else:
        return fen
