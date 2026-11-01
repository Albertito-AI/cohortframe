"""Build the static launch page from the packaged composer and verified artifacts.

Usage: python scripts/build_public_site.py OUTPUT_DIR WHEEL MP4 POSTER_PNG
No credentials, runtime databases or working directories are distributed.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
out, wheel, video, poster = map(Path, sys.argv[1:])
if out.exists():
    raise SystemExit('Use a new output directory; existing files are never replaced.')
for source in (wheel, video, poster):
    if not source.is_file():
        raise SystemExit('Missing required release artifact: ' + str(source))
shutil.copytree(root / 'src/cohortframe/studio', out)
downloads = out / 'downloads'
downloads.mkdir()
shutil.copyfile(wheel, downloads / wheel.name)
shutil.copyfile(video, downloads / 'cohortframe-demo.mp4')
shutil.copyfile(poster, out / 'demo-poster.png')
archive = downloads / 'cohortframe-0.2.0.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    candidates = [root / n for n in ('README.md','NOTICE.md','pyproject.toml','AGENTS.md')]
    for name in ('src','tests','examples','docs','scripts'):
        candidates.extend(p for p in (root/name).rglob('*') if p.is_file() and p.suffix in ('.py','.js','.cjs','.json','.md','.html','.css','.svg'))
    for p in sorted(candidates):
        if '__pycache__' not in p.parts:
            z.write(p, 'cohortframe-0.2.0/' + str(p.relative_to(root)))
html = (out / 'index.html').read_text()
html = html.replace('<meta name="theme-color"', '<link rel="canonical" href="https://cohortframe-studio.travelingbert.chatgpt.site/"><meta property="og:type" content="website"><meta property="og:url" content="https://cohortframe-studio.travelingbert.chatgpt.site/"><meta name="theme-color"')
html = html.replace('id="download-package" href="https://github.com/Albertito-AI/cohortframe">View project repository ↗', 'id="download-package" download href="downloads/cohortframe-0.2.0.zip">Download 0.2.0 source ZIP ↓')
html = html.replace('<p class="fine">Evaluation alpha.', '<p class="fine"><a class="text-link" href="downloads/'+wheel.name+'" download>Download Python wheel</a> · <a class="text-link" href="downloads/SHA256SUMS.txt">Checksums</a></p><p class="fine">Evaluation alpha.')
demo = '''<section class="demo-section" aria-label="Actual rendered example"><div><p class="eyebrow">THE ACTUAL OUTPUT</p><h2>Twelve seconds.<br>Three scenes. One record.</h2><p>This MP4 was rendered with CohortFrame 0.2.0: 1280 × 720, 24 fps, H.264 video and AAC audio. The soundtrack is an original procedural fixture.</p><a class="text-link" href="downloads/cohortframe-demo.mp4" download>Download the example ↓</a></div><video controls preload="metadata" playsinline poster="demo-poster.png" aria-label="CohortFrame demonstration: three title cards with procedural instrumental audio"><source src="downloads/cohortframe-demo.mp4" type="video/mp4">Download the MP4 to view this example.</video></section>'''
html = html.replace('<section id="get-started"', demo + '<section id="get-started"')
(out / 'index.html').write_text(html)
with (out / 'style.css').open('a') as css:
    css.write('\n.demo-section{display:grid;grid-template-columns:1fr 1.4fr;gap:60px;align-items:center;margin:0 0 65px}.demo-section p:not(.eyebrow){font-size:14px;color:var(--muted);max-width:380px}.demo-section video{width:100%;border-radius:6px;background:#101917}@media(max-width:700px){.demo-section{grid-template-columns:1fr;gap:25px;margin-bottom:40px}}\n')
(out / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: https://cohortframe-studio.travelingbert.chatgpt.site/sitemap.xml\n')
(out / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://cohortframe-studio.travelingbert.chatgpt.site/</loc></url></urlset>\n')
checksums = []
for path in sorted(downloads.iterdir()):
    checksums.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name)
(downloads / 'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n')
print(json.dumps({'directory':str(out.resolve()),'files':len(list(out.rglob('*'))),'checksums':checksums},indent=2))
