import base64
import urllib.parse

KEYS = [
    "JxTcdyiA5GZxnbrmthXBQfU2IMTKcY1+3nNhbq98Sgo=",
    "3PordjODbhqla382Cxapmo/1JiABJQcjiJj1+48gTJ4=",
    "OaKvnI5ARA==",
    "MHNBHYWA7lvy867fXgvGcJwWDk79KqUJUVFsh3RwnnI=",
    "8i0Cru/VJBSVB2Y1GcMDVpzx2WepOcfnWdd81yxICl4=",
    "Fyskubz8VvA=",
    "B46L1x+UeWP+19cRpQ+OZvdLAK9EHID8g3mSgn57tew=",
    "DTSTmUt6LpDUw9r1lSQqyb3YlFTzruT8tk8wUGkwehQ=",
    "vY/meeI=",
    "7xWfIF5THL5LAnRgAARg+4mjWHPU9n3PQwvzbaMNi+Q=",
    "bewtiTuV+HJk56xxkf2iCljLgruCpBmN9BgE8i6gc9M=",
    "/Xcb2zAu8AU=",
    "WgeCQ3T8R51uTwVSiVa7Zy0dN6JOg6Z5JleMS+HV8Aw=",
    "yXayUVFrrcW56jQCEfZzuCidjpnWKjTDUNT7XeX9i7k=",
    "tSLco2w=",
]


def get_key_bytes(index: int) -> list[int]:
    try:
        decoded = base64.b64decode(KEYS[index])
        return [b & 0xFF for b in decoded]
    except Exception:
        return []


def rc4(key: list[int], data: list[int]) -> list[int]:
    if not key:
        return data
    s = list(range(256))
    j = 0

    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) % 256
        s[i], s[j] = s[j], s[i]

    i = j = 0
    out = []

    for byte in data:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(byte ^ s[(s[i] + s[j]) % 256])

    return out


# Mutation functions
def get_mut_key(mk: list[int], idx: int) -> int:
    return mk[idx % 32] if mk and (idx % 32) < len(mk) else 0


def op_shift_right7_left1(e: int) -> int:
    return ((e >> 7) | (e << 1)) & 255


def op_shift_left1_right7(e: int) -> int:
    return ((e << 1) | (e >> 7)) & 255


def op_shift_right2_left6(e: int) -> int:
    return ((e >> 2) | (e << 6)) & 255


def op_shift_left4_right4(e: int) -> int:
    return ((e << 4) | (e >> 4)) & 255


def op_shift_right4_left4(e: int) -> int:
    return ((e >> 4) | (e << 4)) & 255


def mutate(
    data: list[int],
    mut_key: list[int],
    pref_key: list[int],
    pref_key_limit: int,
    round_num: int,
) -> list[int]:
    out = []
    for o, byte in enumerate(data):
        if o < pref_key_limit and o < len(pref_key):
            out.append(pref_key[o])
        n = byte ^ get_mut_key(mut_key, o)
        pos = o % 10
        if round_num == 1:
            if pos == 0:
                n = op_shift_right7_left1(n)
            elif pos == 1:
                n = n ^ 37
            elif pos == 2:
                n = n ^ 81
            elif pos == 3:
                n = n ^ 147
            elif pos == 4:
                n = op_shift_right2_left6(n)
            elif pos in (5, 8):
                n = op_shift_right4_left4(n)
            elif pos == 6:
                n = n ^ 218
            elif pos == 7:
                n = (n + 159) & 255
            elif pos == 9:
                n = n ^ 180
        elif round_num == 2:
            if pos in (0, 9):
                n = n ^ 180
            elif pos == 1:
                n = op_shift_left1_right7(n)
            elif pos == 2:
                n = n ^ 147
            elif pos == 3:
                n = op_shift_right7_left1(n)
            elif pos == 4:
                n = op_shift_right2_left6(n)
            elif pos == 5:
                n = op_shift_right4_left4(n)
            elif pos in (6, 8):
                n = (n + 159) & 255
            elif pos == 7:
                n = (n + 34) & 255
        elif round_num == 3:
            if pos == 0:
                n = n ^ 81
            elif pos == 1:
                n = op_shift_right4_left4(n)
            elif pos in (2, 9):
                n = op_shift_left4_right4(n)
            elif pos == 3:
                n = n ^ 37
            elif pos == 4:
                n = (n + 159) & 255
            elif pos == 5:
                n = op_shift_left1_right7(n)
            elif pos == 6:
                n = n ^ 180
            elif pos == 7:
                n = (n + 34) & 255
            elif pos == 8:
                n = op_shift_right2_left6(n)
        elif round_num == 4:
            if pos in (0, 7):
                n = n ^ 218
            elif pos in (1, 4):
                n = op_shift_left1_right7(n)
            elif pos == 2:
                n = op_shift_right7_left1(n)
            elif pos == 3:
                n = (n + 159) & 255
            elif pos in (5, 8):
                n = n ^ 180
            elif pos == 6:
                n = n ^ 147
            elif pos == 9:
                n = n ^ 37
        elif round_num == 5:
            if pos == 0:
                n = op_shift_left4_right4(n)
            elif pos in (1, 3):
                n = n ^ 147
            elif pos == 2:
                n = (n + 34) & 255
            elif pos in (4, 9):
                n = n ^ 218
            elif pos in (5, 7):
                n = op_shift_left1_right7(n)
            elif pos == 6:
                n = n ^ 180
            elif pos == 8:
                n = op_shift_right2_left6(n)
        out.append(n & 255)
    return out


def round1(data: list[int]) -> list[int]:
    return rc4(get_key_bytes(0), mutate(data, get_key_bytes(1), get_key_bytes(2), 7, 1))


def round2(data: list[int]) -> list[int]:
    return rc4(get_key_bytes(3), mutate(data, get_key_bytes(4), get_key_bytes(5), 8, 2))


def round3(data: list[int]) -> list[int]:
    return rc4(get_key_bytes(6), mutate(data, get_key_bytes(7), get_key_bytes(8), 5, 3))


def round4(data: list[int]) -> list[int]:
    return rc4(
        get_key_bytes(9), mutate(data, get_key_bytes(10), get_key_bytes(11), 8, 4)
    )


def round5(data: list[int]) -> list[int]:
    return rc4(
        get_key_bytes(12), mutate(data, get_key_bytes(13), get_key_bytes(14), 5, 5)
    )


def generate_hash(path: str) -> str:
    encoded = (
        urllib.parse.quote(path, safe="~")
        .replace("+", "%20")
        .replace("*", "%2A")
        .replace("%7E", "~")
    )

    initial_bytes = [b & 0xFF for b in encoded.encode("ascii")]

    r1 = round1(initial_bytes)
    r2 = round2(r1)
    r3 = round3(r2)
    r4 = round4(r3)
    r5 = round5(r4)

    return base64.urlsafe_b64encode(bytes(r5)).rstrip(b"=").decode("ascii")
