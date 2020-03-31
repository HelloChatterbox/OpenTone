from opentone import ToneGenerator, ToneDecoder
import pyshorteners as pyshort


def tiny_link(url):
    pyshort.Shortener()
    tinyurl = pyshort.Shortener().tinyurl.short(url)
    # The consant prefix in the TinyURL is standard and can be
    # removed altogether, and added in the receiving station
    URL = "http://tinyurl.com/"
    url = tinyurl[len(URL):]
    return url


url = "https://hellochatterbox.com"
url = tiny_link(url)
wave_file = "chatterbox_encoded.wav"
tone_gen = ToneGenerator()
tone_gen.encode_to_wave(url, wave_file)

decoder = ToneDecoder()
decoded_url = decoder.decode_wave(wave_file)

assert decoded_url == url

print("http://tinyurl.com/" + decoded_url)