import csv
from collections import deque
import time
import os
import hashlib

# --- Configuration ---
MAX_MOVES = 10  # Maximum number of moves (not plies) to explore
OUTPUT_FILENAME = "complete_chopsticks_games.tsv"
CHECKPOINT_INTERVAL = 100000  # Save progress every X games
PROGRESS_REPORT_INTERVAL = 10000  # Report progress every X games

# --- Notation Functions ---
def format_state_str(p1_hands, p2_hands):
    """Converts hand lists to the specified string notation."""
    return f"= {p1_hands[0]}-{p1_hands[1]} | {p2_hands[0]}-{p2_hands[1]}"

def format_tap_move_str(attacker_player_idx, attacker_hand_idx, defender_player_idx, defender_hand_idx):
    """Formats a tap move string (without leading '!')"""
    p_char = {0: "L", 1: "R"}  # Hand index to L/R character
    return f"P{attacker_player_idx+1}{p_char[attacker_hand_idx]}>P{defender_player_idx+1}{p_char[defender_hand_idx]}"

def format_split_move_str(player_idx, old_hands_tuple, new_hands_tuple):
    """Formats a split move string (without leading '!')"""
    return f"Sp(P{player_idx+1}:{old_hands_tuple[0]}|{old_hands_tuple[1]} → {new_hands_tuple[0]}|{new_hands_tuple[1]})"

# --- Game State Classes ---
class GameState:
    """Represents a single state in the Chopsticks game."""
    def __init__(self, p1_hands=(1, 1), p2_hands=(1, 1), current_player=0):
        self.p1_hands = tuple(p1_hands)  # [Left, Right]
        self.p2_hands = tuple(p2_hands)  # [Left, Right]
        self.current_player = current_player  # 0 for P1, 1 for P2
        
    def __eq__(self, other):
        return (self.p1_hands == other.p1_hands and 
                self.p2_hands == other.p2_hands and 
                self.current_player == other.current_player)
                
    def __hash__(self):
        return hash((self.p1_hands, self.p2_hands, self.current_player))
        
    def get_state_tuple(self):
        """Returns a tuple representing the full game state."""
        return (self.p1_hands, self.p2_hands, self.current_player)
        
    def is_terminal(self):
        """Checks if the current state is terminal (a player has lost)."""
        return self.p1_hands == (0, 0) or self.p2_hands == (0, 0)
        
    def get_winner(self):
        """Returns the winner if the state is terminal, None otherwise."""
        if self.p1_hands == (0, 0):
            return "P2"
        elif self.p2_hands == (0, 0):
            return "P1"
        return None
        
    def get_state_str(self):
        """Returns the string representation of the state."""
        return format_state_str(self.p1_hands, self.p2_hands)
        
    def get_player_hands(self):
        """Returns the hands of the current player."""
        return self.p1_hands if self.current_player == 0 else self.p2_hands
        
    def get_opponent_hands(self):
        """Returns the hands of the opponent."""
        return self.p2_hands if self.current_player == 0 else self.p1_hands
    
    def clone(self):
        """Creates a deep copy of the current state."""
        return GameState(self.p1_hands, self.p2_hands, self.current_player)

class GameMove:
    """Represents a move in the Chopsticks game."""
    def __init__(self, move_type, player, details):
        self.move_type = move_type  # "tap" or "split"
        self.player = player  # 0 for P1, 1 for P2
        self.details = details  # For tap: (att_hand, def_hand), For split: (old_l, old_r, new_l, new_r)
        
    def get_notation(self):
        """Returns the string notation for this move."""
        if self.move_type == "tap":
            att_hand, def_hand = self.details
            return format_tap_move_str(self.player, att_hand, 1-self.player, def_hand)
        elif self.move_type == "split":
            old_l, old_r, new_l, new_r = self.details
            return format_split_move_str(self.player, (old_l, old_r), (new_l, new_r))
        return "NO_MOVE"

class GamePath:
    """Represents a complete path (sequence of moves) in the game tree."""
    def __init__(self, initial_state=None):
        self.states = [initial_state or GameState()]
        self.moves = []
        self.visited_states = {self.states[0].get_state_tuple()}
        self.error_flags = []
        
    def clone(self):
        """Creates a deep copy of the current path."""
        new_path = GamePath(self.states[0].clone())
        new_path.states = [state.clone() for state in self.states]
        new_path.moves = self.moves.copy()
        new_path.visited_states = self.visited_states.copy()
        new_path.error_flags = self.error_flags.copy()
        return new_path
        
    def get_current_state(self):
        """Returns the current (last) state in the path."""
        return self.states[-1]
        
    def apply_move(self, move, validate=True):
        """
        Applies the given move to the current state, creating a new state.
        Returns (success, error_code).
        """
        current_state = self.get_current_state()
        next_state = current_state.clone()
        
        # Switch to the next player by default (may be reverted if move is invalid)
        next_state.current_player = 1 - current_state.current_player
        
        error_code = ""
        
        if move.move_type == "tap":
            att_hand, def_hand = move.details
            player_hands = current_state.get_player_hands()
            opponent_hands = current_state.get_opponent_hands()
            
            # Validate the tap
            if validate:
                if player_hands[att_hand] == 0:
                    error_code = "ERR_OVERFLOW"
                elif opponent_hands[def_hand] == 0:
                    # Not specified in prompt, but tapping a dead hand seems invalid
                    error_code = "ERR_OVERFLOW"
            
            # Apply the tap if valid
            if not error_code:
                fingers_to_add = player_hands[att_hand]
                new_defender_fingers = (opponent_hands[def_hand] + fingers_to_add) % 5
                
                # Update the hands in the next state
                if move.player == 0:
                    next_state.p2_hands = tuple(
                        new_defender_fingers if i == def_hand else opponent_hands[i]
                        for i in range(2)
                    )
                else:
                    next_state.p1_hands = tuple(
                        new_defender_fingers if i == def_hand else opponent_hands[i]
                        for i in range(2)
                    )
        
        elif move.move_type == "split":
            old_l, old_r, new_l, new_r = move.details
            player_hands = current_state.get_player_hands()
            
            # Validate the split
            if validate:
                # Check if the split conserves fingers
                if old_l != player_hands[0] or old_r != player_hands[1]:
                    error_code = "ERR_INVALID_SPLIT"
                elif sum(player_hands) < 2:
                    error_code = "ERR_INVALID_SPLIT"
                elif sum(player_hands) != new_l + new_r:
                    error_code = "ERR_INVALID_SPLIT"
                elif not (0 <= new_l <= 4 and 0 <= new_r <= 4):
                    error_code = "ERR_INVALID_SPLIT"
                # Check for reversal (X|Y → Y|X where X != Y)
                elif new_l == player_hands[1] and new_r == player_hands[0] and player_hands[0] != player_hands[1]:
                    error_code = "ERR_REVERSAL"
                # Check for invalid 1|0 or 0|1 split
                elif player_hands == (1, 0) or player_hands == (0, 1):
                    error_code = "ERR_INVALID_SPLIT"
                # Check for no change
                elif (new_l, new_r) == player_hands:
                    error_code = "ERR_INVALID_SPLIT"
            
            # Apply the split if valid
            if not error_code:
                # Update the hands in the next state
                if move.player == 0:
                    next_state.p1_hands = (new_l, new_r)
                else:
                    next_state.p2_hands = (new_l, new_r)
        
        # Check for state repetition
        if not error_code and next_state.get_state_tuple() in self.visited_states:
            error_code = "ERR_REPEAT"
        
        # If move is valid, add it to the path
        if not error_code:
            self.states.append(next_state)
            self.moves.append(move)
            self.visited_states.add(next_state.get_state_tuple())
            self.error_flags.append("")
            return True, ""
        else:
            # For invalid moves, we keep the current state and add an error flag
            self.states.append(current_state.clone())
            self.moves.append(move)
            self.error_flags.append(error_code)
            return False, error_code
    
    def get_game_rows(self, game_id):
        """Converts the path to a list of row dictionaries for TSV output."""
        rows = []
        for i in range(len(self.moves)):
            curr_state = self.states[i]
            next_state = self.states[i+1]
            move = self.moves[i]
            error = self.error_flags[i]
            
            # Determine winner (only on the last move if terminal)
            winner = ""
            if i == len(self.moves) - 1 and next_state.is_terminal():
                winner = next_state.get_winner()
            
            rows.append({
                "GameID": game_id,
                "Turn": i + 1,
                "State": curr_state.get_state_str(),
                "Move": move.get_notation(),
                "NextState": next_state.get_state_str(),
                "Error": error,
                "Winner": winner
            })
        return rows
        
    def get_unique_id(self):
        """Generates a unique identifier for this game path based on moves."""
        # Create a string representation of all moves
        move_str = "-".join(move.get_notation() for move in self.moves)
        # Hash it to get a unique ID
        return hashlib.md5(move_str.encode()).hexdigest()

# --- Game Logic ---
def get_possible_taps(state):
    """Returns all possible tap moves from the current state."""
    taps = []
    player = state.current_player
    player_hands = state.get_player_hands()
    opponent_hands = state.get_opponent_hands()
    
    for att_hand in range(2):
        if player_hands[att_hand] > 0:  # Can only tap with alive hand
            for def_hand in range(2):
                if opponent_hands[def_hand] > 0:  # Can only tap alive hand
                    taps.append(GameMove("tap", player, (att_hand, def_hand)))
    return taps

def get_possible_splits(state):
    """Returns all possible split moves from the current state."""
    splits = []
    player = state.current_player
    player_hands = state.get_player_hands()
    
    total_fingers = sum(player_hands)
    
    # Cannot split if < 2 fingers or both hands dead
    if total_fingers < 2 or player_hands == (0, 0):
        return splits
        
    # Cannot split from 1|0 or 0|1
    if player_hands == (1, 0) or player_hands == (0, 1):
        return splits
        
    for new_l in range(total_fingers + 1):
        new_r = total_fingers - new_l
        
        # Must be valid hand values
        if not (0 <= new_l <= 4 and 0 <= new_r <= 4):
            continue
            
        # Cannot be the same as current
        if (new_l, new_r) == player_hands:
            continue
            
        # Cannot be a reversal (X|Y → Y|X where X != Y)
        if new_l == player_hands[1] and new_r == player_hands[0] and player_hands[0] != player_hands[1]:
            continue
            
        splits.append(GameMove("split", player, (player_hands[0], player_hands[1], new_l, new_r)))
    
    return splits

def get_all_possible_moves(state):
    """Returns all possible moves from the current state."""
    return get_possible_taps(state) + get_possible_splits(state)

def is_duplicate_game(game_path, seen_games):
    """
    Checks if this game is a duplicate of a previously seen game.
    Two games are considered duplicates if they have the same sequence of moves.
    """
    return game_path.get_unique_id() in seen_games

# --- BFS Game Explorer ---
def explore_all_games(max_moves=MAX_MOVES):
    """
    Uses BFS to explore all possible games ending in ≤ max_moves.
    Returns a list of all terminal game paths.
    """
    # Start with the initial state
    initial_path = GamePath()
    
    # Queue for BFS
    queue = deque([initial_path])
    
    # Track completed games and unique states
    completed_games = []
    seen_games = set()
    
    # Track progress
    games_examined = 0
    start_time = time.time()
    last_checkpoint_time = start_time
    
    # Process the queue
    while queue:
        # Get the next path to explore
        current_path = queue.popleft()
        current_state = current_path.get_current_state()
        
        # Skip if we've already processed this state to the same depth
        games_examined += 1
        
        # Report progress periodically
        if games_examined % PROGRESS_REPORT_INTERVAL == 0:
            elapsed = time.time() - start_time
            paths_per_sec = games_examined / elapsed if elapsed > 0 else 0
            print(f"Examined {games_examined:,} paths, found {len(completed_games):,} complete games. "
                  f"Queue size: {len(queue):,}. Rate: {paths_per_sec:.2f} paths/sec")
        
        # Checkpoint periodically by writing completed games to file
        if len(completed_games) % CHECKPOINT_INTERVAL == 0 and len(completed_games) > 0:
            current_time = time.time()
            if current_time - last_checkpoint_time > 300:  # 5 minutes
                last_checkpoint_time = current_time
                write_games_to_tsv(completed_games[-CHECKPOINT_INTERVAL:], 
                                  f"checkpoint_{len(completed_games)}.tsv", append=False)
                print(f"Checkpoint saved at {len(completed_games):,} games")
        
        # If the path is already at max moves or in a terminal state, don't explore further
        if len(current_path.moves) >= max_moves * 2:  # max_moves in plies (2 plies = 1 move)
            continue
            
        # If the state is terminal, add it to completed games and don't explore further
        if current_state.is_terminal():
            # Check if we've seen an identical game before
            if not is_duplicate_game(current_path, seen_games):
                completed_games.append(current_path)
                seen_games.add(current_path.get_unique_id())
            continue
        
        # Get all possible moves from the current state
        possible_moves = get_all_possible_moves(current_state)
        
        # Try each move and add the resulting path to the queue
        for move in possible_moves:
            new_path = current_path.clone()
            success, _ = new_path.apply_move(move)
            
            # Only add valid moves to the queue
            if success:
                queue.append(new_path)
    
    print(f"\nBFS complete. Examined {games_examined:,} paths, found {len(completed_games):,} unique games.")
    return completed_games

# --- TSV Output Functions ---
def write_games_to_tsv(game_paths, filename, append=False):
    """Writes the given game paths to a TSV file."""
    mode = 'a' if append else 'w'
    
    # Prepare all rows
    all_rows = []
    for i, path in enumerate(game_paths):
        game_id = f"G{i+1:04d}"
        all_rows.extend(path.get_game_rows(game_id))
    
    # Write to file
    # Define fieldnames outside the file opening scope
    fieldnames = ["GameID", "Turn", "State", "Move", "NextState", "Error", "Winner"]
    
    with open(filename, mode, newline='', encoding='utf-8') as tsvfile:
        writer = csv.DictWriter(tsvfile, fieldnames=fieldnames, delimiter='\t')
        
        if not append or os.path.getsize(filename) == 0:
            # Write header if file is new or empty
            writer.writeheader()
        
        # Write all rows
        writer.writerows(all_rows)

# --- Metadata Functions ---
def calculate_metadata(game_paths):
    """Calculates metadata for the generated games."""
    total_games = len(game_paths)
    
    if total_games == 0:
        return {
            "total_games": 0,
            "avg_length": 0,
            "p1_wins": 0,
            "p2_wins": 0,
            "p1_win_pct": 0,
            "p2_win_pct": 0
        }
    
    # Calculate game lengths
    game_lengths = [len(path.moves) for path in game_paths]
    avg_length = sum(game_lengths) / total_games
    
    # Count winners
    p1_wins = sum(1 for path in game_paths if path.states[-1].get_winner() == "P1")
    p2_wins = sum(1 for path in game_paths if path.states[-1].get_winner() == "P2")
    
    # Calculate win percentages
    total_wins = p1_wins + p2_wins
    p1_win_pct = (p1_wins / total_wins * 100) if total_wins > 0 else 0
    p2_win_pct = (p2_wins / total_wins * 100) if total_wins > 0 else 0
    
    return {
        "total_games": total_games,
        "avg_length": avg_length,
        "p1_wins": p1_wins,
        "p2_wins": p2_wins,
        "p1_win_pct": p1_win_pct,
        "p2_win_pct": p2_win_pct
    }

# --- Main Function ---
def main():
    print("Starting Complete Chopsticks Game Explorer")
    print(f"Finding all unique games ending in ≤{MAX_MOVES} moves")
    
    start_time = time.time()
    
    # Explore all games
    all_games = explore_all_games(MAX_MOVES)
    
    # Write to TSV
    print(f"Writing {len(all_games):,} games to {OUTPUT_FILENAME}")
    write_games_to_tsv(all_games, OUTPUT_FILENAME)
    
    # Calculate and print metadata
    metadata = calculate_metadata(all_games)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print("\n--- Dataset Metadata ---")
    print(f"Total unique games: {metadata['total_games']:,}")
    print(f"Average game length (moves): {metadata['avg_length']:.2f}")
    print(f"Player 1 wins: {metadata['p1_wins']:,} ({metadata['p1_win_pct']:.2f}%)")
    print(f"Player 2 wins: {metadata['p2_wins']:,} ({metadata['p2_win_pct']:.2f}%)")
    print(f"Total elapsed time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()