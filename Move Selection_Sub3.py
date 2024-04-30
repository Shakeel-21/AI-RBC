import chess
import chess.engine
from collections import Counter
import os

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


n_boards = int(input())
fen_strings = [input() for i in range(n_boards)]


print(select_common_move(fen_strings))