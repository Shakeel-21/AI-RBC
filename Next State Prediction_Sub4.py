import chess

def predict_next_states_with_captures(fen, capture_square):
    board = chess.Board(fen)
    capture_moves = []
    
    for move in board.legal_moves:
        if move.to_square == chess.parse_square(capture_square) and board.is_capture(move):
            board.push(move)
            capture_moves.append(board.fen())   
            board.pop()
    
    capture_moves.sort() 
    return capture_moves

fen_input = input()
capture_square_input = input()

predicted_states = predict_next_states_with_captures(fen_input, capture_square_input)
for state in predicted_states:
    print(state)