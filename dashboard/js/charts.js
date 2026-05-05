/* =============================================================
   charts.js — Chart.js control chart builder
   Reads specLimit from the machine data object.
   Depends on Chart.js 2.9.x (loaded before this script).
   ============================================================= */

(function (global) {
  'use strict';

  var LINE_COLOR  = '#1a6eb5';
  var LIMIT_COLOR = '#cc3333';
  var GRID_COLOR  = '#e8eaef';
  var TICK_COLOR  = '#8b93a8';

  var _instances = {};

  function buildChart(canvasId, labels, data, specLimit) {
    if (_instances[canvasId]) _instances[canvasId].destroy();
    var ctx = document.getElementById(canvasId);
    if (!ctx) return;

    /* replace null with NaN so Chart.js creates a gap */
    var clean = (data || []).map(function(v){ return v != null ? v : NaN; });
    var limit  = labels.map(function(){ return specLimit || 8; });

    _instances[canvasId] = new Chart(ctx.getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Peak Force',
            data: clean,
            borderColor: LINE_COLOR, borderWidth: 1.5,
            pointBackgroundColor: LINE_COLOR, pointBorderColor: LINE_COLOR,
            pointRadius: 4, pointHoverRadius: 6,
            fill: false, lineTension: 0, spanGaps: false
          },
          {
            label: 'Spec Limit',
            data: limit,
            borderColor: LIMIT_COLOR, borderWidth: 1.5,
            borderDash: [6, 4], pointRadius: 0, fill: false
          }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        legend: { display: false },
        scales: {
          xAxes: [{ ticks: { fontColor:TICK_COLOR, fontSize:10, fontFamily:"'IBM Plex Mono',monospace" }, gridLines:{ color:GRID_COLOR } }],
          yAxes: [{ ticks: { fontColor:TICK_COLOR, fontSize:10, fontFamily:"'IBM Plex Mono',monospace", beginAtZero:true }, gridLines:{ color:GRID_COLOR } }]
        },
        tooltips: {
          backgroundColor:'#1a1f2e', titleFontColor:'#8b93a8', bodyFontColor:'#e8eaf0',
          borderColor:'rgba(0,0,0,0.12)', borderWidth:1,
          titleFontFamily:"'IBM Plex Mono',monospace", bodyFontFamily:"'IBM Plex Mono',monospace",
          callbacks: {
            label: function(item) {
              return isNaN(item.yLabel) ? 'No data' : item.yLabel.toFixed(2) + ' g';
            }
          }
        }
      }
    });
  }

  function buildAll(machineData) {
    var sl = machineData.specLimit || 8;
    buildChart('chartType1',      machineData.dates, machineData.t1,  sl);
    buildChart('chartType2',      machineData.dates, machineData.t2,  sl);
    buildChart('chartType3Short', machineData.dates, machineData.t3s, sl);
    buildChart('chartType3Long',  machineData.dates, machineData.t3l, sl);
  }

  global.IntegraCharts = { build: buildChart, buildAll: buildAll };

})(window);
