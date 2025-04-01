# app.py
from flask import Flask, render_template, request, jsonify, session
import os
import random

# Make sure to create the proper folder structure if it doesn't exist:
# - static/
#   - css/
#   - js/
#   - images/

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

def optimal_move(stones):
    """
    Calculate the optimal move for the divination wizard.
    
    Args:
        stones (int): Current number of stones in the pile
        
    Returns:
        int: Number of stones to remove (1-3)
    """
    if stones % 4 != 0:
        return stones % 4
    else:
        return random.randint(1,3)

@app.route('/')
def index():
    """Render the main game page"""
    # Initialize a new game
    session['stones'] = 21
    session['game_over'] = False
    session['winner'] = None
    return render_template('index.html')

@app.route('/play', methods=['POST'])
def play():
    """Handle player moves and AI responses"""
    data = request.get_json()
    stones_taken = int(data.get('stones_taken', 0))
    
    # Get current game state from session
    stones = session.get('stones', 21)
    game_over = session.get('game_over', False)
    
    if game_over:
        return jsonify({
            'stones': stones,
            'game_over': game_over,
            'winner': session.get('winner'),
            'message': 'Game is already over!'
        })
    
    # Validate player move
    if stones_taken < 1 or stones_taken > 3 or stones_taken > stones:
        return jsonify({
            'error': 'Invalid move! Take 1-3 stones only.',
            'stones': stones
        })
    
    # Process player move
    stones -= stones_taken
    player_message = f"You took {stones_taken} stone{'s' if stones_taken > 1 else ''}."
    
    # Check if player won
    if stones == 0:
        session['game_over'] = True
        session['winner'] = 'player'
        session['stones'] = stones
        return jsonify({
            'stones': stones,
            'game_over': True,
            'winner': 'player',
            'message': player_message + " Hans looks surprised, then laughs. 'Well played.'\nDouble or nothing? https://hans-game-2-2.onrender.com/"
        })
    
    # AI's turn
    ai_take = optimal_move(stones)
    if ai_take > stones:  # Safety check
        ai_take = stones
    
    stones -= ai_take
    ai_message = f"Hans takes {ai_take} stone{'s' if ai_take > 1 else ''} with a knowing smile."
    
    # Check if AI won
    if stones == 0:
        session['game_over'] = True
        session['winner'] = 'ai'
        
    # Update session
    session['stones'] = stones
    
    return jsonify({
        'stones': stones,
        'stones_taken_by_ai': ai_take,
        'game_over': stones == 0,
        'winner': 'ai' if stones == 0 else None,
        'message': player_message + " " + ai_message + (" 'As expected.' he says." if stones == 0 else "")
    })

@app.route('/reset', methods=['POST'])
def reset():
    """Reset the game"""
    session['stones'] = 21
    session['game_over'] = False
    session['winner'] = None
    
    return jsonify({
        'stones': 21,
        'game_over': False,
        'message': 'Game reset. You go first!'
    })

if __name__ == '__main__':
    # For local development
    app.run(debug=True)