"""
Game state representation for Chopsticks.
"""
import logging

# Configure logging
logger = logging.getLogger(__name__)

class GameState:
    """Represents a single state in the Chopsticks game."""
    def __init__(self, p1_hands=(1, 1), p2_hands=(1, 1), current_player=0, visited_states=None):
        self.p1_hands = tuple(p1_hands)  # [Left, Right]
        self.p2_hands = tuple(p2_hands)  # [Left, Right]
        self.current_player = current_player  # 0 for P1, 1 for P2
        self.visited_states = visited_states or {self.get_state_tuple()}
        self.is_terminal = self.p1_hands == (0, 0) or self.p2_hands == (0, 0)
        self.winner = self._calculate_winner()
        
    def _calculate_winner(self):
        """Determines the winner if the state is terminal."""
        if self.p1_hands == (0, 0):
            return "P2"
        elif self.p2_hands == (0, 0):
            return "P1"
        return None
        
    def __eq__(self, other):
        return (self.p1_hands == other.p1_hands and 
                self.p2_hands == other.p2_hands and 
                self.current_player == other.current_player)
                
    def __hash__(self):
        return hash((self.p1_hands, self.p2_hands, self.current_player))
        
    def get_state_tuple(self):
        """Returns a tuple representing the full game state."""
        return (self.p1_hands, self.p2_hands)
        
    def get_winner(self):
        """Returns the winner if the state is terminal, None otherwise."""
        return self.winner
        
    def get_state_str(self):
        """Returns the string representation of the state."""
        return f"= {self.p1_hands[0]}-{self.p1_hands[1]} | {self.p2_hands[0]}-{self.p2_hands[1]}"
        
    def clone(self):
        """Creates a deep copy of the current state."""
        return GameState(
            self.p1_hands, 
            self.p2_hands, 
            self.current_player,
            self.visited_states.copy()
        )
        
    def apply_move(self, move, validate=True):
        """
        Applies the given move to the current state.
        Returns (success, error_code).
        """
        if move is None:
            return False, "ERR_NO_MOVE"
        
        print(f"Applying move: {move.get_notation()} to state: {self.get_state_str()}")
            
        next_state = self.clone()
        
        # Switch to the next player by default (may be reverted if move is invalid)
        next_state.current_player = 1 - self.current_player
        
        error_code = ""
        
        if move.move_type == "tap":
            att_hand, def_hand = move.details
            
            # Determine player hands based on move.player
            if move.player == 0:  # P1 -> P2
                player_hands = self.p1_hands
                opponent_hands = self.p2_hands
            else:  # P2 -> P1
                player_hands = self.p2_hands
                opponent_hands = self.p1_hands
            
            # Validate the tap
            if validate:
                if player_hands[att_hand] == 0:
                    error_code = "ERR_OVERFLOW"
                elif opponent_hands[def_hand] == 0:
                    error_code = "ERR_OVERFLOW"
            
            # Apply the tap if valid
            if not error_code:
                fingers_to_add = player_hands[att_hand]
                new_defender_fingers = (opponent_hands[def_hand] + fingers_to_add) % 5
                
                # Update the hands in the next state
                if move.player == 0:  # P1 -> P2
                    next_state.p2_hands = tuple(
                        new_defender_fingers if i == def_hand else opponent_hands[i]
                        for i in range(2)
                    )
                else:  # P2 -> P1
                    next_state.p1_hands = tuple(
                        new_defender_fingers if i == def_hand else opponent_hands[i]
                        for i in range(2)
                    )
        
        elif move.move_type == "split":
            # Handle both old format (flat list) and new format (nested arrays)
            if isinstance(move.details[0], list):
                # New format: [[old_left, old_right], [new_left, new_right]]
                old_hands, new_hands = move.details
                old_l, old_r = old_hands
                new_l, new_r = new_hands
            else:
                # Old format: [old_left, old_right, new_left, new_right]
                old_l, old_r, new_l, new_r = move.details
            
            # Determine player hands based on move.player
            if move.player == 0:  # P1
                player_hands = self.p1_hands
            else:  # P2
                player_hands = self.p2_hands
            
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
                if move.player == 0:  # P1
                    next_state.p1_hands = (new_l, new_r)
                else:  # P2
                    next_state.p2_hands = (new_l, new_r)
        
        # Check for state repetition
        new_state_tuple = next_state.get_state_tuple()
        if not error_code and new_state_tuple in self.visited_states:
            error_code = "ERR_REPEAT"
        
        # If move is valid, update visited_states and check for terminal state
        if not error_code:
            next_state.visited_states.add(new_state_tuple)
            next_state.is_terminal = next_state.p1_hands == (0, 0) or next_state.p2_hands == (0, 0)
            next_state.winner = next_state._calculate_winner()
            
            # Copy the updated state to self
            self.p1_hands = next_state.p1_hands
            self.p2_hands = next_state.p2_hands
            self.current_player = next_state.current_player
            self.visited_states = next_state.visited_states
            self.is_terminal = next_state.is_terminal
            self.winner = next_state.winner
            
            return True, ""
        else:
            # For invalid moves, keep the current state
            logger.warning(f"Invalid move: {error_code}, {move.get_notation()}")
            return False, error_code
    
    def serialize(self):
        """Convert the state to a JSON-serializable dictionary."""
        return {
            'p1_hands': list(self.p1_hands),
            'p2_hands': list(self.p2_hands),
            'current_player': self.current_player,
            'is_terminal': self.is_terminal,
            'winner': self.winner
        }
    
    @classmethod
    def deserialize(cls, data):
        """Create a GameState object from serialized data."""
        state = cls(
            p1_hands=tuple(data['p1_hands']),
            p2_hands=tuple(data['p2_hands']),
            current_player=data['current_player']
        )
        state.is_terminal = data['is_terminal']
        state.winner = data['winner']
        return state


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
            hand_chars = {0: "L", 1: "R"}
            att_player = self.player + 1  # 0->1, 1->2
            def_player = 3 - att_player   # 1->2, 2->1
            
            return f"P{att_player}{hand_chars[att_hand]}>P{def_player}{hand_chars[def_hand]}"
            
        elif self.move_type == "split":
            player_num = self.player + 1  # 0->1, 1->2
            
            # Handle both old format (flat list) and new format (nested arrays)
            if isinstance(self.details[0], list):
                # New format: [[old_left, old_right], [new_left, new_right]]
                old_hands, new_hands = self.details
                old_l, old_r = old_hands
                new_l, new_r = new_hands
            else:
                # Old format: [old_left, old_right, new_left, new_right]
                old_l, old_r, new_l, new_r = self.details
                
            return f"Sp(P{player_num}:{old_l}|{old_r} → {new_l}|{new_r})"
            
        return "NO_MOVE"
    
    def serialize(self):
        """Convert the move to a JSON-serializable dictionary."""
        return {
            'move_type': self.move_type,
            'player': self.player,
            'details': self.details
        }
    
    @classmethod
    def deserialize(cls, data):
        """Create a GameMove object from serialized data."""
        return cls(
            move_type=data['move_type'],
            player=data['player'],
            details=data['details']
        )
