// Chore panel fragment module - handles chore-specific functionality with proper cleanup

class ChoreFragment {
    constructor(rootElement) {
        this.rootElement = rootElement;
        this.choreUpdateInterval = null;
        this.init();
    }

    init() {
        this.updateChoresCount();
        this.startTimer();
        
        // Register cleanup function to be called before HTMX swaps this element
        if (window.htmx) {
            htmx.on('htmx:beforeSwap', (event) => {
                if (event.target === this.rootElement || this.rootElement.contains(event.target)) {
                    this.destroy();
                }
            });
        }
    }

    updateChoresCount() {
        const choreListElement = this.rootElement.querySelector('#chores-list');
        if (!choreListElement) return;

        fetch('/api/chores?completed=false')
            .then(response => response.json())
            .then(chores => {
                const countElement = this.rootElement.querySelector('#chores-count');
                if (countElement) {
                    countElement.textContent = chores.length;
                }

                if (choreListElement && chores && chores.length > 0) {
                    let html = '<ul class="list-group list-group-flush">';
                    chores.slice(0, 5).forEach(chore => { // Show only first 5 chores
                        const locale = window.getPreferredLocale ? window.getPreferredLocale() : undefined;
                        const dueDate = chore.due_date
                            ? new Date(chore.due_date).toLocaleDateString(locale)
                            : 'No due date';
                        html += `
                            <li class="list-group-item chore-item ${chore.priority}-priority" id="chore-item-${chore.id}">
                                <div class="chore-item-content">
                                    <span class="chore-item-title">${chore.title}</span>
                                    <small class="chore-item-assignee">Assignee: ${chore.assignee || 'Unassigned'}</small>
                                    <small class="chore-item-due">Due: ${dueDate}</small>
                                </div>
                                <div class="chore-actions">
                                    <button class="btn btn-sm btn-outline-success"
                                            onclick="toggleChoreCompletion(${chore.id}, false)"
                                            aria-label="Mark chore as completed">
                                        ✓
                                    </button>
                                </div>
                            </li>
                        `;
                    });

                    if (chores.length > 5) {
                        html += `<li class="list-group-item">... and ${chores.length - 5} more chores</li>`;
                    }

                    html += '</ul>';
                    choreListElement.innerHTML = html;
                } else if (choreListElement) {
                    choreListElement.innerHTML = '<p class="text-muted">No active chores</p>';
                }
            })
            .catch(error => {
                console.error('Error fetching chores:', error);
                const listElement = this.rootElement.querySelector('#chores-list');
                if (listElement) {
                    listElement.innerHTML = '<p class="text-danger">Error loading chores</p>';
                }
            });
    }

    startTimer() {
        // Clear any existing interval to prevent duplicates
        if (this.choreUpdateInterval) {
            clearInterval(this.choreUpdateInterval);
        }
        
        // Update every 5 minutes if the panel is visible
        this.choreUpdateInterval = setInterval(() => {
            const panel = this.rootElement.querySelector('#chores-panel');
            if (panel && panel.offsetParent !== null) { // Check if panel is visible
                this.updateChoresCount();
            }
        }, 5 * 60 * 1000); // 5 minutes
    }

    destroy() {
        // Clear the interval when the fragment is about to be swapped out
        if (this.choreUpdateInterval) {
            clearInterval(this.choreUpdateInterval);
            this.choreUpdateInterval = null;
        }
    }
}

// Use htmx onLoad to initialize the chore fragment when it's loaded
if (window.htmx) {
    htmx.onLoad((target) => {
        // Check if this target contains chore functionality
        if (target.querySelector && 
            (target.classList.contains('panel') && target.classList.contains('chores')) ||
            target.id === 'chores-panel' || 
            target.querySelector('.chore-fragment') ||
            (target.querySelector && target.querySelector('#chores-list'))) {
            
            // Create a new instance, making sure to destroy any previous instance
            const existingFragment = target.__choreFragment;
            if (existingFragment) {
                existingFragment.destroy();
            }
            
            const choreFragment = new ChoreFragment(target);
            target.__choreFragment = choreFragment;
        }
    });
}
