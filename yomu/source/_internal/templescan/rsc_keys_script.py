import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://templetoons.com"
CHUNK_PATH = "/_next/static/chunks/"

HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Priority": "u=0, i",
    "Sec-CH-UA": '"Not?A_Brand";v="24", "Chromium";v="152"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Linux"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 Safari/537.36"
    ),
    # Put your own current cf_clearance here if required.
    # "Cookie": "cf_clearance=...",
}


# These are the logical names registered by module 14834.
RSC_FIELDS = [
    "Chapter",
    "images",
    "chapter_slug",
    "title",
    "Season",
    "price",
    "chapter_name",
    "series_slug",
]


def map_rsc_keys(source: str) -> dict[str, str] | None:
    """Extract the RSC field mapping from Webpack module 14834."""

    # 1. Locate module 14834
    module_match = re.search(
        r'(?:^|[,{\s])\s*["\']?14834["\']?\s*:\s*function\s*\(', source
    )

    if not module_match:
        return None

    module_start = module_match.end()

    # Find the next Webpack module boundary.
    end_match = re.search(
        r'\}\s*,\s*["\']?\d+["\']?\s*:\s*function\s*\(', source[module_start:]
    )
    module = (
        source[module_start : module_start + end_match.start() + 1]
        if end_match
        else source[module_start:]
    )

    # 2. Extract the seven-character salt
    salt_match = re.search(
        r'["\']([a-zA-Z0-9]+)["\']\s*'
        r"\.match\(/\.\{7\}/g\)\s*\|\|\s*\[\]",
        module,
    )
    if not salt_match:
        return None

    # JavaScript match(/.{7}/g) ignores incomplete
    # trailing characters, so don't require divisibility.
    chunks = re.findall(r".{7}", salt_match.group(1))
    if not chunks:
        return None

    # 3. Extract initial position and increment
    rotation_match = re.search(
        r"(?P<array>[A-Za-z_$]\w*)\s*=\s*"
        r"[A-Za-z_$]\w*\.slice\(\)\s*,\s*"
        r"(?P<index>[A-Za-z_$]\w*)\s*=\s*"
        r"(?P<initial>\d+)\s*;"
        r"[\s\S]{0,300}?"
        r"[A-Za-z_$]\w*\s*=\s*\(\s*\)\s*=>\s*"
        r"(?P=array)\.splice\(\s*"
        r"(?P=index)\s*=\s*\(\s*"
        r"(?P=index)\s*\+\s*"
        r"(?P<increment>\d+)\s*\)\s*%\s*"
        r"(?P=array)\.length\s*,\s*1\s*\)\s*\[\s*0\s*\]",
        module,
    )
    if not rotation_match:
        return None

    position = int(rotation_match.group("initial"))
    increment = int(rotation_match.group("increment"))

    # 4. Find the registration function
    registrar_match = re.search(
        r"function\s+([A-Za-z_$]\w*)\s*"
        r"\(\s*[A-Za-z_$]\w*\s*\)\s*\{\s*"
        r"let\s+[A-Za-z_$]\w*\s*=\s*"
        r"[A-Za-z_$]\w*\(\s*[A-Za-z_$]\w*\+\+\s*\)",
        module,
    )
    if not registrar_match:
        return None

    # 5. Extract registered logical field names
    registration_pattern = (
        rf"\b{re.escape(registrar_match.group(1))}\s*"
        r'\(\s*["\']([^"\']+)["\']\s*\)'
    )

    fields = re.findall(registration_pattern, module)
    if not fields:
        return None

    # 6. Reproduce JavaScript splice algorithm
    remaining = chunks.copy()
    keys = {}
    for field in fields:
        if not remaining:
            return None

        position = (position + increment) % len(remaining)
        key = remaining.pop(position)

        if len(key) != 7:
            return None
        if key in keys.values():
            return None
        keys[field] = key

    return keys


def get_next_js_chunks(session: requests.Session, url: str) -> list[str]:
    "Finds the Next.js chunks"
    print(f"GET {url}")
    response = session.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    chunks = []
    for script in soup.select("script[src]"):
        src = script.get("src")
        if not src or CHUNK_PATH not in src:
            continue

        chunk_url = urljoin(BASE_URL, src)
        if chunk_url not in chunks:
            chunks.append(chunk_url)
    return chunks


def find_rsc_keys() -> dict[str, str]:
    "Searches for Next.js urls with module 14834"
    session = requests.Session()
    session.headers.update(HEADERS)

    chunks = get_next_js_chunks(session, f"{BASE_URL}/comics")
    print(f"Found {len(chunks)} Next.js chunks")

    for chunk_url in chunks:
        print(f"Checking: {chunk_url}")
        try:
            response = session.get(chunk_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"  Request failed: {exc}")
            continue

        source = response.text
        if not re.search(r'(?:^|[,{\s])\s*["\']?14834["\']?\s*:\s*function', source):
            continue

        print("  Found module 14834")
        keys = map_rsc_keys(source)
        if keys:
            return keys
        break

    print("  Could not extract mapping from this chunk")
    raise RuntimeError("Could not determine the site's RSC field-key table")


def main():
    keys = find_rsc_keys()
    print("\nRSC KEYS:")
    for field, key in keys.items():
        print(f"  {field:15} -> {key}")


if __name__ == "__main__":
    main()
