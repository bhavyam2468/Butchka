// Main game interface logic
document.addEventListener('DOMContentLoaded', function() {
    // Game state variables
    let gameState = null;
    let selectedHand = null;
    let isHumanTurn = true;
    let moveHistory = [];

    // DOM elements
    const gameBoard = document.getElementById('game-board');
    const messageArea = document.getElementById('message-area');
    const moveListElement = document.getElementById('move-list');
    const evaluationMarker = document.getElementById('evaluation-marker');
    const newGameButton = document.getElementById('new-game-button');
    const difficultySelect = document.getElementById('difficulty-select');
    const playerSelect = document.getElementById('player-select');
    const loadingSpinner = document.getElementById('loading-spinner');

    // Initialize the game
    newGameButton.addEventListener('click', startNewGame);

    // Add event listener to split button
    document.getElementById('split-button').addEventListener('click', showSplitOptions);

    // Add event listeners to apply and cancel split buttons
    document.getElementById('apply-split').addEventListener('click', function() {
        const splitSelect = document.getElementById('split-select');
        const option = splitSelect.value.split(',');
        makeSplitMove(option[0], option[1]);
        document.getElementById('split-options').style.display = 'none';
    });

    document.getElementById('cancel-split').addEventListener('click', function() {
        document.getElementById('split-options').style.display = 'none';
    });

    // Start a new game automatically when the page loads
    startNewGame();

    // Function to start a new game
    function startNewGame() {
        // Show loading spinner
        loadingSpinner.classList.add('active');

        // Reset game state variables
        selectedHand = null;
        moveHistory = [];

        // Get settings from UI
        const difficulty = difficultySelect.value;
        const firstPlayer = playerSelect.value;

        // Clear the move list
        moveListElement.innerHTML = '';

        // Start a new game via the API
        fetch('/api/new_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                difficulty: difficulty,
                first_player: firstPlayer
            }),
        })
        .then(response => response.json())
        .then(data => {
            // Store the game state
            gameState = data.game_state;
            console.log("Game state received:", gameState);

            // Determine whose turn it is
            isHumanTurn = data.ai_move ? false : true;

            // Update the UI
            renderGameState();

            // If the AI made a move, add it to the history
            if (data.ai_move) {
                addMoveToHistory({
                    player: 'AI',
                    move: data.ai_move,
                    notation: getMoveNotation(data.ai_move),
                    evaluation: data.evaluation,
                    perfect: data.perfect
                });
            }

            // Hide loading spinner
            loadingSpinner.classList.remove('active');

            // Update message
            updateMessage();

            // If AI goes first, get its move and update UI accordingly
            if (firstPlayer === 'ai') {
                isHumanTurn = false; // Disable human moves until AI moves
                updateMessage();

                // Get AI's first move
                fetch('/api/make_move', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        move: null // Null move triggers AI's first move
                    }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        messageArea.innerText = data.error;
                        isHumanTurn = true;
                    } else {
                        // Update game state
                        gameState = data.game_state;

                        // Add AI move to history
                        if (data.ai_move) {
                            addMoveToHistory({
                                player: 'AI',
                                move: data.ai_move,
                                notation: getMoveNotation(data.ai_move),
                                evaluation: data.evaluation,
                                perfect: data.perfect
                            });
                        }

                        // Update evaluation marker
                        if (data.evaluation !== undefined) {
                            updateEvaluationMarker(data.evaluation);
                        }

                        // Enable human turn
                        isHumanTurn = true;

                        // Update the UI
                        renderGameState();
                        updateMessage();
                    }

                    // Hide loading spinner
                    loadingSpinner.classList.remove('active');
                })
                .catch(error => {
                    console.error('Error getting AI first move:', error);
                    messageArea.innerText = 'Error starting game. Please try again.';
                    isHumanTurn = true;
                    loadingSpinner.classList.remove('active');
                });

              //Removed return statement here
            }

        })
        .catch(error => {
            console.error('Error starting new game:', error);
            messageArea.innerText = 'Error starting game. Please try again.';
            loadingSpinner.classList.remove('active');
        });
    }

    // Function to handle hand clicks (selection & targets)
    function handleHandClick(player, hand) {
        // If game is over or not human's turn, ignore clicks
        if (!gameState || gameState.is_terminal === true || !isHumanTurn) {
            return;
        }
        console.log("Hand clicked", player, hand, gameState);

        // If clicking player 2's hand (AI)
        if (player === 2) {
            // If we already have a hand selected, this is a target for a tap
            if (selectedHand) {
                const [selectedPlayer, selectedHandIndex] = selectedHand;

                // Only allow taps from human to AI
                if (selectedPlayer === 1) {
                    // Check that the source hand and target hand are alive
                    const humanHand = gameState.p1_hands[selectedHandIndex];
                    const aiHand = gameState.p2_hands[hand === 'left' ? 0 : 1];

                    console.log(`Checking tap: Human hand (${selectedHandIndex}) has ${humanHand} fingers, AI hand (${hand}) has ${aiHand} fingers`);

                    if (humanHand > 0 && aiHand > 0) {
                        makeMove({
                            move_type: 'tap',
                            player: 0, // Player 1 (human) is index 0
                            details: [selectedHandIndex, hand === 'left' ? 0 : 1]
                        });
                    } else {
                        messageArea.innerHTML = "<strong>Invalid move:</strong> Can't tap with or target a dead hand (0 fingers)";
                        setTimeout(() => updateMessage(), 2000);
                    }
                }

                // Clear the selection
                selectedHand = null;
                clearHandHighlights();
            }

            return;
        }

        // Player 1's hand (human)
        const handIndex = hand === 'left' ? 0 : 1;

        // If the hand is dead (0 fingers), can't select it
        if (gameState.p1_hands[handIndex] === 0) {
            return;
        }

        // If we already have this hand selected, deselect it
        if (selectedHand && selectedHand[0] === 1 && selectedHand[1] === handIndex) {
            selectedHand = null;
            clearHandHighlights();
            return;
        }

        // Check if we can show split options
        const leftHand = gameState.p1_hands[0];
        const rightHand = gameState.p1_hands[1];
        const totalFingers = leftHand + rightHand;

        // Otherwise, select this hand
        selectedHand = [1, handIndex];
        highlightSelectedHand();
    }

    // Function to show split options directly in the game interface
    function showSplitOptions() {
        // Update the options
        updateSplitOptions();

        // Show the split options container
        const splitOptionsContainer = document.getElementById('split-options');
        splitOptionsContainer.style.display = 'block';
    }

    // Function to update split options based on current hands
    function updateSplitOptions() {
        const splitSelect = document.getElementById('split-select');
        splitSelect.innerHTML = '';

        const leftHand = gameState.p1_hands[0];
        const rightHand = gameState.p1_hands[1];
        const totalFingers = leftHand + rightHand;

        // Create options for all valid distributions
        for (let newLeft = 0; newLeft <= totalFingers; newLeft++) {
            const newRight = totalFingers - newLeft;

            // Skip the current distribution
            if (newLeft === leftHand && newRight === rightHand) continue;

            // Skip distributions with dead hands if both current hands are alive
            if ((leftHand > 0 && rightHand > 0) && (newLeft === 0 || newRight === 0)) continue;

            // Add the option
            const option = document.createElement('option');
            option.value = `${newLeft},${newRight}`;
            option.textContent = `${newLeft}-${newRight}`;
            splitSelect.appendChild(option);
        }
    }

    // Function to make a split move
    function makeSplitMove(newLeft, newRight) {
        const isHuman = playerSelect.value === 'human';
        const hands = isHuman ? gameState.p1_hands : gameState.p2_hands;
        const currentLeft = hands[0];
        const currentRight = hands[1];

        // Validate the split move: total fingers must remain the same
        if (currentLeft + currentRight !== parseInt(newLeft) + parseInt(newRight)) {
            messageArea.innerHTML = "<strong>Invalid split:</strong> Total fingers must remain the same";
            setTimeout(() => updateMessage(), 2000);
            return;
        }

        console.log(`Making split move: [${currentLeft}, ${currentRight}] -> [${newLeft}, ${newRight}]`);

        makeMove({
            move_type: 'split',
            player: isHuman ? 0 : 1, // 0 for human (P1), 1 for AI (P2)
            details: [[currentLeft, currentRight], [parseInt(newLeft), parseInt(newRight)]]
        });

        // Clear the selection
        selectedHand = null;
        clearHandHighlights();
    }

    // Function to send a move to the server
    function makeMove(move) {
        // Show loading spinner
        loadingSpinner.classList.add('active');

        // Disable human turn until we get a response
        isHumanTurn = false;

        console.log("Making move:", move);

        fetch('/api/make_move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                move: move
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                messageArea.innerText = data.error;
                isHumanTurn = true; // Re-enable human turn if there was an error
            } else {
                // Update game state
                gameState = data.game_state;

                // Add human move to history
                addMoveToHistory({
                    player: 'Human',
                    move: move,
                    notation: getMoveNotation(move)
                });

                // Add AI move to history if one was made
                if (data.ai_move) {
                    addMoveToHistory({
                        player: 'AI',
                        move: data.ai_move,
                        notation: getMoveNotation(data.ai_move),
                        evaluation: data.evaluation,
                        perfect: data.perfect
                    });
                }

                // Update evaluation marker
                if (data.evaluation !== undefined) {
                    updateEvaluationMarker(data.evaluation);
                }

                // Re-enable human turn
                isHumanTurn = !data.is_game_over;
            }

            // Update the UI
            renderGameState();
            updateMessage();

            // Hide loading spinner
            loadingSpinner.classList.remove('active');
        })
        .catch(error => {
            console.error('Error making move:', error);
            messageArea.innerText = 'Error making move. Please try again.';
            isHumanTurn = true; // Re-enable human turn
            loadingSpinner.classList.remove('active');
        });
    }

    // Function to render the current game state
    function renderGameState() {
        if (!gameState) return;

        // Update the game board
        const p1LeftFingers = gameState.p1_hands[0];
        const p1RightFingers = gameState.p1_hands[1];
        const p2LeftFingers = gameState.p2_hands[0];
        const p2RightFingers = gameState.p2_hands[1];

        // Update player 1's hands
        document.getElementById('p1-left-fingers').innerHTML = Array(p1LeftFingers).fill('<div class="finger active"></div>').join('');
        document.getElementById('p1-right-fingers').innerHTML = Array(p1RightFingers).fill('<div class="finger active"></div>').join('');

        // Update player 2's hands
        document.getElementById('p2-left-fingers').innerHTML = Array(p2LeftFingers).fill('<div class="finger active"></div>').join('');
        document.getElementById('p2-right-fingers').innerHTML = Array(p2RightFingers).fill('<div class="finger active"></div>').join('');

        // Mark dead hands
        document.getElementById('p1-left-hand').classList.toggle('dead', p1LeftFingers === 0);
        document.getElementById('p1-right-hand').classList.toggle('dead', p1RightFingers === 0);
        document.getElementById('p2-left-hand').classList.toggle('dead', p2LeftFingers === 0);
        document.getElementById('p2-right-hand').classList.toggle('dead', p2RightFingers === 0);

        // Highlight the active player
        document.getElementById('p1-area').classList.toggle('active', isHumanTurn);
        document.getElementById('p2-area').classList.toggle('active', !isHumanTurn);

        // If we have an active hand selection, highlight it
        if (selectedHand) {
            highlightSelectedHand();
        }

        // Update split options if a hand is selected
        updateSplitOptions();
    }

    // Function to highlight the selected hand
    function highlightSelectedHand() {
        clearHandHighlights();

        if (!selectedHand) return;

        const [player, handIndex] = selectedHand;
        if (player === 1) {
            const element = handIndex === 0 ? 
                document.getElementById('p1-left-hand') :
                document.getElementById('p1-right-hand');

            element.classList.add('active');
        }
    }

    // Function to clear all hand highlights
    function clearHandHighlights() {
        document.getElementById('p1-left-hand').classList.remove('active');
        document.getElementById('p1-right-hand').classList.remove('active');
        document.getElementById('p2-left-hand').classList.remove('active');
        document.getElementById('p2-right-hand').classList.remove('active');
    }

    // Function to update available split options
    function updateSplitOptions() {
        const splitOptions = document.getElementById('split-options');
        splitOptions.innerHTML = '';

        if (!selectedHand || selectedHand[0] !== 1 || !isHumanTurn) {
            splitOptions.style.display = 'none';
            return;
        }

        // Get the current hand values
        const currentLeft = gameState.p1_hands[0];
        const currentRight = gameState.p1_hands[1];
        const total = currentLeft + currentRight;

        // If total is less than 2, can't split
        if (total < 2) {
            splitOptions.style.display = 'none';
            return;
        }

        // Show the split options container
        splitOptions.style.display = 'block';

        // Generate all possible splits
        for (let newLeft = 0; newLeft <= 4; newLeft++) {
            const newRight = total - newLeft;

            // Skip invalid splits
            if (newRight < 0 || newRight > 4) continue;
            if (newLeft === currentLeft && newRight === currentRight) continue;
            if (newLeft === currentRight && newRight === currentLeft && currentLeft !== currentRight) continue;

            // Create a button for this split option
            const button = document.createElement('button');
            button.className = 'btn btn-sm btn-outline-info m-1';
            button.innerText = `${newLeft}|${newRight}`;
            button.onclick = () => makeSplitMove(newLeft, newRight);

            splitOptions.appendChild(button);
        }
    }

    // Function to update the game message
    function updateMessage() {
        if (!gameState) {
            messageArea.innerText = 'Starting new game...';
            return;
        }

        if (gameState.is_terminal === true) {
            const winner = gameState.winner === 'P1' ? 'You win!' : 'AI wins!';
            messageArea.innerHTML = `<strong>Game over! ${winner}</strong>`;
            return;
        }

        if (isHumanTurn) {
            messageArea.innerHTML = `<strong>Your turn:</strong> Select a hand to tap or split`;
        } else {
            messageArea.innerHTML = `<strong>AI is thinking...</strong>`;
        }
    }

    // Function to update the evaluation marker on the evaluation bar
    function updateEvaluationMarker(evaluation) {
        // Invert evaluation so positive means human winning
        evaluation = -evaluation;

        // Map the evaluation score to a position on the bar (0-100%)
        // Evaluation ranges from -100 (losing) to +100 (winning)
        const normalizedEval = Math.max(0, Math.min(100, (evaluation + 100) / 2));
        evaluationMarker.style.left = `${normalizedEval}%`;

        // Update the color based on who's winning
        if (evaluation > 15) {
            evaluationMarker.style.backgroundColor = '#4CAF50'; // Green - human advantage
            evaluationMarker.style.height = '18px';
        } else if (evaluation < -15) { 
            evaluationMarker.style.backgroundColor = '#F44336'; // Red - AI advantage
            evaluationMarker.style.height = '18px';
        } else {
            evaluationMarker.style.backgroundColor = '#FFC107'; // Yellow - balanced
            evaluationMarker.style.height = '12px';
        }
    }

    // Function to add a move to the history and display it
    function addMoveToHistory(moveData) {
        moveHistory.push(moveData);

        const moveElement = document.createElement('div');
        moveElement.className = `move ${moveData.perfect ? 'perfect' : ''}`;

        let moveText = `<strong>${moveData.player}:</strong> ${moveData.notation}`;
        if (moveData.evaluation !== undefined) {
            moveText += ` (Eval: ${moveData.evaluation})`;
        }
        if (moveData.perfect) {
            moveText += ` <span class="badge bg-success">Perfect</span>`;
        }

        moveElement.innerHTML = moveText;
        moveListElement.appendChild(moveElement);

        // Scroll to the bottom of the move list
        moveListElement.scrollTop = moveListElement.scrollHeight;
    }

    // Function to get a human-readable notation for a move
    function getMoveNotation(move) {
        if (move.move_type === 'tap') {
            const [attackHand, defendHand] = move.details;
            const attackPlayer = move.player + 1;
            const defendPlayer = attackPlayer === 1 ? 2 : 1;
            const attackHandName = attackHand === 0 ? 'L' : 'R';
            const defendHandName = defendHand === 0 ? 'L' : 'R';

            return `P${attackPlayer}${attackHandName}>P${defendPlayer}${defendHandName}`;
        } else if (move.move_type === 'split') {
            const player = move.player + 1;

            // Check if details are in the new format (array of arrays)
            if (Array.isArray(move.details[0])) {
                const [[oldLeft, oldRight], [newLeft, newRight]] = move.details;
                return `Sp(P${player}:${oldLeft}|${oldRight} → ${newLeft}|${newRight})`;
            } else {
                // Old format for backward compatibility
                const [oldLeft, oldRight, newLeft, newRight] = move.details;
                return `Sp(P${player}:${oldLeft}|${oldRight} → ${newLeft}|${newRight})`;
            }
        }

        return 'Unknown move';
    }

    // Set up event listeners for hand clicks
    document.getElementById('p1-left-hand').addEventListener('click', () => handleHandClick(1, 'left'));
    document.getElementById('p1-right-hand').addEventListener('click', () => handleHandClick(1, 'right'));
    document.getElementById('p2-left-hand').addEventListener('click', () => handleHandClick(2, 'left'));
    document.getElementById('p2-right-hand').addEventListener('click', () => handleHandClick(2, 'right'));
});