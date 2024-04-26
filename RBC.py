import chess
from reconchess import utilities, is_illegal_castle


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


line=input()
# boardRepresentation(line)
# Call moveExecution here
nextMovePrediction(line)
