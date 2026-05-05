/* =============================================================
   dashboard.js
   Single-page controller — reads ?machine=XX from the URL,
   renders the correct machine data, handles tab switching,
   machine switching (updates URL via history.pushState),
   and populates metric cards + data table.

   Load order:
     1. Chart.js 2.9.x
     2. js/machine-data.js   → window.MACHINE_DATA
     3. js/charts.js         → window.IntegraCharts
     4. js/sidebar.js
     5. THIS FILE
   ============================================================= */

(function () {
  'use strict';

  /* ── helpers ── */
  function $(id)          { return document.getElementById(id); }
  function setText(id, v) { var el = $(id); if (el) el.textContent = v; }
  function setHref(id, v) { var el = $(id); if (el) el.href = v; }

  /** Read ?machine=XX from current URL, default to first available machine */
  function getMachineFromURL() {
    var params  = new URLSearchParams(window.location.search);
    var machine = params.get('machine');
    var data    = window.MACHINE_DATA;
    /* fall back to first key if param is missing or unknown */
    if (!machine || !data[machine]) {
      machine = Object.keys(data)[0];
    }
    return machine;
  }

  /** Update the browser URL without a full page reload */
  function pushMachineURL(key) {
    var url = window.location.pathname + '?machine=' + key;
    window.history.pushState({ machine: key }, '', url);
  }

  /* ── percentage delta label ── */
  function pctLabel(current, previous) {
    if (previous == null || previous === 0) return '';
    var diff = ((current - previous) / Math.abs(previous) * 100).toFixed(1);
    return (diff > 0 ? '▲ ' : '▼ ') + Math.abs(diff) + '%';
  }

  function arrowClass(current, previous) {
    return current >= previous ? 'val-up' : 'val-down';
  }

  /* ── metric cards ── */
  function updateMetrics(d) {
    var series = [
      { label: 'Type 1',       data: d.t1,  ids: ['metric1Label','metric1Val','metric1Sub'] },
      { label: 'Type 2',       data: d.t2,  ids: ['metric2Label','metric2Val','metric2Sub'] },
      { label: 'Type 3 Short', data: d.t3s, ids: ['metric3Label','metric3Val','metric3Sub'] },
      { label: 'Type 3 Long',  data: d.t3l, ids: ['metric4Label','metric4Val','metric4Sub'] }
    ];
    series.forEach(function (s) {
      var arr  = s.data;
      var last = arr[arr.length - 1];
      var prev = arr[arr.length - 2];
      var cls  = arrowClass(last, prev);
      setText(s.ids[0], s.label + ' — Latest');
      var valEl = $(s.ids[1]);
      if (valEl) valEl.innerHTML = last.toFixed(2) + '<span class="metric-unit">g</span>';
      var subEl = $(s.ids[2]);
      if (subEl) subEl.innerHTML =
        'Prev: ' + prev.toFixed(2) +
        ' &nbsp;<span class="' + cls + '">' + pctLabel(last, prev) + '</span>';
    });
  }

  /* ── data table ── */
  function updateTable(d) {
    var LIMIT = 8;
    var tbody = $('tableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    d.dates.forEach(function (date, i) {
      var t1  = d.t1[i],  t2  = d.t2[i];
      var t3s = d.t3s[i], t3l = d.t3l[i];
      var min = Math.min(t1, t2, t3s, t3l);
      var status = min < LIMIT ? 'FAIL'   : (min < LIMIT * 1.5 ? 'REVIEW' : 'PASS');
      var cls    = min < LIMIT ? 'td-warn': (min < LIMIT * 1.5 ? 'td-warn' : 'td-ok');
      tbody.innerHTML +=
        '<tr>' +
        '<td>' + date + '</td>' +
        '<td class="td-val">' + t1.toFixed(2)  + '</td>' +
        '<td class="td-val">' + t2.toFixed(2)  + '</td>' +
        '<td class="td-val">' + t3s.toFixed(2) + '</td>' +
        '<td class="td-val">' + t3l.toFixed(2) + '</td>' +
        '<td class="' + cls + '">' + status + '</td>' +
        '</tr>';
    });
  }

  /* ── render a machine ── */
  function renderMachine(key) {
    var d = window.MACHINE_DATA[key];
    if (!d) return;

    /* page title */
    document.title = 'IGN2932M75 — ' + d.label;

    /* header */
    setText('currentMachineLabel', d.label);
    setText('currentMachineTitle', d.title);
    setText('chartDate', 'Last updated: ' + d.date);
    setHref('downloadLink', d.excel);
    setText('tableTitle', d.title + ' — Raw Measurements');

    /* active states — sidebar links + machine tabs */
    document.querySelectorAll('[data-machine]').forEach(function (el) {
      el.classList.toggle('active', el.dataset.machine === key);
    });

    /* charts */
    window.IntegraCharts.buildAll(d);

    /* metrics + table */
    updateMetrics(d);
    updateTable(d);
  }

  /* ── machine switching ── */
  function switchMachine(key) {
    pushMachineURL(key);
    renderMachine(key);
  }

  /* ── tab switching ── */
  function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
        var tab = this.dataset.tab;
        var c = $('tab-charts'), d = $('tab-data');
        if (c) c.style.display = (tab === 'charts') ? '' : 'none';
        if (d) d.style.display = (tab === 'data')   ? '' : 'none';
      });
    });
  }

  /* ── machine click handlers ── */
  function initMachineSwitcher() {
    document.querySelectorAll('[data-machine]').forEach(function (el) {
      el.addEventListener('click', function (e) {
        /* sidebar links are real <a> tags — prevent navigation,
           use pushState instead so the page never reloads */
        if (el.tagName === 'A') e.preventDefault();
        switchMachine(this.dataset.machine);
      });
    });
  }

  /* ── handle browser back / forward ── */
  window.addEventListener('popstate', function (e) {
    var key = (e.state && e.state.machine) ? e.state.machine : getMachineFromURL();
    renderMachine(key);
  });

  /* ── init ── */
  function init() {
    initTabs();
    initMachineSwitcher();
    var key = getMachineFromURL();
    /* replace current history entry so back-button works correctly */
    window.history.replaceState({ machine: key }, '', window.location.pathname + '?machine=' + key);
    renderMachine(key);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
