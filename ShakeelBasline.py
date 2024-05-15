from reconchess import *
import chess.engine

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
            self.possible_states = [next_state for state in self.possible_states for next_state in
                                    nextStatePrediction(state)]

    def choose_sense(self, sense_actions, move_actions, seconds_left):
        valid_sense_actions = [square for square in sense_actions if square not in chess.SquareSet(
            chess.BB_RANK_1 | chess.BB_RANK_8 | chess.BB_FILE_A | chess.BB_FILE_H)]

        # Get the last moved piece by either player
        last_move = self.board.peek() if self.board.move_stack else None

        if last_move and last_move.to_square in valid_sense_actions:
            # If the last move is in the valid sense actions, sense that square
            return last_move.to_square

        # If no last move or the last move is not in the valid sense actions, choose a random sense action
        return random.choice(valid_sense_actions)

    def handle_sense_result(self, sense_result):
        window = ";".join(
            [f"{chess.SQUARE_NAMES[square]}:{piece.symbol() if piece else '?'}" for square, piece in sense_result])
        self.possible_states = [state for fen in self.possible_states for state in
                                nextStateWithSense(fen, window)]

    def choose_move(self, move_actions, seconds_left):
        max_states = 10000  # Limit the number of states to consider
        if len(self.possible_states) > max_states:
            self.possible_states = random.sample(self.possible_states, max_states)

        move_scores = {}
        for fen in self.possible_states:
            board = chess.Board(fen)
            for move in board.legal_moves:
                score = 0
                if board.is_capture(move):
                    captured_piece = board.piece_at(move.to_square)
                    if captured_piece and captured_piece.piece_type == chess.KING:
                        # Prioritize capturing the opponent's king
                        score += 1000
                    elif captured_piece and captured_piece.piece_type != chess.PAWN:
                        score += 500
                    else:
                        score += 400
                if board.is_check():
                    # Prioritize moves that make the king evade capture
                    if board.turn == self.color:
                        score += 100
                    else:
                        score -= 100
                move_scores[move.uci()] = move_scores.get(move.uci(), 0) + score

        valid_moves = [move for move in move_scores if chess.Move.from_uci(move) in move_actions]

        if valid_moves:
            best_move = max(valid_moves, key=move_scores.get)
            return chess.Move.from_uci(best_move)
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
    for square_name, piece_symbol in (item.split(':') for item in window.split(';')):
        square = chess.parse_square(square_name)
        if piece_symbol == '?':
            if board.piece_at(square) is not None:
                return {fen}
        else:
            piece = chess.Piece.from_symbol(piece_symbol)
            if board.piece_at(square) != piece:
                return {}
    return {fen}


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


def execute_move(fen, move):
    board = chess.Board(fen)
    chess_move = chess.Move.from_uci(move)
    if chess_move in board.legal_moves:
        board.push(chess_move)
        return board.fen()
    else:
        return fen
