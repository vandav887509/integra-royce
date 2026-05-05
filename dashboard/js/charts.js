/* =============================================================
   charts.js — Chart.js control chart builder, shared across all pages
   Depends on: Chart.js 2.9.x (loaded before this script)
   ============================================================= */

(function (global) {
  'use strict';

  /* ── config ── */
  var LINE_COLOR  = '#1a6eb5';
  var LIMIT_COLOR = '#cc3333';
  var GRID_COLOR  = '#e8eaef';
  var TICK_COLOR  = '#8b93a8';
  var LIMIT_VAL   = 8;        /* lower spec limit (g) */

  var _instances = {};

  /**
   * buildChart(canvasId, labels, data)
   * Draws (or redraws) a control chart on the given canvas.
   *
   * @param {string}   canvasId  - DOM id of the <canvas> element
   * @param {string[]} labels    - x-axis date labels
   * @param {number[]} data      - y-axis measurement values
   */
  function buildChart(canvasId, labels, data) {
    if (_instances[canvasId]) {
      _instances[canvasId].destroy();
    }

    var ctx = document.getElementById(canvasId);
    if (!ctx) return;

    var limitLine = data.map(function () { return LIMIT_VAL; });

    _instances[canvasId] = new Chart(ctx.getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Peak Force',
            data: data,
            borderColor: LINE_COLOR,
            borderWidth: 1.5,
            pointBackgroundColor: LINE_COLOR,
            pointBorderColor: LINE_COLOR,
            pointRadius: 4,
            pointHoverRadius: 6,
            fill: false,
            lineTension: 0
          },
          {
            label: 'Spec Limit',
            data: limitLine,
            borderColor: LIMIT_COLOR,
            borderWidth: 1.5,
            borderDash: [6, 4],
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: { display: false },
        scales: {
          xAxes: [{
            ticks: { fontColor: TICK_COLOR, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" },
            gridLines: { color: GRID_COLOR }
          }],
          yAxes: [{
            ticks: { fontColor: TICK_COLOR, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", beginAtZero: true },
            gridLines: { color: GRID_COLOR }
          }]
        },
        tooltips: {
          backgroundColor: '#1a1f2e',
          titleFontColor: '#8b93a8',
          bodyFontColor: '#e8eaf0',
          borderColor: 'rgba(0,0,0,0.12)',
          borderWidth: 1,
          titleFontFamily: "'IBM Plex Mono', monospace",
          bodyFontFamily: "'IBM Plex Mono', monospace"
        }
      }
    });
  }

  /**
   * buildAllCharts(machineData)
   * Renders all 4 charts for a given machine dataset.
   *
   * machineData shape:
   * {
   *   dates : string[],
   *   t1    : number[],
   *   t2    : number[],
   *   t3s   : number[],
   *   t3l   : number[]
   * }
   */
  function buildAllCharts(machineData) {
    buildChart('chartType1',      machineData.dates, machineData.t1);
    buildChart('chartType2',      machineData.dates, machineData.t2);
    buildChart('chartType3Short', machineData.dates, machineData.t3s);
    buildChart('chartType3Long',  machineData.dates, machineData.t3l);
  }

  /* expose on window */
  global.IntegraCharts = {
    build:    buildChart,
    buildAll: buildAllCharts
  };

})(window);
