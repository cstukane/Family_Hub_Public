// Voice command functionality for Kitchen Hub
let recognition = null;
let isListening = false;
let isVoiceEnabled = false;
let wakeWord = 'kitchen'; // Default wake word
let isWaitingForWakeWord = true; // Whether we're waiting for the wake word

// Check if the browser supports speech recognition
function initVoice() {
    // Check if voice commands are enabled in the app config
    fetch('/api/voice/status')
        .then(response => response.json())
        .then(data => {
            if (data.enabled) {
                isVoiceEnabled = true;
                // Get the configured wake word
                getWakeWordConfig();
                setupVoiceControls();
            } else {
                console.log('Voice commands are not enabled');
                // Hide the voice button if voice is not enabled
                const voiceBtn = document.getElementById('voice-control-btn');
                if (voiceBtn) {
                    voiceBtn.style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('Error checking voice status:', error);
            // Hide the voice button if there's an error
            const voiceBtn = document.getElementById('voice-control-btn');
            if (voiceBtn) {
                voiceBtn.style.display = 'none';
            }
        });
}

function getWakeWordConfig() {
    // Fetch the configured wake word from the server
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.features && data.features.voice_wake_word) {
                wakeWord = data.features.voice_wake_word.toLowerCase();
                console.log('Wake word configured:', wakeWord);
            }
        })
        .catch(error => {
            console.log('Could not fetch config, using default wake word:', wakeWord);
        });
}

function setupVoiceControls() {
    const voiceBtn = document.getElementById('voice-control-btn');
    if (voiceBtn) {
        voiceBtn.addEventListener('click', toggleListening);
        // Add keyboard accessibility
        voiceBtn.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                toggleListening();
            }
        });
    }
    
    // Set up the close button for the voice help modal
    const closeBtn = document.getElementById('close-voice-help');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            document.getElementById('voice-help-modal').style.display = 'none';
            // Return focus to the voice button when closing
            if (voiceBtn) {
                voiceBtn.focus();
            }
        });
        
        // Add keyboard accessibility to the close button
        closeBtn.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                document.getElementById('voice-help-modal').style.display = 'none';
                if (voiceBtn) {
                    voiceBtn.focus();
                }
            }
        });
    }
    
    // Also close the modal when clicking outside of it
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('voice-help-modal');
        if (event.target === modal) {
            modal.style.display = 'none';
            // Return focus to the voice button when closing
            if (voiceBtn) {
                voiceBtn.focus();
            }
        }
    });
    
    // Load voice commands for the help modal
    loadVoiceCommands();
}

function toggleListening() {
    if (!isVoiceEnabled) {
        showVoiceFeedback('Voice commands are not enabled. Please check your configuration.', 'error');
        return;
    }
    
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showVoiceFeedback('Speech recognition is not supported in your browser. Please try using Chrome or Edge.', 'error');
        return;
    }
    
    if (!recognition) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;  // Stop after first recognition
        recognition.interimResults = false;  // Only return final results
        recognition.lang = 'en-US';  // Set language to English US
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript.trim();
            console.log('Recognized:', transcript);
            processVoiceCommand(transcript);
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            isListening = false;
            updateVoiceButtonState();
            // Show error in UI
            showVoiceFeedback(`Error: ${event.error}`, 'error');
        };
        
        recognition.onend = function() {
            console.log('Speech recognition ended');
            isListening = false;
            updateVoiceButtonState();
        };
    }
    
    if (isListening) {
        recognition.stop();
        isListening = false;
        showVoiceFeedback('Stopped listening', 'info');
        // Reset to wake word mode
        isWaitingForWakeWord = true;
    } else {
        recognition.start();
        isListening = true;
        if (isWaitingForWakeWord) {
            showVoiceFeedback(`Say "${wakeWord}" to activate voice commands`, 'info');
        } else {
            showVoiceFeedback('Listening... Speak now', 'info');
        }
    }
    
    updateVoiceButtonState();
}

function updateVoiceButtonState() {
    const voiceBtn = document.getElementById('voice-control-btn');
    if (voiceBtn) {
        if (isListening) {
            voiceBtn.style.backgroundColor = 'var(--error-color)';
            voiceBtn.setAttribute('aria-pressed', 'true');
            voiceBtn.setAttribute('aria-label', 'Voice listening - click to stop');
        } else {
            voiceBtn.style.backgroundColor = '';
            voiceBtn.setAttribute('aria-pressed', 'false');
            voiceBtn.setAttribute('aria-label', 'Voice control - click to start listening');
        }
    }
}

function processVoiceCommand(command) {
    // Check if we're in wake word mode
    if (isWaitingForWakeWord) {
        // Check if the wake word is in the command
        if (command.toLowerCase().includes(wakeWord)) {
            // Wake word detected, switch to command mode
            isWaitingForWakeWord = false;
            showVoiceFeedback(`Wake word detected! You can now give a command.`, 'success');
            
            // Extract the actual command after the wake word
            const commandText = command.toLowerCase().replace(wakeWord, '').trim();
            if (commandText) {
                // Process the command that came after the wake word
                processActualCommand(commandText);
            } else {
                // Wait for the next command
                showVoiceFeedback('Listening for command...', 'info');
            }
        } else {
            // Wake word not detected, keep listening
            showVoiceFeedback(`Say "${wakeWord}" to activate voice commands`, 'info');
        }
    } else {
        // We're in command mode, process the command directly
        processActualCommand(command);
    }
}

function processActualCommand(command) {
    // Send the command to the server
    fetch('/api/voice/recognize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ command: command })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showVoiceFeedback(data.message, 'success');
            
            // Handle specific actions based on the response
            if (data.action === 'media_launch' && data.app_id) {
                // Launch the app via the existing API
                fetch('/api/launch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ app_id: data.app_id })
                })
                .then(response => response.text())
                .then(html => {
                    document.getElementById('main-content').innerHTML = html;
                })
                .catch(error => console.error('Error launching app:', error));
                
            } else if (data.action === 'view_switch' && data.view_name) {
                // Switch to the requested view
                fetch(`/view/${data.view_name}`)
                    .then(response => response.text())
                    .then(html => {
                        document.getElementById('main-content').innerHTML = html;
                    })
                    .catch(error => console.error('Error switching view:', error));
            }
            
            // After processing, go back to listening for wake word
            isWaitingForWakeWord = true;
        } else {
            showVoiceFeedback(data.message || 'Command failed', 'error');
            // Go back to wake word listening even if command failed
            isWaitingForWakeWord = true;
        }
    })
    .catch(error => {
        console.error('Error processing voice command:', error);
        showVoiceFeedback('Error processing command', 'error');
        // Go back to wake word listening on error
        isWaitingForWakeWord = true;
    });
}

function showVoiceFeedback(message, type) {
    // Create or update a feedback element
    let feedbackEl = document.getElementById('voice-feedback');
    if (!feedbackEl) {
        feedbackEl = document.createElement('div');
        feedbackEl.id = 'voice-feedback';
        feedbackEl.setAttribute('role', 'alert');
        feedbackEl.setAttribute('aria-live', 'polite');
        feedbackEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: var(--border-radius);
            color: white;
            font-weight: bold;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s;
        `;
        document.body.appendChild(feedbackEl);
    }
    
    // Set the style based on the message type
    switch (type) {
        case 'success':
            feedbackEl.style.backgroundColor = 'var(--success-color)';
            break;
        case 'error':
            feedbackEl.style.backgroundColor = 'var(--error-color)';
            break;
        case 'info':
        default:
            feedbackEl.style.backgroundColor = 'var(--info-color)';
            break;
    }
    
    feedbackEl.textContent = message;
    feedbackEl.style.opacity = '1';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        feedbackEl.style.opacity = '0';
        setTimeout(() => {
            feedbackEl.style.display = 'none';
        }, 300);
    }, 3000);
}

function loadVoiceCommands() {
    fetch('/api/voice/commands')
        .then(response => response.json())
        .then(data => {
            const commandsList = document.getElementById('voice-commands-list');
            if (commandsList && data.commands) {
                let html = '<p>Available voice commands:</p><ul role="list" style="text-align: left;">';
                for (const [command, description] of Object.entries(data.commands)) {
                    html += `<li role="listitem"><strong>${command}</strong>: ${description}</li>`;
                }
                html += '</ul>';
                commandsList.innerHTML = html;
            }
        })
        .catch(error => {
            console.error('Error loading voice commands:', error);
            const commandsList = document.getElementById('voice-commands-list');
            if (commandsList) {
                commandsList.innerHTML = '<p>Could not load voice commands. Please try again later.</p>';
            }
        });
}

// Initialize voice functionality when the page loads
document.addEventListener('DOMContentLoaded', function() {
    initVoice();
    
    // Also add a keyboard shortcut for voice commands (e.g., Alt+V)
    document.addEventListener('keydown', function(event) {
        // Alt+V to toggle voice
        if (event.altKey && event.key.toLowerCase() === 'v') {
            event.preventDefault();
            if (isVoiceEnabled) {
                toggleListening();
            }
        }
        
        // Escape to close the help modal
        if (event.key === 'Escape') {
            const modal = document.getElementById('voice-help-modal');
            if (modal && modal.style.display !== 'none') {
                modal.style.display = 'none';
                // Return focus to the voice button when closing
                const voiceBtn = document.getElementById('voice-control-btn');
                if (voiceBtn) {
                    voiceBtn.focus();
                }
            }
        }
    });
});