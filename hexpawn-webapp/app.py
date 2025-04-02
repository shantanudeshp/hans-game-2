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
# Row 0: AI pawns (top)
# Row 1: empty
# Row 2: Player pawns (bottom)
INITIAL_BOARD: List[List[int]] = [
    [2, 2, 2],
    [0, 0, 0],
    [1, 1, 1]
]

def board_to_string(board: List[List[int]]) -> str:
    """Convert board to a canonical 9-character string (row-by-row)."""
    return ''.join(''.join(str(cell) for cell in row) for row in board)

def is_valid_move(board: List[List[int]], from_pos: Tuple[int, int],
                  to_pos: Tuple[int, int], current_player: int) -> bool:
    """Return True if the move is valid for current_player."""
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    if not (0 <= from_row < 3 and 0 <= from_col < 3 and 0 <= to_row < 3 and 0 <= to_col < 3):
        return False
    if board[from_row][from_col] != current_player:
        return False
    if (from_row, from_col) == (to_row, to_col):
        return False
    # Movement direction: White moves upward (-1), Black moves downward (+1)
    direction: int = -1 if current_player == PLAYER else 1
    if to_col == from_col:
        return to_row == from_row + direction and board[to_row][to_col] == EMPTY
    elif abs(to_col - from_col) == 1:
        # Diagonal move must capture opponent pawn.
        return to_row == from_row + direction and board[to_row][to_col] not in [EMPTY, current_player]
    return False

def get_all_valid_moves(board: List[List[int]], current_player: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Return a list of all valid moves for current_player."""
    moves: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    for row in range(3):
        for col in range(3):
            if board[row][col] == current_player:
                direction: int = -1 if current_player == PLAYER else 1
                new_row: int = row + direction
                if 0 <= new_row < 3 and board[new_row][col] == EMPTY:
                    moves.append(((row, col), (new_row, col)))
                for dc in [-1, 1]:
                    new_col: int = col + dc
                    if 0 <= new_row < 3 and 0 <= new_col < 3:
                        if board[new_row][new_col] not in [EMPTY, current_player]:
                            moves.append(((row, col), (new_row, new_col)))
    return moves

def make_move(board: List[List[int]], from_pos: Tuple[int, int],
              to_pos: Tuple[int, int]) -> List[List[int]]:
    """Return a new board state after making the given move."""
    new_board: List[List[int]] = copy.deepcopy(board)
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    new_board[to_row][to_col] = new_board[from_row][from_col]
    new_board[from_row][from_col] = EMPTY
    return new_board

def check_win(board: List[List[int]], current_player: int) -> bool:
    """
    Return True if current_player has won.
    Winning conditions:
      1. A pawn reaches the opponent's back row.
      2. The opponent has no pawns.
      3. The opponent has no legal moves.
    """
    opponent: int = PLAYER if current_player == AI else AI
    # Condition 1: Reaching the opponent's back row.
    target_row: int = 0 if current_player == PLAYER else 2
    for col in range(3):
        if board[target_row][col] == current_player:
            return True
    # Condition 2: Opponent has no pawns.
    opponent_pawns: int = sum(row.count(opponent) for row in board)
    if opponent_pawns == 0:
        return True
    # Condition 3: Opponent has no legal moves.
    if not get_all_valid_moves(board, opponent):
        return True
    return False

# --- Retrograde Analysis (Negamax) to compute perfect moves ---
# We use a negamax search with memoization. The outcome is defined from the
# perspective of the player whose turn it is: +1 means a forced win, -1 a forced loss.
# (There are no draws in hexapawn with optimal play.)

# Memoization dictionary: key is (board_string, turn) and value is (value, best_move)
MemoType = Dict[Tuple[str, int], Tuple[int, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]]

def negamax(board: List[List[int]], turn: int, memo: MemoType) -> Tuple[int, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    state = (board_to_string(board), turn)
    if state in memo:
        return memo[state]
    
    # Terminal conditions: if the board is already winning for someone.
    if check_win(board, PLAYER) or check_win(board, AI):
        # If the current board is terminal, then the previous move won.
        # So the outcome for the player whose turn it is is a loss.
        outcome: int = -1
        memo[state] = (outcome, None)
        return (outcome, None)
    
    moves: List[Tuple[Tuple[int, int], Tuple[int, int]]] = get_all_valid_moves(board, turn)
    if not moves:
        # No moves: lose immediately.
        memo[state] = (-1, None)
        return (-1, None)
    
    best_value: int = -1000
    best_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
    for move in moves:
        new_board: List[List[int]] = make_move(board, move[0], move[1])
        # Switch turn: if turn was AI, opponent becomes PLAYER, and vice versa.
        opponent: int = PLAYER if turn == AI else AI
        value, _ = negamax(new_board, opponent, memo)
        value = -value  # Negamax: value is the negative of opponent's value.
        if value > best_value:
            best_value = value
            best_move = move
        # If a winning move is found, no need to search further.
        if best_value == 1:
            break
    memo[state] = (best_value, best_move)
    return memo[state]

# Now we traverse the entire game tree (starting from the initial board with white to move)
# and record the perfect move for every board state where it’s Black’s turn.
COMPLETE_PERFECT_MOVES: Dict[str, Tuple[Tuple[int, int], Tuple[int, int]]] = {}

def traverse(board: List[List[int]], turn: int, visited: Set[Tuple[str, int]], memo: MemoType) -> None:
    state = (board_to_string(board), turn)
    if state in visited:
        return
    visited.add(state)
    
    # If it is Black’s turn, record the best move (if one exists)
    if turn == AI:
        value, best_move = negamax(board, turn, memo)
        if best_move is not None:
            COMPLETE_PERFECT_MOVES[board_to_string(board)] = best_move
    
    # Recurse over all possible moves for the current player.
    for move in get_all_valid_moves(board, turn):
        new_board: List[List[int]] = make_move(board, move[0], move[1])
        opponent: int = PLAYER if turn == AI else AI
        traverse(new_board, opponent, visited, memo)

# Compute the complete dictionary at startup.
memo: MemoType = {}
visited_states: Set[Tuple[str, int]] = set()
# White moves first from the initial board.
traverse(INITIAL_BOARD, PLAYER, visited_states, memo)

# --- End Retrograde Analysis ---

def debug_board_to_move(board: List[List[int]]) -> None:
    """Print the board state and (if available) the lookup move."""
    board_str: str = board_to_string(board)
    print("Current Board State:")
    for row in board:
        print(row)
    print("String representation:", board_str)
    if board_str in COMPLETE_PERFECT_MOVES:
        print("Found in COMPLETE_PERFECT_MOVES:", COMPLETE_PERFECT_MOVES[board_str])
    else:
        print("State not in COMPLETE_PERFECT_MOVES.")

def get_best_move(board: List[List[int]]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """
    Return Black's perfect move for the current board by looking it up in the complete dictionary.
    If the board state is not found, return the first valid move.
    """
    board_str: str = board_to_string(board)
    debug_board_to_move(board)
    if board_str in COMPLETE_PERFECT_MOVES:
        return COMPLETE_PERFECT_MOVES[board_str]
    valid_moves: List[Tuple[Tuple[int, int], Tuple[int, int]]] = get_all_valid_moves(board, AI)
    if valid_moves:
        return valid_moves[0]
    raise Exception("No valid moves available for AI.")

@app.route('/')
def index() -> Any:
    """Render the main game page."""
    session['board'] = INITIAL_BOARD
    session['game_over'] = False
    session['winner'] = None
    return render_template('index.html')

@app.route('/get_game_state', methods=['GET'])
def get_game_state() -> Any:
    """Return the current game state."""
    return jsonify({
        'board': session.get('board', INITIAL_BOARD),
        'game_over': session.get('game_over', False),
        'winner': session.get('winner', None)
    })

@app.route('/move', methods=['POST'])
def move() -> Any:
    """Process the player's move and respond with Black's perfect move."""
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
    
    if not is_valid_move(board, from_pos, to_pos, PLAYER):
        return jsonify({
            'error': 'Invalid move!',
            'board': board
        })
    
    # Process Player's move.
    board = make_move(board, from_pos, to_pos)
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
    
    # Black's turn.
    valid_moves = get_all_valid_moves(board, AI)
    if not valid_moves:
        session['game_over'] = True
        session['winner'] = 'draw'
        session['board'] = board
        return jsonify({
            'board': board,
            'game_over': True,
            'winner': 'draw',
            'message': "It's a draw! 'A stalemate... reality itself seems distorted,' Hans whispers."
        })
    
    ai_from_pos, ai_to_pos = get_best_move(board)
    print(f"Board: {board_to_string(board)}, AI Move: From {ai_from_pos} to {ai_to_pos}")
    
    board = make_move(board, ai_from_pos, ai_to_pos)
    if check_win(board, AI):
        session['game_over'] = True
        session['winner'] = 'ai'
        session['board'] = board
        ai_message: str = "Hans never loses... https://i.imgur.com/tV1rKks.jpeg"
        return jsonify({
            'board': board,
            'game_over': True,
            'winner': 'ai',
            'ai_from': ai_from_pos,
            'ai_to': ai_to_pos,
            'message': ai_message
        })
    
    if not get_all_valid_moves(board, PLAYER):
        session['game_over'] = True
        session['winner'] = 'ai'
        session['board'] = board
        ai_win_message: str = "'With no moves left, you must concede. Your defeat was inevitable,' Hans says triumphantly."
        return jsonify({
            'board': board,
            'game_over': True,
            'winner': 'ai',
            'ai_from': ai_from_pos,
            'ai_to': ai_to_pos,
            'message': ai_win_message
        })
    
    session['board'] = board
    ai_message: str = "'Every move brings you closer to the inevitable,' Hans states calmly."
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
    """Reset the game state."""
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
    port = int(os.environ.get("PORT", 5000))  # 5000 is default for local testing
    app.run(host="0.0.0.0", port=port)
