"""
Alpha-beta minimax search for the Chopsticks game.
"""
import random
import logging
from engine.movegen import get_all_possible_moves
from engine.evaluator import evaluate_position

# Configure logging
logger = logging.getLogger(__name__)

def get_best_move(game_state, depth=4):
    """
    Find the best move using alpha-beta search.
    Returns the best move and its evaluation score.
    """
    # Get all possible moves
    possible_moves = get_all_possible_moves(game_state)
    
    # If no legal moves or the state is terminal, return None
    if not possible_moves or game_state.is_terminal:
        return None, evaluate_position(game_state)
    
    # Shuffle moves to avoid bias in equal evaluations
    random.shuffle(possible_moves)
    
    best_move = None
    best_value = float('-inf')
    alpha = float('-inf')
    beta = float('inf')
    
    # Try each move and evaluate with alpha-beta
    for move in possible_moves:
        # Apply the move to get the next state
        next_state = game_state.clone()
        success, error = next_state.apply_move(move)
        
        if not success:
            logger.warning(f"Illegal move attempted in search: {move.get_notation()} - {error}")
            continue
        
        # Get value from opponent's perspective (minimax)
        value = -alpha_beta(next_state, depth - 1, -beta, -alpha)
        
        # Update best move if found
        if value > best_value:
            best_value = value
            best_move = move
            alpha = max(alpha, value)
    
    return best_move, best_value


def alpha_beta(game_state, depth, alpha, beta):
    """
    Alpha-beta pruning search algorithm.
    Returns the value of the position from the current player's perspective.
    """
    # Check terminal conditions
    if depth == 0 or game_state.is_terminal:
        return evaluate_position(game_state)
    
    # Get all possible moves
    possible_moves = get_all_possible_moves(game_state)
    
    # If no legal moves, evaluate current position
    if not possible_moves:
        return evaluate_position(game_state)
    
    # Try each move and update alpha
    for move in possible_moves:
        # Apply the move to get the next state
        next_state = game_state.clone()
        success, error = next_state.apply_move(move)
        
        if not success:
            continue
        
        # Evaluate from opponent's perspective (minimax)
        value = -alpha_beta(next_state, depth - 1, -beta, -alpha)
        
        # Beta cutoff (pruning)
        if value >= beta:
            return beta
        
        # Update alpha
        alpha = max(alpha, value)
    
    return alpha
