function activateTab(index){
  document.querySelectorAll('.tab-panel').forEach((p,i)=>{
    p.classList.toggle('active', i === index);
  });
  document.querySelectorAll('.tab-btn').forEach((b,i)=>{
    b.classList.toggle('active', i === index);
  });
}

document.querySelectorAll('.tab-btn').forEach((btn,i)=>{
  btn.addEventListener('click', () => activateTab(i));
});

let remaining = REFRESH_RATE;

function updateCountdownDisplay(){
  const el = document.getElementById('countdown');
  if(!el || !REFRESH_RATE) return;
  el.textContent = `次の自動更新まで: ${remaining}s`;
}

async function renderRankings(rankings){
  document.querySelectorAll('.tab-panel').forEach(panel=>{
    const title = panel.dataset.title;
    if(!rankings[title]) return;

    const ol = panel.querySelector('ol');
    ol.innerHTML = '';

    rankings[title].forEach((it,idx)=>{
      ol.insertAdjacentHTML('beforeend', `
        <li>
          <div class="left">
            <span class="rank">${idx+1}.</span>
            <span class="player">${it.player}</span>
          </div>
          <div class="score-wrap">
            <span class="score">${it.formatted_value}</span>
          </div>
        </li>
      `);
    });
  });
}

document.getElementById('refreshBtn').addEventListener('click', async ()=>{
  const status = document.getElementById('status');
  status.textContent = '更新中...';

  try{
    const res = await fetch('/api/refresh');
    const json = await res.json();
    renderRankings(json.rankings);
    remaining = REFRESH_RATE;
    status.textContent = '更新完了';
    setTimeout(()=>status.textContent='',2000);
  }catch(e){
    status.textContent = '更新失敗';
    console.error(e);
  }
});

if(REFRESH_RATE > 0){
  updateCountdownDisplay();

  setInterval(()=>{
    remaining--;
    if(remaining < 0) remaining = 0;
    updateCountdownDisplay();
  },1000);

  setInterval(async ()=>{
    const res = await fetch('/api/refresh');
    const json = await res.json();
    renderRankings(json.rankings);
    remaining = REFRESH_RATE;
  }, REFRESH_RATE * 1000);
}
