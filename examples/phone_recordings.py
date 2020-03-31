from opentone import ToneDecoder

# test noisy 8khz (phone)
goertzel_N = 92
min_consecutive = 3
hex_decode = False

d = ToneDecoder(8000, goertzel_N, min_consecutive, hex_decode)

decoded = d.decode_wave("phonecall.wav")

# since this is a phone e -> *  f -> #
decoded = decoded.lower().replace("e", "*").replace("f", "#")

# NOTE: this is one is imperfectly decoded
print(decoded)  # "05464273316"
print("0546427316")  #  should be this
