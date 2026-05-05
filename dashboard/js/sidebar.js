/* =============================================================
   sidebar.js — sidebar toggle, shared across all pages
   ============================================================= */

(function () {
  'use strict';

  var sidebar = document.getElementById('sidebar');
  var main    = document.getElementById('mainContent');
  var footer  = document.getElementById('siteFooter');
  var btn     = document.getElementById('sidebarToggle');

  if (!btn || !sidebar) return;

  btn.addEventListener('click', function () {
    sidebar.classList.toggle('collapsed');
    if (main)   main.classList.toggle('expanded');
    if (footer) footer.classList.toggle('expanded');
  });

  /* Mark the active sidebar link based on current page filename */
  var page = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.sidebar-link[data-page]').forEach(function (el) {
    if (el.dataset.page === page) el.classList.add('active');
  });
})();
