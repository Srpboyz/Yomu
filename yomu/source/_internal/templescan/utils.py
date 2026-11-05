def imul(a: int, b: int) -> int:
    return (
        ((((a >> 16) * b) & 0xFFFFFFFF) << 16)
        + (((a & 0xFFFF) * b) & 0xFFFFFFFF)
        & 0xFFFFFFFF
    )  # fmt: skip


def decrypt_image_string(encoded_str: str, page_index: int, key: str) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    bits, buffer = 0, 0
    byte_array = bytearray()

    for char in encoded_str:
        if char not in alphabet:
            continue
        val = alphabet.index(char)
        buffer = (buffer << 6) | val
        bits += 6
        if bits >= 8:
            bits -= 8
            byte_array.append((buffer >> bits) & 0xFF)

    seed = imul(page_index + 1, 795580989) ^ len(key)
    for char in key:
        seed = imul(seed ^ ord(char), 2048675417)
        seed ^= (seed >> 15) & 0xFFFFFFFF

    seed = seed & 0xFFFFFFFF
    if seed == 0:
        seed = 1

    decrypted_bytes = bytearray(len(byte_array))
    r = seed
    for i in range(len(byte_array)):
        r ^= (r << 13) & 0xFFFFFFFF
        r ^= (r >> 17) & 0xFFFFFFFF
        r ^= (r << 5) & 0xFFFFFFFF
        r = r & 0xFFFFFFFF

        decrypted_bytes[i] = byte_array[i] ^ (0xFF & r)

    return decrypted_bytes.decode("utf-8", errors="ignore")
