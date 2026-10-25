import base64
from functools import reduce


TABLE_1 = "yINlmUNho8VYJT+ibTIP+9ESiULpVEtMOoD6U6lRE0R/xwXo/Xp9NrUgC4cw/Lmo33vUyjUE40kUoEWIr/fxfNNcq2s79ShQ5NhNrFnJ4hXPwOu/SuXzIbuTQKGFvfm08E9jvCfqAtoDqvQq3dVWPQFmJjgvkISBeXY3BgANR+yVnjGbcxZ47d6kLNfZPIayTq3/YGySb1KuVZodWp/WGNAO5pfMcpaK53Hhs0allBszaMaxuouOwdxbwgxIw6YunSsXjI05Yi0j9j4eHKfSXR8Ifo/Od+8iamRfCXTyvm7NGRGYdcQ0ywcK/u6RXhrbcCm4t2eCtrDgQVecJGkQ+A=="
KEY_1 = "0Ec58JOY3uBzJK9m3zqIOpdlF7UFiax9DmA="
TABLE_2 = "IUFltCxD3Oc2cwCgkJffthaOg9cgPUb0LgW6H/VtfcF0kc5F25t+aWj6JH9VOhOaY0rAFdUxlDnl5BLNvwEJvQtP5qcw7vdb/K+chnbwnspSHT8mz5lqwz41TezG0hkO06FTjJZhsyNuFLDpD2ZZxQj/QIRcF90zpmQ7Byu483WsQqUE0C342HL+JXngRB6fRzxRyVTaKu83h7UYTJ0QMt6ixFh6S3F8gqkKwrGTL3jHNBsD45UnifK8+RGtishQV2K3rujLKEkiZxpr2dYcudFW4oFsDKhad3CLBvuyTqsCo4B7mL5IKQ1vXo/MOOvq1I1d8ar9X6Ttu5KF4fZgiA=="
KEY_2 = "AAdjb1iPY8CiDmq9H34tKTBF8a3oDQ=="
TABLE_3 = "NQHlu1/wVO5EmkwQymF810qqY2xG1k2obcas4Z9mCsPEIFl9pRIjFxbJ7ybMHbBckT5Ton85E0FOeHezbh/mjlEYpmpnlXOS8dgrqeq2KfxImTh1YK9y0PeMNhzA1OQzSY9brYOJq/l2QnE/hwOeZIhPixVSKIUlDb5vLcH6RWKxkIEMuP0bDwIqQ71AJJaEaMJL7A6YtyIwoRT+L5v4aZzodN/0+3nOGsfblFjgxSfPzVDjNFeNl5P26+kEC/8AHgdrpAbt3hHz3HrRN1Y6e+JHgF7ncFWnoF0y3THL1S71WgWGCa6KtSzTCCG58n68nTyj2T3Sshk7utqCtMi/ZQ=="
KEY_3 = "DELOJgPsVaCcblDtTGMdHzM="
STAGES = (
    (base64.b64decode(TABLE_1), base64.b64decode(KEY_1), 0x5A),
    (base64.b64decode(TABLE_2), base64.b64decode(KEY_2), 0x35),
    (base64.b64decode(TABLE_3), base64.b64decode(KEY_3), 0xBA),
)


def encrypt_stage(data: bytes, table: bytes, key: bytes, iv: int) -> bytes:
    def step(state, byte):
        previous, output = state
        value = table[byte ^ key[len(output) % len(key)] ^ previous]
        return value, output + bytes([value])

    return reduce(step, data, (iv, b""))[1]


def encrypt(data: bytes) -> bytes:
    return reduce(lambda current, stage: encrypt_stage(current, *stage), STAGES, data)


def normalize_params(params: dict) -> list[tuple[str, str]]:
    return sorted(
        (
            (key, str(value))
            for key, values in params.items()
            for value in (values if isinstance(values, (list, tuple)) else [values])
        ),
        key=lambda item: item[0],
    )


def build_sorted_query(path: str, params: dict) -> str:
    pairs = normalize_params(params)

    def indexed_keys(pairs):
        last_key = None
        index = 0

        for key, value in pairs:
            if key.endswith("[]"):
                if key != last_key:
                    index = 0
                last_key = key
                new_key = key[:-2] + f"[{index}]"
                index += 1
            else:
                last_key = key
                new_key = key

            yield f"{new_key}={value}"

    query = "&".join(indexed_keys(pairs))
    return path + (f"?{query}" if query else "")


def get_vrf_token(path: str, params: dict) -> str:
    signing_input = build_sorted_query(path, params)
    encrypted = encrypt(signing_input.encode("utf-8"))
    return base64.urlsafe_b64encode(encrypted).decode("ascii").rstrip("=")
