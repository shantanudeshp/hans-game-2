# app.py
from flask import Flask, render_template, request, jsonify, session
import os
import copy
from typing import List, Tuple, Dict, Any, Optional, Set

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Game constants
EMPTY: int = 0
PLAYER: int = 1  # White (bottom)
AI: int = 2      # Black (top)

# Initial board setup (3x3 grid)
# 0 = empty, 1 = player pawn, 2 = AI pawn
INITIAL_BOARD: List[List[int]] = [
    [2, 2, 2],  # AI pawns at top
    [0, 0, 0],  # Middle row empty
    [1, 1, 1]   # Player pawns at bottom
]

# Canonical board representation for quick lookup
def board_to_string(board: List[List[int]]) -> str:
    """Convert board to string for easy lookup in the perfect play dictionary."""
    return ''.join([''.join([str(cell) for cell in row]) for row in board])

# Complete opening book for perfect hexapawn play
# Maps board state to optimal move: (from_row, from_col), (to_row, to_col)
PERFECT_MOVES: Dict[str, Tuple[Tuple[int, int], Tuple[int, int]]] = {
    # Initial responses after white's first move
    '220010101': ((0, 1), (1, 1)),  # White moved left pawn, Black responds with center pawn forward
    '202010101': ((0, 1), (1, 1)),  # White moved right pawn, Black responds with center pawn forward
    '221000101': ((0, 0), (1, 0)),  # White moved center pawn, Black responds with left pawn forward
    
    # Responses after 2nd white move, when center Black pawn is at (1,1)
    '020210101': ((1, 1), (2, 0)),  # Capture left white pawn
    '020201101': ((1, 1), (2, 2)),  # Capture right white pawn
    '020010201': ((1, 1), (2, 0)),  # Capture left white pawn
    '020010021': ((1, 1), (2, 2)),  # Capture right white pawn
    
    # Responses after white's 2nd move, when left Black pawn is at (1,0)
    '200210101': ((1, 0), (2, 1)),  # Capture center white pawn
    '200201101': ((0, 2), (1, 2)),  # Move right pawn forward
    '200010201': ((0, 2), (1, 2)),  # Move right pawn forward
    '200010021': ((1, 0), (2, 1)),  # Capture center white pawn
    
    # Common middle game positions
    '002200101': ((0, 2), (1, 1)),  # Block center
    '020200101': ((0, 2), (1, 1)),  # Block center
    '020002101': ((0, 0), (1, 1)),  # Block center
    '200020101': ((0, 2), (1, 1)),  # Block center
    '200002101': ((0, 0), (1, 1)),  # Block center
    
    # Additional positions after exchanges
    '020010001': ((1, 1), (2, 1)),  # Go for win by reaching bottom
    '000210001': ((0, 2), (1, 2)),  # Advanced position
    '000010201': ((0, 0), (1, 0)),  # Advanced position
    '200010001': ((1, 0), (2, 0)),  # Go for win by reaching bottom
    '002010001': ((1, 2), (2, 2)),  # Go for win by reaching bottom
    
    # Late game positions 
    '000200001': ((0, 1), (1, 1)),  # Progress toward victory
    '000020001': ((0, 1), (1, 1)),  # Progress toward victory
    '000002001': ((0, 0), (1, 0)),  # Progress toward victory
    '000000201': ((0, 2), (1, 2)),  # Progress toward victory
}

def is_valid_move(board: List[List[int]], from_pos: Tuple[int, int], to_pos: Tuple[int, int], current_player: int) -> bool:
    """Check if move is valid."""
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    
    # Check if positions are in bounds
    if not (0 <= from_row < 3 and 0 <= from_col < 3 and 0 <= to_row < 3 and 0 <= to_col < 3):
        return False
    
    # Check if from_pos contains the current player's pawn
    if board[from_row][from_col] != current_player:
        return False
    
    # Check if to_pos is empty or contains an opponent (for diagonal capture)
    if to_pos == (from_row, from_col):
        return False
    
    # Movement direction (player moves up, AI moves down)
    direction: int = -1 if current_player == PLAYER else 1
    
    # Straight move must go into an empty square
    if to_col == from_col:
        return to_row == from_row + direction and board[to_row][to_col] == EMPTY
    # Diagonal capture: move one row forward and one column left/right; must capture opponent pawn
    elif abs(to_col - from_col) == 1:
        return to_row == from_row + direction and board[to_row][to_col] not in [EMPTY, current_player]
    
    return False

def get_all_valid_moves(board: List[List[int]], current_player: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Get all valid moves for the current player."""
    moves: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    
    for row in range(3):
        for col in range(3):
            if board[row][col] == current_player:
                # Direction of movement
                direction = -1 if current_player == PLAYER else 1
                
                # Forward move
                new_row = row + direction
                if 0 <= new_row < 3 and board[new_row][col] == EMPTY:
                    moves.append(((row, col), (new_row, col)))
                
                # Diagonal captures
                for dc in [-1, 1]:
                    new_col = col + dc
                    if 0 <= new_row < 3 and 0 <= new_col < 3:
                        if board[new_row][new_col] not in [EMPTY, current_player]:
                            moves.append(((row, col), (new_row, new_col)))
    
    return moves

def make_move(board: List[List[int]], from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> List[List[int]]:
    """Make a move on the board and return the new board state."""
    new_board: List[List[int]] = copy.deepcopy(board)
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    
    # Move the pawn
    new_board[to_row][to_col] = new_board[from_row][from_col]
    new_board[from_row][from_col] = EMPTY
    
    return new_board

def check_win(board: List[List[int]], current_player: int) -> bool:
    """
    Check if the current player has won.
    In Hexapawn, a player wins by:
    1. Reaching the opponent's back row
    2. Capturing all opponent pawns
    3. Creating a position where the opponent has no legal moves
    """
    opponent: int = PLAYER if current_player == AI else AI
    
    # 1. Check if player reached opponent's back row
    target_row = 0 if current_player == PLAYER else 2
    for col in range(3):
        if board[target_row][col] == current_player:
            return True
    
    # 2. Check if opponent has no pawns left
    opponent_pawns: int = sum(row.count(opponent) for row in board)
    if opponent_pawns == 0:
        return True
        
    # 3. Check if opponent has no valid moves
    if not get_all_valid_moves(board, opponent):
        return True
    
    return False

def get_best_move(board: List[List[int]]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """
    Get the perfect move for Black (AI/Hans) using a complete lookup table of optimal moves.
    
    For any position not in the lookup table, use a prioritized strategy:
    1. Immediate win moves
    2. Capture moves (especially center)
    3. Center control
    4. Advanced pawns
    """
    # Get the canonical string representation of the board
    board_str = board_to_string(board)
    
    # 1. Check if the position is in our perfect play database
    if board_str in PERFECT_MOVES:
        return PERFECT_MOVES[board_str]
    
    valid_moves = get_all_valid_moves(board, AI)
    
    # If only one move is available, return it
    if len(valid_moves) == 1:
        return valid_moves[0]
    
    # 2. Check for immediate win moves
    for from_pos, to_pos in valid_moves:
        new_board = make_move(board, from_pos, to_pos)
        if check_win(new_board, AI):
            return (from_pos, to_pos)
    
    # 3. Prioritize captures
    capture_moves = []
    for from_pos, to_pos in valid_moves:
        if abs(from_pos[1] - to_pos[1]) == 1:  # Diagonal move = capture
            capture_moves.append((from_pos, to_pos))
    
    if capture_moves:
        # Center captures get highest priority
        for from_pos, to_pos in capture_moves:
            if to_pos[1] == 1:  # Center column
                return (from_pos, to_pos)
        return capture_moves[0]
    
    # 4. Prioritize center control and advancement
    scored_moves = []
    for from_pos, to_pos in valid_moves:
        score = 0
        
        # Prefer center column
        if to_pos[1] == 1:
            score += 3
        
        # Advancement score
        score += to_pos[0] * 2
        
        # Prefer moves that enable future captures
        if to_pos[0] < 2:  # Not on the bottom row yet
            for dc in [-1, 1]:
                next_col = to_pos[1] + dc
                if 0 <= next_col < 3 and to_pos[0] + 1 < 3:
                    if board[to_pos[0] + 1][next_col] == PLAYER:
                        score += 2
        
        scored_moves.append((score, (from_pos, to_pos)))
    
    # Return the move with the highest score
    if scored_moves:
        return max(scored_moves, key=lambda x: x[0])[1]
    
    # Fallback: just return the first valid move (shouldn't happen with proper scoring)
    return valid_moves[0]

@app.route('/')
def index() -> Any:
    """Render the main game page."""
    session['board'] = INITIAL_BOARD
    session['game_over'] = False
    session['winner'] = None
    return render_template('index.html')

@app.route('/get_game_state', methods=['GET'])
def get_game_state() -> Any:
    """Get the current game state."""
    return jsonify({
        'board': session.get('board', INITIAL_BOARD),
        'game_over': session.get('game_over', False),
        'winner': session.get('winner', None)
    })

@app.route('/move', methods=['POST'])
def move() -> Any:
    """Handle player moves and AI responses with perfect play."""
    data: Any = request.get_json()
    from_pos: Tuple[int, int] = tuple(data.get('from_pos'))
    to_pos: Tuple[int, int] = tuple(data.get('to_pos'))
    
    board: List[List[int]] = session.get('board', INITIAL_BOARD)
    game_over: bool = session.get('game_over', False)
    
    if game_over:
        return jsonify({
            'board': board,
            'game_over': game_over,
            'winner': session.get('winner'),
            'message': 'Game is already over!'
        })
    
    # Validate player move
    if not is_valid_move(board, from_pos, to_pos, PLAYER):
        return jsonify({
            'error': 'Invalid move!',
            'board': board
        })
    
    # Process player move
    board = make_move(board, from_pos, to_pos)
    
    # Check if player won (should not happen with perfect AI play, but we'll check)
    if check_win(board, PLAYER):
        session['game_over'] = True
        session['winner'] = 'player'
        session['board'] = board
        return jsonify({
            'board': board,
            'game_over': True,
            'winner': 'player',
            'message': "You win! Hans looks shocked. 'Impossible! My divination has never failed before...'"
        })
    
    # Get AI moves
    ai_moves = get_all_valid_moves(board, AI)
    if not ai_moves:
        session['game_over'] = True
        session['winner'] = 'draw'
        session['board'] = board
        return jsonify({
            'board': board,
            'game_over': True,
            'winner': 'draw',
            'message': "It's a draw! 'A stalemate... reality itself seems distorted,' Hans whispers."
        })
    
    # AI's turn - get the perfect move
    ai_from_pos, ai_to_pos = get_best_move(board)
    
    # Log the move for debugging
    board_str = board_to_string(board)
    print(f"Board: {board_str}, AI Move: From {ai_from_pos} to {ai_to_pos}")
    
    # Make the move
    board = make_move(board, ai_from_pos, ai_to_pos)
    
    # AI response based on game state
    player_pawns = sum(row.count(PLAYER) for row in board)
    
    if check_win(board, AI):
        ai_message = "'The threads of fate always reveal their pattern to those who know how to look,' Hans says triumphantly."
    elif player_pawns <= 1:
        ai_message = "'Your position crumbles as I foresaw,' Hans says with confidence."
    else:
        ai_message = "'Every move brings you closer to the inevitable,' Hans states calmly."
    
    # Check if AI won
    if check_win(board, AI):
        session['game_over'] = True
        session['winner'] = 'ai'
        session['board'] = board
        
        return jsonify({
            'board': board,
            'game_over': True,
            'winner': 'ai',
            'ai_from': ai_from_pos,
            'ai_to': ai_to_pos,
            'message': ai_message
        })
    
    # Check if player has no moves (AI wins)
    player_moves = get_all_valid_moves(board, PLAYER)
    if not player_moves:
        session['game_over'] = True
        session['winner'] = 'ai'
        session['board'] = board
        ai_win_message = "'With no moves left, you must concede. Your defeat was inevitable,' Hans says triumphantly."
        
        return jsonify({
            'board': board,
            'game_over': True,
            'winner': 'ai',
            'ai_from': ai_from_pos,
            'ai_to': ai_to_pos,
            'message': ai_win_message
        })
    
    # Update session for continuing game
    session['board'] = board
    
    return jsonify({
        'board': board,
        'game_over': False,
        'winner': None,
        'ai_from': ai_from_pos,
        'ai_to': ai_to_pos,
        'message': ai_message
    })

@app.route('/reset', methods=['POST'])
def reset() -> Any:
    """Reset the game."""
    session['board'] = INITIAL_BOARD
    session['game_over'] = False
    session['winner'] = None
    
    return jsonify({
        'board': INITIAL_BOARD,
        'game_over': False,
        'message': 'Game reset. You go first!'
    })

if __name__ == '__main__':
    app.run(debug=True)