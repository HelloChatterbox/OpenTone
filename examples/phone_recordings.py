from opentone import ToneDecoder

# test clean 8khz phone
d = ToneDecoder(8000, min_consecutive=2, hex_decode=False)

decoded = d.decode_wave("0123456789.wav")
assert decoded == "0123456789"


# test noisy 8khz (phone)
goertzel_N = 92
d = ToneDecoder(8000, goertzel_N, min_consecutive=3, hex_decode=False)

decoded = d.decode_wave("phonecall.wav")

# since this is a phone e -> *  f -> #
decoded = decoded.lower().replace("e", "*").replace("f", "#")

# NOTE: this is one is imperfectly decoded
print(decoded)  # "05464273316"
print("0546427316")  #  should be this



