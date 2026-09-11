"""Export the published portfolio."""
import concurrent.futures
import pathlib
import re
import subprocess
import urllib.parse
OUT = pathlib.Path('github-public')
SITES = [
 ('https://weiwei-design-portfolio.weiweiwei760.chatgpt.site', '/portfolio/', ['', 'work/dreame', 'work/aiper', 'work/taildao', 'work/luminousidol', 'work/yadiyadi', 'work/ceramics', 'work/whobeast', 'work/ip', 'work/more']),
 ('https://sunseeker-design-portfolio.weiweiwei760.chatgpt.site', '/portfolio/sunseeker/', ['']),
]
ASSET = re.compile(r'''(?:https://|/|\./)[^\s<>"'\\]*?\.(?:js|css|jpg|jpeg|png|webp|svg|gif|mp4|webm|woff2?|ico)(?:\?[^\s<>"'\\]*)?''')
def fetch(url):
    result = subprocess.run(['curl', '-L', '--fail', '--retry', '3', '--max-time', '180', '--silent', '--show-error', url], capture_output=True)
    if result.returncode:
        raise RuntimeError(url + ': ' + result.stderr.decode()[-300:])
    return result.stdout

def rewrite(text, base):
    text = re.sub(r'''(["'])(/)(?!/)''', lambda m: m[1] + base, text)
    text = re.sub(r'url\(/(?!/)', 'url(' + base, text)
    for origin, target, _ in SITES:
        text = text.replace(origin + '/', target).replace(origin, target.rstrip('/'))
    return text

def mirror(origin, base, routes):
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
                        asset_url = urllib.parse.urljoin(url, value)
                        if asset_url.startswith(origin + '/') and asset_url not in seen and asset_url not in batch:
                            queue[asset_url] = False
                    data = rewrite(text, base).encode()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                count += 1
        print(origin, count, 'downloaded;', len(queue), 'remaining', flush=True)
    return count

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    total = sum(mirror(*site) for site in SITES)
    (OUT / '.nojekyll').touch()
    assert total > 200, 'Incomplete export'
    assert len(list(OUT.rglob('index.html'))) == 11
    print('Complete:', total, 'files')

