from reconchess import *
import chess.engine
import random
from collections import Counter


class ImprovedAgent(Player):
    def __init__(self):
        self.board = None
        self.color = None
        self.opponent = None
        self.my_piece_captured_square = None
        self.count = None
        self.possible_states = set()
        self.engine = chess.engine.SimpleEngine.popen_uci('/opt/stockfish/stockfish', setpgrp=True)

    def handle_game_start(self, color, board, opponent_name):
        self.board = board
        self.count = 0
        self.color = color
        self.opponent = opponent_name
        self.possible_states = {board.fen()}

    def handle_opponent_move_result(self, captured_my_piece, capture_square):
        self.my_piece_captured_square = capture_square
        if captured_my_piece:
            self.board.remove_piece_at(capture_square)
            capture_square_name = chess.SQUARE_NAMES[capture_square]
            self.possible_states = predict_next_states_with_captures(self.possible_states, capture_square_name)
        else:
            self.possible_states = [next_state for state in self.possible_states for next_state in
                                    nextStatePrediction(state)]

    def choose_sense(self, sense_actions, move_actions, seconds_left):
        valid_sense_actions = [square for square in sense_actions if square not in chess.SquareSet(
            chess.BB_RANK_1 | chess.BB_RANK_8 | chess.BB_FILE_A | chess.BB_FILE_H)]

        if self.my_piece_captured_square:
            return self.my_piece_captured_square

        future_move = self.choose_move(move_actions, seconds_left)
        if future_move is not None and self.board.piece_at(future_move.to_square) is not None:
            return future_move.to_square

        for square, piece in self.board.piece_map().items():
            if piece.color == self.color and square in valid_sense_actions:
                valid_sense_actions.remove(square)

        if self.count < 4:
            if self.color == chess.WHITE:
                valid_sense_actions = [chess.C7, chess.F7]
            else:
                valid_sense_actions = [chess.C2, chess.F2]
        elif self.count < 10:
            if self.color == chess.WHITE:
                valid_sense_actions = [square for square in sense_actions if square not in chess.SquareSet(
                    chess.BB_RANK_1 | chess.BB_RANK_8 | chess.BB_RANK_2 | chess.BB_RANK_3 | chess.BB_FILE_A | chess.BB_FILE_H)]
            else:
                valid_sense_actions = [square for square in sense_actions if square not in chess.SquareSet(
                    chess.BB_RANK_1 | chess.BB_RANK_8 | chess.BB_RANK_7 | chess.BB_RANK_6 | chess.BB_FILE_A | chess.BB_FILE_H)]

        return random.choice(valid_sense_actions)

    def handle_sense_result(self, sense_result):
        for square, piece in sense_result:
            self.board.set_piece_at(square, piece)

        window = ";".join(
            [f"{chess.SQUARE_NAMES[square]}:{piece.symbol() if piece else '?'}" for square, piece in sense_result])
        self.possible_states = [state for fen in self.possible_states for state in nextStateWithSense(fen, window)]

    def select_common_move(self, move_actions):
        move_counter = Counter()
        for fen in self.possible_states:
            board = chess.Board(fen)

            time_limit = min(2, 10 / len(self.possible_states))
            result = self.engine.play(board, chess.engine.Limit(time=time_limit), info=chess.engine.INFO_SCORE)
            move = result.move

            if move is None or move not in move_actions or not self.board.is_legal(move):
                continue

            move_counter[move.uci()] += 1

        if not move_counter:
            return random.choice(list(move_actions))

        most_common_move = sorted(move_counter.items(), key=lambda x: (-x[1], x[0]))[0][0]
        return chess.Move.from_uci(most_common_move)

    def choose_move(self, move_actions, seconds_left):
        enemy_king_square = self.board.king(not self.color)
        if enemy_king_square:
            enemy_king_attackers = self.board.attackers(self.color, enemy_king_square)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                move = chess.Move(attacker_square, enemy_king_square)
                if self.board.is_legal(move):
                    return move

        max_states = 10000  # Limit the number of states to consider
        if len(self.possible_states) > max_states:
            self.possible_states = random.sample(self.possible_states, max_states)

        move_scores = {}

        for fen in self.possible_states:
            board = chess.Board(fen)

            try:
                self.board.turn = self.color
                self.board.clear_stack()
                time_limit = min(1, 10 / len(self.possible_states))
                result = self.engine.play(board, chess.engine.Limit(time=time_limit), info=chess.engine.INFO_SCORE)
                move = result.move

                if move is None:
                    continue

                score = 0

                board.push(move)

                # Check if the move results in attackers on the enemy king in the next move
                enemy_king_square = board.king(not self.color)
                if enemy_king_square:
                    enemy_king_attackers = board.attackers(self.color, enemy_king_square)
                    if enemy_king_attackers:
                        score += 2000  # Prioritize moves that lead to attackers on the enemy king

                my_king_square = board.king(self.color)
                if my_king_square:
                    my_king_attackers = board.attackers(not self.color, my_king_square)
                    if my_king_attackers:
                        score -= 2000  # Penalize moves that leave your king exposed to capture

                board.pop()

                if board.is_capture(move):
                    captured_piece = board.piece_at(move.to_square)
                    if captured_piece:
                        if captured_piece.piece_type == chess.KING:
                            score += 900  # Prioritize capturing the opponent's king
                        elif captured_piece.piece_type != chess.PAWN:
                            score += 500  # Prioritize capturing non-pawn pieces
                        else:
                            score += 100  # Capturing pawns is less important

                move_scores[move.uci()] = score
            except chess.engine.EngineTerminatedError:
                # Handle engine termination gracefully
                move = random.choice(list(board.legal_moves))
                move_scores[move.uci()] = 0

        # If the time limit is not exceeded, continue with the original logic
        valid_moves = [move for move in move_scores if chess.Move.from_uci(move) in move_actions]
        if valid_moves:
            best_move = max(valid_moves, key=lambda move: move_scores.get(move, float('-inf')))
            return chess.Move.from_uci(best_move)
        else:
            # If no valid moves are found, choose a random move from the legal moves
            return random.choice(move_actions)

    def handle_move_result(self, requested_move, taken_move, captured_opponent_piece, capture_square):
        if taken_move is not None:
            self.board.push(taken_move)
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
            print("Game Over. Improved won!")
        elif winner_color is None:
            print("Game Over. It was a draw.")
        else:
            print("Game Over. Improved lost.")



class RandomSensing(Player):
    def __init__(self):
        self.board = None
        self.color = None
        self.opponent = None
        self.possible_states = []
        self.engine = chess.engine.SimpleEngine.popen_uci('/opt/stockfish/stockfish', setpgrp=True)

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

    def select_common_move(self, move_actions):
        move_counter = Counter()
        for fen in self.possible_states:
            board = chess.Board(fen)

            time_limit = min(2.0, 10 / len(self.possible_states))
            result = self.engine.play(board, chess.engine.Limit(time=time_limit), info=chess.engine.INFO_SCORE)
            move = result.move

            if move is None or move not in move_actions or not self.board.is_legal(move):
                continue

            move_counter[move.uci()] += 1

        if not move_counter:
            return []

        sorted_moves = sorted(move_counter.items(), key=lambda x: (-x[1], x[0]))
        return [chess.Move.from_uci(move[0]) for move in sorted_moves]
    def choose_move(self, move_actions, seconds_left):
        max_states = 10000  # Limit the number of states to consider
        if len(self.possible_states) > max_states:
            self.possible_states = random.sample(self.possible_states, max_states)

        common_moves = self.select_common_move(move_actions)

        for move in common_moves:
            if self.board.is_legal(move):
                return move

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
            print("Game Over. Random won!")
        elif winner_color is None:
            print("Game Over. It was a draw.")
        else:
            print("Game Over. Random lost.")



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