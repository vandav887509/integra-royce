/* =============================================================
   sidebar.js — sidebar toggle only.
   Active-link highlighting is now handled by dashboard.js
   via the [data-machine] attribute, not by page filename.
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
})();
