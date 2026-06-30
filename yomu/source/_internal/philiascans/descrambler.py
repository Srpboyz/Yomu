import base64
import hmac
import hashlib
import struct
from io import BytesIO

from Crypto.Cipher import AES
from PIL import Image

from yomu.core.network import Response

AES_MAGIC = bytes.fromhex("ff02")
CHACHA_MAGIC = bytes.fromhex("ff03")
AES4_MAGIC = bytes.fromhex("ff04")


def get_chapter_key(fragment: str) -> tuple[bool, str, bytes, int]:
    parts = fragment.split(";", maxsplit=5)

    is_scrambled = bool(int(parts[0]))
    mime_type, chapter_key_b64 = parts[1:3]
    grid_size = int(parts[3])
    payload_a, payload_b = parts[4:]

    if payload_a and payload_a != "null" and payload_b and payload_b != "null":
        a = base64.b64decode(payload_a)
        b = base64.b64decode(payload_b)
        chapter_key = bytes(a[i] ^ b[i] for i in range(min(32, len(a), len(b))))
    else:
        chapter_key = base64.b64decode(chapter_key_b64)

    return is_scrambled, mime_type, chapter_key, grid_size


def mac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def rotl32(v: int, n: int) -> int:
    return ((v << n) | (v >> (32 - n))) & 0xFFFFFFFF


def quarter_round(state: list[int], a: int, b: int, c: int, d: int):
    state[a] = (state[a] + state[b]) & 0xFFFFFFFF
    state[d] = rotl32(state[d] ^ state[a], 16)
    state[c] = (state[c] + state[d]) & 0xFFFFFFFF
    state[b] = rotl32(state[b] ^ state[c], 12)
    state[a] = (state[a] + state[b]) & 0xFFFFFFFF
    state[d] = rotl32(state[d] ^ state[a], 8)
    state[c] = (state[c] + state[d]) & 0xFFFFFFFF
    state[b] = rotl32(state[b] ^ state[c], 7)


def chacha20_block(key: bytes, nonce: bytes, counter: int) -> bytes:
    state = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]
    state.extend(struct.unpack("<8I", key))
    state.append(counter)
    state.extend(struct.unpack("<3I", nonce))

    working = state.copy()
    for _ in range(10):
        quarter_round(working, 0, 4, 8, 12)
        quarter_round(working, 1, 5, 9, 13)
        quarter_round(working, 2, 6, 10, 14)
        quarter_round(working, 3, 7, 11, 15)
        quarter_round(working, 0, 5, 10, 15)
        quarter_round(working, 1, 6, 11, 12)
        quarter_round(working, 2, 7, 8, 13)
        quarter_round(working, 3, 4, 9, 14)

    out = bytearray(64)
    for i in range(16):
        struct.pack_into("<I", out, i * 4, (working[i] + state[i]) & 0xFFFFFFFF)

    return bytes(out)


def chacha20_decrypt(chapter_key: bytes, page_index: int, data: bytes) -> bytes:
    key = mac(chapter_key, f"cc:{page_index}".encode())
    nonce = b"\0" * 12
    data = bytearray(data)
    counter, offset = 0, 0

    while offset < len(data):
        block = chacha20_block(key, nonce, counter)
        counter += 1

        size = min(64, len(data) - offset)
        for i in range(size):
            data[offset + i] ^= block[i]
        offset += size

    return bytes(data)


def aes_ctr_cipher(
    chapter_key: bytes, page_index: int, data: bytes, is_aes4: bool
) -> bytes:
    aes_str = "aesctr4" if is_aes4 else "aesctr"
    derived_key = mac(chapter_key, f"{aes_str}:{page_index}".encode())
    cipher = AES.new(derived_key, AES.MODE_CTR, nonce=b"", initial_value=0)
    return cipher.decrypt(data)


def unscramble(
    bitmap: Image.Image,
    chapter_key: bytes,
    page_index: int,
    grid_size: int,
    original_width: int,
    original_height: int,
) -> Image.Image:
    tile_w = bitmap.width // grid_size
    tile_h = bitmap.height // grid_size
    n = grid_size * grid_size
    order = list(range(n))

    if n >= 2:
        mac1 = lambda d: mac(chapter_key, d)
        tiles_sig = mac1(f"tiles:{page_index}".encode())
        mac2 = lambda d: mac(tiles_sig, d)

        counter, buf, idx = 0, [], 8

        def next_rand():
            nonlocal buf, idx, counter

            if idx >= 8:
                raw = mac2(f"perm:{counter}".encode())
                counter += 1
                buf[:] = struct.unpack("<8I", raw)
                idx = 0

            val = buf[idx]
            idx += 1
            return val & 0xFFFFFFFF

        for i in range(n - 1, 0, -1):
            j = next_rand() % (i + 1)
            order[i], order[j] = order[j], order[i]

    inverse = [0] * n
    for i in range(n):
        inverse[order[i]] = i

    result = Image.new("RGBA", (original_width, original_height))

    for t in range(n):
        src = inverse[t]

        sx = (src % grid_size) * tile_w
        sy = (src // grid_size) * tile_h

        dx = (t % grid_size) * tile_w
        dy = (t // grid_size) * tile_h

        tile = bitmap.crop((sx, sy, sx + tile_w, sy + tile_h))
        result.paste(tile, (dx, dy))

    return result


def encode_image(img: Image.Image, mime_type: str) -> bytes:
    out = BytesIO()

    mt = mime_type.lower()
    if mt in ("image/jpeg", "image/jpg"):
        img.save(out, format="JPEG", quality=100)
    elif mt == "image/png":
        img.save(out, format="PNG", quality=100)
    else:
        img.save(out, format="WEBP", quality=100)

    return out.getvalue()


def process_image(response: Response, index: int) -> bytes | None:
    fragment = response.url().fragment()
    if not fragment:
        return None

    is_scrambled, mime_type, chapter_key, grid_size = get_chapter_key(fragment)

    body = bytes(response.read_all())
    stream = BytesIO(body)
    header = stream.read(2)
    if len(header) < 2:
        return None

    is_aes_scheme = header == AES_MAGIC
    is_chacha_scheme = header == CHACHA_MAGIC
    is_aes4_scheme = header == AES4_MAGIC
    has_scheme_magic = is_aes_scheme or is_chacha_scheme or is_aes4_scheme
    if not has_scheme_magic:
        return body

    required = 6 if has_scheme_magic else 4
    if len(body) < required:
        return None

    if not has_scheme_magic:
        stream.seek(0)

    header = stream.read(4)
    if len(header) != 4:
        return None

    original_width, original_height = struct.unpack(">HH", header)
    plain_data = (
        aes_ctr_cipher(chapter_key, index, stream.read(), True)
        if is_aes4_scheme
        else aes_ctr_cipher(chapter_key, index, stream.read(), False)
        if is_aes_scheme
        else chacha20_decrypt(chapter_key, index, stream.read())
    )

    if not is_scrambled or is_chacha_scheme or is_aes4_scheme:
        return plain_data

    bitmap = Image.open(BytesIO(plain_data)).convert("RGBA")
    image = unscramble(
        bitmap, chapter_key, index, grid_size, original_width, original_height
    )
    return encode_image(image, mime_type)
