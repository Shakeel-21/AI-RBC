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
        self.possible_states = set()
        self.engine = chess.engine.SimpleEngine.popen_uci('./opt/stockfish/stockfish', setpgrp=True)

    def handle_game_start(self, color, board, opponent_name):
        self.board = board
        self.color = color
        self.opponent = opponent_name
        self.possible_states = {board.fen()}

    def handle_opponent_move_result(self, captured_my_piece, capture_square):
        if captured_my_piece:
            capture_square_name = chess.SQUARE_NAMES[capture_square]
            self.possible_states = predict_next_states_with_captures(self.possible_states, capture_square_name)
        else:
            self.possible_states = [next_state for state in self.possible_states for next_state, _ in
                                    nextStatePrediction(state, self.engine, depth=3)]

        # Select a subset of promising states
        self.possible_states = select_promising_states(self.possible_states, max_states=1000)

    def choose_sense(self, sense_actions, move_actions, seconds_left):
        valid_sense_actions = [square for square in sense_actions if square not in chess.SquareSet(
            chess.BB_RANK_1 | chess.BB_RANK_8 | chess.BB_FILE_A | chess.BB_FILE_H)]
        return random.choice(valid_sense_actions)

    def handle_sense_result(self, sense_result):
        window = ";".join(
            [f"{chess.SQUARE_NAMES[square]}:{piece.symbol() if piece else '?'}" for square, piece in sense_result])

        # Filter the possible states based on the current sensing result
        self.possible_states = [state for state, _ in self.possible_states if nextStateWithSense(state, window)]

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
                    time_limit = min(1, 10 / len(self.possible_states))
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
            print("Game Over. Shakeel won!")
        elif winner_color is None:
            print("Game Over. It was a draw.")
        else:
            print("Game Over. Shakeel lost.")


def nextStatePrediction(fen, engine, depth, alpha=-float('inf'), beta=float('inf'), time_limit=0.1):
    board = chess.Board(fen)

    if depth == 0:
        info = engine.analyse(board, chess.engine.Limit(time=time_limit))
        score = info["score"].white().score()
        if score is None:
            score = 0
        return [(board.fen(), score)]

    next_positions = []

    for move in board.legal_moves:
        board.push(move)

        # Recursively evaluate the next positions
        next_pos = nextStatePrediction(board.fen(), engine, depth - 1, -beta, -alpha, time_limit)

        # Negamax score for the current move
        score = -next_pos[0][1]

        next_positions.append((board.fen(), score))

        board.pop()

        # Update alpha value
        alpha = max(alpha, score)

        # Alpha-beta pruning
        if alpha >= beta:
            break

    # Sort the positions based on the evaluation score in descending order
    next_positions.sort(key=lambda x: x[1], reverse=True)

    return next_positions


def nextStateWithSense(fen, window):
    if not isinstance(fen, str):
        raise TypeError("Expected 'fen' to be a string, got {}".format(type(fen)))

    board = chess.Board(fen)
    for square_name, piece_symbol in (item.split(':') for item in window.split(';')):
        square = chess.parse_square(square_name)
        if piece_symbol == '?':
            if board.piece_at(square) is not None:
                return False
        else:
            piece = chess.Piece.from_symbol(piece_symbol)
            if board.piece_at(square) != piece:
                return False
    return True


def predict_next_states_with_captures(fen_list, capture_square):
    capture_moves = set()
    for fen in fen_list:
        board = chess.Board(fen)
        try:
            capture_square_index = chess.parse_square(capture_square)
            for move in board.generate_legal_captures():
                if move.to_square == capture_square_index and board.is_capture(move):
                    board.push(move)
                    capture_moves.add(board.fen())
                    board.pop()
        except ValueError:
            # Handle invalid capture_square gracefully
            pass

    return capture_moves


def select_promising_states(states, max_states):
    if len(states) <= max_states:
        return states

    # Sort the states based on their evaluation scores
    sorted_states = sorted(states, key=lambda x: x[1], reverse=True)

    # Select the top max_states promising states
    promising_states = sorted_states[:max_states]

    return [state for state, _ in promising_states]


def execute_move(fen, move):
    board = chess.Board(fen)
    chess_move = chess.Move.from_uci(move)
    if chess_move in board.legal_moves:
        board.push(chess_move)
        return board.fen()
    else:
        return fen
