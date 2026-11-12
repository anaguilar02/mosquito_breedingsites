import base64, io, json, logging, os, sys

import numpy as np, pandas as pd

CSV = sys.argv[1] if len(sys.argv) > 1 else 'breeding_sites.csv'
OUT = 'breeding_sites_map.html'
CO = 'location.country.name_en'

def to_bool(s):
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(['true', '1', '1.0', 'yes'])

raw = pd.read_csv(CSV)
raw['latitude'] = pd.to_numeric(raw['location.point.latitude'], errors='coerce')
raw['longitude'] = pd.to_numeric(raw['location.point.longitude'], errors='coerce')

df1 = raw.dropna(subset=['latitude', 'longitude']).copy()
df2 = raw.dropna(subset=['latitude', 'longitude', 'has_water', 'has_larvae']).copy()
df2['has_water'] = to_bool(df2['has_water'])
df2['has_larvae'] = to_bool(df2['has_larvae'])

for d in (df1, df2):
    d['lat3'], d['lon3'] = d['latitude'].round(3), d['longitude'].round(3)

print(f'[Breeding sites] {len(df1):,} registros')
print(f'[Agua y larvas]  {len(df2):,} registros | con agua: {int(df2.has_water.sum()):,} | '
      f'con larvas: {int(df2.has_larvae.sum()):,}')

top = lambda s: m.iat[0] if len(m := s.dropna().mode()) else 'Unknown'

PLEN = [1.0, .9986, .9954, .99, .9822, .973, .96, .9427, .9216, .8962, .8679, .835,
        .7986, .7597, .7186, .6732, .6213, .5722, .5322]
PDFE = [0.0, .062, .124, .186, .248, .31, .372, .434, .4958, .5571, .6176, .6769,
        .7346, .7903, .8435, .8936, .9394, .9761, 1.0]
LATS = np.arange(0, 95, 5)

def robinson(lon, lat):
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    a = np.abs(lat)
    return (0.8487 * np.interp(a, LATS, PLEN) * np.radians(lon),
            1.3523 * np.interp(a, LATS, PDFE) * np.sign(lat))

pts = lambda x, y: np.round(np.c_[x, y], 5).tolist()
rr = lambda a, nd=5: np.round(np.asarray(a, float), nd).tolist()

def load_land():
    try:
        import cartopy.io.shapereader as shp
        out = []
        for geom in shp.Reader(shp.natural_earth('50m', 'physical', 'land')).geometries():
            for poly in getattr(geom, 'geoms', [geom]):
                px, py = robinson(*map(np.asarray, poly.exterior.xy))
                out.append(np.round(np.c_[px, py].ravel(), 5).tolist())
        return out
    except Exception as e:
        print('Sin continentes:', e)
        return []

OFFSETS = {'Spain': (-.6, -.28), 'Italy': (.8, -.12), 'Austria': (.62, .58),
           'Netherlands': (.02, .62), 'France': (-.55, .6), 'Uruguay': (.55, -.15),
           'India': (.25, -.4), 'United States': (0, .4),
           'Republic of Korea': (-.25, .4), 'Argentina': (-.62, -.35),
           'Libya': (.25, -.62)}
DEFAULT_OFFSET = (0, .45)
NAMES = {'Republic of Korea': 'South Korea'}

ZONES = {'A': ('Iberian Peninsula', (-9.6, 4.6), (35.8, 44.0), (-.16, .14)),
         'B': ('Barcelona', (2.05, 2.25), (41.32, 41.48), (.13, -.17)),
         'C': ('Rome and surroundings', (12.3, 12.7), (41.75, 42.05), (.2, .12))}

def in_zone(d, lon_lim, lat_lim):
    return d[d['lon3'].between(*lon_lim) & d['lat3'].between(*lat_lim)]

zones = []
for key, (name, lon_lim, lat_lim, (bdx, bdy)) in ZONES.items():
    (lo0, lo1), (la0, la1) = lon_lim, lat_lim
    cx, cy = robinson([lo0, lo1, lo1, lo0, lo0], [la0, la0, la1, la1, la0])
    zx, zy = robinson((lo0 + lo1) / 2, (la0 + la1) / 2)
    zones.append({'key': key, 'name': name, 'rect': pts(cx, cy),
                  'bbox': [round(float(v), 5) for v in (cx.min(), cx.max(), cy.min(), cy.max())],
                  'cx': round(float(zx), 5), 'cy': round(float(zy), 5), 'dx': bdx, 'dy': bdy})

def build_view(df, water):
    agg = dict(n=('lat3', 'size'), country=(CO, top))
    cagg = dict(n=('lat3', 'size'), lat=('lat3', 'median'), lon=('lon3', 'median'))
    if water:
        agg.update(nl=('has_larvae', 'sum'), nw=('has_water', 'sum'))
        cagg.update(nl=('has_larvae', 'sum'))
    g = (df.groupby(['lat3', 'lon3']).agg(**agg).reset_index()
           .sort_values('n', kind='stable').reset_index(drop=True))
    countries = df.groupby(CO).agg(**cagg).sort_values('n', ascending=False)

    px, py = robinson(g['lon3'], g['lat3'])
    cats = pd.Categorical(g['country'])

    labels = []
    for c, row in countries.head(10).iterrows():
        if not water and c not in OFFSETS:
            continue
        ax, ay = robinson(row['lon'], row['lat'])
        dx, dy = OFFSETS.get(c, DEFAULT_OFFSET)
        text = f"{NAMES.get(c, c)}  {int(row['n']):,}"
        if water:
            text += f"  ({100 * row['nl'] / row['n']:.0f}% larvae)"
        labels.append({'text': text, 'x': round(float(ax), 5), 'y': round(float(ay), 5),
                       'dx': dx, 'dy': dy})

    ztext = []
    for key, (name, lon_lim, lat_lim, _) in ZONES.items():
        sub = in_zone(g if not water else df, lon_lim, lat_lim)
        if not water:
            ztext.append(f"{name}: {int(sub['n'].sum()):,} breeding sites, "
                         f"{len(sub):,} unique coordinates")
        elif len(sub) == 0:
            ztext.append(f'{name}: no records')
        else:
            ztext.append(f"{name}: {len(sub):,} breeding site{'' if len(sub) == 1 else 's'}, "
                         f"{100 * sub['has_water'].mean():.0f}% with stagnant water, "
                         f"{100 * sub['has_larvae'].mean():.0f}% with larvae")

    v = {'x': rr(px), 'y': rr(py), 'n': g['n'].astype(int).tolist(),
         'lat': rr(g['lat3'], 3), 'lon': rr(g['lon3'], 3), 'c': cats.codes.astype(int).tolist(),
         'countries': [str(c) for c in cats.categories], 'nmax': int(g['n'].max()),
         'labels': labels, 'ztext': ztext}
    if water:
        v['nl'] = g['nl'].astype(int).tolist()
        v['nw'] = g['nw'].astype(int).tolist()
    return v

views = {'countries': build_view(df1, False), 'water': build_view(df2, True)}

lats = np.linspace(-90, 90, 200)
xl, yl = robinson(np.full_like(lats, -180), lats)
xr, yr = robinson(np.full_like(lats, 180), lats)
outline = pts(np.r_[xl, xr[::-1]], np.r_[yl, yr[::-1]])

grid = []
for lon in range(-180, 181, 30):
    la = np.linspace(-90, 90, 100)
    grid.append(pts(*robinson(np.full_like(la, lon), la)))
for lat in range(-60, 91, 30):
    lo = np.linspace(-180, 180, 200)
    grid.append(pts(*robinson(lo, np.full_like(lo, lat))))

axl = []
for lat in range(-60, 90, 30):
    xx, yy = robinson(-180, lat)
    axl.append({'x': float(xx), 'y': float(yy), 'text': f'{lat}°', 'dx': -.03, 'dy': 0,
                'ha': 'right', 'va': 'middle'})
for lon in range(-120, 181, 60):
    xx, yy = robinson(lon, -90)
    axl.append({'x': float(xx), 'y': float(yy), 'text': f'{lon}°', 'dx': 0, 'dy': -.05,
                'ha': 'center', 'va': 'top'})

data = {'views': views, 'zones': zones, 'outline': outline, 'grid': grid, 'axl': axl,
        'cmap': ['#f2c14e', '#f78154', '#d1495b', '#8c1c4b', '#3b0f3f'],
        'land': load_land()}
payload = json.dumps(data, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')

def embed_fonts():
    try:
        import matplotlib
        from fontTools import subset
        from fontTools.ttLib import TTFont
        logging.getLogger('fontTools').setLevel(logging.ERROR)
        d = os.path.join(matplotlib.get_data_path(), 'fonts', 'ttf')
        css = []
        for fname, w in (('DejaVuSans.ttf', 400), ('DejaVuSans-Bold.ttf', 700)):
            font = TTFont(os.path.join(d, fname))
            sub = subset.Subsetter(subset.Options())
            sub.populate(unicodes=list(range(0x20, 0x250)) + list(range(0x2000, 0x2070)) + [0x20AC])
            sub.subset(font)
            buf = io.BytesIO()
            font.save(buf)
            css.append("@font-face{font-family:'DejaVuE';font-weight:%d;src:url(data:font/ttf;base64,%s) format('truetype')}"
                       % (w, base64.b64encode(buf.getvalue()).decode()))
        return '\n'.join(css)
    except Exception:
        return ''

TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Breeding Sites</title>
<style>
/*__FONTS__*/
:root{--bg:#f4efe6;--ocean:#dfe9ee;--ink:#1f2a37;--muted:#6b7686;--grid:#c3d0d8;--accent:#8c1c4b}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:'DejaVuE','DejaVu Sans','Segoe UI',Helvetica,Arial,sans-serif}
body{min-height:100vh;display:flex;justify-content:center;align-items:center}
#fig{position:relative;width:min(100vw,160vh);aspect-ratio:16/10;container-type:inline-size;background:var(--bg);overflow:hidden}
h1,#lglabel,#bar,#ticks,#areasT,.badge,.txt,#swap{position:absolute}
#lglabel{left:74.5%;bottom:94.2%;font-size:max(10px,.6597cqw);line-height:1;white-space:nowrap}
#bar{left:74.5%;bottom:91.5%;width:23%;height:1.2%;border:.6px solid var(--ink)}
#ticks{left:74.5%;bottom:89.4%;width:23%;height:1.8%}
#ticks span{position:absolute;top:0;transform:translateX(-50%);font-size:max(8px,.59cqw);color:var(--muted);white-space:nowrap}
h1{margin:0;left:3.5%;bottom:94%;font-size:max(18px,2.0833cqw);font-weight:700;line-height:1;white-space:nowrap}
#wrap{position:absolute;left:3.5%;top:12%;width:94%;height:68%;touch-action:none;cursor:grab;outline:none;overflow:hidden}
#wrap.drag{cursor:grabbing}
canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
#ring{position:absolute;display:none;width:28px;height:28px;border:1.3px solid var(--ink);border-radius:50%;transform:translate(-50%,-50%);pointer-events:none}
#tip{position:absolute;display:none;pointer-events:none;white-space:pre;background:var(--bg);color:var(--ink);border:.8px solid var(--ink);border-radius:6px;padding:6px 9px;font-size:max(10px,.66cqw);line-height:1.35;z-index:5}
#areasT{left:3.5%;bottom:16.5%;font-weight:700;font-size:max(11px,.764cqw);line-height:1;white-space:nowrap}
.badge{left:3.5%;transform:translate(-50%,-50%);width:max(16px,1.25cqw);height:max(16px,1.25cqw);border-radius:50%;background:var(--ink);color:var(--bg);font-weight:700;font-size:max(9px,.694cqw);display:flex;align-items:center;justify-content:center;cursor:pointer}
.txt{left:5.2%;transform:translateY(-50%);font-size:max(10px,.625cqw);white-space:nowrap;cursor:pointer}
.txt:hover{text-decoration:underline}
#swap{left:76.5%;bottom:4.2%;width:21%;height:6.4%;border:0;border-radius:999px;background:var(--ink);color:var(--bg);
  font-family:inherit;font-weight:700;font-size:max(11px,.9cqw);cursor:pointer;
  box-shadow:0 .35cqw .8cqw rgba(31,42,55,.22);transition:background .18s,transform .12s,box-shadow .18s}
#swap:hover{background:var(--ink);box-shadow:0 .45cqw 1cqw rgba(31,42,55,.30)}
#swap:active{background:var(--ink);transform:translateY(1px) scale(.99)}
#swap:focus-visible{outline:2px solid var(--ink);outline-offset:3px}
</style></head>
<body>
<div id="fig">
<h1 id="title">Breeding Sites</h1>
<div id="lglabel"></div>
<div id="bar"></div><div id="ticks"></div>
<div id="wrap" tabindex="0"><canvas id="cv"></canvas><div id="ring"></div><div id="tip"></div></div>
<div id="areasT">Highlighted areas</div>
<button id="swap" type="button"></button>
</div>
<script>
(function(){
'use strict';
const D=__DATA__;
const BG='#f4efe6',OCEAN='#dfe9ee',INK='#1f2a37',MUTED='#6b7686',GRID='#c3d0d8';
const HX=2.75,HY=1.45,HOVER_PX=14,MIN_W=.002,TAU=Math.PI*2;
const FONT="'DejaVuE','DejaVu Sans','Segoe UI',Helvetica,Arial,sans-serif";
const META={
  countries:{title:'Breeding Sites',caption:'Breeding sites per coordinate',btn:'View water and larvae',next:'water'},
  water:{title:'Stagnant Water and Larvae',caption:'Share of breeding sites with larvae',btn:'View breeding sites',next:'countries'}
};
const $=id=>document.getElementById(id);
const fig=$('fig'),wrap=$('wrap'),cv=$('cv'),ctx=cv.getContext('2d'),tip=$('tip'),ring=$('ring');
const STOPS=D.cmap.map(h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)));
function cmap(t){
  t=Math.min(1,Math.max(0,t));
  const p=t*(STOPS.length-1),i=Math.min(STOPS.length-2,Math.floor(p)),f=p-i,a=STOPS[i],b=STOPS[i+1];
  return [0,1,2].map(k=>Math.round(a[k]+(b[k]-a[k])*f));
}
const LAND=D.land.map(p=>{
  let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
  for(let j=0;j<p.length;j+=2){
    x0=Math.min(x0,p[j]);x1=Math.max(x1,p[j]);y0=Math.min(y0,p[j+1]);y1=Math.max(y1,p[j+1]);
  }
  return {p:p,b:[x0,x1,y0,y1]};
});
let W=1,H=1,dpr=1,s0=1,K=1,S=1,zoom=1,cx=0,cy=0,zmax=1000,dragging=false;
let view='countries',V=null,water=false,N=0,X,Y,NN,CC,NL,NW,colMain,colHalo,baseD,PX,PY,VIS;
const sx=x=>W/2+(x-cx)*S,sy=y=>H/2-(y-cy)*S;
function setView(name){
  view=name;V=D.views[name];water=name==='water';
  const M=META[name];
  N=V.n.length;X=Float64Array.from(V.x);Y=Float64Array.from(V.y);
  NN=Float64Array.from(V.n);CC=Int32Array.from(V.c);
  NL=water?Float64Array.from(V.nl):null;NW=water?Float64Array.from(V.nw):null;
  colMain=new Array(N);colHalo=new Array(N);baseD=new Float64Array(N);
  const nmax=V.nmax;
  for(let i=0;i<N;i++){
    const t=water?NL[i]/NN[i]:(nmax>1?Math.sqrt((NN[i]-1)/(nmax-1)):0);
    const c=cmap(t).join(',');
    colMain[i]='rgba('+c+',0.85)';colHalo[i]='rgba('+c+',0.10)';
    baseD[i]=Math.sqrt(6+16*Math.sqrt(NN[i]));
  }
  PX=new Float64Array(N);PY=new Float64Array(N);VIS=new Int32Array(N);
  $('title').textContent=M.title;$('lglabel').textContent=M.caption;$('swap').textContent=M.btn;
  document.title=M.title;
  buildTicks();
  zoneEls.forEach((el,i)=>{el.textContent=V.ztext[i];});
  hideTip();schedule();
}
function toggle(){setView(META[view].next);}
function clampView(){
  zoom=Math.min(zmax,Math.max(1,zoom));S=s0*zoom;
  const hw=W/(2*S),hh=H/(2*S);
  cx=hw>=HX?0:Math.min(HX-hw,Math.max(-HX+hw,cx));
  cy=hh>=HY?0:Math.min(HY-hh,Math.max(-HY+hh,cy));
}
function resize(){
  const rc=wrap.getBoundingClientRect();
  W=Math.max(1,rc.width);H=Math.max(1,rc.height);dpr=window.devicePixelRatio||1;
  cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);
  s0=Math.min(W/(2*HX),H/(2*HY));
  K=fig.getBoundingClientRect().width/1440;
  zmax=(W/s0)/MIN_W;clampView();draw();
}
let raf=0;
const schedule=()=>{if(!raf)raf=requestAnimationFrame(()=>{raf=0;draw();});};
function zoomAt(mx,my,f){
  const ax=(mx-W/2)/S+cx,ay=-(my-H/2)/S+cy;
  zoom=Math.min(zmax,Math.max(1,zoom*f));S=s0*zoom;
  cx=ax-(mx-W/2)/S;cy=ay+(my-H/2)/S;clampView();schedule();
}
function reset(){zoom=1;cx=0;cy=0;clampView();hideTip();schedule();}
function fitZone(z){
  const b=z.bbox,wn=Math.max((b[1]-b[0])*1.6,1e-5),hn=Math.max((b[3]-b[2])*1.6,1e-5);
  zoom=Math.min(W/(wn*s0),H/(hn*s0));cx=(b[0]+b[1])/2;cy=(b[2]+b[3])/2;
  clampView();hideTip();schedule();
}
function path(pts,close){
  pts.forEach((p,i)=>i?ctx.lineTo(sx(p[0]),sy(p[1])):ctx.moveTo(sx(p[0]),sy(p[1])));
  if(close)ctx.closePath();
}
function roundRect(x,y,w,h,r){
  ctx.beginPath();ctx.moveTo(x+r,y);
  ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);
  ctx.closePath();
}
const out=(x,y,m)=>x<-m||x>W+m||y<-m||y>H+m;
function draw(){
  if(!V)return;
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle=BG;ctx.fillRect(0,0,W,H);
  ctx.beginPath();path(D.outline,true);ctx.fillStyle=OCEAN;ctx.fill();
  if(LAND.length){
    const vx0=cx-W/(2*S),vx1=cx+W/(2*S),vy0=cy-H/(2*S),vy1=cy+H/(2*S);
    ctx.beginPath();
    for(const rg of LAND){
      const b=rg.b,p=rg.p;
      if(b[1]<vx0||b[0]>vx1||b[3]<vy0||b[2]>vy1)continue;
      ctx.moveTo(sx(p[0]),sy(p[1]));
      for(let j=2;j<p.length;j+=2)ctx.lineTo(sx(p[j]),sy(p[j+1]));
      ctx.closePath();
    }
    ctx.fillStyle='#fbf8f1';ctx.fill();
    ctx.strokeStyle='#aebbc2';ctx.lineWidth=Math.max(.3,.4*K);ctx.stroke();
  }
  ctx.beginPath();D.grid.forEach(l=>path(l));
  ctx.strokeStyle=GRID;ctx.lineWidth=Math.max(.5,.6*K);ctx.stroke();
  ctx.beginPath();path(D.outline,true);
  ctx.strokeStyle=INK;ctx.lineWidth=Math.max(.8,.8*K);ctx.stroke();
  ctx.fillStyle=MUTED;ctx.font=Math.max(8,8*K)+'px '+FONT;
  for(const l of D.axl){
    const x=sx(l.x)+l.dx*s0,y=sy(l.y)-l.dy*s0;
    if(out(x,y,30))continue;
    ctx.textAlign=l.ha;ctx.textBaseline=l.va;ctx.fillText(l.text,x,y);
  }
  let cnt=0;
  for(let i=0;i<N;i++){
    const x=sx(X[i]),y=sy(Y[i]);
    if(out(x,y,40))continue;
    PX[i]=x;PY[i]=y;VIS[cnt++]=i;
  }
  if(!dragging)for(let k=0;k<cnt;k++){
    const i=VIS[k];ctx.fillStyle=colHalo[i];
    ctx.beginPath();ctx.arc(PX[i],PY[i],baseD[i]*K*Math.sqrt(5)/2,0,TAU);ctx.fill();
  }
  ctx.strokeStyle=BG;ctx.lineWidth=Math.max(.3,.3*K);
  for(let k=0;k<cnt;k++){
    const i=VIS[k];ctx.fillStyle=colMain[i];
    ctx.beginPath();ctx.arc(PX[i],PY[i],baseD[i]*K/2,0,TAU);ctx.fill();
    if(!dragging)ctx.stroke();
  }
  ctx.strokeStyle=INK;ctx.lineWidth=Math.max(1,K);
  for(const z of D.zones){ctx.beginPath();path(z.rect);ctx.stroke();}
  const fs=Math.max(9,9.5*K);
  ctx.font='bold '+fs+'px '+FONT;ctx.textAlign='center';ctx.textBaseline='middle';
  for(const l of V.labels){
    const ax=sx(l.x),ay=sy(l.y);
    if(out(ax,ay,40))continue;
    const lx=ax+l.dx*s0,ly=ay-l.dy*s0;
    ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(lx,ly);ctx.strokeStyle=INK;ctx.lineWidth=.8;ctx.stroke();
    const tw=ctx.measureText(l.text).width,pad=fs*.25,th=fs*1.15;
    roundRect(lx-tw/2-pad,ly-th/2-pad,tw+pad*2,th+pad*2,pad);
    ctx.fillStyle=BG;ctx.fill();ctx.strokeStyle=INK;ctx.lineWidth=.7;ctx.stroke();
    ctx.fillStyle=INK;ctx.fillText(l.text,lx,ly+.5);
  }
  const br=Math.max(8,9*K);
  ctx.font='bold '+Math.max(9,11*K)+'px '+FONT;
  for(const z of D.zones){
    const bx=sx(z.cx)+z.dx*s0,by=sy(z.cy)-z.dy*s0;
    if(out(bx,by,30))continue;
    ctx.beginPath();ctx.arc(bx,by,br,0,TAU);ctx.fillStyle=INK;ctx.fill();
    ctx.fillStyle=BG;ctx.fillText(z.key,bx,by+.5);
  }
}
function hideTip(){tip.style.display='none';ring.style.display='none';}
function hoverAt(mx,my){
  const ux=(mx-W/2)/S+cx,uy=-(my-H/2)/S+cy,r=HOVER_PX/S,r2=r*r;
  let k=0,total=0,tl=0,tw=0,best=-1,bestN=-1;
  const byC=new Map();
  for(let i=0;i<N;i++){
    const dx=X[i]-ux;if(dx>r||dx<-r)continue;
    const dy=Y[i]-uy;if(dy>r||dy<-r)continue;
    if(dx*dx+dy*dy>r2)continue;
    k++;total+=NN[i];
    if(water){tl+=NL[i];tw+=NW[i];}
    if(NN[i]>bestN){bestN=NN[i];best=i;}
    byC.set(CC[i],(byC.get(CC[i])||0)+NN[i]);
  }
  if(!k){hideTip();return;}
  let topC=-1,topV=-1;
  byC.forEach((v,c)=>{if(v>topV){topV=v;topC=c;}});
  const country=V.countries[topC],fmt=v=>Number(v).toLocaleString('en-US');
  const coord='Lat '+V.lat[best].toFixed(3)+'°, Lon '+V.lon[best].toFixed(3)+'°';
  const yn=v=>v>0?'yes':'no';
  let txt;
  if(k===1){
    txt=country+'**\n**'+coord+'**\n**'+fmt(NN[best])+' breeding sites';
    if(water){
      txt+=NN[best]===1
        ?'**\n**Stagnant water: '+yn(NW[best])+'**\n**Larvae: '+yn(NL[best])
        :'**\n**'+fmt(NW[best])+' with stagnant wate&#x72;**\n**'+fmt(NL[best])+' with larvae ('+Math.round(100*NL[best]/NN[best])+'%)';
    }
  }else{
    txt=country+(byC.size>1?'  (+'+(byC.size-1)+' more)':'')+'**\n**'+fmt(total)+' breeding sites in '+fmt(k)+' coordinates';
    if(water)txt+='**\n**'+fmt(tw)+' with stagnant wate&#x72;**\n**'+fmt(tl)+' with larvae ('+Math.round(100*tl/total)+'%)';
    txt+='**\n**Largest: '+coord+' ('+fmt(NN[best])+')**\n**Zoom in to see each one';
  }
  tip.textContent=txt;
  tip.style.display='block';
  const tipW=tip.offsetWidth,tipH=tip.offsetHeight;
  let left=mx>W*.65?mx-16-tipW:mx+16,top=my<H*.25?my+16:my-16-tipH;
  tip.style.left=Math.max(0,Math.min(W-tipW,left))+'px';
  tip.style.top=Math.max(0,Math.min(H-tipH,top))+'px';
  ring.style.left=mx+'px';ring.style.top=my+'px';ring.style.display='block';
}
const pos=e=>{const rc=wrap.getBoundingClientRect();return [e.clientX-rc.left,e.clientY-rc.top];};
const ptrs=new Map();
let pan=null,pinch=null;
function pinchState(){
  const [a,b]=[...ptrs.values()],mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2;
  return {d0:Math.hypot(a[0]-b[0],a[1]-b[1])||1,z0:zoom,ax:(mx-W/2)/S+cx,ay:-(my-H/2)/S+cy};
}
wrap.addEventListener('pointerdown',e=>{
  wrap.setPointerCapture(e.pointerId);
  const p=pos(e);ptrs.set(e.pointerId,p);hideTip();wrap.focus({preventScroll:true});
  if(ptrs.size===1)pan={x:p[0],y:p[1],cx:cx,cy:cy,moved:false};
  else if(ptrs.size===2){pan=null;pinch=pinchState();}
});
wrap.addEventListener('pointermove',e=>{
  const p=pos(e);
  if(ptrs.has(e.pointerId))ptrs.set(e.pointerId,p);
  if(pinch&&ptrs.size>=2){
    const [a,b]=[...ptrs.values()],mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2,d=Math.hypot(a[0]-b[0],a[1]-b[1])||1;
    zoom=pinch.z0*d/pinch.d0;clampView();
    cx=pinch.ax-(mx-W/2)/S;cy=pinch.ay+(my-H/2)/S;clampView();
    dragging=true;schedule();return;
  }
  if(pan&&ptrs.has(e.pointerId)){
    const dx=p[0]-pan.x,dy=p[1]-pan.y;
    if(!pan.moved&&Math.hypot(dx,dy)>4){pan.moved=true;dragging=true;wrap.classList.add('drag');}
    if(pan.moved){cx=pan.cx-dx/S;cy=pan.cy+dy/S;clampView();schedule();}
    return;
  }
  if(e.pointerType==='mouse')hoverAt(p[0],p[1]);
});
function endPointer(e){
  const p=pos(e),wasTap=pan&&!pan.moved&&ptrs.size===1&&e.pointerType!=='mouse'&&e.type==='pointerup';
  ptrs.delete(e.pointerId);
  if(ptrs.size<2)pinch=null;
  if(ptrs.size===0){
    pan=null;dragging=false;wrap.classList.remove('drag');schedule();
    if(wasTap)hoverAt(p[0],p[1]);
  }else if(ptrs.size===1){
    const q=[...ptrs.values()][0];pan={x:q[0],y:q[1],cx:cx,cy:cy,moved:true};
  }
}
wrap.addEventListener('pointerup',endPointer);
wrap.addEventListener('pointercancel',endPointer);
wrap.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse'&&!dragging)hideTip();});
wrap.addEventListener('wheel',e=>{
  e.preventDefault();
  let dy=e.deltaY;
  if(e.deltaMode===1)dy*=33;else if(e.deltaMode===2)dy*=400;
  dy=Math.max(-120,Math.min(120,dy));
  const p=pos(e);hideTip();
  zoomAt(p[0],p[1],Math.exp(-dy*(e.ctrlKey?.01:.0022)));
},{passive:false});
wrap.addEventListener('dblclick',reset);
wrap.addEventListener('keydown',e=>{
  const st=.15,hw=W/(2*S),hh=H/(2*S);
  let used=true;
  switch(e.key){
    case 'ArrowLeft':cx-=st*2*hw;break;
    case 'ArrowRight':cx+=st*2*hw;break;
    case 'ArrowUp':cy+=st*2*hh;break;
    case 'ArrowDown':cy-=st*2*hh;break;
    case '+':case '=':zoomAt(W/2,H/2,1.25);break;
    case '-':case '_':zoomAt(W/2,H/2,.8);break;
    case 'r':case 'R':reset();break;
    case 'v':case 'V':toggle();break;
    default:used=false;
  }
  if(used){e.preventDefault();hideTip();clampView();schedule();}
});
$('bar').style.background='linear-gradient(to right,'+D.cmap.join(',')+')';
function buildTicks(){
  const box=$('ticks');box.innerHTML='';
  let arr=[];
  if(water){
    [0,20,40,60,80,100].forEach(v=>arr.push({p:v/100,t:v+'%'}));
  }else{
    const nmax=V.nmax,tv=[1,5,20,50,100].filter(v=>v<nmax);tv.push(nmax);
    tv.forEach(v=>{
      const p=nmax>1?Math.sqrt((v-1)/(nmax-1)):0;
      if(arr.length&&p-arr[arr.length-1].p<.06){if(v===nmax)arr.pop();else return;}
      arr.push({p:p,t:v.toLocaleString('en-US')});
    });
  }
  arr.forEach(t=>{
    const s=document.createElement('span');
    s.style.left=(t.p*100)+'%';s.textContent=t.t;box.appendChild(s);
  });
}
const zoneEls=[];
D.zones.forEach((z,i)=>{
  const top=(1-(.125-i*.04))*100+'%';
  const b=document.createElement('div');b.className='badge';b.textContent=z.key;b.style.top=top;
  const t=document.createElement('div');t.className='txt';t.style.top=top;
  b.title=t.title='Click to zoom to this area';
  b.onclick=t.onclick=()=>fitZone(z);
  fig.appendChild(b);fig.appendChild(t);zoneEls.push(t);
});
$('swap').addEventListener('click',toggle);
setView('countries');
new ResizeObserver(resize).observe(wrap);
window.addEventListener('resize',resize);
resize();
if(document.fonts&&document.fonts.load)
  Promise.all([document.fonts.load("12px 'DejaVuE'"),document.fonts.load("bold 12px 'DejaVuE'")]).then(resize,resize);
})();
</script>
</body></html>
'''

html = TEMPLATE.replace('/*__FONTS__*/', embed_fonts()).replace('__DATA__', payload)

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Listo: {OUT} ({len(html) / 1e6:.1f} MB)')
