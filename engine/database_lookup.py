"""
Database lookup for pre-computed optimal moves in Chopsticks.
"""
import os
import csv
import subprocess
import pickle
import logging
from collections import defaultdict
from engine.game_state import GameState, GameMove

# Configure logging
logger = logging.getLogger(__name__)

# Database file paths
DATABASE_FILE = "chopsticks_database.pkl"
RAW_GAMES_FILE = "complete_chopsticks_games.tsv"

# Global database
move_database = {}
state_count = 0

def load_or_generate_database():
    """
    Load the pre-computed database or generate it if it doesn't exist.
    """
    global move_database, state_count
    
    if os.path.exists(DATABASE_FILE):
        logger.info(f"Loading pre-computed database from {DATABASE_FILE}")
        with open(DATABASE_FILE, 'rb') as f:
            move_database = pickle.load(f)
        state_count = len(move_database)
        logger.info(f"Loaded {state_count} positions from database")
    else:
        logger.info("Database not found, generating from raw games data")
        
        # Check if raw games file exists, if not generate it
        if not os.path.exists(RAW_GAMES_FILE):
            logger.info("Generating raw games data...")
            try:
                # Run the script to generate games
                script_path = "attached_assets/optimized-chopsticks-generator.py"
                if os.path.exists(script_path):
                    subprocess.run(["python", script_path], check=True)
                else:
                    logger.error(f"Game generator script not found at {script_path}")
                    # Create a small database with basic positions
                    create_minimal_database()
                    return
            except Exception as e:
                logger.error(f"Error generating games: {e}")
                # Create a small database with basic positions
                create_minimal_database()
                return
        
        # Process the raw games file
        process_raw_games()


def process_raw_games():
    """
    Process the raw games file to create the optimized database.
    """
    global move_database, state_count
    
    if not os.path.exists(RAW_GAMES_FILE):
        logger.error(f"Raw games file not found: {RAW_GAMES_FILE}")
        create_minimal_database()
        return
    
    logger.info(f"Processing raw games from {RAW_GAMES_FILE}")
    
    # Initialize database with win probabilities
    win_counts = defaultdict(int)
    total_counts = defaultdict(int)
    move_database = {}
    
    try:
        with open(RAW_GAMES_FILE, 'r', newline='') as f:
            # Define the fieldnames expected in the TSV file
            fieldnames = ["GameID", "Turn", "State", "Move", "NextState", "Error", "Winner"]
            reader = csv.DictReader(f, delimiter='\t', fieldnames=fieldnames)
            
            # Skip header row if present
            try:
                next(reader)
            except StopIteration:
                # Empty file
                create_minimal_database()
                return
                
            for row in reader:
                # Skip rows with errors
                if row.get('Error'):
                    continue
                
                # Parse current state
                state_str = row.get('State')
                next_state_str = row.get('NextState')
                move_str = row.get('Move')
                
                if not all([state_str, next_state_str, move_str]):
                    continue
                
                # Create GameState object
                game_state = parse_state_string(state_str)
                if not game_state:
                    continue
                
                # Create a key for the database
                state_key = state_to_key(game_state)
                
                # Parse the move
                move = parse_move_string(move_str, game_state)
                if not move:
                    continue
                
                # Track game outcomes for this state
                winner = row.get('Winner')
                if winner:
                    # This is the final move of a game
                    # Check if current player won
                    player_str = f"P{game_state.current_player + 1}"
                    win_counts[state_key] += 1 if winner == player_str else 0
                    total_counts[state_key] += 1
                else:
                    # For non-terminal moves, track the move made
                    if state_key not in move_database:
                        move_database[state_key] = {'moves': [], 'scores': []}
                    
                    # Add this move to the database
                    move_database[state_key]['moves'].append(move)
                    # For now, just use 0 as placeholder score
                    move_database[state_key]['scores'].append(0)
    
        # Now calculate scores based on win probabilities
        for state_key in move_database:
            if state_key in total_counts and total_counts[state_key] > 0:
                win_probability = win_counts[state_key] / total_counts[state_key]
                # Convert to a score between -100 and 100
                score = (win_probability * 200) - 100
                
                # Update all move scores for this state
                for i in range(len(move_database[state_key]['scores'])):
                    move_database[state_key]['scores'][i] = score
        
        state_count = len(move_database)
        logger.info(f"Created database with {state_count} positions")
        
        # Save database to file
        with open(DATABASE_FILE, 'wb') as f:
            pickle.dump(move_database, f)
        logger.info(f"Saved database to {DATABASE_FILE}")
        
    except Exception as e:
        logger.error(f"Error processing raw games: {e}")
        create_minimal_database()


def create_minimal_database():
    """
    Create a minimal database with some common positions.
    """
    global move_database, state_count
    
    logger.info("Creating minimal database with common positions")
    
    # Start with an empty database
    move_database = {}
    
    # Add the initial position
    initial_state = GameState()
    state_key = state_to_key(initial_state)
    
    # For initial position 1-1|1-1, standard opening is P1L>P2R
    move = GameMove("tap", 0, (0, 1))
    move_database[state_key] = {
        'moves': [move],
        'scores': [10]
    }
    
    state_count = len(move_database)
    logger.info(f"Created minimal database with {state_count} positions")
    
    # Save the minimal database
    with open(DATABASE_FILE, 'wb') as f:
        pickle.dump(move_database, f)


def is_in_database(game_state):
    """
    Check if the given game state is in the database.
    """
    state_key = state_to_key(game_state)
    return state_key in move_database


def get_best_move_from_database(game_state):
    """
    Get the best move for the given game state from the database.
    Returns (move, evaluation) or (None, 0) if not found.
    """
    state_key = state_to_key(game_state)
    
    if state_key not in move_database:
        return None, 0
    
    moves = move_database[state_key]['moves']
    scores = move_database[state_key]['scores']
    
    if not moves:
        return None, 0
    
    # Find the move with the highest score
    best_idx = scores.index(max(scores))
    return moves[best_idx], scores[best_idx]


def state_to_key(game_state):
    """
    Convert a GameState object to a key for the database.
    """
    return (
        game_state.p1_hands[0],
        game_state.p1_hands[1],
        game_state.p2_hands[0],
        game_state.p2_hands[1],
        game_state.current_player
    )


def parse_state_string(state_str):
    """
    Parse a state string (e.g., "= 1-1 | 2-3") into a GameState object.
    """
    try:
        # Remove the "=" prefix if present
        if state_str.startswith("="):
            state_str = state_str[1:].strip()
        
        # Split the state string
        parts = state_str.split("|")
        p1_part = parts[0].strip()
        p2_part = parts[1].strip()
        
        # Parse player hands
        p1_hands = tuple(map(int, p1_part.split("-")))
        p2_hands = tuple(map(int, p2_part.split("-")))
        
        # Create GameState (assuming it's player 1's turn)
        return GameState(p1_hands=p1_hands, p2_hands=p2_hands, current_player=0)
    except Exception as e:
        logger.error(f"Error parsing state string '{state_str}': {e}")
        return None


def parse_move_string(move_str, game_state):
    """
    Parse a move string into a GameMove object.
    """
    try:
        # Handle tap moves (e.g., "P1L>P2R")
        if ">" in move_str:
            parts = move_str.split(">")
            attacker = parts[0]
            defender = parts[1]
            
            # Parse attacker
            att_player = int(attacker[1]) - 1  # P1 -> 0, P2 -> 1
            att_hand = 0 if attacker[2] == "L" else 1  # L -> 0, R -> 1
            
            # Parse defender
            def_player = int(defender[1]) - 1
            def_hand = 0 if defender[2] == "L" else 1
            
            return GameMove("tap", att_player, (att_hand, def_hand))
        
        # Handle split moves (e.g., "Sp(P2:4|0 → 2|2)")
        elif "Sp" in move_str:
            # Extract player
            player_str = move_str.split("(")[1].split(":")[0]
            player = int(player_str[1]) - 1  # P1 -> 0, P2 -> 1
            
            # Extract pre-split and post-split
            split_parts = move_str.split("→")
            pre_split = split_parts[0].split(":")[-1].strip()
            post_split = split_parts[1].split(")")[0].strip()
            
            # Parse hands
            old_l, old_r = map(int, pre_split.split("|"))
            new_l, new_r = map(int, post_split.split("|"))
            
            return GameMove("split", player, (old_l, old_r, new_l, new_r))
    except Exception as e:
        logger.error(f"Error parsing move string '{move_str}': {e}")
    
    return None
