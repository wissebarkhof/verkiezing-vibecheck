/* Custom JS — HTMX handles most interactivity */

/* Comparison page: topic tabs + party filter */
document.addEventListener('DOMContentLoaded', function () {
    var topicTabs = document.querySelectorAll('.topic-tab');
    var topicPanels = document.querySelectorAll('[data-topic-panel]');
    var partyPills = document.querySelectorAll('.party-filter-pill:not([disabled])');

    if (!topicTabs.length) return;

    function switchTopic(topicName) {
        topicPanels.forEach(function (panel) {
            panel.classList.toggle('hidden', panel.dataset.topicPanel !== topicName);
        });
        topicTabs.forEach(function (tab) {
            var isActive = tab.dataset.topic === topicName;
            if (isActive) {
                tab.style.background = tab.dataset.gradient;
                tab.classList.add('text-white', 'border-transparent');
                tab.classList.remove('bg-white', 'text-gray-700', 'border-gray-200');
            } else {
                tab.style.background = '';
                tab.classList.remove('text-white', 'border-transparent');
                tab.classList.add('bg-white', 'text-gray-700', 'border-gray-200');
            }
        });
    }

    function toggleParty(partyName) {
        var pill = document.querySelector('.party-filter-pill[data-party="' + CSS.escape(partyName) + '"]');
        if (!pill) return;
        var isActive = pill.dataset.active === 'true';
        pill.dataset.active = isActive ? 'false' : 'true';

        if (isActive) {
            // Deselect: show as faded outline
            pill.classList.remove('bg-indigo-50', 'text-indigo-700', 'border-indigo-300');
            pill.classList.add('bg-white', 'text-gray-400', 'border-gray-200');
        } else {
            // Select: highlight
            pill.classList.remove('bg-white', 'text-gray-400', 'border-gray-200');
            pill.classList.add('bg-indigo-50', 'text-indigo-700', 'border-indigo-300');
        }

        document.querySelectorAll('[data-party-card="' + CSS.escape(partyName) + '"]').forEach(function (card) {
            card.classList.toggle('hidden', isActive);
        });
    }

    topicTabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            switchTopic(tab.dataset.topic);
        });
    });

    partyPills.forEach(function (pill) {
        pill.addEventListener('click', function () {
            toggleParty(pill.dataset.party);
        });
    });
});
