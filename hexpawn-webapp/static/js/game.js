// static/js/game.js
document.addEventListener('DOMContentLoaded', function () {
    const boardElement = document.getElementById('board');
    const messageElement = document.getElementById('message');
    const wizardThought = document.getElementById('wizard-thought');
    const resetBtn = document.getElementById('reset-game');

    // Game constants
    const EMPTY = 0;
    const PLAYER = 1;
    const AI = 2;

    // Game state
    let gameState = {
        board: [
            [2, 2, 2],
            [0, 0, 0],
            [1, 1, 1]
        ],
        selectedPawn: null,
        possibleMoves: [],
        gameOver: false,
        winner: null,
        aiThinking: false
    };

    const wizardThoughts = {
        start: [
            "\"The paths of this game are clear to me...\"",
            "\"I can see all possible futures of this match.\"",
            "\"Every move you make narrows your path to defeat.\"",
        ],
        thinking: [
            "\"Just as I foresaw...\"",
            "\"The pattern unfolds precisely as expected.\"",
            "\"Your move was anticipated centuries ago.\"",
        ],
        winning: [
            "\"Victory was inevitable from our first moves.\"",
            "\"The outcome was written in the cosmic tapestry.\"",
            "\"I could see your defeat from the moment we began.\"",
        ],
        losing: [
            "\"Impossible! The threads of fate have been severed!\"",
            "\"This... cannot be. My divination has never failed before.\"",
            "\"A remarkable anomaly. You've defied destiny itself!\"",
        ]
    };

    initializeBoard();
    resetBtn.addEventListener('click', resetGame);

    function initializeBoard() {
        boardElement.innerHTML = '';

        for (let row = 0; row < 3; row++) {
            for (let col = 0; col < 3; col++) {
                const square = document.createElement('div');
                square.classList.add('square');

                if ((row + col) % 2 === 0) {
                    square.classList.add('square-light');
                } else {
                    square.classList.add('square-dark');
                }

                square.dataset.row = row.toString();
                square.dataset.col = col.toString();

                if (gameState.board[row][col] !== EMPTY) {
                    const pawn = document.createElement('div');
                    pawn.classList.add('pawn');
                    pawn.classList.add(gameState.board[row][col] === PLAYER ? 'player' : 'ai');
                    square.appendChild(pawn);
                }

                square.addEventListener('click', handleSquareClick);
                boardElement.appendChild(square);
            }
        }
    }

    function handleSquareClick(event) {
        // Prevent actions if AI is thinking or game is over
        if (gameState.aiThinking || gameState.gameOver) {
            messageElement.textContent = gameState.gameOver 
                ? "Game is over! Press 'Reset Game' to play again."
                : "Please wait, Hans is contemplating his move...";
            return;
        }

        const square = event.currentTarget;
        const row = parseInt(square.dataset.row ?? '-1', 10);
        const col = parseInt(square.dataset.col ?? '-1', 10);

        if (isNaN(row) || isNaN(col) || row < 0 || col < 0 || row > 2 || col > 2) {
            return;
        }

        if (gameState.selectedPawn === null) {
            if (gameState.board[row][col] === PLAYER) {
                gameState.selectedPawn = { row, col };
                square.classList.add('highlighted');
                square.querySelector('.pawn')?.classList.add('selected');
                showPossibleMoves(row, col);
            }
        } else {
            const { row: selectedRow, col: selectedCol } = gameState.selectedPawn;

            if (row === selectedRow && col === selectedCol) {
                deselectPawn();
            } else if (isPossibleMove(row, col)) {
                makeMove(selectedRow, selectedCol, row, col);
            } else if (gameState.board[row][col] === PLAYER) {
                deselectPawn();
                gameState.selectedPawn = { row, col };
                square.classList.add('highlighted');
                square.querySelector('.pawn')?.classList.add('selected');
                showPossibleMoves(row, col);
            } else {
                deselectPawn();
            }
        }
    }

    function showPossibleMoves(row, col) {
        clearPossibleMoves();

        // Forward move
        if (row > 0 && gameState.board[row - 1][col] === EMPTY) {
            const forwardSquare = getSquareElement(row - 1, col);
            if (forwardSquare) {
                forwardSquare.classList.add('possible-move');
                gameState.possibleMoves.push({ row: row - 1, col });
            }
        }

        // Diagonal captures (left and right)
        for (const dc of [-1, 1]) {
            const diagCol = col + dc;
            if (row > 0 && diagCol >= 0 && diagCol < 3 && gameState.board[row - 1][diagCol] === AI) {
                const diagSquare = getSquareElement(row - 1, diagCol);
                if (diagSquare) {
                    diagSquare.classList.add('possible-move');
                    gameState.possibleMoves.push({ row: row - 1, col: diagCol });
                }
            }
        }
    }

    function clearPossibleMoves() {
        gameState.possibleMoves = [];

        const squares = boardElement.querySelectorAll('.square');
        squares.forEach(square => {
            square.classList.remove('possible-move');
        });
    }

    function deselectPawn() {
        if (gameState.selectedPawn) {
            const { row, col } = gameState.selectedPawn;
            const square = getSquareElement(row, col);
            if (square) {
                square.classList.remove('highlighted');
                square.querySelector('.pawn')?.classList.remove('selected');
            }

            gameState.selectedPawn = null;
            clearPossibleMoves();
        }
    }

    function isPossibleMove(row, col) {
        return gameState.possibleMoves.some(move => move.row === row && move.col === col);
    }

    function makeMove(fromRow, fromCol, toRow, toCol) {
        // Set AI thinking state to prevent multiple clicks
        gameState.aiThinking = true;
        
        // Disable all squares during processing
        const allSquares = boardElement.querySelectorAll('.square');
        allSquares.forEach(square => {
            square.style.pointerEvents = 'none';
        });

        const fromSquare = getSquareElement(fromRow, fromCol);
        const toSquare = getSquareElement(toRow, toCol);

        if (fromSquare && toSquare) {
            fromSquare.classList.add('highlighted');

            setTimeout(() => {
                fromSquare.classList.remove('highlighted');

                fetch('/move', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        from_pos: [fromRow, fromCol],
                        to_pos: [toRow, toCol]
                    }),
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Server error: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Re-enable squares
                    allSquares.forEach(square => {
                        square.style.pointerEvents = 'auto';
                    });
                    
                    // Reset AI thinking state
                    gameState.aiThinking = false;

                    if (data.error) {
                        messageElement.textContent = data.error;
                        return;
                    }

                    gameState.board = data.board;
                    gameState.gameOver = data.game_over === true;
                    gameState.winner = data.winner;

                    deselectPawn();
                    updateBoardUI();
                    messageElement.textContent = data.message || "Your move";

                    if (gameState.gameOver) {
                        if (gameState.winner === 'player') {
                            wizardThought.textContent = getRandomThought('losing');
                            messageElement.classList.add('success');
                        } else if (gameState.winner === 'ai') {
                            wizardThought.textContent = getRandomThought('winning');
                            messageElement.classList.add('danger');
                        } else {
                            wizardThought.textContent = "\"A draw... the threads of fate are tangled today.\"";
                        }
                        return;
                    }

                    if (data.ai_from && data.ai_to) {
                        animateAIMove(data.ai_from, data.ai_to);
                        wizardThought.textContent = getRandomThought('thinking');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    messageElement.textContent = 'An error occurred. Please try again.';
                    gameState.aiThinking = false;
                    allSquares.forEach(square => {
                        square.style.pointerEvents = 'auto';
                    });
                });
            }, 100);
        }
    }

    function animateAIMove(fromPos, toPos) {
        const [fromRow, fromCol] = fromPos;
        const [toRow, toCol] = toPos;

        const fromSquare = getSquareElement(fromRow, fromCol);
        const toSquare = getSquareElement(toRow, toCol);

        if (fromSquare && toSquare) {
            fromSquare.classList.add('highlighted');

            setTimeout(() => {
                fromSquare.classList.remove('highlighted');
                toSquare.classList.add('highlighted');

                setTimeout(() => {
                    toSquare.classList.remove('highlighted');
                    updateBoardUI();
                }, 500);
            }, 500);
        }
    }

    function updateBoardUI() {
        const squares = boardElement.querySelectorAll('.square');

        squares.forEach(square => {
            const row = parseInt(square.dataset.row ?? '-1', 10);
            const col = parseInt(square.dataset.col ?? '-1', 10);
            
            if (isNaN(row) || isNaN(col) || row < 0 || col < 0 || row > 2 || col > 2) {
                return;
            }

            square.innerHTML = '';

            if (gameState.board[row][col] !== EMPTY) {
                const pawn = document.createElement('div');
                pawn.classList.add('pawn');
                pawn.classList.add(gameState.board[row][col] === PLAYER ? 'player' : 'ai');
                square.appendChild(pawn);
            }
        });
    }

    function getSquareElement(row, col) {
        return document.querySelector(`.square[data-row="${row}"][data-col="${col}"]`);
    }

    function resetGame() {
        if (gameState.aiThinking) {
            messageElement.textContent = "Please wait, Hans is still contemplating...";
            return;
        }
        
        fetch('/reset', {
            method: 'POST',
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            gameState.board = data.board;
            gameState.gameOver = data.game_over;
            gameState.winner = null;
            gameState.selectedPawn = null;
            gameState.possibleMoves = [];
            gameState.aiThinking = false;

            messageElement.textContent = data.message;
            messageElement.classList.remove('success', 'danger');
            wizardThought.textContent = getRandomThought('start');

            initializeBoard();
        })
        .catch(error => {
            console.error('Error:', error);
            messageElement.textContent = 'An error occurred while resetting. Please try again.';
        });
    }

    function getRandomThought(state) {
        const thoughts = wizardThoughts[state];
        return thoughts[Math.floor(Math.random() * thoughts.length)];
    }
});