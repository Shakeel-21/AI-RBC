import chess
from reconchess import utilities, is_illegal_castle


def boardRepresentation(line):
    board = chess.Board(line)
    print(board)


def nextMovePrediction(line):
  board = chess.Board(line)
  possible_moves = list(board.pseudo_legal_moves) + [chess.Move.null()]

  if board.castling_rights:
    temp_board = board.copy()
    for move in utilities.without_opponent_pieces(temp_board).generate_castling_moves():
      if not is_illegal_castle(temp_board, move):
        possible_moves.append(move)

  possible_moves = list(set(possible_moves))
  possible_moves.sort(key=lambda move: move.uci())

  for move in possible_moves:
    print(move)


line=input()
# boardRepresentation(line)
# Call moveExecution here
nextMovePrediction(line)


