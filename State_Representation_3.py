import chess

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

# Ask for user input
fen_input = input()
move_input = input()

# Get the new FEN after the move
new_fen = execute_move(fen_input, move_input)
print(new_fen)