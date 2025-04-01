// static/js/game.js
document.addEventListener('DOMContentLoaded', function() {
    const stonesDisplay = document.getElementById('stones-display');
    const stonesCount = document.getElementById('stones-count');
    const messageElement = document.getElementById('message');
    const wizardThought = document.getElementById('wizard-thought');
    const takeOneBtn = document.getElementById('take-1');
    const takeTwoBtn = document.getElementById('take-2');
    const takeThreeBtn = document.getElementById('take-3');
    const resetBtn = document.getElementById('reset-game');
    
    // Wizard thoughts for different game states
    const wizardThoughts = {
        start: [
            "\"Let's see how your fate unfolds...\"",
            "\"The stones reveal many paths...\"",
            "\"I can see all possible outcomes.\"",
        ],
        thinking: [
            "\"Hmm, interesting choice...\"",
            "\"As I foresaw...\"",
            "\"The pattern emerges...\"",
        ],
        winning: [
            "\"The threads of fate always reveal their pattern to those who know how to look.\"",
            "\"Your defeat was written in the stars.\"",
            "\"I saw this outcome from the beginning.\"",
        ],
        losing: [
            "\"Perhaps there are futures even I cannot foresee.\"",
            "\"Most unexpected! Your fate surprises me.\"",
            "\"You have defied my divination!\"",
        ]
    };

    // Initialize the game
    let gameState = {
        stones: 21,
        gameOver: false,
        winner: null
    };

    // Initialize the stones display
    renderStones();

    // Add event listeners to the buttons
    takeOneBtn.addEventListener('click', () => makeMove(1));
    takeTwoBtn.addEventListener('click', () => makeMove(2));
    takeThreeBtn.addEventListener('click', () => makeMove(3));
    resetBtn.addEventListener('click', resetGame);

    // Function to render the stones
    function renderStones() {
        stonesDisplay.innerHTML = '';
        stonesCount.textContent = gameState.stones;
        
        // Create a more organic, pile-like arrangement
        for (let i = 0; i < gameState.stones; i++) {
            const stone = document.createElement('div');
            stone.classList.add('stone');
            
            // Add random rotation and slight position variation to make it look natural
            const rotation = Math.random() * 360;
            const xOffset = Math.random() * 10 - 5; // -5 to 5px
            const yOffset = Math.random() * 10 - 5; // -5 to 5px
            
            // Adjust stone size slightly for variation
            const scale = 0.85 + Math.random() * 0.3; // 0.85 to 1.15
            
            stone.style.transform = `rotate(${rotation}deg) translate(${xOffset}px, ${yOffset}px) scale(${scale})`;
            
            // Add animation delay when stones appear
            stone.style.animationDelay = `${i * 50}ms`;
            
            stonesDisplay.appendChild(stone);
        }
        
        // Enable/disable buttons based on stones left
        updateButtons();
    }
    
    // Function to update button states
    function updateButtons() {
        const buttonsEnabled = !gameState.gameOver && gameState.stones > 0;
        takeOneBtn.disabled = !buttonsEnabled || gameState.stones < 1;
        takeTwoBtn.disabled = !buttonsEnabled || gameState.stones < 2;
        takeThreeBtn.disabled = !buttonsEnabled || gameState.stones < 3;
    }

    // Function to handle player move
    function makeMove(stonesCount) {
        if (gameState.gameOver || stonesCount > gameState.stones) {
            return;
        }
        
        // Disable buttons during processing
        takeOneBtn.disabled = true;
        takeTwoBtn.disabled = true;
        takeThreeBtn.disabled = true;
        
        // Update message
        messageElement.textContent = `Taking ${stonesCount} stone${stonesCount > 1 ? 's' : ''}...`;
        
        // Visual feedback - fade out stones being taken
        const allStones = document.querySelectorAll('.stone');
        const stonesToRemove = Math.min(stonesCount, allStones.length);
        
        for (let i = 0; i < stonesToRemove; i++) {
            // Select a random stone to remove for natural feel
            const randomIndex = Math.floor(Math.random() * allStones.length);
            const stone = allStones[randomIndex];
            stone.style.opacity = "0";
            stone.style.transform += " scale(0.5) translateY(-20px)";
        }
        
        // Wait for animation, then send move to server
        setTimeout(() => {
            fetch('/play', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ stones_taken: stonesCount }),
            })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                messageElement.textContent = data.error;
                updateButtons();
                return;
            }
            
            // Update game state
            gameState.stones = data.stones;
            gameState.gameOver = data.game_over;
            gameState.winner = data.winner;
            
            // Update UI
            renderStones();
            messageElement.textContent = data.message;
            
            // Update wizard thought bubble
            if (data.game_over) {
                if (data.winner === 'ai') {
                    wizardThought.textContent = getRandomThought('winning');
                    messageElement.classList.add('danger');
                } else {
                    wizardThought.textContent = getRandomThought('losing');
                    messageElement.classList.add('success');
                }
            } else {
                wizardThought.textContent = getRandomThought('thinking');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            messageElement.textContent = 'An error occurred. Please try again.';
            updateButtons();
        });
        }, 400); // Match the animation duration
    }

    // Function to reset the game
    function resetGame() {
        fetch('/reset', {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            gameState.stones = data.stones;
            gameState.gameOver = data.game_over;
            gameState.winner = null;
            
            messageElement.textContent = data.message;
            messageElement.classList.remove('success', 'danger');
            wizardThought.textContent = getRandomThought('start');
            
            renderStones();
        })
        .catch(error => {
            console.error('Error:', error);
            messageElement.textContent = 'An error occurred while resetting. Please try again.';
        });
    }
    
    // Function to get a random thought from the wizard
    function getRandomThought(state) {
        const thoughts = wizardThoughts[state];
        return thoughts[Math.floor(Math.random() * thoughts.length)];
    }
});