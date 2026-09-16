import concurrent.futures
import io
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse

OUT = pathlib.Path('github-public')
SITES = [
 ('https://weiwei-design-portfolio.weiweiwei760.chatgpt.site', '/portfolio/'),
 ('https://sunseeker-design-portfolio.weiweiwei760.chatgpt.site', '/portfolio/sunseeker/'),
]
ASSET = re.compile(r'''(?<=["'\x60(])(?:https://|/|(?:\.\.?/)+|_next/)[^\s<>"'\x60\\]*?\.(?:js|css|jpg|jpeg|png|webp|svg|gif|mp4|mov|webm|woff2?|ico)(?:\?[^\s<>"'\x60\\]*)?''')

def fetch(url):
    result = subprocess.run(['curl', '-L', '--fail', '--retry', '3', '--max-time', '180', '--silent', '--show-error', url], capture_output=True)
    if result.returncode:
        raise RuntimeError(url + ': ' + result.stderr.decode()[-300:])
    return result.stdout

def rewrite(text, base):
    text = re.sub(r'''(["'\x60])(/)(?=[A-Za-z0-9_#])''', lambda m: m[1] + base, text)
    text = re.sub(r'''(href\s*[:=]\s*["'\x60])/(["'\x60])''', lambda m: m[1] + base + m[2], text)
    text = text.replace(r'\"href\":\"/\"', r'\"href\":\"' + base + r'\"')
    text = text.replace('return' + chr(96) + '/' + chr(96) + '+', 'return' + chr(96) + base + chr(96) + '+')
    text = re.sub(r'url\(/(?!/)', 'url(' + base, text)
    for origin, target in SITES:
        text = text.replace(origin + '/', target).replace(origin, target.rstrip('/'))
    return text

def mirror(origin, base):
    routes = ['']
    if base == '/portfolio/':
        homepage = fetch(origin + '/').decode()
        routes += sorted(set(re.findall(r'href="/(work/[A-Za-z0-9_-]+)"', homepage)))
        assert len(routes) > 1, 'Missing project links'
    prefix = base.removeprefix('/portfolio/').strip('/')
    seen = set()
    queue = {urllib.parse.urljoin(origin+'/', route): True for route in routes}
    count = 0
    while queue:
        batch = queue
        queue = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fetch, url): (url, page) for url, page in batch.items()}
            for future in concurrent.futures.as_completed(futures):
                url, page = futures[future]
                data = future.result()
                seen.add(url)
                path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lstrip('/')
                dest = OUT / prefix / (path + '/index.html' if page and path else 'index.html' if page else path)
                if page or path.endswith(('.js', '.css')):
                    text = data.decode()
                    if page:
                        if '<html' not in text or '<main' not in text:
                            raise RuntimeError('Invalid page response: ' + url)
                        text = re.sub(r'<script>\(function\(\)\{function c\(\).*?</script>', '', text, flags=re.S)
                    raw = text.replace('\\"', '"').replace('\\/', '/')
                    for match in ASSET.finditer(raw):
                        value = match.group().split('#')[0]
                        if '{' in value or '}' in value:
                            continue
                        asset_url = urllib.parse.urljoin(origin+'/' if value.startswith('_next/') else url, value)
                        if asset_url.startswith(origin + '/') and asset_url not in seen and asset_url not in batch:
                            queue[asset_url] = False
                    data = rewrite(text, base).encode()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                count += 1
        print(origin, count, 'downloaded;', len(queue), 'remaining', flush=True)
    return count

def optimize():
    from PIL import Image, ImageOps
    replacements = {}
    report = []
    for path in sorted(OUT.rglob('*')):
        if path.suffix.lower() not in {'.jpg', '.jpeg', '.png'} or path.stat().st_size < 160_000:
            continue
        with Image.open(path) as original:
            if getattr(original, 'is_animated', False) or max(original.size) > 16383:
                continue
            image = ImageOps.exif_transpose(original)
            if image.mode not in ('RGB', 'RGBA'):
                image = image.convert('RGBA' if 'transparency' in image.info else 'RGB')
            data = io.BytesIO()
            # Keep every pixel dimension. PNG graphics use lossless encoding.
            image.save(data, format='WEBP', quality=95, method=6,
                       lossless=path.suffix.lower() == '.png',
                       icc_profile=original.info.get('icc_profile', b''))
            payload = data.getvalue()
            before = path.stat().st_size
            if len(payload) >= before * 0.85:
                continue
            output = path.with_name(path.name + '.optimized.webp')
            output.write_bytes(payload)
            with Image.open(output) as verified:
                assert verified.size == image.size
            old = path.relative_to(OUT).as_posix()
            new = output.relative_to(OUT).as_posix()
            replacements[old] = new
            if old.startswith('sunseeker/'):
                replacements[old.removeprefix('sunseeker/')] = new.removeprefix('sunseeker/')
            report.append({'file': old, 'before': before, 'after': len(payload), 'pixels': image.size})
            print(old, before, '->', len(payload), flush=True)
    mapping = dict(replacements)
    mapping.update({urllib.parse.quote(k): urllib.parse.quote(v) for k, v in replacements.items()})
    pattern = re.compile('|'.join(re.escape(k) for k in sorted(mapping, key=len, reverse=True))) if mapping else None
    for path in OUT.rglob('*'):
        if path.suffix in {'.html', '.js', '.css', '.json'} and pattern:
            text = path.read_text()
            path.write_text(pattern.sub(lambda m: mapping[m[0]], text))
    (OUT / 'image-optimization-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('Optimized', len(report), 'images:', sum(r['before'] for r in report), '->', sum(r['after'] for r in report), flush=True)

if __name__ == '__main__':
    # Install only in the ephemeral publishing environment, not the visitor browser.
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow>=12.1,<13'])
    OUT.mkdir(exist_ok=True)
    total = sum(mirror(*site) for site in SITES)
    assert total > 150, 'Incomplete export'
    optimize()
    (OUT / '.nojekyll').touch()
    print('Complete:', total, 'source files; originals retained')
