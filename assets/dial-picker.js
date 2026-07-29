function mountDialPicker(container, opts = {}) {
  const TICKS_PER_REV = 288;   // 5-min steps over a full 24h face
  const STEP_MIN = 5;
  const R_OUTER = 130, R_INNER = 108, R_MAJOR_IN = 96, CENTER = 150;
  const NS = 'http://www.w3.org/2000/svg';

  const initialMinutes = ((opts.initialMinutes ?? 8*60) + 1440) % 1440;
  const onChange = opts.onChange || (() => {});

  let valueTicks = Math.round(initialMinutes / STEP_MIN);

  const uid = 'dp' + Math.random().toString(36).slice(2, 9);
  container.innerHTML = `
    <div class="dp-wrap" id="${uid}-wrap">
      <svg class="dp-svg" id="${uid}-svg" viewBox="0 0 300 300"></svg>
      <div class="dp-index"></div>
      <div class="dp-readout">
        <div class="dp-time" id="${uid}-time">00:00</div>
      </div>
    </div>`;
  const wrap = container.querySelector(`#${uid}-wrap`);
  const svg = container.querySelector(`#${uid}-svg`);
  const timeEl = container.querySelector(`#${uid}-time`);

  for (let i = 0; i < TICKS_PER_REV; i++) {
    const isMajor = i % 12 === 0;
    const line = document.createElementNS(NS, 'line');
    line.setAttribute('data-i', i);
    line.setAttribute('class', isMajor ? 'dp-tick-major' : 'dp-tick');
    svg.appendChild(line);
    if (isMajor) {
      const label = document.createElementNS(NS, 'text');
      label.setAttribute('data-label', i);
      label.setAttribute('class', 'dp-label');
      label.setAttribute('text-anchor', 'middle');
      label.textContent = String(i/12);
      svg.appendChild(label);
    }
  }

  function render() {
    const rotationDeg = -(valueTicks % TICKS_PER_REV) * (360/TICKS_PER_REV);
    for (let i = 0; i < TICKS_PER_REV; i++) {
      const tickAngleDeg = i * (360/TICKS_PER_REV) + rotationDeg;
      const rad = (tickAngleDeg - 90) * Math.PI/180;
      const isMajor = i % 12 === 0;
      const rIn = isMajor ? R_MAJOR_IN : R_INNER;
      const x1 = CENTER + R_OUTER*Math.cos(rad), y1 = CENTER + R_OUTER*Math.sin(rad);
      const x2 = CENTER + rIn*Math.cos(rad), y2 = CENTER + rIn*Math.sin(rad);
      const line = svg.querySelector(`[data-i="${i}"]`);
      line.setAttribute('x1',x1); line.setAttribute('y1',y1);
      line.setAttribute('x2',x2); line.setAttribute('y2',y2);

      let screenAngle = ((tickAngleDeg % 360) + 360) % 360;
      let dist = Math.min(screenAngle, 360-screenAngle);
      let opacity = dist <= 70 ? 1 : dist >= 150 ? 0 : 1 - (dist-70)/80;
      line.style.opacity = opacity;

      if (isMajor) {
        const lx = CENTER + (R_OUTER+14)*Math.cos(rad), ly = CENTER + (R_OUTER+14)*Math.sin(rad);
        const label = svg.querySelector(`[data-label="${i}"]`);
        label.setAttribute('x', lx); label.setAttribute('y', ly+4);
        label.style.opacity = opacity;
      }
    }
    const totalMinutes = (((valueTicks % TICKS_PER_REV) + TICKS_PER_REV) % TICKS_PER_REV) * STEP_MIN;
    const h = Math.floor(totalMinutes/60), m = totalMinutes%60;
    timeEl.textContent = String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0');

    onChange(totalMinutes % 1440);
  }
  render();

  let actx = null;
  function ensureAudio(){
    if(!actx) actx = new (window.AudioContext||window.webkitAudioContext)();
    if (actx.state === 'suspended') actx.resume();
  }
  let clickVariant = 0;
  function playClick(isMajor){
    if (!actx) return;
    const t0 = actx.currentTime;
    const dur = isMajor ? 0.014 : 0.008;
    const bufLen = Math.floor(actx.sampleRate * dur);
    const buf = actx.createBuffer(1, bufLen, actx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i=0;i<bufLen;i++) data[i] = (Math.random()*2-1) * (1 - i/bufLen);
    const noise = actx.createBufferSource(); noise.buffer = buf;
    const bp = actx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = isMajor ? 1600 : (clickVariant ? 2350 : 2050);
    bp.Q.value = 6;
    const osc = actx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = isMajor ? 1200 : (clickVariant ? 2280 : 2120);
    const oscGain = actx.createGain();
    oscGain.gain.setValueAtTime(isMajor ? 0.18 : 0.1, t0);
    oscGain.gain.exponentialRampToValueAtTime(0.001, t0+dur);
    const master = actx.createGain();
    master.gain.value = 0.8;
    noise.connect(bp).connect(master);
    osc.connect(oscGain).connect(master);
    master.connect(actx.destination);
    noise.start(t0); noise.stop(t0+dur);
    osc.start(t0); osc.stop(t0+dur);
    clickVariant = clickVariant ? 0 : 1;
  }
  function hapticTick(isMajor){
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(isMajor ? 'medium' : 'light');
  }

  let dragging = false, lastAngle = 0;
  function pointerAngle(e){
    const rect = wrap.getBoundingClientRect();
    const cx = rect.left + rect.width/2, cy = rect.top + rect.height/2;
    return Math.atan2(e.clientY-cy, e.clientX-cx) * 180/Math.PI;
  }
  function onDown(e){
    ensureAudio();
    dragging = true;
    lastAngle = pointerAngle(e);
    wrap.setPointerCapture(e.pointerId);
  }
  function onMove(e){
    if (!dragging) return;
    const a = pointerAngle(e);
    let delta = a - lastAngle;
    if (delta > 180) delta -= 360;
    if (delta < -180) delta += 360;
    lastAngle = a;
    const before = Math.floor(valueTicks);
    valueTicks += delta / (360/TICKS_PER_REV);
    const after = Math.floor(valueTicks);
    if (after !== before) {
      const step = after > before ? 1 : -1;
      for (let t = before + step; t !== after + step; t += step) {
        const isMajor = ((t % TICKS_PER_REV) + TICKS_PER_REV) % TICKS_PER_REV % 12 === 0;
        playClick(isMajor); hapticTick(isMajor);
      }
    }
    render();
  }
  function onUp(){
    if (!dragging) return;
    dragging = false;
    valueTicks = Math.round(valueTicks);
    render();
  }
  wrap.addEventListener('pointerdown', onDown);
  wrap.addEventListener('pointermove', onMove);
  wrap.addEventListener('pointerup', onUp);
  wrap.addEventListener('pointercancel', onUp);

  return {
    getMinutes: () => {
      const totalMinutes = (((valueTicks % TICKS_PER_REV) + TICKS_PER_REV) % TICKS_PER_REV) * STEP_MIN;
      return totalMinutes % 1440;
    },
    setMinutes: (m) => { valueTicks = Math.round(((m%1440)+1440)%1440 / STEP_MIN); render(); },
    destroy: () => {
      wrap.removeEventListener('pointerdown', onDown);
      wrap.removeEventListener('pointermove', onMove);
      wrap.removeEventListener('pointerup', onUp);
      wrap.removeEventListener('pointercancel', onUp);
      container.innerHTML = '';
    }
  };
}
