"""
Move generation logic for Chopsticks game.
"""
from engine.game_state import GameMove

def get_possible_taps(state):
    """Returns all possible tap moves from the current state."""
    taps = []
    player = state.current_player
    
    # Get hands based on current player
    if player == 0:
        player_hands = state.p1_hands
        opponent_hands = state.p2_hands
    else:
        player_hands = state.p2_hands
        opponent_hands = state.p1_hands
    
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
    
    # Get hands based on current player
    if player == 0:
        player_hands = state.p1_hands
    else:
        player_hands = state.p2_hands
    
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
