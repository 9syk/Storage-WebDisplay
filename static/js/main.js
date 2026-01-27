function activateTab(index){
  document.querySelectorAll('.tab-panel').forEach((p, i)=>{
    p.classList.toggle('active', String(i)===String(index));
  });
  document.querySelectorAll('.tab-btn').forEach((b, i)=>{
    b.classList.toggle('active', String(i)===String(index));
  });
}

document.querySelectorAll('.tab-btn').forEach((btn, i)=>{
  btn.addEventListener('click', ()=> activateTab(i));
});

let remaining = REFRESH_RATE;

function updateCountdownDisplay(){
  const el = document.getElementById('countdown');
  if(!el) return;
  if(!REFRESH_RATE || REFRESH_RATE <= 0){
    el.textContent = '';
    return;
  }
  el.textContent = `次の自動更新まで: ${remaining}s`;
}

async function renderRankings(obj){
  const panels = Array.from(document.querySelectorAll('.tab-panel'));
  for(const title in obj){
    const items = obj[title];
    const panel = panels.find(p => p.dataset.title === title);
    if(!panel) continue;
    const ol = panel.querySelector('ol');
    if(!ol) continue;
    ol.innerHTML = '';
    items.forEach((it, idx) => {
      const li = document.createElement('li');
      const left = document.createElement('div');
      left.className = 'left';

      const r = document.createElement('span');
      r.className = 'rank';
      r.textContent = (idx + 1) + '.';

      const p = document.createElement('span');
      p.className = 'player';
      p.textContent = it.player;

      left.appendChild(r);
      left.appendChild(p);

      const right = document.createElement('div');
      right.className = 'score-wrap';

      const s = document.createElement('span');
      s.className = 'score';
      s.textContent = it.formatted_value;

      right.appendChild(s);

      li.appendChild(left);
      li.appendChild(right);
      ol.appendChild(li);
    });
  }
}

document.getElementById('refreshBtn').addEventListener('click', async function(){
  const status = document.getElementById('status');
  status.textContent = '更新中...';
  try{
    const res = await fetch('/api/refresh');
    if(!res.ok) throw new Error('network');
    const j = await res.json();
    renderRankings(j.rankings);
    status.textContent = '更新完了';
    remaining = REFRESH_RATE;
    updateCountdownDisplay();
    setTimeout(()=>status.textContent='', 2000);
  }catch(e){
    status.textContent = '更新失敗';
    console.error(e);
  }
});

if (REFRESH_RATE && REFRESH_RATE > 0) {
  remaining = REFRESH_RATE;
  updateCountdownDisplay();

  setInterval(() => {
    if (remaining > 0) {
      remaining -= 1;
    }
    updateCountdownDisplay();
  }, 1000);

  setInterval(async () => {
    try {
      const res = await fetch('/api/refresh');
      if (!res.ok) throw new Error('network');
      const j = await res.json();
      renderRankings(j.rankings);
      remaining = REFRESH_RATE;
      updateCountdownDisplay();
    } catch (e) {
      console.error('Auto-refresh failed', e);
    }
  }, REFRESH_RATE * 1000);
} else {
  remaining = 0;
  updateCountdownDisplay();
}
