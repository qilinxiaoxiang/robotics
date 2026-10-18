<title>MicroDuck Battery Backpack</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a bench manual. Sticky step index on the left (desktop), one reading column, figures that run a little wider than the text. */
:root{
  --bg:#f2f4f3; --paper:#ffffff; --ink:#1d2326; --muted:#5b6669; --rule:#d5dbda;
  --red:#cf3426; --blk:#22282b; --xt:#e9b21c; --xt-ink:#5a4300; --pad:#c99a3a; --pcb:#1e2427;
  --ok:#23824f; --warn:#b4560f; --live:#ff5a3c; --wash:#e7ecea;
  --f-display:"Archivo","Arial Narrow",Arial,sans-serif;
  --f-body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#14191b; --paper:#1c2225; --ink:#e6ebea; --muted:#9aa6a8; --rule:#2f383b;
  --red:#ff6a57; --blk:#9fb0b4; --xt:#f0bf35; --xt-ink:#3b2c00; --pad:#d9ad55; --pcb:#0d1112;
  --ok:#4cc584; --warn:#f0954a; --live:#ff7a5e; --wash:#232b2e; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#14191b; --paper:#1c2225; --ink:#e6ebea; --muted:#9aa6a8; --rule:#2f383b;
  --red:#ff6a57; --blk:#9fb0b4; --xt:#f0bf35; --xt-ink:#3b2c00; --pad:#d9ad55; --pcb:#0d1112;
  --ok:#4cc584; --warn:#f0954a; --live:#ff7a5e; --wash:#232b2e; color-scheme:dark}

*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:16px;line-height:1.6;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0 64px}
.wrap{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:220px minmax(0,1fr);gap:48px}
nav.toc{position:sticky;top:calc(env(safe-area-inset-top,0px) + 24px);align-self:start;padding-top:40px;font-size:14px}
nav.toc ol{list-style:none;margin:0;padding:0;display:grid;gap:2px;counter-reset:t}
nav.toc a{display:flex;gap:10px;color:var(--muted);text-decoration:none;padding:5px 8px;border-radius:6px}
nav.toc a:hover,nav.toc a:focus-visible{background:var(--wash);color:var(--ink)}
nav.toc .n{font-family:var(--f-mono);font-size:12px;width:20px;flex:none;padding-top:2px}
main{min-width:0;max-width:760px}
header.hero{padding:40px 0 8px}
.eyebrow{font-family:var(--f-mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--f-display);font-weight:800;font-size:clamp(34px,5.4vw,54px);line-height:1.02;letter-spacing:-.01em;margin:10px 0 14px;text-wrap:balance}
h2{font-family:var(--f-display);font-weight:700;font-size:28px;line-height:1.15;margin:0 0 10px;text-wrap:balance;display:flex;gap:14px;align-items:baseline}
h2 .sn{font-family:var(--f-mono);font-weight:500;font-size:14px;color:var(--red);flex:none}
h3{font-family:var(--f-display);font-weight:700;font-size:19px;margin:22px 0 6px}
p{margin:0 0 12px;max-width:66ch}
.lede{font-size:18px;color:var(--muted);max-width:60ch}
section{padding:44px 0 8px;border-top:1px solid var(--rule);margin-top:36px}
code,.mono{font-family:var(--f-mono);font-size:.92em}
.v{font-family:var(--f-mono);font-size:.92em;white-space:nowrap;font-variant-numeric:tabular-nums}
.red{color:var(--red);font-weight:600}.blk{font-weight:600}
a{color:inherit;text-decoration-color:var(--red);text-underline-offset:3px}

figure{margin:18px 0 20px}
figcaption{font-size:13.5px;color:var(--muted);margin-top:8px;max-width:70ch}
.fig{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:14px;overflow-x:auto}
.fig svg{display:block;width:100%;height:auto;min-width:520px}
.fig.narrow svg{min-width:0}
.fig img{display:block;width:100%;height:auto;border-radius:6px}
svg text{font-family:var(--f-body)}
svg text:not([fill]){fill:var(--ink)}
svg .mono{font-family:var(--f-mono)}
svg text.muted{fill:var(--muted)}

.callout{border-left:3px solid var(--warn);background:var(--wash);padding:12px 16px;border-radius:0 8px 8px 0;margin:16px 0;max-width:68ch}
.callout.stop{border-color:var(--red)}
.callout strong{display:block;font-family:var(--f-display);font-size:15px;letter-spacing:.02em;margin-bottom:2px}

ol.steps{list-style:none;padding:0;margin:14px 0;counter-reset:s;display:grid;gap:12px}
ol.steps>li{counter-increment:s;display:grid;grid-template-columns:34px minmax(0,1fr);gap:12px}
ol.steps>li::before{content:counter(s);font-family:var(--f-mono);font-size:13px;width:28px;height:28px;border-radius:50%;border:1.5px solid var(--ink);display:grid;place-items:center;margin-top:1px}
ol.steps b{font-weight:600}

.leads{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:16px 0}
.lead{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:14px 16px;min-width:0}
.lead .tag{font-family:var(--f-display);font-weight:800;font-size:26px;line-height:1;display:flex;align-items:center;gap:10px}
.lead .tag small{font-family:var(--f-body);font-weight:500;font-size:14px;color:var(--muted)}
.lead dl{display:grid;grid-template-columns:76px minmax(0,1fr);gap:4px 10px;margin:10px 0 0;font-size:14.5px}
.lead dt{color:var(--muted)}.lead dd{margin:0}
.chip{display:inline-block;font-family:var(--f-mono);font-size:11.5px;padding:1px 7px;border-radius:99px;background:var(--xt);color:var(--xt-ink);font-weight:500;vertical-align:2px}

ul.parts{list-style:none;padding:0;margin:12px 0;display:grid;gap:0;border-top:1px solid var(--rule)}
ul.parts li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 16px;padding:10px 0;border-bottom:1px solid var(--rule)}
ul.parts .what{font-weight:600}
ul.parts .note{grid-column:1/-1;font-size:14px;color:var(--muted)}
ul.parts .qty{font-family:var(--f-mono);font-size:13px;color:var(--muted)}

.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
button,.seg label{font:inherit;font-size:16px;border:1.5px solid var(--ink);background:var(--paper);color:var(--ink);border-radius:99px;padding:6px 14px;cursor:pointer;line-height:1.3}
button:hover{background:var(--wash)}
button:focus-visible,.seg input:focus-visible+span{outline:2px solid var(--red);outline-offset:2px}
button.primary{background:var(--ink);color:var(--bg)}
button[aria-pressed="true"]{background:var(--ink);color:var(--bg)}
.seg{display:inline-flex;border:1.5px solid var(--ink);border-radius:99px;overflow:hidden}
.seg label{border:0;border-radius:0;padding:0;display:block}
.seg input{position:absolute;opacity:0;pointer-events:none;font-size:16px}
.seg span{display:block;padding:6px 12px}
.seg input:checked+span{background:var(--ink);color:var(--bg)}
.ctl-label{font-size:13px;color:var(--muted);margin-right:2px}

.step-caption{min-height:3.2em;margin-top:10px;font-size:15px}
.step-caption b{font-family:var(--f-display)}
.dots{display:flex;gap:6px;margin-left:auto}
.dots i{width:8px;height:8px;border-radius:50%;background:var(--rule)}
.dots i.on{background:var(--red)}

.result{display:flex;align-items:center;gap:12px;margin-top:12px;padding:10px 14px;border-radius:8px;background:var(--wash);font-size:15px}
.result .lamp{width:16px;height:16px;border-radius:50%;background:var(--rule);flex:none;transition:background .15s}
.result.beep .lamp{background:var(--ok);box-shadow:0 0 0 4px color-mix(in srgb,var(--ok) 25%,transparent)}
.lcd{font-family:var(--f-mono);font-size:34px;font-variant-numeric:tabular-nums;background:var(--pcb);color:#d7f5c8;border-radius:8px;padding:8px 16px;min-width:150px;text-align:right;letter-spacing:.02em}
.meter{display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin-top:12px}
.meter .verdict{font-size:15px;max-width:40ch}
.meter .verdict b{display:block;font-family:var(--f-display)}
.verdict.good b{color:var(--ok)}.verdict.bad b{color:var(--red)}

.check{list-style:none;padding:0;margin:12px 0;display:grid;gap:8px}
.check label{display:flex;gap:12px;align-items:flex-start;background:var(--paper);border:1px solid var(--rule);border-radius:8px;padding:10px 14px;cursor:pointer}
.check input{font-size:16px;width:20px;height:20px;margin-top:3px;accent-color:var(--ok);flex:none}
.check input:checked+span{color:var(--muted);text-decoration:line-through;text-decoration-color:var(--ok)}
.progress{font-family:var(--f-mono);font-size:13px;color:var(--muted)}

.gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.gallery figure{margin:0}
.twocol{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;align-items:start}

/* animation */
.flow{stroke-dasharray:5 13;animation:flow 0.9s linear infinite;opacity:0;transition:opacity .25s}
.on .flow{opacity:1}
@keyframes flow{to{stroke-dashoffset:-18}}
.rocker{transition:transform .25s;transform-box:fill-box;transform-origin:center}
.on .rocker{transform:rotate(-14deg)}
.vread{transition:opacity .2s}
.mate{animation:mate 3.2s ease-in-out infinite}
@keyframes mate{0%,12%{transform:translateX(0)}45%,72%{transform:translateX(58px)}100%{transform:translateX(0)}}
.cupanim *{transition:all .6s ease}
@media (prefers-reduced-motion: reduce){
  .flow,.mate{animation:none}.cupanim *,.rocker{transition:none}
}
@media (max-width:900px){
  .wrap{grid-template-columns:minmax(0,1fr)}
  nav.toc{position:static;padding-top:24px}
  nav.toc ol{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:600px){
  .leads,.gallery,.twocol{grid-template-columns:minmax(0,1fr)}
  h2{font-size:24px}
  .lcd{font-size:28px;min-width:0}
  nav.toc ol{grid-template-columns:minmax(0,1fr)}
}
</style>

<div class="wrap">
<nav class="toc" aria-label="Sections">
  <div class="eyebrow" style="padding:0 8px 8px">On this page</div>
  <ol>
    <li><a href="#overview"><span class="n">00</span>What you are building</a></li>
    <li><a href="#interface"><span class="n">01</span>The robot side</a></li>
    <li><a href="#parts"><span class="n">02</span>Parts and tools</a></li>
    <li><a href="#polarity"><span class="n">03</span>Mark polarity</a></li>
    <li><a href="#cups"><span class="n">04</span>Solder a plug</a></li>
    <li><a href="#switch"><span class="n">05</span>Switch lead S</a></li>
    <li><a href="#dfr"><span class="n">06</span>DFR1202 leads</a></li>
    <li><a href="#meter"><span class="n">07</span>Meter checks</a></li>
    <li><a href="#assemble"><span class="n">08</span>Assemble the box</a></li>
    <li><a href="#mount"><span class="n">09</span>Mount and swap</a></li>
    <li><a href="#safety"><span class="n">10</span>LiPo safety</a></li>
    <li><a href="#handoff"><span class="n">11</span>Hand-off checklist</a></li>
  </ol>
</nav>

<main>
<header class="hero" id="overview">
  <div class="eyebrow">MicroDuck · battery backpack · build guide for teammates</div>
  <h1>Build the battery backpack</h1>
  <p class="lede">A small printed box on the duck's back that holds a 2S LiPo, an on/off switch and a 5 V converter. It plugs into the robot with two connectors, so we can swap between the desk supply and the battery in under a minute.</p>

  <figure>
    <div class="fig" id="flowfig">
      <svg viewBox="0 0 1000 330" role="img" aria-labelledby="flowT">
        <title id="flowT">Power path: battery, plug 1, switch lead S, plug 2, DFR1202, then plug 3 to the servos and plug 4 to the A7Z computer</title>
        <!-- robot zone -->
        <rect x="826" y="14" width="164" height="300" rx="10" fill="none" stroke="var(--muted)" stroke-dasharray="5 5"/>
        <text x="908" y="36" text-anchor="middle" font-size="12" class="mono muted">ROBOT</text>
        <!-- backpack zone -->
        <rect x="14" y="14" width="796" height="300" rx="10" fill="none" stroke="var(--red)" stroke-opacity=".5" stroke-dasharray="5 5"/>
        <text x="30" y="36" font-size="12" class="mono" fill="var(--red)">BATTERY BACKPACK · you build this</text>

        <!-- battery -->
        <rect x="34" y="140" width="118" height="96" rx="8" fill="var(--wash)" stroke="var(--ink)" stroke-width="1.5"/>
        <text x="93" y="176" text-anchor="middle" font-size="15" font-weight="700">2S LiPo</text>
        <text x="93" y="196" text-anchor="middle" font-size="12" class="muted">Tattu 650 mAh</text>
        <text x="93" y="216" text-anchor="middle" font-size="12" class="mono muted">6.6–8.4 V</text>
        <path d="M152,188 H190" stroke="var(--blk)" stroke-width="7" stroke-linecap="round" fill="none"/>
        <path class="flow" d="M152,188 H190" stroke="var(--live)" stroke-width="3" fill="none"/>
        <!-- plug 1 -->
        <rect x="190" y="174" width="38" height="28" rx="5" fill="var(--xt)" stroke="var(--xt-ink)"/>
        <text x="209" y="193" text-anchor="middle" font-size="13" font-weight="700" fill="var(--xt-ink)">1</text>
        <text x="209" y="222" text-anchor="middle" font-size="11" class="mono muted">XT30</text>

        <!-- switch lead S: red through switch, black straight -->
        <path d="M228,183 H258 V96 H300" stroke="var(--red)" stroke-width="4" fill="none"/>
        <path d="M366,96 H404 V183 H436" stroke="var(--red)" stroke-width="4" fill="none"/>
        <path d="M228,195 H436" stroke="var(--blk)" stroke-width="4" fill="none"/>
        <path class="flow" d="M228,183 H258 V96 H300" stroke="var(--live)" stroke-width="2" fill="none"/>
        <path class="flow" d="M366,96 H404 V183 H436" stroke="var(--live)" stroke-width="2" fill="none"/>
        <rect x="300" y="74" width="66" height="44" rx="6" fill="var(--pcb)"/>
        <rect class="rocker" x="312" y="62" width="42" height="16" rx="4" fill="var(--blk)" stroke="var(--ink)"/>
        <text x="333" y="102" text-anchor="middle" font-size="11" fill="#fff" class="mono">S</text>
        <text x="333" y="138" text-anchor="middle" font-size="12" class="muted">switch lead S</text>
        <text x="333" y="216" text-anchor="middle" font-size="11" class="muted">black runs straight past the switch</text>

        <!-- plug 2 -->
        <rect x="436" y="174" width="38" height="28" rx="5" fill="var(--xt)" stroke="var(--xt-ink)"/>
        <text x="455" y="193" text-anchor="middle" font-size="13" font-weight="700" fill="var(--xt-ink)">2</text>
        <text x="455" y="222" text-anchor="middle" font-size="11" class="mono muted">XT30</text>

        <!-- lead C -->
        <path d="M474,188 H560" stroke="var(--blk)" stroke-width="7" stroke-linecap="round" fill="none"/>
        <path class="flow" d="M474,188 H560" stroke="var(--live)" stroke-width="3" fill="none"/>
        <text x="520" y="178" text-anchor="middle" font-size="13" font-weight="700">C</text>
        <!-- lead D branch from the VIN/GND pads -->
        <path d="M576,150 V70 H762" stroke="var(--blk)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path class="flow" d="M576,150 V70 H762" stroke="var(--live)" stroke-width="3" fill="none"/>
        <text x="668" y="60" text-anchor="middle" font-size="13" font-weight="700">D</text>
        <text x="668" y="92" text-anchor="middle" font-size="11" class="muted">battery voltage, no converter</text>
        <!-- DFR1202 -->
        <rect x="560" y="150" width="130" height="96" rx="6" fill="var(--pcb)"/>
        <rect x="560" y="160" width="10" height="14" fill="var(--pad)"/><rect x="560" y="191" width="10" height="14" fill="var(--pad)"/><rect x="560" y="222" width="10" height="14" fill="var(--pad)"/>
        <text x="630" y="194" text-anchor="middle" font-size="14" font-weight="700" fill="#fff">DFR1202</text>
        <text x="630" y="213" text-anchor="middle" font-size="11" fill="#c9d2d4" class="mono">→ 5.0 V</text>
        <!-- lead E -->
        <path d="M690,228 H762" stroke="var(--blk)" stroke-width="7" stroke-linecap="round" fill="none"/>
        <path class="flow" d="M690,228 H762" stroke="var(--live)" stroke-width="3" fill="none"/>
        <text x="726" y="218" text-anchor="middle" font-size="13" font-weight="700">E</text>

        <!-- plug 3 (XT30 female in backpack, male on robot) -->
        <rect x="762" y="56" width="38" height="28" rx="5" fill="var(--xt)" stroke="var(--xt-ink)"/>
        <text x="781" y="75" text-anchor="middle" font-size="13" font-weight="700" fill="var(--xt-ink)">3</text>
        <rect x="800" y="58" width="36" height="24" rx="4" fill="var(--xt)" stroke="var(--xt-ink)" opacity=".75"/>
        <text x="781" y="108" text-anchor="middle" font-size="11" class="mono muted">XT30</text>
        <!-- plug 4 (MR30) -->
        <rect x="762" y="216" width="38" height="24" rx="5" fill="var(--xt)" stroke="var(--xt-ink)"/>
        <text x="781" y="233" text-anchor="middle" font-size="13" font-weight="700" fill="var(--xt-ink)">4</text>
        <rect x="800" y="218" width="36" height="20" rx="4" fill="var(--xt)" stroke="var(--xt-ink)" opacity=".75"/>
        <text x="781" y="262" text-anchor="middle" font-size="11" class="mono muted">MR30</text>

        <!-- robot leads -->
        <path d="M836,70 H858" stroke="var(--blk)" stroke-width="7" stroke-linecap="round"/>
        <path class="flow" d="M836,70 H858" stroke="var(--live)" stroke-width="3"/>
        <text x="866" y="66" font-size="13" font-weight="700">OpenRB J4</text>
        <text x="866" y="84" font-size="11" class="muted">all 15 servos</text>
        <path d="M836,228 H858" stroke="var(--blk)" stroke-width="7" stroke-linecap="round"/>
        <path class="flow" d="M836,228 H858" stroke="var(--live)" stroke-width="3"/>
        <text x="866" y="224" font-size="13" font-weight="700">A7Z head</text>
        <text x="866" y="242" font-size="11" class="muted">header pins 2 + 6</text>

        <!-- live voltage readouts -->
        <g class="vread">
          <rect x="866" y="104" width="96" height="30" rx="5" fill="var(--pcb)"/>
          <text id="v3" x="914" y="125" text-anchor="middle" font-size="16" class="mono" fill="#d7f5c8">0.00 V</text>
          <rect x="866" y="262" width="96" height="30" rx="5" fill="var(--pcb)"/>
          <text id="v4" x="914" y="283" text-anchor="middle" font-size="16" class="mono" fill="#d7f5c8">0.00 V</text>
        </g>
      </svg>
      <div class="controls">
        <button id="flowBtn" class="primary" aria-pressed="false">Turn the switch on</button>
        <span class="ctl-label">Each thick line is one red + black pair. Plug numbers 1–4 match chapter 11 of the assembly guide.</span>
      </div>
    </div>
    <figcaption>The whole backpack. Servos run straight from the battery (6.6–8.4 V); the A7Z computer gets a regulated 5.0 V from the DFR1202. One switch cuts both.</figcaption>
  </figure>

  <p>You will make <b>four short leads</b> (S, C, D, E), put them with the battery into the printed box, and check every plug with a multimeter. Nothing on the robot itself gets cut, soldered or rewired.</p>
  <div class="callout stop"><strong>Before you start</strong>A LiPo can catch fire if its leads touch or the pack is crushed. Keep the battery unplugged and away from the iron until section 7, and never solder anything that is connected to it.</div>
</header>

<section id="interface">
  <h2><span class="sn">01</span>The robot side: what you plug into</h2>
  <p>The robot already has exactly two power leads coming out behind its electronics pack. Your backpack has to supply both, through the matching plug halves. All the wiring logic lives in the backpack, so the desk supply and the battery look identical to the robot.</p>
  <div class="leads">
    <div class="lead">
      <div class="tag">J4 <small>servo power</small></div>
      <dl><dt>Wires</dt><dd>red + black pair from the OpenRB-150 board's J4 terminal</dd>
      <dt>Ends in</dt><dd><span class="chip">XT30 male</span> (pins)</dd>
      <dt>Wants</dt><dd>6.6–8.4 V, about 1.3 A walking, 8 A peaks</dd>
      <dt>Mates</dt><dd>your plug 3 (lead D)</dd></dl>
    </div>
    <div class="lead">
      <div class="tag">A7Z <small>head computer</small></div>
      <dl><dt>Wires</dt><dd>red + black pair from header pin 2 (5 V) and pin 6 (GND)</dd>
      <dt>Ends in</dt><dd><span class="chip">MR30 male</span>, outer two pins only</dd>
      <dt>Wants</dt><dd>4.95–5.05 V, up to about 2.2 A</dd>
      <dt>Mates</dt><dd>your plug 4 (lead E)</dd></dl>
    </div>
  </div>
  <p>XT30 and MR30 have different shapes and cannot be plugged into each other. That is on purpose: battery voltage can never reach the 5 V computer by mistake.</p>
</section>

<section id="parts">
  <h2><span class="sn">02</span>Parts and tools</h2>
  <p>Everything below is already in hand. Ask Shawn for anything you cannot find.</p>
  <ul class="parts">
    <li><span class="what">Battery backpack frame and cap (V1.20 print, orange)</span><span class="qty">1 + 1</span><span class="note">Frame has a 12.3 × 27.5 mm hole in its floor for the switch.</span></li>
    <li><span class="what">Tattu 2S 650 mAh 75C LiPo with XT30</span><span class="qty">2</span><span class="note">57 × 31 × 12 mm, 43 g, 8.4 V full. One in use, one charging.</span></li>
    <li><span class="what">Swann 39 rocker switch</span><span class="qty">1</span><span class="note">Single pole, two bare solder lugs, no leads. Rated 15 A.</span></li>
    <li><span class="what">DFRobot DFR1202 5 V buck converter</span><span class="qty">1</span><span class="note">6–24 V in, 5.0 V out. Solder pads only.</span></li>
    <li><span class="what">Amass XT30 pairs (with heat shrink)</span><span class="qty">2 male + 2 female</span><span class="note">From the 10-pair bag. Male = pins, female = sockets.</span></li>
    <li><span class="what">Amass MR30 pair</span><span class="qty">1 female</span><span class="note">Three contacts; you use the two outer ones only.</span></li>
    <li><span class="what">20 or 22 AWG stranded silicone wire, red and black</span><span class="qty">~40 cm each</span><span class="note">Stranded and soft. Not solid core (it snaps at the joint when the robot walks).</span></li>
    <li><span class="what">Heat shrink, 3 mm and 6 mm</span><span class="qty">a few cm</span><span class="note">Plus the 10 mm pieces that come with the XT30s.</span></li>
    <li><span class="what">Foam pads, 2 mm and 1 mm, self-adhesive</span><span class="qty">1 + 1</span><span class="note">One on the converter's inductor, one inside the cap.</span></li>
    <li><span class="what">Screws: M2 × 6 and M2 × 8</span><span class="qty">4 + 3</span><span class="note">M2 × 6 fix the box to the robot, M2 × 8 hold the cap.</span></li>
  </ul>
  <p><b>Tools:</b> soldering iron at 350–400 °C, rosin-core solder, flux, wire stripper, flush cutters, helping hands, heat gun (or a lighter held well away), multimeter with continuity beep, paint pen or marker, a small Phillips driver no thicker than 3 mm.</p>
  <figure class="twocol">
    <div class="fig narrow"><img src="{{IMG:swann}}" alt="Swann 39 rocker switch seen from the side, two solder lugs on the left, snap wings top and bottom"></div>
    <figcaption style="margin:0">The Swann 39 switch from the RoboClub bin. The two lugs on the left are where the red wires go (either way round). The plastic wings at top and bottom snap it into the floor of the box. Photo: Shawn, 2026-10-17.</figcaption>
  </figure>
</section>

<section id="polarity">
  <h2><span class="sn">03</span>Mark polarity before you solder anything</h2>
  <p>XT30 and MR30 housings have no reliable + marking you can see while soldering. So mark every plug with a paint dot on its + side first. Then the rule is simple: <span class="red">red wire</span> goes into the cup under the dot, <span class="blk">black</span> into the other.</p>
  <figure>
    <div class="fig">
      <svg viewBox="0 0 640 210" role="img" aria-labelledby="dotT">
        <title id="dotT">A male and a female plug slide together; their paint dots line up on the same side</title>
        <text x="20" y="28" font-size="13" font-weight="700">Correct: dots on the same side after mating</text>
        <g class="mate">
          <path d="M60,62 H150 L164,72 V116 L150,126 H60 Z" fill="var(--xt)" stroke="var(--xt-ink)"/>
          <rect x="164" y="80" width="26" height="8" rx="2" fill="var(--pad)"/><rect x="164" y="100" width="26" height="8" rx="2" fill="var(--pad)"/>
          <circle cx="92" cy="74" r="7" fill="var(--red)"/>
          <path d="M20,84 H60" stroke="var(--red)" stroke-width="5"/><path d="M20,104 H60" stroke="var(--blk)" stroke-width="5"/>
          <text x="110" y="150" text-anchor="middle" font-size="12" class="muted">male (pins)</text>
        </g>
        <path d="M262,62 H360 V126 H262 L248,116 V72 Z" fill="var(--xt)" stroke="var(--xt-ink)"/>
        <rect x="250" y="80" width="10" height="8" fill="var(--xt-ink)" opacity=".5"/><rect x="250" y="100" width="10" height="8" fill="var(--xt-ink)" opacity=".5"/>
        <circle cx="330" cy="74" r="7" fill="var(--red)"/>
        <path d="M360,84 H400" stroke="var(--red)" stroke-width="5"/><path d="M360,104 H400" stroke="var(--blk)" stroke-width="5"/>
        <text x="304" y="150" text-anchor="middle" font-size="12" class="muted">female (sockets)</text>
        <g transform="translate(430,40)">
          <text x="0" y="22" font-size="13" font-weight="700">The reference</text>
          <text x="0" y="44" font-size="12.5" class="muted">XT30: the battery's own plug.</text>
          <text x="0" y="62" font-size="12.5" class="muted">Its red wire side is +.</text>
          <text x="0" y="88" font-size="12.5" class="muted">MR30: the robot's A7Z plug.</text>
          <text x="0" y="106" font-size="12.5" class="muted">Copy the dot Shawn put on it.</text>
        </g>
        <text x="20" y="194" font-size="12.5" class="muted">If the dots end up on opposite sides, every meter reading later comes out negative.</text>
      </svg>
    </div>
  </figure>
  <ol class="steps">
    <li><div><b>XT30 males</b> (for lead C and the battery end of S): plug each onto the battery's XT30. Put a dot on the shell on the same side as the battery's red wire. Unplug.</div></li>
    <li><div><b>XT30 females</b> (for lead D and the far end of S): plug each onto a male you just marked. Dot the side facing the male's dot.</div></li>
    <li><div><b>MR30 female</b> (lead E): plug it onto the robot's MR30 male and dot the side facing its dot. The middle contact stays empty.</div></li>
    <li><div>Plug every pair together once more and look: both dots on the same side.</div></li>
  </ol>
</section>

<section id="cups">
  <h2><span class="sn">04</span>Solder a wire into a plug cup</h2>
  <p>Every plug in this build is soldered the same way. The back of each contact is a small open cup. A good joint fills the cup, holds the wire when you tug it, and has no solder bridging to the neighbouring cup.</p>
  <figure>
    <div class="fig">
      <svg viewBox="0 0 640 230" role="img" aria-labelledby="cupT" class="cupanim" id="cupsvg">
        <title id="cupT">Animated cross-section of a solder cup, step by step</title>
        <!-- plug body -->
        <rect x="380" y="70" width="200" height="90" rx="6" fill="var(--xt)" stroke="var(--xt-ink)"/>
        <text x="520" y="186" text-anchor="middle" font-size="12" class="muted">plug, mated to a spare half while you solder</text>
        <!-- cup -->
        <path d="M330,92 H392 V138 H330" fill="none" stroke="var(--pad)" stroke-width="6" stroke-linejoin="round"/>
        <rect id="cupFill" x="333" y="135" width="56" height="0" fill="#b9c0c4"/>
        <!-- wire -->
        <g id="wire" transform="translate(-60,0)">
          <rect x="40" y="108" width="250" height="14" rx="3" fill="var(--red)"/>
          <rect id="strands" x="288" y="110" width="40" height="10" rx="2" fill="#c48a52"/>
          <rect id="tinned" x="288" y="110" width="40" height="10" rx="2" fill="#b9c0c4" opacity="0"/>
          <rect id="shrink" x="120" y="102" width="56" height="26" rx="4" fill="var(--ink)" opacity=".35"/>
        </g>
        <!-- iron -->
        <g id="iron" opacity="0">
          <path d="M300,20 L338,86" stroke="var(--muted)" stroke-width="8" stroke-linecap="round"/>
          <text x="262" y="20" font-size="12" class="muted">iron</text>
        </g>
        <g id="timer" opacity="0"><circle cx="240" cy="60" r="20" fill="none" stroke="var(--ok)" stroke-width="3"/><text x="240" y="65" text-anchor="middle" font-size="13" class="mono">3 s</text></g>
        <text id="cupStepNo" x="20" y="30" font-size="13" class="mono" fill="var(--red)">STEP 1 / 6</text>
      </svg>
      <div class="step-caption" id="cupCap"></div>
      <div class="controls">
        <button id="cupPrev" aria-label="Previous step">Back</button>
        <button id="cupNext" aria-label="Next step">Next</button>
        <button id="cupPlay" aria-pressed="false">Play</button>
        <div class="dots" id="cupDots"></div>
      </div>
    </div>
  </figure>
  <div class="callout"><strong>Quick test after every plug</strong>Set the meter to continuity (beep). Touch the two contacts of the same plug: it must stay silent. A beep means solder bridged the two cups.</div>
</section>

<section id="switch">
  <h2><span class="sn">05</span>Build the switch lead S</h2>
  <p>The switch interrupts only the <span class="red">red</span> wire. The <span class="blk">black</span> wire runs straight from one plug to the other and never touches the switch. The battery end gets an XT30 <b>male</b> (it mates the battery's female plug 1); the other end gets an XT30 <b>female</b> (plug 2, for lead C).</p>
  <figure>
    <div class="fig">
      <svg viewBox="0 0 720 220" role="img" aria-labelledby="sT">
        <title id="sT">Switch lead S: XT30 male, two red wires through the switch lugs, one black wire straight, XT30 female</title>
        <!-- male -->
        <path d="M40,80 H112 L124,88 V132 L112,140 H40 Z" fill="var(--xt)" stroke="var(--xt-ink)"/>
        <circle cx="70" cy="92" r="6" fill="var(--red)"/>
        <text x="82" y="166" text-anchor="middle" font-size="12" font-weight="700">XT30 male</text>
        <text x="82" y="182" text-anchor="middle" font-size="11" class="muted">to battery · plug 1</text>
        <!-- red 1 -->
        <path d="M124,98 H190 V50 H290" stroke="var(--red)" stroke-width="5" fill="none"/>
        <text x="220" y="40" text-anchor="middle" font-size="12" class="mono">red 6 cm</text>
        <!-- switch -->
        <rect x="290" y="22" width="140" height="56" rx="6" fill="var(--pcb)"/>
        <circle cx="304" cy="50" r="8" fill="none" stroke="var(--pad)" stroke-width="4"/>
        <circle cx="416" cy="50" r="8" fill="none" stroke="var(--pad)" stroke-width="4"/>
        <rect x="292" y="40" width="22" height="20" rx="3" fill="var(--ink)" opacity=".4"/>
        <rect x="406" y="40" width="22" height="20" rx="3" fill="var(--ink)" opacity=".4"/>
        <text x="360" y="54" text-anchor="middle" font-size="12" fill="#fff">Swann 39</text>
        <text x="360" y="96" text-anchor="middle" font-size="11" class="muted">heat shrink over each lug</text>
        <!-- red 2 -->
        <path d="M430,50 H530 V98 H596" stroke="var(--red)" stroke-width="5" fill="none"/>
        <text x="500" y="40" text-anchor="middle" font-size="12" class="mono">red 6 cm</text>
        <!-- black -->
        <path d="M124,122 H596" stroke="var(--blk)" stroke-width="5" fill="none"/>
        <text x="360" y="142" text-anchor="middle" font-size="12" class="mono">black 12 cm, straight through</text>
        <!-- female -->
        <path d="M608,80 H680 V140 H608 L596,132 V88 Z" fill="var(--xt)" stroke="var(--xt-ink)"/>
        <circle cx="650" cy="92" r="6" fill="var(--red)"/>
        <text x="638" y="166" text-anchor="middle" font-size="12" font-weight="700">XT30 female</text>
        <text x="638" y="182" text-anchor="middle" font-size="11" class="muted">to lead C · plug 2</text>
        <text x="20" y="210" font-size="12" class="muted">Red dots = the paint dots from section 3. Red wires go into the dotted cups.</text>
      </svg>
    </div>
  </figure>
  <ol class="steps">
    <li><div><b>Cut:</b> two red pieces of 6 cm, one black piece of 12 cm. Strip 5 mm at each end, twist, tin.</div></li>
    <li><div><b>Slide on heat shrink first:</b> a 15 mm piece of 3 mm tube on each red wire (push it to the middle, away from the heat), and the 10 mm XT30 pieces on all wire ends that go into plugs.</div></li>
    <li><div><b>Solder the lugs:</b> clamp the switch lugs up. Hook one red wire through each lug hole, bend it back, and heat for 2–3 seconds while feeding solder. Then stop. The switch body is plastic; heating too long softens it and the rocker sticks.</div></li>
    <li><div><b>Cover the lugs:</b> once cool, slide each 3 mm tube over its lug and shrink it. The lugs are close together, so each needs its own tube.</div></li>
    <li><div><b>Male XT30 (battery end):</b> red wire from lug 1 into the dotted cup, one end of the black into the other cup.</div></li>
    <li><div><b>Female XT30 (plug 2 end):</b> red wire from lug 2 into the dotted cup, the other end of the black into the other cup. Finish both plugs as in section 4.</div></li>
  </ol>
  <h3>Check it with the continuity beep</h3>
  <p>Try it here first to see what the meter should do, then do the same on your real lead.</p>
  <div class="fig narrow" style="padding:16px">
    <div class="controls" style="margin-top:0">
      <span class="ctl-label">Rocker:</span>
      <div class="seg" role="radiogroup" aria-label="Rocker position">
        <label><input type="radio" name="rk" id="rkA" value="a" checked><span>pressed side A</span></label>
        <label><input type="radio" name="rk" id="rkB" value="b"><span>pressed side B</span></label>
      </div>
    </div>
    <div class="controls">
      <span class="ctl-label">Probes on:</span>
      <div class="seg" role="radiogroup" aria-label="Probe pair">
        <label><input type="radio" name="pp" id="ppBB" value="bb" checked><span>− to −</span></label>
        <label><input type="radio" name="pp" id="ppRR" value="rr"><span>+ to +</span></label>
        <label><input type="radio" name="pp" id="ppRB" value="rb"><span>+ to − (same plug)</span></label>
      </div>
    </div>
    <div class="result" id="ctResult" aria-live="polite"><span class="lamp"></span><span id="ctText"></span></div>
  </div>
  <p style="margin-top:12px">Whichever rocker side makes <b>+ to +</b> beep is ON. Mark it with a marker on the rocker face. In the box the rocker faces down, so you press it from under the backpack.</p>
</section>

<section id="dfr">
  <h2><span class="sn">06</span>Solder leads C, D and E to the DFR1202</h2>
  <p>Three pairs land on three pads on the board's edge. Leads C (from the switch) and D (to the servos) share the VIN and GND pads: the servo current passes through those two joints, so make them solid. Lead E takes the 5 V from VOUT.</p>
  <figure>
    <div class="fig">
      <svg viewBox="0 0 700 330" role="img" aria-labelledby="dT">
        <title id="dT">DFR1202 pad map: VIN gets two red wires, GND three black wires, VOUT one red wire; EN, AGND and PGOOD stay empty</title>
        <!-- board -->
        <rect x="250" y="40" width="250" height="240" rx="10" fill="var(--pcb)"/>
        <path d="M250,62 h14 a10,10 0 0 1 0,20 h-14 Z" fill="var(--pad)"/>
        <path d="M250,150 h14 a10,10 0 0 1 0,20 h-14 Z" fill="var(--pad)"/>
        <path d="M250,238 h14 a10,10 0 0 1 0,20 h-14 Z" fill="var(--pad)"/>
        <text x="276" y="77" font-size="15" font-weight="700" fill="#fff">VIN</text>
        <text x="276" y="165" font-size="15" font-weight="700" fill="#fff">GND</text>
        <text x="276" y="253" font-size="15" font-weight="700" fill="#fff">VOUT</text>
        <path d="M500,66 h-10 a8,8 0 0 0 0,16 h10 Z" fill="var(--pad)" opacity=".5"/>
        <path d="M500,96 h-10 a8,8 0 0 0 0,16 h10 Z" fill="var(--pad)" opacity=".5"/>
        <path d="M500,126 h-10 a8,8 0 0 0 0,16 h10 Z" fill="var(--pad)" opacity=".5"/>
        <text x="482" y="79" text-anchor="end" font-size="12" fill="#c9d2d4">EN</text>
        <text x="482" y="109" text-anchor="end" font-size="12" fill="#c9d2d4">AGND</text>
        <text x="482" y="139" text-anchor="end" font-size="12" fill="#c9d2d4">PGOOD</text>
        <rect x="380" y="170" width="100" height="94" rx="6" fill="#596266"/>
        <text x="430" y="222" text-anchor="middle" font-size="11" fill="#e6ebea">inductor</text>
        <text x="430" y="238" text-anchor="middle" font-size="10" fill="#e6ebea">(2 mm foam here)</text>
        <text x="520" y="110" font-size="12" class="muted">leave empty</text>
        <path d="M515,106 h-10" stroke="var(--muted)"/>
        <!-- wires -->
        <path d="M30,64 H250" stroke="var(--red)" stroke-width="5"/>
        <path d="M30,80 H250" stroke="var(--red)" stroke-width="5"/>
        <text x="30" y="56" font-size="12.5"><tspan font-weight="700">C</tspan> red · from switch</text>
        <text x="30" y="100" font-size="12.5"><tspan font-weight="700">D</tspan> red · to servos</text>
        <path d="M30,150 H250" stroke="var(--blk)" stroke-width="5"/>
        <path d="M30,160 H250" stroke="var(--blk)" stroke-width="5"/>
        <path d="M30,170 H250" stroke="var(--blk)" stroke-width="5"/>
        <text x="30" y="140" font-size="12.5"><tspan font-weight="700">C D E</tspan> black · all three</text>
        <path d="M30,248 H250" stroke="var(--red)" stroke-width="5"/>
        <text x="30" y="240" font-size="12.5"><tspan font-weight="700">E</tspan> red · 5 V out</text>
        <text x="30" y="306" font-size="12" class="muted">All wires leave outward from the pad edge, never across the board.</text>
      </svg>
    </div>
    <figcaption>Drawing of the DFR1202 top face (pads on the left edge, as on the real board). In the box it stands on that edge, pads at the bottom.</figcaption>
  </figure>
  <div class="leads">
    <div class="lead"><div class="tag">C <small>feed in</small></div><dl><dt>Plug</dt><dd><span class="chip">XT30 male</span> → mates plug 2 on S</dd><dt>Length</dt><dd><span class="v">~80 mm</span></dd><dt>Pads</dt><dd>red VIN, black GND</dd></dl></div>
    <div class="lead"><div class="tag">D <small>servo out</small></div><dl><dt>Plug</dt><dd><span class="chip">XT30 female</span> = plug 3</dd><dt>Length</dt><dd><span class="v">~100 mm</span></dd><dt>Pads</dt><dd>red VIN, black GND</dd></dl></div>
    <div class="lead"><div class="tag">E <small>5 V out</small></div><dl><dt>Plug</dt><dd><span class="chip">MR30 female</span> = plug 4, outer contacts</dd><dt>Length</dt><dd><span class="v">~100 mm</span></dd><dt>Pads</dt><dd>red VOUT, black GND</dd></dl></div>
    <div class="lead"><div class="tag">— <small>not used</small></div><dl><dt>Pads</dt><dd>EN, AGND, PGOOD</dd><dt>Why</dt><dd>EN floating = always on, which is what we want.</dd></dl></div>
  </div>
  <ol class="steps">
    <li><div><b>Plugs first.</b> Solder the plug end of C, D and E as in section 4 (slide the MR30's black boot onto E's wires before soldering). Strip the free ends 4 mm and tin them.</div></li>
    <li><div><b>Tin the pads.</b> Clamp the board flat and put a layer of solder on VIN, GND and VOUT.</div></li>
    <li><div><b>VIN:</b> twist C red and D red together, tin them as one, lay them flat on the pad and press the iron down until both solders flow together.</div></li>
    <li><div><b>GND:</b> solder C black and D black together first, then add E black beside them. All three must sit in one blob of solder.</div></li>
    <li><div><b>VOUT:</b> E red.</div></li>
    <li><div><b>Pull test and short test.</b> Once cool, tug each wire: nothing moves. Continuity mode: VIN–GND and VOUT–GND must not beep steadily (a short chirp is the input capacitor charging, that is fine). VIN–VOUT must not beep.</div></li>
  </ol>
  <div class="callout"><strong>Why VIN and GND matter most</strong>All servo current flows through those two joints: about 1 A while walking and around 8 A for a fraction of a second when the duck stands up. A dull, grainy joint will warm up. Make them shiny and full.</div>
</section>

<section id="meter">
  <h2><span class="sn">07</span>Meter checks before anything touches the robot</h2>
  <p>Do this with the battery and the multimeter only, on the bench, outside the box. Red probe in the dotted side, black probe in the other side.</p>
  <ol class="steps">
    <li><div><b>No battery, continuity mode:</b> across plug 3 (D) and across plug 4 (E): no steady beep.</div></li>
    <li><div><b>Switch OFF.</b> Plug the battery into S (plug 1) and S into C (plug 2). DC volts: plug 3 reads 0 V.</div></li>
    <li><div><b>Switch ON.</b> Read plug 3 and plug 4. Compare with the simulator below.</div></li>
    <li><div><b>Switch OFF</b> again before you go on.</div></li>
  </ol>
  <div class="fig narrow" style="padding:16px">
    <div class="controls" style="margin-top:0">
      <span class="ctl-label">Plug:</span>
      <div class="seg" role="radiogroup" aria-label="Plug to measure">
        <label><input type="radio" name="mp" id="mp3" value="3" checked><span>3 · XT30 (D)</span></label>
        <label><input type="radio" name="mp" id="mp4" value="4"><span>4 · MR30 (E)</span></label>
      </div>
      <span class="ctl-label">Switch:</span>
      <div class="seg" role="radiogroup" aria-label="Switch">
        <label><input type="radio" name="ms" id="msOff" value="off"><span>off</span></label>
        <label><input type="radio" name="ms" id="msOn" value="on" checked><span>on</span></label>
      </div>
      <span class="ctl-label">Wiring:</span>
      <div class="seg" role="radiogroup" aria-label="Wiring">
        <label><input type="radio" name="mw" id="mwOk" value="ok" checked><span>correct</span></label>
        <label><input type="radio" name="mw" id="mwRev" value="rev"><span>dot reversed</span></label>
      </div>
    </div>
    <div class="meter">
      <div class="lcd" id="lcd" aria-live="polite">8.12</div>
      <div class="verdict good" id="verdict"><b>Pass</b>Battery voltage, 7.0–8.4 V for a charged pack.</div>
    </div>
    <p style="font-size:13px;color:var(--muted);margin:10px 0 0">Example readings for a freshly charged pack. Your number will differ; the range is what counts.</p>
  </div>
  <div class="callout stop"><strong>Negative number?</strong>Stop. A paint dot or a wire is reversed. Fix it before the backpack goes anywhere near the robot: reversed 5 V destroys the A7Z.</div>
</section>

<section id="assemble">
  <h2><span class="sn">08</span>Assemble the backpack</h2>
  <p>Order matters: the switch goes in from below, the converter from behind, and the leads must already be soldered because the plugs pass through holes in the print.</p>
  <ol class="steps">
    <li><div><b>Switch into the floor, rocker down.</b> Hold the frame upside down. Feed both XT30 plugs of S up through the 12.3 × 27.5 mm floor hole, then push the switch body after them until both snap wings click over the panel. Press on the body, not the rocker. The rocker ends flush in its pocket.</div></li>
    <li><div><b>Foam on the inductor.</b> Stick the 2 mm pad on the DFR1202's big grey inductor. It rests against the battery later and stops rattling.</div></li>
    <li><div><b>Plugs 3 and 4 out the front window.</b> From inside, push D's XT30 and E's MR30 out through the flat window in the front plate, about 4 cm. MR30 dot facing up.</div></li>
    <li><div><b>Clip the DFR1202 in.</b> Pads down, components towards you, VIN end on the stop side. Slide it straight forward from the open back until it sits on the two ribs, then press its long edges past the flexible lips until they click. Do not over-bend the lips.</div></li>
    <li><div><b>Plug C into S</b> (plug 2) and tuck it into the space on the robot's left side of the battery bay. It stays plugged; it only exists so the switch can be replaced.</div></li>
  </ol>
  <div class="gallery">
    <figure><div class="fig narrow"><img src="{{IMG:side}}" alt="Side see-through render of the backpack: DFR1202 against the front plate, battery upright, switch at the bottom"></div><figcaption>Side view, robot front to the left. Battery stands upright behind the converter; switch at the bottom.</figcaption></figure>
    <figure><div class="fig narrow"><img src="{{IMG:rear}}" alt="Rear see-through render: battery in the middle, plug 1 on the right, plug 2 on the left, balance plug on top"></div><figcaption>From behind. Plug 1 on the robot's right of the battery, plug 2 on its left, balance plug on top.</figcaption></figure>
    <figure><div class="fig narrow"><img src="{{IMG:low}}" alt="Render from below showing the switch rocker flush in a floor pocket and the two lower fixing screws"></div><figcaption>From below. The rocker sits flush in the floor pocket; you press it with a finger from underneath.</figcaption></figure>
    <figure><div class="fig narrow"><img src="{{IMG:swap}}" alt="Render of the two swap plugs standing in the channel behind the OpenRB board"></div><figcaption>Plugs 3 and 4 stand in the channel behind the OpenRB, robot half on top.</figcaption></figure>
  </div>
  <p style="font-size:13.5px;color:var(--muted);margin-top:10px">Renders are from the 2026-10-15 CAD. Your V1.20 print is the same layout with a slightly wider switch hole for the Swann 39.</p>
</section>

<section id="mount">
  <h2><span class="sn">09</span>Mount it and swap power</h2>
  <p>Do the first mount together with Shawn. After that, a swap takes about a minute.</p>
  <ol class="steps">
    <li><div><b>Shut the A7Z down</b> (<code>sudo shutdown -h now</code>), wait 10–15 s, then unplug the desk supply's USB-C.</div></li>
    <li><div><b>Take the desk box off.</b> Remove its cap (four M2 × 10). Lift the top converter off its two lower M2 × 4 and let it hang on its wires, so you can reach the upper cover screws. Remove all four cover screws (M2 × 6, keep them), pull the box back about 4 cm and unplug its XT30 and MR30 from the robot's two leads.</div></li>
    <li><div><b>Plug in the backpack</b> about 4 cm behind the robot: plug 3 onto the robot's XT30, plug 4 onto its MR30. Stand both plugs in the channel.</div></li>
    <li><div><b>Fix the frame</b> with four M2 × 6: the upper two through the empty battery bay, the lower two from behind under the box floor. Start all four, then tighten evenly.</div></li>
    <li><div><b>Battery in.</b> Switch off. Plug the battery into plug 1 outside the box, stand it upright with leads at the top on the robot's right side, slide it in against the foam. Nothing under the battery.</div></li>
    <li><div><b>Cap on.</b> 1 mm foam inside the cap between its two fences, push it straight on, three M2 × 8 from the back.</div></li>
    <li><div><b>Power on</b> by pressing the rocker from below, with someone holding the robot. It may wake up lying on its side; that is normal.</div></li>
  </ol>
  <figure><div class="fig narrow"><img src="{{IMG:out}}" alt="Render showing the cap and battery coming out of the back of the backpack"></div><figcaption>Charging: switch off, three cap screws out, slide the battery out the back, unplug plug 1 outside the box.</figcaption></figure>
  <div class="callout stop"><strong>Two rules for every swap</strong>Swap only with the switch off and the A7Z shut down. Never connect the desk supply and the battery to the robot at the same time.</div>
</section>

<section id="safety">
  <h2><span class="sn">10</span>LiPo safety and charging</h2>
  <ul class="parts">
    <li><span class="what">Charge off the robot, in the LiPo bag, with someone watching</span><span class="note">Use a balance charger on the white JST-XH balance plug. 0.6–0.65 A (1C) is the safe rate for this 650 mAh pack.</span></li>
    <li><span class="what">New packs arrive at storage charge (~3.8 V per cell)</span><span class="note">Charge fully before the first run. Return unused packs to storage charge within a few days.</span></li>
    <li><span class="what">Stop at 6.6 V</span><span class="note">The robot's software warns at 7.0 V and stops at 6.6 V (3.3 V per cell). Going lower damages the pack.</span></li>
    <li><span class="what">Retire a pack that puffs, runs hot, or shows more than 0.05 V between cells</span><span class="note">Check the cells with the LiPo checker after charging.</span></li>
    <li><span class="what">Power off in this order</span><span class="note">A7Z shutdown, wait 10–15 s, hold the robot, then switch off. The servos go limp the instant the switch opens.</span></li>
    <li><span class="what">Never plug a USB-C supply into the A7Z while the backpack powers it</span><span class="note">The header 5 V and the USB-C port are the same wire on that board.</span></li>
  </ul>
</section>

<section id="handoff">
  <h2><span class="sn">11</span>Hand-off checklist</h2>
  <p>Tick these as you go. The ticks stay in your browser only.</p>
  <ul class="check" id="checklist">
    <li><label><input type="checkbox" id="c1"><span>Every plug has a paint dot, and mated pairs show both dots on the same side.</span></label></li>
    <li><label><input type="checkbox" id="c2"><span>No plug beeps between its own two contacts.</span></label></li>
    <li><label><input type="checkbox" id="c3"><span>Switch lead S: − to − always beeps, + to + beeps on one rocker side only, ON side marked.</span></label></li>
    <li><label><input type="checkbox" id="c4"><span>DFR1202: VIN has 2 wires, GND 3, VOUT 1; every wire passes a tug test.</span></label></li>
    <li><label><input type="checkbox" id="c5"><span>Plug 3 reads +7.0 to +8.4 V with the switch on, 0 V off.</span></label></li>
    <li><label><input type="checkbox" id="c6"><span>Plug 4 reads +4.95 to +5.05 V with the switch on.</span></label></li>
    <li><label><input type="checkbox" id="c7"><span>Switch snapped in rocker down; DFR1202 clipped with foam; plugs 3 and 4 out of the front window.</span></label></li>
    <li><label><input type="checkbox" id="c8"><span>Battery unplugged and in the LiPo bag when you hand it over.</span></label></li>
  </ul>
  <p class="progress" id="prog">0 of 8 done</p>
  <p style="font-size:13.5px;color:var(--muted);margin-top:24px">Source: MicroDuck battery plan (decision D-010, 2026-10-15), battery wiring notes and assembly guide chapter 11 (2026-10-17). Questions go to Shawn.</p>
</section>
</main>
</div>

<script>
(function(){
  const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Hero power flow
  const fig = document.getElementById('flowfig'), btn = document.getElementById('flowBtn');
  const v3 = document.getElementById('v3'), v4 = document.getElementById('v4');
  btn.addEventListener('click', () => {
    const on = !fig.classList.contains('on');
    fig.classList.toggle('on', on);
    btn.setAttribute('aria-pressed', on);
    btn.textContent = on ? 'Turn the switch off' : 'Turn the switch on';
    v3.textContent = on ? '8.12 V' : '0.00 V';
    v4.textContent = on ? '5.01 V' : '0.00 V';
  });

  // Solder cup stepper
  const S = [
    ['Slide heat shrink on first.', 'Put the 10 mm tube on the wire and push it well back from the end, so the iron does not shrink it early. On an MR30, slide the black boot on now.'],
    ['Strip 5 mm and tin the wire.', 'Twist the strands tight, dab flux, and coat the tip with a thin layer of solder.'],
    ['Fill the cup two-thirds.', 'Mate the plug to a spare half (keeps the pins straight when the plastic warms), clamp it cup-up, hold the iron on the outside of the cup and feed solder in.'],
    ['Push the wire in while the solder is liquid.', 'Insert the tinned tip all the way to the bottom of the cup. Keep each cup under 3–4 seconds of heat.'],
    ['Hold still for 3 seconds.', 'Take the iron away and do not move the wire until the joint goes from shiny-liquid to solid. A good joint is smooth and wraps the wire.'],
    ['Cover the metal.', 'Slide the heat shrink over the whole cup and shrink it. On an MR30, push the boot up until it clicks onto the housing. Then tug the wire.']
  ];
  const el = id => document.getElementById(id);
  const dots = el('cupDots'); S.forEach(()=>dots.appendChild(document.createElement('i')));
  let k = 0, timer = null;
  function cup(i){
    k = (i + S.length) % S.length;
    const w = el('wire'), fill = el('cupFill');
    const tinned = k >= 1, filled = k >= 2, inserted = k >= 3;
    w.setAttribute('transform', `translate(${inserted ? 60 : -60},0)`);
    el('tinned').setAttribute('opacity', tinned ? 1 : 0);
    fill.setAttribute('y', filled ? 104 : 135);
    fill.setAttribute('height', filled ? 31 : 0);
    el('iron').setAttribute('opacity', (k===2||k===3) ? 1 : 0);
    el('timer').setAttribute('opacity', k===4 ? 1 : 0);
    const sh = el('shrink');
    if (k === 5){ sh.setAttribute('x', 262); sh.setAttribute('width', 80); sh.setAttribute('y', 98); sh.setAttribute('height', 34); sh.setAttribute('opacity', .55); }
    else { sh.setAttribute('x', 120); sh.setAttribute('width', 56); sh.setAttribute('y', 102); sh.setAttribute('height', 26); sh.setAttribute('opacity', .35); }
    el('cupStepNo').textContent = `STEP ${k+1} / ${S.length}`;
    el('cupCap').innerHTML = `<b>${S[k][0]}</b> ${S[k][1]}`;
    [...dots.children].forEach((d,j)=>d.classList.toggle('on', j===k));
  }
  el('cupPrev').onclick = () => { stop(); cup(k-1); };
  el('cupNext').onclick = () => { stop(); cup(k+1); };
  function stop(){ if (timer){ clearInterval(timer); timer=null; el('cupPlay').setAttribute('aria-pressed','false'); el('cupPlay').textContent='Play'; } }
  el('cupPlay').onclick = () => {
    if (timer) return stop();
    el('cupPlay').setAttribute('aria-pressed','true'); el('cupPlay').textContent='Pause';
    timer = setInterval(()=>cup(k+1), 2600);
  };
  cup(0);

  // Continuity tester for S
  function ct(){
    const rk = document.querySelector('input[name=rk]:checked').value;
    const pp = document.querySelector('input[name=pp]:checked').value;
    let beep, msg;
    if (pp === 'bb'){ beep = true; msg = 'Beeps on either rocker side. The black wire runs straight through.'; }
    else if (pp === 'rr'){ beep = rk === 'a'; msg = beep ? 'Beeps: this rocker side is ON. Mark it.' : 'Silent: this rocker side is OFF.'; }
    else { beep = false; msg = 'Must stay silent on both rocker sides. A beep here is a short: find the solder bridge.'; }
    el('ctResult').classList.toggle('beep', beep);
    el('ctText').textContent = (beep ? 'BEEP · ' : 'silent · ') + msg;
  }
  document.querySelectorAll('input[name=rk],input[name=pp]').forEach(i=>i.addEventListener('change', ct)); ct();

  // Meter simulator
  function meter(){
    const p = document.querySelector('input[name=mp]:checked').value;
    const on = document.querySelector('input[name=ms]:checked').value === 'on';
    const rev = document.querySelector('input[name=mw]:checked').value === 'rev';
    let v = !on ? 0 : (p === '3' ? 8.12 : 5.01);
    if (rev) v = -v;
    el('lcd').textContent = (v === 0 ? '0.00' : v.toFixed(2));
    const vd = el('verdict');
    let good, title, text;
    if (!on){ good = true; title = 'Expected with the switch off'; text = 'Both plugs read 0 V. If plug 3 shows battery voltage, the red wire bypasses the switch.'; }
    else if (rev){ good = false; title = 'Fail: reversed'; text = 'A dot or a wire is the wrong way round. Fix it before anything is plugged into the robot.'; }
    else if (p === '3'){ good = true; title = 'Pass'; text = 'Battery voltage: +7.0 to +8.4 V for a charged pack.'; }
    else { good = true; title = 'Pass'; text = 'Regulated 5 V: +4.95 to +5.05 V.'; }
    vd.className = 'verdict ' + (good ? 'good' : 'bad');
    vd.innerHTML = `<b>${title}</b>${text}`;
  }
  document.querySelectorAll('input[name=mp],input[name=ms],input[name=mw]').forEach(i=>i.addEventListener('change', meter)); meter();

  // Checklist (per-viewer convenience only)
  const boxes = [...document.querySelectorAll('#checklist input')];
  function prog(){ el('prog').textContent = `${boxes.filter(b=>b.checked).length} of ${boxes.length} done`; }
  boxes.forEach(b=>{
    try { b.checked = localStorage.getItem('bp-'+b.id) === '1'; } catch(e){}
    b.addEventListener('change', ()=>{ try { localStorage.setItem('bp-'+b.id, b.checked ? '1':'0'); } catch(e){} prog(); });
  });
  prog();
})();
</script>
