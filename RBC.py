import chess

def boardRepresentation(line):
    board = chess.Board(line)
    print(board)

line=input()
boardRepresentation(line)