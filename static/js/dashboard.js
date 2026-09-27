document.addEventListener('DOMContentLoaded', () => {
    wireIcons();
    wireSidebar();
    wirePopovers();
    wireModals();
    wireTableSearch();
    wireCsvExport();
    wireMockForms();
    wireMessages();
    wirePasswordToggles();
});

// Fill every `<span class="icon" data-icon="name">` with its sprite symbol.
// width/height="1em" here are a defensive fallback: if dashboard.css fails
// to load for any reason, the icon still sizes to its surrounding text
// instead of falling back to the browser's ~300x150 default SVG size.
function wireIcons() {
    document.querySelectorAll('[data-icon]').forEach((el) => {
        const name = el.getAttribute('data-icon');
        el.innerHTML = `<svg width="1em" height="1em"><use href="#icon-${name}"></use></svg>`;
    });
}

function wireSidebar() {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const scrim = document.getElementById('sidebarScrim');
    if (!toggle || !sidebar) return;

    const close = () => {
        sidebar.classList.remove('is-open');
        scrim.classList.remove('is-visible');
        toggle.setAttribute('aria-expanded', 'false');
    };
    toggle.addEventListener('click', () => {
        const open = sidebar.classList.toggle('is-open');
        scrim.classList.toggle('is-visible', open);
        toggle.setAttribute('aria-expanded', String(open));
    });
    scrim.addEventListener('click', close);
}

function wirePopovers() {
    const popovers = document.querySelectorAll('[data-popover]');

    document.addEventListener('click', (event) => {
        popovers.forEach((popover) => {
            const trigger = popover.querySelector('[data-popover-trigger]');
            const isClickInside = popover.contains(event.target);
            if (trigger === event.target || trigger?.contains(event.target)) {
                const willOpen = !popover.classList.contains('is-open');
                popovers.forEach((p) => p.classList.remove('is-open'));
                popover.classList.toggle('is-open', willOpen);
                trigger.setAttribute('aria-expanded', String(willOpen));
            } else if (!isClickInside) {
                popover.classList.remove('is-open');
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') popovers.forEach((p) => p.classList.remove('is-open'));
    });
}

function wireModals() {
    const openModal = (modal) => {
        modal.hidden = false;
        modal.querySelector('input, select, button')?.focus();
    };
    const closeModal = (modal) => {
        modal.hidden = true;
    };

    document.querySelectorAll('[data-modal-open]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const modal = document.getElementById(btn.getAttribute('data-modal-open'));
            if (modal) openModal(modal);
        });
    });

    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) closeModal(modal);
        });
        modal.querySelectorAll('[data-modal-close]').forEach((btn) => {
            btn.addEventListener('click', () => closeModal(modal));
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        document.querySelectorAll('.modal').forEach((modal) => {
            modal.hidden = true;
        });
    });
}

// Demo-only: shows a success message instead of hitting a real endpoint.
function wireMockForms() {
    document.querySelectorAll('[data-mock-submit]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            let success = form.querySelector('.modal__success');
            if (!success) {
                success = document.createElement('p');
                success.className = 'modal__success';
                form.prepend(success);
            }
            success.textContent = form.dataset.successMessage || 'Request received.';
            setTimeout(() => {
                const modal = form.closest('.modal');
                if (modal) modal.hidden = true;
                success.remove();
                form.reset();
            }, 1400);
        });
    });
}

function wireMessages() {
    document.querySelectorAll('[data-message-close]').forEach((btn) => {
        btn.addEventListener('click', () => btn.closest('.message')?.classList.add('is-dismissed'));
    });
}

// Toggles a password field between masked and plain text via its trailing button.
function wirePasswordToggles() {
    document.querySelectorAll('[data-password-toggle]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const input = document.getElementById(btn.getAttribute('data-password-toggle'));
            if (!input) return;
            const showing = input.type === 'text';
            input.type = showing ? 'password' : 'text';
            btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
        });
    });
}

function wireTableSearch() {
    const input = document.getElementById('txnSearch');
    const table = document.getElementById('txnTable');
    const noResults = document.getElementById('noResults');
    if (!input || !table) return;

    const rows = Array.from(table.querySelectorAll('tbody tr'));

    input.addEventListener('input', () => {
        const term = input.value.trim().toLowerCase();
        let visibleCount = 0;

        rows.forEach((row) => {
            const matches = row.textContent.toLowerCase().includes(term);
            row.hidden = !matches;
            if (matches) visibleCount += 1;
        });

        if (noResults) noResults.hidden = visibleCount !== 0 || rows.length === 0;
    });
}

// Demo-only: builds a CSV client-side from the currently visible rows.
function wireCsvExport() {
    const button = document.getElementById('exportCsv');
    const table = document.getElementById('txnTable');
    if (!button || !table) return;

    button.addEventListener('click', () => {
        const headerCells = Array.from(table.querySelectorAll('thead th')).map((th) => th.textContent.trim());
        const rows = Array.from(table.querySelectorAll('tbody tr')).filter((row) => !row.hidden);

        const csvLines = [headerCells.join(',')];
        rows.forEach((row) => {
            const cells = Array.from(row.querySelectorAll('td')).map((td) => `"${td.textContent.trim().replace(/"/g, '""')}"`);
            csvLines.push(cells.join(','));
        });

        const blob = new Blob([csvLines.join('\n')], {type: 'text/csv;charset=utf-8;'});
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'transaction-history.csv';
        link.click();
        URL.revokeObjectURL(url);
    });
}
