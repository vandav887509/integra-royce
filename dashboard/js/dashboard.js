(function () {
  'use strict';
  function $(id) { return document.getElementById(id); }
  function setText(id, v) { var el=$(id); if(el) el.textContent=v; }
  function setHref(id, v) { var el=$(id); if(el) el.href=v; }

  function getMachineFromURL() {
    var params  = new URLSearchParams(window.location.search);
    var machine = params.get('machine');
    var data    = window.MACHINE_DATA;
    // default to B21 if no machine param or unrecognised
    if (!machine || !data[machine]) machine = '21';
    return machine;
  }

  function pushMachineURL(key) { window.history.pushState({machine:key},'',window.location.pathname+'?machine='+key); }
  function pctLabel(c,p) { if(p==null||p===0) return ''; var d=((c-p)/Math.abs(p)*100).toFixed(1); return (d>0?'\u25b2 ':'\u25bc ')+Math.abs(d)+'%'; }
  function arrowClass(c,p) { return c>=p?'val-up':'val-down'; }

  function updateMetrics(d) {
    var series=[
      {label:'Type 1',data:d.t1,ids:['metric1Label','metric1Val','metric1Sub']},
      {label:'Type 2',data:d.t2,ids:['metric2Label','metric2Val','metric2Sub']},
      {label:'Type 3 Short',data:d.t3s,ids:['metric3Label','metric3Val','metric3Sub']},
      {label:'Type 3 Long',data:d.t3l,ids:['metric4Label','metric4Val','metric4Sub']}
    ];
    series.forEach(function(s) {
      var arr=(s.data||[]).filter(function(v){return v!=null;});
      if(!arr.length){setText(s.ids[0],s.label+' \u2014 Latest');var vEl=$(s.ids[1]);if(vEl)vEl.innerHTML='\u2014';setText(s.ids[2],'');return;}
      var last=arr[arr.length-1],prev=arr.length>1?arr[arr.length-2]:null;
      setText(s.ids[0],s.label+' \u2014 Latest');
      var valEl=$(s.ids[1]); if(valEl) valEl.innerHTML=last.toFixed(2)+'<span class="metric-unit">g</span>';
      var subEl=$(s.ids[2]);
      if(subEl&&prev!=null){subEl.innerHTML='Prev: '+prev.toFixed(2)+' &nbsp;<span class="'+arrowClass(last,prev)+'">'+pctLabel(last,prev)+'</span>';}
      else if(subEl){subEl.textContent='';}
    });
  }

  function updateTable(d) {
    var LIMIT=d.specLimit||8,tbody=$('tableBody');
    if(!tbody) return;
    tbody.innerHTML='';
    if(!d.dates||!d.dates.length){tbody.innerHTML='<tr><td colspan="6" style="padding:16px;color:#8b93a8;">No data.</td></tr>';return;}
    d.dates.forEach(function(date,i){
      var t1=d.t1[i],t2=d.t2[i],t3s=d.t3s[i],t3l=d.t3l[i];
      var vals=[t1,t2,t3s,t3l].filter(function(v){return v!=null;});
      var minV=vals.length?Math.min.apply(null,vals):Infinity;
      var status=minV<LIMIT?'FAIL':(minV<LIMIT*1.5?'REVIEW':'PASS');
      var cls=minV<LIMIT?'td-warn':(minV<LIMIT*1.5?'td-warn':'td-ok');
      function fmt(v){return v!=null?v.toFixed(2):'\u2014';}
      tbody.innerHTML+='<tr><td>'+date+'</td><td class="td-val">'+fmt(t1)+'</td><td class="td-val">'+fmt(t2)+'</td><td class="td-val">'+fmt(t3s)+'</td><td class="td-val">'+fmt(t3l)+'</td><td class="'+cls+'">'+status+'</td></tr>';
    });
  }

  function renderMachine(key) {
    var d=window.MACHINE_DATA[key]; if(!d) return;
    document.title='IGN2932M75 \u2014 '+d.label;
    setText('currentMachineLabel',d.label); setText('currentMachineTitle',d.title);
    setText('chartDate','Last updated: '+d.date);
    setText('tableTitle',d.title+' \u2014 Raw Measurements');
    document.querySelectorAll('[data-machine]').forEach(function(el){el.classList.toggle('active',el.dataset.machine===key);});
    window.IntegraCharts.buildAll(d);
    updateMetrics(d); updateTable(d);
  }

  function switchMachine(key) { pushMachineURL(key); renderMachine(key); }

  function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(function(btn){
      btn.addEventListener('click',function(){
        document.querySelectorAll('.tab-btn').forEach(function(b){b.classList.remove('active');});
        this.classList.add('active');
        var tab=this.dataset.tab,c=$('tab-charts'),dt=$('tab-data');
        if(c) c.style.display=(tab==='charts')?'':'none';
        if(dt) dt.style.display=(tab==='data')?'':'none';
      });
    });
  }

  function initMachineSwitcher() {
    document.querySelectorAll('[data-machine]').forEach(function(el){
      el.addEventListener('click',function(e){if(el.tagName==='A') e.preventDefault(); switchMachine(this.dataset.machine);});
    });
  }

  window.addEventListener('popstate',function(e){renderMachine((e.state&&e.state.machine)?e.state.machine:getMachineFromURL());});

  function init() {
    initTabs(); initMachineSwitcher();
    var key = getMachineFromURL();
    // Always update URL to show which machine is active
    window.history.replaceState({machine:key},'',window.location.pathname+'?machine='+key);
    renderMachine(key);
  }

  document.addEventListener('machineDataReady', init);
})();
