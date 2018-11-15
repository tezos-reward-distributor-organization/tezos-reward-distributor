iseq, bseq, buffer = (lambda s: s, bytes, lambda s: s.buffer,)
# 58 character alphabet used
alphabet = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def decode(str):
    decoded = b58decode(str).hex()
    print(decoded)

def scrub_input(v):
    if isinstance(v, str) and not isinstance(v, bytes):
        v = v.encode('ascii')

    if not isinstance(v, bytes):
        raise TypeError(
            "a bytes-like object is required (also str), not '%s'" %
            type(v).__name__)

    return v

def b58decode_int(v):
    '''Decode a Base58 encoded string as an integer'''

    v = scrub_input(v)

    decimal = 0
    for char in v:
        decimal = decimal * 58 + alphabet.index(char)
    return decimal

def b58decode(v):
    '''Decode a Base58 encoded string'''

    v = scrub_input(v)

    origlen = len(v)
    v = v.lstrip(alphabet[0:1])
    newlen = len(v)

    acc = b58decode_int(v)

    result = []
    while acc > 0:
        acc, mod = divmod(acc, 256)
        result.append(mod)

    return (b'\0' * (origlen - newlen) + bseq(reversed(result)))


if __name__ == '__main__':
    decode("edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q")
    # 09f5cd861200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000194e5b51
    decode("edsigtat7ty1341C4rnHj1hPqWXwjYGVGAhES7c3YYzBHn3NFDtw8YgCmdyVrtad6DsVPEYHnmV9iB7XXLkyowSjFGFUx7LnP")
    # c20a2940633252cfb5e66b2aff8832a2e1c774e0639de7beecc1e345034f644df830df518536f8aef307be3e567520cade85b90cc17953d6c689db5306aef684dcf9057b5f3234
