# Searchable catalog of every decoded HKX clip: category, tags, motion metrics, stick-figure GIF preview.
# Run: python catalog6.py [decoded_dir] [out_dir]   (pure Python + PIL; reads out/decoded/*.json.gz)
# Output: catalog.json, catalog.tsv, gifs/<set>/<clip>.gif, catalog.html (offline filter/search page)
import sys, os, json, gzip, math, re, glob
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode import qmul, qrot

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DEC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "decoded")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "out", "catalog")
B = dict(pelvis=5, lthigh=6, lcalf=7, lfoot=8, rthigh=9, rcalf=10, rfoot=11, spine=24, spine2=26, lua=28, lfa=29, rua=31, rfa=32,
         neck=35, head=36, lhand=38, rhand=39, weapon=43)
STICK = [("pelvis", "spine2"), ("spine2", "neck"), ("neck", "head"), ("spine2", "lua"), ("lua", "lfa"), ("lfa", "lhand"),
         ("spine2", "rua"), ("rua", "rfa"), ("rfa", "rhand"), ("pelvis", "lthigh"), ("lthigh", "lcalf"), ("lcalf", "lfoot"),
         ("pelvis", "rthigh"), ("rthigh", "rcalf"), ("rcalf", "rfoot")]
CATS = [  # (category, regex on file+cond, lowercase) first match wins
    ("hit_reaction", r"stagger|recoil|hit_|_hit|hitreact|knock|getup|get_up|bleedout|flinch|blockhit"),
    ("block_parry", r"block|parry|bash|guard|counter"),
    ("dodge", r"dodge|evade|roll|step(?!.*attack)|sidestep|backstep|tk_|slide"),
    ("cast", r"cast|magic|spell|ritual|concentration|(?<!for)(?<!back)ward|shout|channel"),
    ("equip", r"equip|sheath|draw|unequip"),
    ("jump_air", r"jump|fall|land|air|aerial|leap"),
    ("idle", r"idle|stance|pose|wait"),
    ("locomotion", r"walk|run|sprint|move|turn|sneak|strafe|jog"),
    ("attack", r"attack|power|combo|slash|swing|punch|kick|strike|stab|thrust|finisher|special|bfco|mco_"),
]


def load(path, skel):
    d = json.load(gzip.open(path, "rt"))
    d["skeleton"] = skel
    return d


def world(d, f, skel, refloc):
    loc = list(refloc)
    for ti, bi in enumerate(d["t2b"]):
        r = d["frames"][f][ti]
        if 0 <= bi < len(loc):
            loc[bi] = (tuple(r[0:3]), tuple(r[3:7]))
    W = [None] * len(loc)
    par = skel["parents"]
    for i in range(len(loc)):
        t, q = loc[i]
        p = par[i]
        if p < 0:
            W[i] = (t, q)
        else:
            pt, pq = W[p]
            wt = qrot(pq, t)
            W[i] = ((pt[0] + wt[0], pt[1] + wt[1], pt[2] + wt[2]), qmul(pq, q))
    return W


def yaw_of(q):  # pelvis facing about Z (Skyrim Z up); forward = +Y
    v = qrot(q, (0, 1, 0))
    return math.degrees(math.atan2(v[0], v[1]))


def one(job):
    path, skel_path, gif_path = job
    try:
        skel = json.load(open(skel_path))
        refloc = [(tuple(r["t"]), tuple(r["q"])) for r in skel["ref"]]
        d = json.load(gzip.open(path, "rt"))
        nf = d["numFrames"]; fps = d["fps"] or 30
        step = max(1, nf // 60)
        fr = list(range(0, nf, step))
        pos = []
        yaws = []; leans = []
        for f in fr:
            W = world(d, f, skel, refloc)
            pos.append({k: W[i][0] for k, i in B.items() if i < len(W)})
            rt, lt = W[B["rthigh"]][0], W[B["lthigh"]][0]
            rx, ry = rt[0] - lt[0], rt[1] - lt[1]  # right vector; forward = z_up x right = (-ry, rx)
            yaws.append(math.degrees(math.atan2(-ry, rx)))
            sp = W[B["spine2"]][0]; pv = W[B["pelvis"]][0]
            v = (sp[0] - pv[0], sp[1] - pv[1], sp[2] - pv[2]); n = math.sqrt(sum(x * x for x in v)) or 1
            leans.append(math.degrees(math.acos(max(-1, min(1, v[2] / n)))))
        dt = step / fps
        def speed(k):
            return max((math.dist(pos[a][k], pos[a + 1][k]) / dt for a in range(len(pos) - 1)), default=0.0)
        spd = {k: round(speed(k), 1) for k in ("lhand", "rhand", "lfoot", "rfoot", "weapon")}
        # animmotion root translation (annotations) + pelvis displacement
        mot = [0.0, 0.0, 0.0]
        for t, s in d.get("annotations", []):
            m = re.match(r"animmotion\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", s)
            if m:
                mot = [float(m.group(k)) for k in (1, 2, 3)]
        p0, p1 = pos[0]["pelvis"], pos[-1]["pelvis"]
        dx, dy = p1[0] - p0[0] + mot[0], p1[1] - p0[1] + mot[1]
        travel = math.hypot(dx, dy)
        a0 = math.radians(yaws[0])  # facing = (sin a, cos a); right = (cos a, -sin a)
        fwd, side = dy, dx  # actor facing = model +Y (NPC Root), right = +X
        # 60 fps frame of peak strike-limb speed (for clips without Hitframe annotations)
        sp_series = [0.0] + [max(math.dist(pos[a][k], pos[a - 1][k]) for k in ("lhand", "rhand", "lfoot", "rfoot")) / dt for a in range(1, len(pos))]
        peak60 = round(fr[max(range(len(sp_series)), key=lambda a: sp_series[a])] * 60 / fps)
        pel_series = [0.0] + [math.dist(pos[a]["pelvis"], pos[a - 1]["pelvis"]) / dt for a in range(1, len(pos))]
        pelpeak60 = round(fr[max(range(len(pel_series)), key=lambda a: pel_series[a])] * 60 / fps)
        zs = [p["pelvis"][2] for p in pos]
        turn = 0.0
        for a in range(1, len(yaws)):
            dy = (yaws[a] - yaws[a - 1] + 180) % 360 - 180
            turn += dy
        hits = sorted(round(t, 3) for t, s in d.get("annotations", []) if s.lower().startswith("hitframe"))
        name = os.path.splitext(os.path.splitext(os.path.basename(path))[0])[0]
        setname = os.path.basename(os.path.dirname(path))
        src = d.get("source", "")
        cond = os.path.basename(os.path.dirname(src))
        low = (name + " " + cond).lower()
        cat = next((c for c, rx in CATS if re.search(rx, low)), "misc")
        limbs = sorted(spd, key=lambda k: -spd[k])
        dom = limbs[0] if spd[limbs[0]] > 0 else ""
        weapon_set = bool(re.search(r"sword|blade|katana|1hm|2hm|2hw|dagger|axe|spear|glaive|pike|halberd|greatsword|heavyblade|sanguine", (setname + " " + src).lower())) and "unarmed" not in (setname + src).lower()
        tags = []
        if cat == "attack":
            if "power" in low or "heavy" in low: tags.append("heavy")
            if dom in ("lfoot", "rfoot") and spd[dom] > 250: tags.append("kick")
            elif dom in ("lhand", "rhand"): tags.append("hand")
            if weapon_set: tags.append("weapon")
            if len(hits) > 1: tags.append("multihit")
        if max(zs) - zs[0] > 25: tags.append("airborne")
        if abs(turn) > 270: tags.append("spin")
        if travel > 120: tags.append("travel")
        if max(leans) > 60: tags.append("lean")
        if "sprint" in low or "dash" in low: tags.append("dash")
        rec = dict(set=setname, clip=name, cond=cond, source=src, cat=cat, tags=tags, frames=nf, fps=round(fps, 2),
                   dur=round(d["duration"], 3), hits=hits, speed=spd, dom=dom, travel=round(travel, 1), fwd=round(fwd, 1), side=round(side, 1), peak60=peak60, pelpeak60=pelpeak60, rise=round(max(zs) - zs[0], 1),
                   drop=round(zs[0] - min(zs), 1), turn=round(turn, 0), lean=round(max(leans), 0), weapon=weapon_set,
                   gif=os.path.relpath(gif_path, OUT).replace("\\", "/"), decoded=os.path.relpath(path, ROOT).replace("\\", "/"))
        # GIF: side view (Y forward -> screen x, Z up -> screen y), 12 frames
        try:
            from PIL import Image, ImageDraw
            idx = [round(k * (len(pos) - 1) / 11) for k in range(12)]
            allp = [v for k in idx for v in pos[k].values()]
            cx = sum(v[1] for v in allp) / len(allp); zmin = min(v[2] for v in allp); zmax = max(v[2] for v in allp)
            sc = 88 / max(140.0, zmax - zmin + 20)
            ims = []
            for k in idx:
                im = Image.new("P", (96, 96), 0); im.putpalette([24, 24, 28, 230, 140, 60, 90, 200, 110, 225, 220, 210, 160, 200, 255] + [0] * 753)
                dr = ImageDraw.Draw(im)
                P = lambda v: (48 + (v[1] - cx) * sc, 92 - (v[2] - zmin) * sc)
                dr.line([(0, 92), (96, 92)], fill=3)
                for a, b in STICK:
                    col = 1 if (a.startswith("r") or b.startswith("r")) and not a.startswith("spine") else 2 if (a.startswith("l") or b.startswith("l")) else 3
                    dr.line([P(pos[k][a]), P(pos[k][b])], fill=col, width=2)
                dr.ellipse([P(pos[k]["head"])[0] - 4, P(pos[k]["head"])[1] - 4, P(pos[k]["head"])[0] + 4, P(pos[k]["head"])[1] + 4], outline=3)
                if weapon_set:
                    dr.line([P(pos[k]["rhand"]), P(pos[k]["weapon"])], fill=4, width=1)
                ims.append(im)
            os.makedirs(os.path.dirname(gif_path), exist_ok=True)
            ims[0].save(gif_path, save_all=True, append_images=ims[1:], duration=int(1000 * d["duration"] / 12) or 80, loop=0)
        except Exception as e:
            rec["gif_error"] = repr(e)
        return rec
    except Exception as e:
        return dict(decoded=path, error=repr(e))


def main():
    skel_path = os.path.join(DEC, "skeleton.json")
    files = sorted(glob.glob(os.path.join(DEC, "*", "*.json.gz")))
    jobs = [(f, skel_path, os.path.join(OUT, "gifs", os.path.basename(os.path.dirname(f)), os.path.basename(f)[:-8] + ".gif")) for f in files]
    os.makedirs(OUT, exist_ok=True)
    with ProcessPoolExecutor(max_workers=6) as ex:
        recs = list(ex.map(one, jobs, chunksize=4))
    json.dump(recs, open(os.path.join(OUT, "catalog.json"), "w"), indent=0)
    cols = ["set", "clip", "cond", "cat", "tags", "frames", "fps", "dur", "hits", "dom", "travel", "fwd", "side", "peak60", "pelpeak60", "rise", "drop", "turn", "lean", "weapon", "speed", "gif", "decoded"]
    with open(os.path.join(OUT, "catalog.tsv"), "w", encoding="utf-8") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in recs:
            if "error" not in r:
                fh.write("\t".join(json.dumps(r[c]) if isinstance(r[c], (list, dict)) else str(r[c]) for c in cols) + "\n")
    html = ["<!doctype html><meta charset=utf-8><title>HKX catalog</title><style>body{font:13px system-ui;background:#16161a;color:#ddd;margin:16px}"
            "input{width:60%;padding:6px;font-size:14px}.g{display:flex;flex-wrap:wrap;gap:8px}.c{width:150px;background:#222;padding:4px;border-radius:4px}"
            ".c img{width:96px;height:96px;image-rendering:pixelated}small{color:#999}</style>",
            "<input id=q placeholder='filter: words match set/clip/cat/tags, e.g. dodge unarmed or attack kick'> <span id=n></span><div class=g id=g>"]
    for r in recs:
        if "error" in r:
            continue
        key = " ".join([r["set"], r["clip"], r["cond"], r["cat"]] + r["tags"]).lower().replace('"', "")
        html.append('<div class=c data-k="%s"><img loading=lazy src="%s"><br><b>%s</b><br><small>%s | %s<br>%s %.2fs hits %d turn %d</small></div>'
                    % (key, r["gif"], r["clip"], r["set"][:28], r["cat"], " ".join(r["tags"]), r["dur"], len(r["hits"]), r["turn"]))
    html.append("</div><script>const q=document.getElementById('q'),cs=[...document.querySelectorAll('.c')],n=document.getElementById('n');"
                "function f(){const w=q.value.toLowerCase().split(/\\s+/).filter(Boolean);let k=0;for(const c of cs){const ok=w.every(x=>c.dataset.k.includes(x));c.hidden=!ok;k+=ok}n.textContent=k+' clips'}"
                "q.oninput=f;f()</script>")
    open(os.path.join(OUT, "catalog.html"), "w", encoding="utf-8").write("\n".join(html))
    from collections import Counter
    ok = [r for r in recs if "error" not in r]
    print("catalog", len(ok), "clips; errors", len(recs) - len(ok))
    print(Counter(r["cat"] for r in ok).most_common())
    print(Counter(t for r in ok for t in r["tags"]).most_common())


if __name__ == "__main__":
    main()
