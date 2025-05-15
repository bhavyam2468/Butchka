"""
Evaluation function for Chopsticks game positions.
"""

def evaluate_position(game_state):
    """
    Evaluate a given game state from the perspective of the current player.
    Returns a score between -100 (losing) and +100 (winning).
    """
    # If terminal state, return extreme value
    if game_state.is_terminal:
        winner = game_state.get_winner()
        if (winner == "P1" and game_state.current_player == 0) or (winner == "P2" and game_state.current_player == 1):
            return 100  # Current player wins
        else:
            return -100  # Current player loses
    
    # Get hands for the current player and opponent
    if game_state.current_player == 0:
        player_hands = game_state.p1_hands
        opponent_hands = game_state.p2_hands
    else:
        player_hands = game_state.p2_hands
        opponent_hands = game_state.p1_hands
    
    # Count alive hands for both players
    player_alive_hands = sum(1 for h in player_hands if h > 0)
    opponent_alive_hands = sum(1 for h in opponent_hands if h > 0)
    
    # Calculate finger advantage
    player_total_fingers = sum(player_hands)
    opponent_total_fingers = sum(opponent_hands)
    finger_advantage = player_total_fingers - opponent_total_fingers
    
    # Calculate hand advantage (alive hands)
    hand_advantage = player_alive_hands - opponent_alive_hands
    
    # Evaluate the potential for splitting (flexibility)
    player_split_potential = 0
    if player_total_fingers >= 2 and player_alive_hands > 0:
        # Each additional finger increases split options
        player_split_potential = player_total_fingers
        
        # Bonus for having both hands alive
        if player_alive_hands == 2:
            player_split_potential += 5
    
    # Evaluate vulnerability (dead hand state)
    player_vulnerability = 0
    opponent_vulnerability = 0
    
    # If one hand is dead, that's a vulnerable position
    if player_alive_hands == 1:
        player_vulnerability = 10
    
    if opponent_alive_hands == 1:
        opponent_vulnerability = 10
    
    # Additional bonus for specific patterns and traps
    trap_potential = 0
    
    # Look for mirror lock (can't split effectively)
    if player_hands == opponent_hands and player_hands[0] == player_hands[1]:
        trap_potential += 5  # Mirror positions can be advantageous
    
    # Check for mod-5 trap potential (if any hand is close to dying)
    for i in range(2):
        for j in range(2):
            if opponent_hands[j] > 0:  # Only consider alive opponent hands
                remaining_to_zero = (5 - opponent_hands[j]) % 5
                if remaining_to_zero > 0 and player_hands[i] == remaining_to_zero:
                    trap_potential += 8  # Can eliminate an opponent hand
    
    # Calculate final score
    score = 0
    score += finger_advantage * 5     # Each finger advantage is worth 5 points
    score += hand_advantage * 20      # Each hand advantage is worth 20 points
    score += player_split_potential   # Split potential adds flexibility
    score -= player_vulnerability     # Being vulnerable is bad
    score += opponent_vulnerability   # Opponent being vulnerable is good
    score += trap_potential           # Traps are valuable
    
    # Normalize the score to the range -100 to 100
    score = max(min(score, 100), -100)
    
    return score
