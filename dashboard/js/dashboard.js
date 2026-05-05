/* =============================================================
   dashboard.js
   Page controller — machine switching, tab switching, metric
   card updates. Used by index.html, index24.html, index25.html,
   index27.html (and any future machine pages).

   Depends on (load order):
     1. Chart.js 2.9.x
     2. js/machine-data.js
     3. js/charts.js
     4. js/sidebar.js
     5. THIS FILE
   ============================================================= */

(function () {
  'use strict';

  /* ── helpers ── */
  function $(id) { return document.getElementById(id); }
  function setText(id, val) { var el = $(id); if (el) el.textContent = val; }
  function setHref(id, val) { var el = $(id); if (el) el.href = val; }

  function pct(current, previous) {
    if (!previous || previous === 0) return '';
    var diff = ((current - previous) / Math.abs(previous) * 100).toFixed(1);
    return (diff > 0 ? '▲ ' : '▼ ') + Math.abs(diff) + '%';
  }

  function arrowClass(current, previous) {
    return current >= previous ? 'val-up' : 'val-down';
  }

  /* ── metric card update ── */
  function updateMetrics(d) {
    var series = [
      { labelId: 'metric1Label', valId: 'metric1Val', subId: 'metric1Sub', data: d.t1,  name: 'Type 1' },
      { labelId: 'metric2Label', valId: 'metric2Val', subId: 'metric2Sub', data: d.t2,  name: 'Type 2' },
      { labelId: 'metric3Label', valId: 'metric3Val', subId: 'metric3Sub', data: d.t3s, name: 'Type 3 Short' },
      { labelId: 'metric4Label', valId: 'metric4Val', subId: 'metric4Sub', data: d.t3l, name: 'Type 3 Long' }
    ];

    series.forEach(function (s) {
      var arr  = s.data;
      var last = arr[arr.length - 1];
      var prev = arr[arr.length - 2];
      var pctStr = pct(last, prev);
      var cls    = arrowClass(last, prev);

      setText(s.labelId, s.name + ' — Latest');
      var valEl = $(s.valId);
      if (valEl) valEl.innerHTML = last.toFixed(2) + '<span class="metric-unit">g</span>';

      var subEl = $(s.subId);
      if (subEl) subEl.innerHTML = 'Prev: ' + prev.toFixed(2) + ' &nbsp;<span class="' + cls + '">' + pctStr + '</span>';
    });
  }

  /* ── switch machine ── */
  function switchMachine(key) {
    var d = window.MACHINE_DATA[key];
    if (!d) return;

    /* header */
    setText('currentMachineLabel', d.label);
    setText('currentMachineTitle', d.title);
    setText('chartDate', 'Last updated: ' + d.date);
    setHref('downloadLink', d.excel);
    setText('tableTitle', d.title + ' — Raw Measurements');

    /* active states */
    document.querySelectorAll('[data-machine]').forEach(function (el) {
      el.classList.toggle('active', el.dataset.machine === key);
    });

    /* charts */
    window.IntegraCharts.buildAll(d);

    /* metrics */
    updateMetrics(d);

    /* store active key */
    window._activeMachine = key;
  }

  /* ── tab switching ── */
  function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
        var tab = this.dataset.tab;
        var charts = $('tab-charts');
        var data   = $('tab-data');
        if (charts) charts.style.display = (tab === 'charts') ? '' : 'none';
        if (data)   data.style.display   = (tab === 'data')   ? '' : 'none';
      });
    });
  }

  /* ── machine tab / sidebar clicks ── */
  function initMachineSwitcher() {
    document.querySelectorAll('[data-machine]').forEach(function (el) {
      el.addEventListener('click', function (e) {
        e.preventDefault();
        switchMachine(this.dataset.machine);
      });
    });
  }

  /* ── init ── */
  function init() {
    /* Which machine is this page for? Read from <body data-machine="27"> */
    var defaultMachine = document.body.dataset.machine || '27';
    initTabs();
    initMachineSwitcher();
    switchMachine(defaultMachine);
  }

  /* Run after DOM ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
