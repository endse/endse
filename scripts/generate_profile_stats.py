#!/usr/bin/env python3
from __future__ import annotations
import json, os, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
HEADERS = {"Accept":"application/vnd.github+json",
           "X-GitHub-Api-Version":"2022-11-28",
           "User-Agent":"endse-profile-graphics"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def get_json(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (403,429,500,502,503,504) and attempt < 4:
                reset = exc.headers.get("X-RateLimit-Reset")
                delay = min(30,max(2,int(reset or 0)-int(time.time()))) if reset else 2**attempt
                time.sleep(delay)
            else:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(2**attempt)
    raise RuntimeError(f"Could not fetch {url}")

def get_repos(url):
    repos=[]
    page=1
    while True:
        data=get_json(f"{url}?per_page=100&page={page}")
        if not isinstance(data,list) or not data:
            break
        repos.extend(data)
        if len(data)<100:
            break
        page+=1
    return repos

def stats_svg(personal_count,org_count,stars,forks,followers):
    values=[("PERSONAL REPOS",personal_count),("ORG REPOS",org_count),
            ("TOTAL STARS",stars),("FOLLOWERS",followers)]
    parts=[]
    for i,(label,value) in enumerate(values):
        x=78+i*127
        parts.append(f'<text x="{x}" y="105" text-anchor="middle" fill="#7dd3fc" font-size="26" font-weight="700">{value}</text><text x="{x}" y="132" text-anchor="middle" fill="#a5b4fc" font-size="10">{label}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="190" viewBox="0 0 520 190">
<rect width="520" height="190" rx="14" fill="#1b1b2e" stroke="#343653"/>
<text x="25" y="33" fill="#e5e7eb" font-size="14" font-weight="700">GITHUB STATS</text><text x="495" y="33" text-anchor="end" fill="#22d3ee" font-size="10">LIVE · AUTO-UPDATED</text><path d="M25 47H495" stroke="#3a3d5b"/>
{''.join(parts)}
<text x="260" y="165" text-anchor="middle" fill="#94a3b8" font-size="10">Across endse + Endsett public repositories · {forks} forks</text></svg>'''

COLORS={"TypeScript":"#3178c6","JavaScript":"#f1e05a","Python":"#3572A5",
"Dart":"#00B4AB","C++":"#f34b7d","Java":"#b07219","HTML":"#e34c26",
"CSS":"#563d7c","Go":"#00ADD8","Rust":"#dea584","Shell":"#89e051",
"Jupyter Notebook":"#DA5B0B","Kotlin":"#A97BFF","Swift":"#F05138","C":"#555555"}
EXTRA=["#22d3ee","#8b5cf6","#34d399","#f59e0b","#f472b6","#60a5fa","#a3e635"]

def languages_svg(data):
    ranked=sorted(data.items(),key=lambda item:item[1],reverse=True)[:7]
    total=sum(data.values())
    if not ranked:
        ranked=[("No language data yet",1)]
        total=1
    chunks=[]
    used=0.0
    for i,(name,size) in enumerate(ranked):
        width=470*size/total
        if i==len(ranked)-1:
            width=470-used
        color=COLORS.get(name,EXTRA[i%len(EXTRA)])
        chunks.append(f'<rect x="{25+used:.2f}" y="62" width="{max(0,width):.2f}" height="13" fill="{color}"/>')
        used+=width
    legend=[]
    for i,(name,size) in enumerate(ranked):
        col=i%2
        row=i//2
        x=30+col*245
        y=100+row*23
        color=COLORS.get(name,EXTRA[i%len(EXTRA)])
        label=escape(name[:24])
        legend.append(f'<circle cx="{x+5}" cy="{y-4}" r="4" fill="{color}"/><text x="{x+17}" y="{y}" fill="#e5e7eb" font-size="11">{label}</text><text x="{x+220}" y="{y}" text-anchor="end" fill="#94a3b8" font-size="10">{size/total*100:.1f}%</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="190" viewBox="0 0 520 190">
<rect width="520" height="190" rx="14" fill="#1b1b2e" stroke="#343653"/>
<text x="25" y="33" fill="#e5e7eb" font-size="14" font-weight="700">MOST USED LANGUAGES</text><text x="495" y="33" text-anchor="end" fill="#22d3ee" font-size="10">LIVE · AUTO-UPDATED</text><path d="M25 47H495" stroke="#3a3d5b"/>
{''.join(chunks)}
{''.join(legend)}
</svg>'''

def main():
    ASSETS.mkdir(exist_ok=True)
    user=get_json("https://api.github.com/users/endse")
    personal=[r for r in get_repos("https://api.github.com/users/endse/repos") if not r.get("fork")]
    try:
        org=[r for r in get_repos("https://api.github.com/orgs/Endsett/repos") if not r.get("fork")]
    except Exception as error:
        print(f"Org repo lookup skipped: {error}")
        org=[]
    repos=personal+org
    stars=sum(int(r.get("stargazers_count",0)) for r in repos)
    forks=sum(int(r.get("forks_count",0)) for r in repos)
    urls=[r["languages_url"] for r in repos if r.get("languages_url")]
    languages={}
    skipped=0
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs=[executor.submit(get_json,url) for url in urls]
        for job in as_completed(jobs):
            try:
                for lang,size in (job.result() or {}).items():
                    languages[lang]=languages.get(lang,0)+int(size)
            except Exception as error:
                skipped+=1
                print(f"Skipping a language endpoint: {error}")
    (ASSETS/"github-stats.svg").write_text(
        stats_svg(len(personal),len(org),stars,forks,int(user.get("followers",0))),encoding="utf-8")
    (ASSETS/"top-languages.svg").write_text(languages_svg(languages),encoding="utf-8")
    print(f"Updated stats: personal={len(personal)}, org={len(org)}, languages={len(languages)}, skipped={skipped}")

if __name__=="__main__":
    main()
