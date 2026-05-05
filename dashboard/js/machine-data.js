/* =============================================================
   machine-data.js
   Static machine datasets — will be replaced by CSV-driven
   data in a future sprint.

   Structure per machine:
   {
     label : string        display name
     title : string        short code (B21, B24, …)
     date  : string        last-updated date string
     excel : string        path to Excel download
     dates : string[]      x-axis labels
     t1    : number[]      Type 1 peak force readings (g)
     t2    : number[]      Type 2 peak force readings (g)
     t3s   : number[]      Type 3 Short peak force readings (g)
     t3l   : number[]      Type 3 Long peak force readings (g)
   }
   ============================================================= */

(function (global) {
  'use strict';

  var DATES = [
    '04.30.24','05.09.24','05.09.24','05.09.24','05.09.24',
    '06.12.24','07.23.24','08.28.24','09.11.24','10.04.24'
  ];

  /* NOTE: B21 / B24 / B25 / B27 currently share the same sample
     readings extracted from the reference PNG charts.
     Replace each array with machine-specific CSV data. */

  var T1  = [46.46,50.89,21.42,42.24,34.57,46.76,42.76,41.19,28.94,20.74];
  var T2  = [32.18,31.08,26.14,29.80,33.59,25.59,28.60,32.09,12.58,20.06];
  var T3S = [37.77,43.72,19.29,40.27,29.97,29.82,23.68,31.10,41.12,45.23];
  var T3L = [36.18,36.14,36.39,37.70,32.61,35.48,24.78,23.59,23.59,23.72];

  global.MACHINE_DATA = {
    '21': {
      label: 'B21 Machine', title: 'B21',
      date:  '2024-10-14',
      excel: 'data/BOND PULL DATA IGN2932M75 B21 bonder.xlsx',
      dates: DATES, t1: T1, t2: T2, t3s: T3S, t3l: T3L
    },
    '24': {
      label: 'B24 Machine', title: 'B24',
      date:  '2024-09-26',
      excel: 'data/BOND PULL DATA IGN2932M75 B24 bonder.xlsx',
      dates: DATES, t1: T1, t2: T2, t3s: T3S, t3l: T3L
    },
    '25': {
      label: 'B25 Machine', title: 'B25',
      date:  '2024-10-14',
      excel: 'data/BOND PULL DATA IGN2932M75 B25 bonder.xlsx',
      dates: DATES, t1: T1, t2: T2, t3s: T3S, t3l: T3L
    },
    '27': {
      label: 'B27 Machine', title: 'B27',
      date:  '2024-10-14',
      excel: 'data/BOND PULL DATA IGN2932M75 B27 bonder.xlsx',
      dates: DATES, t1: T1, t2: T2, t3s: T3S, t3l: T3L
    }
  };

})(window);
