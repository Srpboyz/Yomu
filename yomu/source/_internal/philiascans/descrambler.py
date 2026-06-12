import base64
import hmac
import hashlib
import struct
from io import BytesIO

from Crypto.Cipher import AES
from PIL import Image

AES_MAGIC = bytes.fromhex("ff02")


def get_chapter_key(fragment: str) -> tuple[bool, str, bytes, int]:
    parts = fragment.split(";", maxsplit=5)

    is_scrambled = bool(parts[0])
    mime_type, chapter_key_b64 = parts[1:3]
    grid_size = int(parts[3])
    payload_a, payload_b = parts[4:]

    if payload_a and payload_a != "null" and payload_b and payload_b != "null":
        a = base64.b64decode(payload_a)
        b = base64.b64decode(payload_b)
        chapter_key = bytes(x ^ y for x, y in zip(a, b))
    else:
        chapter_key = base64.b64decode(chapter_key_b64)

    return is_scrambled, mime_type, chapter_key, grid_size


def mac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def xor_keystream(chapter_key: bytes, page_index: int, data: bytes) -> bytes:
    data = bytearray(data)
    num_blocks = (len(data) + 31) // 32
    for i in range(num_blocks):
        ks = mac(chapter_key, f"page:{page_index}:{i}".encode())

        start = i * 32
        end = min(start + 32, len(data))
        for j in range(end - start):
            data[start + j] ^= ks[j]

    return bytes(data)


def aes_ctr_cipher(chapter_key: bytes, page_index: int, data: bytes) -> bytes:
    derived_key = mac(chapter_key, f"aesctr:{page_index}".encode())

    cipher = AES.new(
        derived_key,
        AES.MODE_CTR,
        nonce=b"",
        initial_value=0,
    )

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
        img.save(out, format="JPEG", quality=90)
    elif mt == "image/png":
        img.save(out, format="PNG", quality=100)
    else:
        img.save(out, format="WEBP", quality=100)

    return out.getvalue()


def process_image(response, index: int) -> bytes | None:
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
    required = 6 if is_aes_scheme else 4
    if len(body) < required:
        return None

    if not is_aes_scheme:
        stream.seek(0)

    header = stream.read(4)
    if len(header) != 4:
        return None

    original_width, original_height = struct.unpack(">HH", header)
    plain_data = (
        aes_ctr_cipher(chapter_key, index, stream.read())
        if is_aes_scheme
        else xor_keystream(chapter_key, index, stream.read())
    )
    bitmap = Image.open(BytesIO(plain_data)).convert("RGBA")

    if not is_scrambled:
        return encode_image(bitmap, mime_type)

    image = unscramble(
        bitmap, chapter_key, index, grid_size, original_width, original_height
    )
    return encode_image(image, mime_type)
