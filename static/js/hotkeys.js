// UI Event Bus for publish/subscribe pattern
class UIEventBus {
    constructor() {
        this.events = {};
    }
    
    subscribe(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
        // Return unsubscribe function
        return () => {
            this.events[event] = this.events[event].filter(cb => cb !== callback);
        };
    }
    
    publish(event, data) {
        if (this.events[event]) {
            this.events[event].forEach(callback => callback(data));
        }
    }
}

// Create global instance
window.uiEventBus = new UIEventBus();

// Initialize CSS variables based on viewport height
function updateCSSVariables() {
    // Update --vh variable to be 1% of viewport height
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
    
    // Update header and footer heights if elements exist
    const headerEl = document.querySelector('.header'); // if we have a header
    const footerEl = document.querySelector('.app-bar');
    const sidebarEl = document.querySelector('.sidebar');
    
    if (footerEl) {
        const footerHeight = footerEl.offsetHeight;
        document.documentElement.style.setProperty('--footer-h', `${footerHeight}px`);
    }
    
    if (sidebarEl) {
        const sidebarWidth = sidebarEl.offsetWidth;
        document.documentElement.style.setProperty('--sidebar-w', `${sidebarWidth}px`);
    }
}

// Update CSS variables on load and resize
document.addEventListener('DOMContentLoaded', function() {
    updateCSSVariables();
    window.addEventListener('resize', updateCSSVariables);
});

// Toast component
class Toast {
    constructor() {
        this.container = this.createContainer();
        this.maxToasts = 3;
        this.queue = [];
    }
    
    createContainer() {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }
    
    show(message, type = 'info', duration = 5000) {
        // If we have too many toasts, queue the new one
        if (this.container.children.length >= this.maxToasts) {
            this.queue.push({ message, type, duration });
            return;
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        const toastContent = document.createElement('div');
        toastContent.textContent = message;
        toast.appendChild(toastContent);
        
        this.container.appendChild(toast);
        
        // Trigger the show animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Auto remove after duration
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                    
                    // If there are queued toasts, show the next one
                    if (this.queue.length > 0) {
                        const next = this.queue.shift();
                        this.show(next.message, next.type, next.duration);
                    }
                }
            }, 300);
        }, duration);
    }
    
    success(message, duration = 5000) {
        this.show(message, 'success', duration);
    }
    
    error(message, duration = 5000) {
        this.show(message, 'error', duration);
    }
    
    warning(message, duration = 5000) {
        this.show(message, 'warning', duration);
    }
    
    info(message, duration = 5000) {
        this.show(message, 'info', duration);
    }
}

// Create global toast instance
window.toast = new Toast();

// Modal component
class Modal {
    constructor(id, options = {}) {
        this.id = id;
        this.options = {
            closable: true,
            closeOnBackdrop: true,
            ...options
        };
        this.element = this.createModal();
        this.isOpen = false;
    }
    
    createModal() {
        let modal = document.getElementById(this.id);
        if (!modal) {
            modal = document.createElement('div');
            modal.id = this.id;
            modal.className = 'modal';
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');
            modal.setAttribute('aria-hidden', 'true');
            
            const content = document.createElement('div');
            content.className = 'modal-content';
            
            if (this.options.closable) {
                const closeBtn = document.createElement('button');
                closeBtn.className = 'modal-close';
                closeBtn.innerHTML = '&times;';
                closeBtn.setAttribute('aria-label', 'Close modal');
                closeBtn.onclick = () => this.close();
                content.appendChild(closeBtn);
            }
            
            modal.appendChild(content);
            document.body.appendChild(modal);
            
            // Add event listener for backdrop click
            if (this.options.closeOnBackdrop) {
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        this.close();
                    }
                });
            }
        }
        return modal;
    }
    
    open() {
        this.element.classList.add('show');
        this.element.setAttribute('aria-hidden', 'false');
        this.isOpen = true;
        
        // Focus the modal for accessibility
        const content = this.element.querySelector('.modal-content');
        if (content) {
            content.setAttribute('tabindex', '-1');
            content.focus();
        }
    }
    
    close() {
        this.element.classList.remove('show');
        this.element.setAttribute('aria-hidden', 'true');
        this.isOpen = false;
        
        // Return focus to the element that opened the modal
        if (this.opener) {
            this.opener.focus();
        }
    }
    
    setContent(content) {
        const contentEl = this.element.querySelector('.modal-content');
        if (contentEl) {
            // Preserve the close button if it exists
            const closeBtn = contentEl.querySelector('.modal-close');
            contentEl.innerHTML = '';
            if (closeBtn) {
                contentEl.appendChild(closeBtn);
            }
            
            if (typeof content === 'string') {
                contentEl.insertAdjacentHTML('beforeend', content);
            } else {
                contentEl.appendChild(content);
            }
        }
    }
    
    setTitle(title) {
        let titleEl = this.element.querySelector('.modal-title');
        if (!titleEl) {
            titleEl = document.createElement('h2');
            titleEl.className = 'modal-title';
            const content = this.element.querySelector('.modal-content');
            content.insertBefore(titleEl, content.firstChild);
        }
        titleEl.textContent = title;
    }
}

// IconButton component
class IconButton {
    constructor(element) {
        this.element = element;
        this.init();
    }
    
    init() {
        // Ensure the button has proper accessibility attributes
        if (!this.element.getAttribute('role')) {
            this.element.setAttribute('role', 'button');
        }
        if (!this.element.getAttribute('tabindex')) {
            this.element.setAttribute('tabindex', '0');
        }
        
        // Add keyboard support
        this.element.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.element.click();
            }
        });
    }
    
    static create(label, icon, onClick, options = {}) {
        const button = document.createElement('button');
        button.className = `icon-button ${options.size || ''}`;
        button.setAttribute('aria-label', label);
        button.title = label;
        
        if (icon) {
            const iconEl = document.createElement('span');
            iconEl.className = 'icon';
            // If it's a valid SVG string, use it directly, otherwise use icon placeholder
            if (icon.includes('<svg') || icon.includes('.svg')) {
                iconEl.innerHTML = typeof icon === 'string' && icon.includes('<svg') ? icon : 
                                  `<span class="icon-placeholder">${label.charAt(0)}</span>`;
            } else {
                iconEl.innerHTML = `<span class="icon-placeholder">${label.charAt(0)}</span>`;
            }
            button.appendChild(iconEl);
        } else {
            // If no icon provided, use the first letter of the label
            const iconEl = document.createElement('span');
            iconEl.className = 'icon';
            iconEl.innerHTML = `<span class="icon-placeholder">${label.charAt(0)}</span>`;
            button.appendChild(iconEl);
        }
        
        if (onClick) {
            button.addEventListener('click', onClick);
        }
        
        return button;
    }
}

// Chip component
class Chip {
    static create(text, options = {}) {
        const chip = document.createElement('span');
        chip.className = `chip ${options.size || ''}`;
        chip.setAttribute('role', 'group');
        chip.setAttribute('aria-label', text);
        
        chip.textContent = text;
        
        if (options.onclick) {
            chip.style.cursor = 'pointer';
            chip.addEventListener('click', options.onclick);
        }
        
        return chip;
    }
}

// SectionHeader component
class SectionHeader {
    static create(title, options = {}) {
        const header = document.createElement('div');
        header.className = 'section-header';
        header.setAttribute('role', 'banner');
        
        const titleEl = document.createElement('h2');
        titleEl.className = 'section-title';
        titleEl.textContent = title;
        header.appendChild(titleEl);
        
        if (options.actions) {
            const actions = document.createElement('div');
            actions.className = 'section-actions';
            if (Array.isArray(options.actions)) {
                options.actions.forEach(action => {
                    if (action instanceof HTMLElement) {
                        actions.appendChild(action);
                    }
                });
            } else {
                actions.appendChild(options.actions);
            }
            header.appendChild(actions);
        }
        
        return header;
    }
}

// Icon Placeholder component
class IconPlaceholder {
    static create(label, options = {}) {
        const icon = document.createElement('span');
        icon.className = 'icon-placeholder';
        icon.setAttribute('role', 'img');
        icon.setAttribute('aria-label', `Icon for ${label}`);
        
        // Use first character or abbreviation
        const text = options.text || (label.length > 0 ? label.charAt(0).toUpperCase() : '?');
        icon.textContent = text;
        icon.title = label;
        
        return icon;
    }
}

// Store components globally for easy access
window.Toast = Toast;
window.Modal = Modal;
window.IconButton = IconButton;
window.Chip = Chip;
window.SectionHeader = SectionHeader;
window.IconPlaceholder = IconPlaceholder;

function formatDateTimeLocal(date) {
    const pad = (value) => String(value).padStart(2, '0');
    return [
        date.getFullYear(),
        pad(date.getMonth() + 1),
        pad(date.getDate()),
    ].join('-') + 'T' + pad(date.getHours()) + ':' + pad(date.getMinutes());
}

function formatDateTimeWithOffset(date) {
    const pad = (value) => String(value).padStart(2, '0');
    const offsetMinutes = -date.getTimezoneOffset();
    const sign = offsetMinutes >= 0 ? '+' : '-';
    const absMinutes = Math.abs(offsetMinutes);
    const offsetHours = Math.floor(absMinutes / 60);
    const offsetMins = absMinutes % 60;
    return (
        formatDateTimeLocal(date) +
        sign +
        pad(offsetHours) +
        ':' +
        pad(offsetMins)
    );
}

function closeModal(modalElement) {
    if (modalElement) {
        modalElement.remove();
    }
}

function toggleAdvancedFields(modalElement, forceState) {
    if (!modalElement) {
        return;
    }
    const advancedFields = modalElement.querySelector('#advanced-fields');
    const toggleButton = modalElement.querySelector('[data-action="toggle-advanced-fields"]');
    if (!advancedFields || !toggleButton) {
        return;
    }

    const shouldOpen = typeof forceState === 'boolean'
        ? forceState
        : advancedFields.style.display === 'none' || advancedFields.style.display === '';

    advancedFields.style.display = shouldOpen ? 'block' : 'none';
    toggleButton.textContent = shouldOpen ? 'Fewer options...' : 'More options...';
}

function initializeAddEventModal(modalElement) {
    if (!modalElement || modalElement.dataset.initialized === 'true') {
        return;
    }
    modalElement.dataset.initialized = 'true';

    const form = modalElement.querySelector('#add-event-form');
    if (!form) {
        return;
    }

    const startInput = form.querySelector('#event-starts-at');
    const endInput = form.querySelector('#event-ends-at');
    const defaultMinutes = parseInt(form.dataset.defaultDuration || '60', 10);
    const allDayCheckbox = form.querySelector('#event-all-day');

    const applyDefaultDuration = () => {
        if (!startInput || !endInput || !startInput.value) {
            return;
        }
        const startDate = new Date(startInput.value);
        if (Number.isNaN(startDate.getTime())) {
            return;
        }

        if (allDayCheckbox && allDayCheckbox.checked) {
            // For all-day events, align end date to start date (backend will expand to full day)
            endInput.value = startInput.value;
            return;
        }

        let endDate = endInput.value ? new Date(endInput.value) : null;
        if (!endDate || Number.isNaN(endDate.getTime()) || endDate <= startDate) {
            endDate = new Date(startDate.getTime() + defaultMinutes * 60000);
            endInput.value = formatDateTimeLocal(endDate);
        }
    };

    if (startInput) {
        startInput.addEventListener('change', applyDefaultDuration);
    }
    if (allDayCheckbox) {
        allDayCheckbox.addEventListener('change', () => applyDefaultDuration());
    }
    if (startInput && !endInput.value) {
        applyDefaultDuration();
    }

    // Ensure the calendar selection defaults to the first option
    const calendarSelect = form.querySelector('#event-calendar');
    if (calendarSelect && !calendarSelect.value && calendarSelect.options.length > 0) {
        calendarSelect.value = calendarSelect.options[0].value;
    }

    const repeatSelect = form.querySelector('#event-repeat');
    const repeatEndRow = form.querySelector('#repeat-end-row');
    const repeatEndSelect = form.querySelector('#event-repeat-end');
    const repeatEndCount = form.querySelector('[data-repeat-end="count"]');
    const repeatEndUntil = form.querySelector('[data-repeat-end="until"]');

    const updateRepeatEndFields = () => {
        if (!repeatEndSelect) {
            return;
        }
        const endValue = repeatEndSelect.value;
        if (repeatEndCount) {
            repeatEndCount.style.display = endValue === 'count' ? 'block' : 'none';
        }
        if (repeatEndUntil) {
            repeatEndUntil.style.display = endValue === 'until' ? 'block' : 'none';
        }
    };

    const updateRepeatVisibility = () => {
        if (!repeatSelect || !repeatEndRow) {
            return;
        }
        const isRepeating = repeatSelect.value && repeatSelect.value !== 'none';
        repeatEndRow.style.display = isRepeating ? 'flex' : 'none';
        if (!isRepeating && repeatEndSelect) {
            repeatEndSelect.value = 'never';
        }
        updateRepeatEndFields();
    };

    if (repeatSelect) {
        repeatSelect.addEventListener('change', updateRepeatVisibility);
    }
    if (repeatEndSelect) {
        repeatEndSelect.addEventListener('change', updateRepeatEndFields);
    }
    updateRepeatVisibility();

    // Focus the title field for ease of entry
    const titleInput = form.querySelector('#event-title');
    if (titleInput) {
        setTimeout(() => titleInput.focus(), 0);
    }
}

function prepareAddEventPayload(form) {
    const formData = new FormData(form);
    const payload = {};
    const trimmed = (value) => (typeof value === 'string' ? value.trim() : value);
    const defaultMinutes = parseInt(form.dataset.defaultDuration || '60', 10);
    const startField = form.querySelector('#event-starts-at');
    const endField = form.querySelector('#event-ends-at');

    const title = trimmed(formData.get('title') || '');
    if (!title) {
        throw new Error('Title is required');
    }
    payload.title = title;

    const hasAllDay = formData.has('all_day');
    payload.all_day = hasAllDay;

    const startsValue = formData.get('starts_at');
    if (!startsValue) {
        throw new Error('Start time is required');
    }
    const startDate = new Date(startsValue);
    if (Number.isNaN(startDate.getTime())) {
        throw new Error('Start time is invalid');
    }

    const endsValue = formData.get('ends_at');
    let endDate = endsValue ? new Date(endsValue) : null;
    if (!endDate || Number.isNaN(endDate.getTime()) || endDate <= startDate) {
        endDate = new Date(startDate.getTime() + defaultMinutes * 60000);
    }

    if (endField) {
        endField.value = formatDateTimeLocal(endDate);
    }
    if (startField) {
        startField.value = formatDateTimeLocal(startDate);
    }

    payload.starts_at = formatDateTimeWithOffset(startDate);
    payload.ends_at = formatDateTimeWithOffset(endDate);

    const optionalFields = ['location', 'description', 'visibility', 'color'];
    optionalFields.forEach((field) => {
        const value = trimmed(formData.get(field) || '');
        if (value) {
            payload[field] = value;
        }
    });

    const guestsValue = trimmed(formData.get('guests') || '');
    if (guestsValue) {
        payload.guests = guestsValue;
    }

    const remindersValue = trimmed(formData.get('reminders') || '');
    if (remindersValue) {
        payload.reminders = remindersValue;
    }

    const repeatValue = trimmed(formData.get('repeat') || '');
    if (repeatValue && repeatValue !== 'none') {
        payload.repeat = repeatValue;
        const repeatEndValue = trimmed(formData.get('repeat_end') || 'never');
        payload.repeat_end = repeatEndValue;
        if (repeatEndValue === 'count') {
            const repeatCount = parseInt(formData.get('repeat_count') || '0', 10);
            if (repeatCount > 0) {
                payload.repeat_count = repeatCount;
            }
        } else if (repeatEndValue === 'until') {
            const repeatUntil = trimmed(formData.get('repeat_until') || '');
            if (repeatUntil) {
                payload.repeat_until = repeatUntil;
            }
        }
    }

    const calendarSelection = trimmed(formData.get('calendar_selection') || 'local');
    if (typeof calendarSelection === 'string' && calendarSelection.startsWith('google:')) {
        payload.calendar_type = 'google';
        payload.calendar_id = calendarSelection.split(':').slice(1).join(':') || 'primary';
    } else {
        payload.calendar_type = 'local';
    }

    return payload;
}

// Add functionality to handle dynamic modal insertion
document.addEventListener('DOMContentLoaded', function() {
    // Set up event delegation for modal close buttons
    document.addEventListener('click', function(e) {
        const target = e.target;
        if (!target) {
            return;
        }

        if (target.classList && target.classList.contains('modal')) {
            closeModal(target);
            return;
        }

        const action = target.dataset ? target.dataset.action : null;
        if (action === 'close-modal') {
            e.preventDefault();
            closeModal(target.closest('.modal'));
            return;
        }

        if (action === 'toggle-advanced-fields') {
            e.preventDefault();
            toggleAdvancedFields(target.closest('.modal'));
            return;
        }

        if (target.classList.contains('modal-close')) {
            e.preventDefault();
            closeModal(target.closest('.modal'));
            return;
        }

        if (target.textContent && target.textContent.trim() === 'Cancel') {
            const addEventModal = target.closest('[data-modal="add-event"]');
            if (addEventModal) {
                e.preventDefault();
                closeModal(addEventModal);
            }
        }
    });
    
    // Set up form submission for modals
    document.addEventListener('submit', function(e) {
        if (e.target.id === 'add-event-form') {
            e.preventDefault();

            const form = e.target;
            const modal = form.closest('.modal');
            const submitButton = form.querySelector('[type="submit"]');

            let payload;
            try {
                payload = prepareAddEventPayload(form);
            } catch (validationError) {
                if (window.toast) {
                    window.toast.error(validationError.message);
                }
                return;
            }

            if (submitButton) {
                submitButton.disabled = true;
            }

            fetch('/api/calendar/local', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            })
                .then(async (response) => {
                    const result = await response.json().catch(() => ({}));
                    if (!response.ok || result.error) {
                        const errorMessage = result.error || 'Failed to create event';
                        throw new Error(errorMessage);
                    }
                    if (window.toast) {
                        window.toast.success('Event added successfully!');
                    }
                    const calendarContainer = document.getElementById('calendar-container');
                    if (calendarContainer) {
                        htmx.ajax('GET', '/partials/calendar/week', { target: '#calendar-container' });
                    }
                    closeModal(modal);
                })
                .catch((error) => {
                    console.error('Error adding event:', error);
                    if (window.toast) {
                        window.toast.error(error.message || 'Error creating event');
                    }
                })
                .finally(() => {
                    if (submitButton) {
                        submitButton.disabled = false;
                    }
                });
        }
    });

    // Initialize modal if it already exists on page load
    document.querySelectorAll('[data-modal="add-event"]').forEach((modalElement) => {
        initializeAddEventModal(modalElement);
    });
});

// When HTMX swaps in the modal partial, initialize its interactions
document.body.addEventListener('htmx:afterSwap', function(event) {
    const target = event.detail && event.detail.target ? event.detail.target : null;
    if (!target) {
        return;
    }
    if (target.id === 'modals') {
        const modalElement = target.querySelector('[data-modal="add-event"]');
        if (modalElement) {
            initializeAddEventModal(modalElement);
        }
    } else if (target.matches && target.matches('[data-modal="add-event"]')) {
        initializeAddEventModal(target);
    } else {
        const nestedModal = target.querySelector && target.querySelector('[data-modal="add-event"]');
        if (nestedModal) {
            initializeAddEventModal(nestedModal);
        }
    }
});

// Keyboard shortcuts for app switching
document.addEventListener('keydown', function(event) {
    // Alt + number keys to launch apps (1-9)
    if (event.altKey && event.key >= '1' && event.key <= '9') {
        event.preventDefault();
        const appIndex = parseInt(event.key) - 1;
        
        const appButtons = document.querySelectorAll('.app-bar-btn');
        if (appButtons[appIndex]) {
            appButtons[appIndex].click();
            // Provide visual feedback for keyboard users
            appButtons[appIndex].focus();
        }
    }
    
    // Alt + letter shortcuts for specific apps (if they exist)
    if (event.altKey) {
        const key = event.key.toLowerCase();
        
        // Try to find a button with the corresponding letter in its label
        const allButtons = document.querySelectorAll('.app-bar-btn');
        for (const button of allButtons) {
            const label = button.querySelector('.app-bar-btn-label');
            if (label && label.textContent.toLowerCase().startsWith(key)) {
                event.preventDefault();
                button.click();
                // Provide visual feedback for keyboard users
                button.focus();
                break;
            }
        }
    }
    
    // H key for high contrast mode
    if (event.key === 'h' && event.ctrlKey) {
        event.preventDefault();
        const currentContrast = document.documentElement.getAttribute('data-contrast');
        if (currentContrast === 'high') {
            document.documentElement.removeAttribute('data-contrast');
            localStorage.setItem('contrast-mode', 'normal');
            // Announce the change to screen readers
            announceToScreenReader('High contrast mode disabled');
        } else {
            document.documentElement.setAttribute('data-contrast', 'high');
            localStorage.setItem('contrast-mode', 'high');
            // Announce the change to screen readers
            announceToScreenReader('High contrast mode enabled');
        }
    }
});

// Helper function to announce changes to screen readers
function announceToScreenReader(message) {
    // Create a temporary element for screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.style.position = 'absolute';
    announcement.style.left = '-9999px';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    // Remove the element after the message has been announced
    setTimeout(function() {
        document.body.removeChild(announcement);
    }, 1000);
}
