import os
import logging
import random
from flask import Flask, render_template, request, jsonify, session
from engine.game_state import GameState, GameMove
from engine.movegen import get_all_possible_moves
from engine.search import get_best_move
from engine.database_lookup import is_in_database, get_best_move_from_database

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "chopsticks-secret-key")

# Import and initialize game engine components
from engine import evaluator, movegen, search, database_lookup, game_state

# Generate and load the database if it doesn't exist
database_lookup.load_or_generate_database()


@app.route('/')
def index():
    """Render the main game page"""
    return render_template('index.html')


@app.route('/about')
def about():
    """Render the about page with game rules and information"""
    return render_template('about.html')


@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Initialize a new game session"""
    data = request.get_json(silent=True) or {}
    difficulty = data.get('difficulty', 'master')
    first_player = data.get('first_player', 'human')
    
    logger.debug(f"New game with settings: difficulty={difficulty}, first_player={first_player}")
    
    # Create initial game state
    game = GameState()
    
    # Store game state in session
    session['game_state'] = game.serialize()
    session['difficulty'] = difficulty
    session['first_player'] = first_player
    
    # Initialize session variables without making AI move yet
    session['game_state'] = game.serialize()
    session['difficulty'] = difficulty
    session['first_player'] = first_player
    
    return jsonify({
        'game_state': game.serialize(),
        'possible_moves': [move.serialize() for move in get_all_possible_moves(game)],
        'is_game_over': game.is_terminal,
        'winner': game.get_winner()
    })
    
    return jsonify({
        'game_state': game.serialize(),
        'possible_moves': [move.serialize() for move in get_all_possible_moves(game)],
        'is_game_over': game.is_terminal,
        'winner': game.get_winner()
    })


@app.route('/api/make_move', methods=['POST'])
def make_move():
    """Apply a human move and get AI's response"""
    if 'game_state' not in session:
        return jsonify({'error': 'No active game'}), 400
    
    # Deserialize game state and move
    game = GameState.deserialize(session['game_state'])
    data = request.get_json(silent=True) or {}
    move_data = data.get('move')
    difficulty = session.get('difficulty', 'master')
    first_player = session.get('first_player', 'human')
    
    # Handle null move for AI's first turn
    if move_data is None and first_player == 'ai':
        ai_move, evaluation, perfect = get_ai_move(game, difficulty)
        game.apply_move(ai_move)
        session['game_state'] = game.serialize()
        return jsonify({
            'game_state': game.serialize(),
            'ai_move': ai_move.serialize(),
            'evaluation': evaluation,
            'perfect': perfect,
            'possible_moves': [move.serialize() for move in get_all_possible_moves(game)],
            'is_game_over': game.is_terminal,
            'winner': game.get_winner()
        })
    
    logger.debug(f"Move data received: {move_data}")
    
    # Create the move object from move_data
    if move_data:
        try:
            move_type = move_data.get('move_type')
            player = move_data.get('player')
            details = move_data.get('details')
            
            if all([move_type, player is not None, details]):
                human_move = GameMove(move_type, player, details)
            else:
                human_move = None
        except Exception as e:
            logger.error(f"Error creating move: {e}")
            human_move = None
    else:
        human_move = None
    
    if not human_move:
        return jsonify({'error': 'Invalid move data'}), 400
    
    # Apply human move
    logger.debug(f"Applying human move: {human_move.get_notation()}")
    success, error = game.apply_move(human_move)
    if not success:
        return jsonify({'error': f'Invalid move: {error}'}), 400
    
    # Check if game is over after human move
    if game.is_terminal:
        session['game_state'] = game.serialize()
        return jsonify({
            'game_state': game.serialize(),
            'is_game_over': True,
            'winner': game.get_winner()
        })
    
    # Get AI's response move
    ai_move, evaluation, perfect = get_ai_move(game, difficulty)
    
    if ai_move:
        logger.debug(f"AI move: {ai_move.get_notation()}, Eval: {evaluation}, Perfect: {perfect}")
        success, error = game.apply_move(ai_move)
        if not success:
            logger.error(f"AI move application failed: {error}")
            return jsonify({'error': f'AI move failed: {error}'}), 500
    else:
        logger.error("No AI move found")
        return jsonify({'error': 'No AI move found'}), 500
    
    # Update session with new game state
    session['game_state'] = game.serialize()
    
    return jsonify({
        'game_state': game.serialize(),
        'ai_move': ai_move.serialize(),
        'evaluation': evaluation,
        'perfect': perfect,
        'possible_moves': [move.serialize() for move in get_all_possible_moves(game)],
        'is_game_over': game.is_terminal,
        'winner': game.get_winner()
    })


def get_ai_move(game, difficulty):
    """Get the best move for the AI based on difficulty level"""
    perfect = False
    
    # Check if the position is in the database
    if is_in_database(game):
        move, evaluation = get_best_move_from_database(game)
        perfect = True
        logger.debug(f"Using perfect move from database: {move.get_notation()}")
        return move, evaluation, perfect
    
    # Otherwise use search with appropriate depth based on difficulty
    depth = 2  # Default for 'novice'
    if difficulty == 'intermediate':
        depth = 4
    elif difficulty == 'master':
        depth = 6
    
    # For novice, occasionally make random moves
    if difficulty == 'novice' and random.random() < 0.3:
        moves = get_all_possible_moves(game)
        move = random.choice(moves)
        evaluation = 0
        return move, evaluation, perfect
    
    # Use minimax/alpha-beta search for the move
    move, evaluation = get_best_move(game, depth)
    logger.debug(f"Using search with depth {depth}: {move.get_notation()} (eval: {evaluation})")
    
    return move, evaluation, perfect


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
