import logging
from reconchess import Player
import chess.engine
import random
from collections import Counter
import chess
import concurrent.futures
from threading import Lock

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class ImprovedAgent(Player):
    def __init__(self):
        logging.debug('Initializing ImprovedAgent')
        self.board = None
        self.color = None
        self.opponent = None
        self.my_piece_captured_square = None
        self.count = None
        self.possible_states = set()
        self.lock = Lock()
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci('./opt/stockfish/stockfish', setpgrp=True)
        except Exception as e:
            logging.error(f'Failed to start Stockfish engine: {e}')
            raise

    def handle_game_start(self, color, board, opponent_name):
        logging.info(f'Game started. Color: {color}, Opponent: {opponent_name}')
        self.board = board
        self.count = 0
        self.color = color
        self.opponent = opponent_name
        self.possible_states = {board.fen()}

    def handle_opponent_move_result(self, captured_my_piece, capture_square):
        logging.info(f'Opponent move result. Captured my piece: {captured_my_piece}, Capture square: {capture_square}')
        self.my_piece_captured_square = capture_square
        if captured_my_piece:
            self.board.remove_piece_at(capture_square)
            capture_square_name = chess.SQUARE_NAMES[capture_square]
            self.possible_states = predict_next_states_with_captures(self.possible_states, capture_square_name)
        else:
            self.possible_states = {next_state for state in self.possible_states for next_state in nextStatePrediction(state)}

    def choose_sense(self, sense_actions, move_actions, seconds_left):
        logging.debug(f'Choosing sense. Sense actions: {sense_actions}, Move actions: {move_actions}, Seconds left: {seconds_left}')
        valid_sense_actions = [square for square in sense_actions if square not in chess.SquareSet(
            chess.BB_RANK_1 | chess.BB_RANK_8 | chess.BB_FILE_A | chess.BB_FILE_H)]

        if self.my_piece_captured_square:
            logging.info(f'Choosing captured square for sense: {self.my_piece_captured_square}')
            return self.my_piece_captured_square

        future_move = self.future_move(move_actions, seconds_left)
        if future_move is not None and self.board.piece_at(future_move.to_square) is not None:
            logging.info(f'Choosing future move square for sense: {future_move.to_square}')
            return future_move.to_square

        for square, piece in self.board.piece_map().items():
            if piece.color == self.color and square in valid_sense_actions:
                valid_sense_actions.remove(square)

        chosen_sense = random.choice(valid_sense_actions)
        logging.info(f'Chosen sense square: {chosen_sense}')
        return chosen_sense

    def handle_sense_result(self, sense_result):
        logging.info(f'Handling sense result: {sense_result}')
        for square, piece in sense_result:
            self.board.set_piece_at(square, piece)

        window = ";".join(
            [f"{chess.SQUARE_NAMES[square]}:{piece.symbol() if piece else '?'}" for square, piece in sense_result])
        self.possible_states = {state for fen in self.possible_states for state in nextStateWithSense(fen, window)}

    def select_common_move(self, move_actions):
        logging.debug(f'Selecting common move from actions: {move_actions}')
        move_counter = Counter()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.evaluate_state, fen, move_actions): fen for fen in self.possible_states}
            for future in concurrent.futures.as_completed(futures):
                try:
                    move = future.result()
                    if move:
                        move_counter[move.uci()] += 1
                except Exception as exc:
                    logging.error(f'Error evaluating state: {exc}')

        if not move_counter:
            chosen_move = random.choice(list(move_actions))
            logging.info(f'No common moves found. Choosing random move: {chosen_move}')
            return chosen_move

        most_common_move = sorted(move_counter.items(), key=lambda x: (-x[1], x[0]))[0][0]
        logging.info(f'Most common move selected: {most_common_move}')
        return chess.Move.from_uci(most_common_move)

    def future_move(self, move_actions, seconds_left):
        logging.debug(f'Predicting future move. Move actions: {move_actions}, Seconds left: {seconds_left}')
        enemy_king_square = self.board.king(not self.color)
        if enemy_king_square:
            enemy_king_attackers = self.board.attackers(self.color, enemy_king_square)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                future_move = chess.Move(attacker_square, enemy_king_square)
                logging.info(f'Future move attacking enemy king: {future_move}')
                return future_move

        try:
            self.board.turn = self.color
            self.board.clear_stack()
            result = self.engine.play(self.board, chess.engine.Limit(time=0.1))
            logging.info(f'Stockfish suggested move: {result.move}')
            return result.move
        except chess.engine.EngineTerminatedError:
            logging.error('Stockfish Engine died')
        except chess.engine.EngineError:
            logging.error(f'Stockfish Engine bad state at "{self.board.fen()}"')

        logging.info('No future move found, returning None')
        return None

    def choose_move(self, move_actions, seconds_left):
        logging.debug(f'Choosing move. Move actions: {move_actions}, Seconds left: {seconds_left}')
        enemy_king_square = self.board.king(not self.color)
        if enemy_king_square:
            enemy_king_attackers = self.board.attackers(self.color, enemy_king_square)
            if enemy_king_attackers:
                attacker_square = enemy_king_attackers.pop()
                move = chess.Move(attacker_square, enemy_king_square)
                if self.board.is_legal(move):
                    logging.info(f'Choosing move to capture enemy king: {move}')
                    return move

        max_states = 10000
        if len(self.possible_states) > max_states:
            self.possible_states = random.sample(self.possible_states, max_states)

        move_scores = self.evaluate_moves(move_actions, seconds_left)

        valid_moves = [chess.Move.from_uci(move) for move in move_scores if chess.Move.from_uci(move) in move_actions]
        if valid_moves:
            sorted_moves = sorted(valid_moves, key=lambda move: move_scores.get(move.uci(), float('-inf')), reverse=True)
            for move in sorted_moves:
                if self.board.is_legal(move):
                    logging.info(f'Chosen move: {move}')
                    return move
        else:
            chosen_move = random.choice(move_actions)
            logging.info(f'No valid moves found. Choosing random move: {chosen_move}')
            return chosen_move

    def handle_move_result(self, requested_move, taken_move, captured_opponent_piece, capture_square):
        logging.info(f'Handling move result. Requested move: {requested_move}, Taken move: {taken_move}, Captured opponent piece: {captured_opponent_piece}, Capture square: {capture_square}')
        if taken_move is not None and self.board.is_legal(taken_move):
            self.board.push(taken_move)
        if captured_opponent_piece:
            capture_square_name = chess.SQUARE_NAMES[capture_square]
            self.possible_states = predict_next_states_with_captures(self.possible_states, capture_square_name)
        else:
            if taken_move:
                self.possible_states = [execute_move(state, taken_move.uci()) for state in self.possible_states if self.is_valid_fen(state)]
            else:
                self.possible_states = [state for state in self.possible_states if state == self.board.fen()]

    def handle_game_end(self, winner_color, win_reason, game_history):
        logging.info(f'Game ended. Winner color: {winner_color}, Win reason: {win_reason}')
        self.engine.quit()
        if winner_color == self.color:
            logging.info("Game Over. Improved won!")
        elif winner_color is None:
            logging.info("Game Over. It was a draw.")
        else:
            logging.info("Game Over. Improved lost.")

    def is_valid_fen(self, fen):
        try:
            board = chess.Board(fen)
            return board.is_valid()
        except ValueError:
            return False

    def evaluate_moves(self, move_actions, seconds_left):
        move_scores = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.evaluate_state, fen, move_actions): fen for fen in self.possible_states}
            for future in concurrent.futures.as_completed(futures):
                try:
                    move, score = future.result()
                    if move is not None:
                        if move.uci() in move_scores:
                            move_scores[move.uci()] += score
                        else:
                            move_scores[move.uci()] = score
                except Exception as exc:
                    logging.error(f'Error evaluating state: {exc}')
        return move_scores

    def evaluate_state(self, fen, move_actions):
        try:
            board = chess.Board(fen)
            if not board.is_valid():
                return None, 0
            self.board.turn = self.color
            self.board.clear_stack()
            time_limit = min(1, 10 / len(self.possible_states))
            result = self.engine.play(board, chess.engine.Limit(time=time_limit), info=chess.engine.INFO_SCORE)
            move = result.move

            if move is None or not self.board.is_legal(move):
                return None, 0

            score = 0
            board.push(move)
            enemy_king_square = board.king(not self.color)
            if enemy_king_square:
                enemy_king_attackers = board.attackers(self.color, enemy_king_square)
                if enemy_king_attackers:
                    score += 2000

            my_king_square = board.king(self.color)
            if my_king_square:
                my_king_attackers = board.attackers(not self.color, my_king_square)
                if my_king_attackers:
                    score -= 2000

            board.pop()

            if board.is_capture(move):
                captured_piece = board.piece_at(move.to_square)
                if captured_piece:
                    if captured_piece.piece_type == chess.KING:
                        score += 900
                    elif captured_piece.piece_type != chess.PAWN:
                        score += 500
                    else:
                        score += 100

            return move, score
        except Exception as e:
            logging.error(f'Error evaluating state {fen}: {e}')
            return None, 0


def nextStatePrediction(fen):
    board = chess.Board(fen)
    if not board.is_valid():
        return []
    next_positions = []

    for move in board.legal_moves:
        temp_board = board.copy()
        temp_board.push(move)
        next_positions.append(temp_board.fen())

    next_positions.sort()
    return next_positions

def nextStateWithSense(fen, window):
    board = chess.Board(fen)
    if not board.is_valid():
        return []
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
        if not board.is_valid():
            continue
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
    try:
        board = chess.Board(fen)
        chess_move = chess.Move.from_uci(move)
        if chess_move in board.legal_moves:
            board.push(chess_move)
            return board.fen()
        else:
            return fen
    except ValueError:
        return fen

