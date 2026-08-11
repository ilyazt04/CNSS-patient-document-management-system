(function () {
    const backdrop = document.getElementById('modal-backdrop');
    const modalBox = document.getElementById('modal-box');

    function openModal(html) {
        modalBox.innerHTML = html;
        backdrop.classList.add('is-open');
        document.body.style.overflow = 'hidden';
        wireModalForms();
    }

    function closeModal() {
        backdrop.classList.remove('is-open');
        modalBox.innerHTML = '';
        document.body.style.overflow = '';
    }

    function extractModalContent(htmlText) {
        const doc = new DOMParser().parseFromString(htmlText, 'text/html');
        const content = doc.getElementById('modal-content');
        return content ? content.innerHTML : htmlText;
    }

    function loadModal(url) {
        fetch(url).then(function (res) { return res.text(); })
            .then(function (html) { openModal(extractModalContent(html)); });
    }

    function wireModalForms() {
        modalBox.querySelectorAll('.js-modal-form').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                fetch(form.action, { method: 'POST', body: new FormData(form) })
                    .then(function (res) {
                        if (res.ok) window.location = res.url;
                    });
            });
        });
    }

    document.addEventListener('click', function (e) {
        const link = e.target.closest('.js-modal-link');
        if (link) {
            e.preventDefault();
            loadModal(link.getAttribute('href'));
            return;
        }
        const closeBtn = e.target.closest('.js-modal-close');
        if (closeBtn) {
            e.preventDefault();
            modalBox.contains(closeBtn) ? closeModal() : window.history.back();
        }
    });

    backdrop.addEventListener('click', function (e) {
        if (e.target === backdrop) closeModal();
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeModal();
    });
})();