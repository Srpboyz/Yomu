import base64
import urllib.parse

KEYS = [
    "13YDu67uDgFczo3DnuTIURqas4lfMEPADY6Jaeqky+w=",
    "yEy7wBfBc+gsYPiQL/4Dfd0pIBZFzMwrtlRQGwMXy3Q=",
    "yrP+EVA1Dw==",
    "vZ23RT7pbSlxwiygkHd1dhToIku8SNHPC6V36L4cnwM=",
    "QX0sLahOByWLcWGnv6l98vQudWqdRI3DOXBdit9bxCE=",
    "WJwgqCmf",
    "BkWI8feqSlDZKMq6awfzWlUypl88nz65KVRmpH0RWIc=",
    "v7EIpiQQjd2BGuJzMbBA0qPWDSS+wTJRQ7uGzZ6rJKs=",
    "1SUReYlCRA==",
    "RougjiFHkSKs20DZ6BWXiWwQUGZXtseZIyQWKz5eG34=",
    "LL97cwoDoG5cw8QmhI+KSWzfW+8VehIh+inTxnVJ2ps=",
    "52iDqjzlqe8=",
    "U9LRYFL2zXU4TtALIYDj+lCATRk/EJtH7/y7qYYNlh8=",
    "e/GtffFDTvnw7LBRixAD+iGixjqTq9kIZ1m0Hj+s6fY=",
    "xb2XwHNB",
]


def get_key_bytes(index):
    try:
        b64 = KEYS[index]
        decoded = base64.b64decode(b64)
        return [b & 0xFF for b in decoded]
    except Exception:
        return []


def rc4(key, data):
    if not key:
        return data[:]

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
def mutS(e):
    return (e + 143) % 256


def mutL(e):
    return ((e >> 1) | (e << 7)) & 255


def mutC(e):
    return (e + 115) % 256


def mutM(e):
    return e ^ 177


def mutF(e):
    return (e - 188 + 256) % 256


def mutG(e):
    return ((e << 2) | (e >> 6)) & 255


def mutH(e):
    return (e - 42 + 256) % 256


def mutDollar(e):
    return ((e << 4) | (e >> 4)) & 255


def mutB(e):
    return (e - 12 + 256) % 256


def mutUnderscore(e):
    return (e - 20 + 256) % 256


def mutY(e):
    return ((e >> 1) | (e << 7)) & 255


def mutK(e):
    return (e - 241 + 256) % 256


def get_mut_key(mk, idx):
    return mk[idx % 32] if mk and (idx % 32) < len(mk) else 0


def round1(data):
    enc = rc4(get_key_bytes(0), data)
    mut_key = get_key_bytes(1)
    pref_key = get_key_bytes(2)

    out = []
    for i, val in enumerate(enc):
        if i < 7 and i < len(pref_key):
            out.append(pref_key[i])

        v = val ^ get_mut_key(mut_key, i)

        mod = i % 10
        if mod in (0, 9):
            v = mutC(v)
        elif mod == 1:
            v = mutB(v)
        elif mod == 2:
            v = mutY(v)
        elif mod == 3:
            v = mutDollar(v)
        elif mod in (4, 6):
            v = mutH(v)
        elif mod == 5:
            v = mutS(v)
        elif mod == 7:
            v = mutK(v)
        elif mod == 8:
            v = mutL(v)

        out.append(v & 255)

    return out


def round2(data):
    enc = rc4(get_key_bytes(3), data)
    mut_key = get_key_bytes(4)
    pref_key = get_key_bytes(5)

    out = []
    for i, val in enumerate(enc):
        if i < 6 and i < len(pref_key):
            out.append(pref_key[i])

        v = val ^ get_mut_key(mut_key, i)

        mod = i % 10
        if mod in (0, 8):
            v = mutC(v)
        elif mod == 1:
            v = mutB(v)
        elif mod in (2, 6):
            v = mutDollar(v)
        elif mod == 3:
            v = mutH(v)
        elif mod in (4, 9):
            v = mutS(v)
        elif mod == 5:
            v = mutK(v)
        elif mod == 7:
            v = mutUnderscore(v)

        out.append(v & 255)

    return out


def round3(data):
    enc = rc4(get_key_bytes(6), data)
    mut_key = get_key_bytes(7)
    pref_key = get_key_bytes(8)

    out = []
    for i, val in enumerate(enc):
        if i < 7 and i < len(pref_key):
            out.append(pref_key[i])

        v = val ^ get_mut_key(mut_key, i)

        mod = i % 10
        if mod == 0:
            v = mutC(v)
        elif mod == 1:
            v = mutF(v)
        elif mod in (2, 8):
            v = mutS(v)
        elif mod == 3:
            v = mutG(v)
        elif mod == 4:
            v = mutY(v)
        elif mod == 5:
            v = mutM(v)
        elif mod == 6:
            v = mutDollar(v)
        elif mod == 7:
            v = mutK(v)
        elif mod == 9:
            v = mutB(v)

        out.append(v & 255)

    return out


def round4(data):
    enc = rc4(get_key_bytes(9), data)
    mut_key = get_key_bytes(10)
    pref_key = get_key_bytes(11)

    out = []
    for i, val in enumerate(enc):
        if i < 8 and i < len(pref_key):
            out.append(pref_key[i])

        v = val ^ get_mut_key(mut_key, i)

        mod = i % 10
        if mod == 0:
            v = mutB(v)
        elif mod in (1, 9):
            v = mutM(v)
        elif mod in (2, 7):
            v = mutL(v)
        elif mod in (3, 5):
            v = mutS(v)
        elif mod in (4, 6):
            v = mutUnderscore(v)
        elif mod == 8:
            v = mutY(v)

        out.append(v & 255)

    return out


def round5(data):
    enc = rc4(get_key_bytes(12), data)
    mut_key = get_key_bytes(13)
    pref_key = get_key_bytes(14)

    out = []
    for i, val in enumerate(enc):
        if i < 6 and i < len(pref_key):
            out.append(pref_key[i])

        v = val ^ get_mut_key(mut_key, i)

        mod = i % 10
        if mod == 0:
            v = mutUnderscore(v)
        elif mod in (1, 7):
            v = mutS(v)
        elif mod == 2:
            v = mutC(v)
        elif mod in (3, 5):
            v = mutM(v)
        elif mod == 4:
            v = mutB(v)
        elif mod == 6:
            v = mutF(v)
        elif mod == 8:
            v = mutDollar(v)
        elif mod == 9:
            v = mutG(v)

        out.append(v & 255)

    return out


def generate_hash(path: str):
    base_string = f"{path}:0:1"

    encoded = urllib.parse.quote(base_string, safe="~")
    encoded = encoded.replace("+", "%20").replace("*", "%2A")

    initial_bytes = [b & 0xFF for b in encoded.encode("ascii")]

    r1 = round1(initial_bytes)
    r2 = round2(r1)
    r3 = round3(r2)
    r4 = round4(r3)
    r5 = round5(r4)

    final_bytes = bytes(r5)

    return base64.urlsafe_b64encode(final_bytes).rstrip(b"=").decode("ascii")
