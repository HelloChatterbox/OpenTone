import math
import wave
import struct


class ToneGenerator:
    SAMPLE_RATE = 8000  # hz
    SAMPLE_WIDTH = 2
    NUMBER_OF_CHANNELS = 1
    COMPRESSION_TYPE = "NONE"
    COMPRESSION_NAME = "Uncompressed"

    # Define Frequency Rows & Columns to generate standard DTMF tones
    frequencyR = [697, 770, 852, 941]
    frequencyC = [1209, 1336, 1477, 1633]

    FREQUENCY_MAPPINGS = {'0': [frequencyR[3], frequencyC[1]],
                          '1': [frequencyR[0], frequencyC[0]],
                          '2': [frequencyR[0], frequencyC[1]],
                          '3': [frequencyR[0], frequencyC[2]],
                          '4': [frequencyR[1], frequencyC[0]],
                          '5': [frequencyR[1], frequencyC[1]],
                          '6': [frequencyR[1], frequencyC[2]],
                          '7': [frequencyR[2], frequencyC[0]],
                          '8': [frequencyR[2], frequencyC[1]],
                          '9': [frequencyR[2], frequencyC[2]],
                          'A': [frequencyR[0], frequencyC[3]],
                          'B': [frequencyR[1], frequencyC[3]],
                          'C': [frequencyR[2], frequencyC[3]],
                          'D': [frequencyR[3], frequencyC[3]],
                          'E': [frequencyR[3], frequencyC[0]],
                          'F': [frequencyR[3], frequencyC[2]]
                          }

    def __init__(self, duration=100, pause=500):
        self.duration = duration
        self.pause = pause

    @staticmethod
    def hex_encode(text_to_encode):
        hex_encoded = text_to_encode.encode(encoding="ascii").hex()
        return hex_encoded

    def _generate_raw_data(self, text_to_encode):
        data = []
        sequence = [(s, self.duration) for s in text_to_encode.upper()]
        for tone_tuple in sequence:
            key = tone_tuple[0]
            tone_duration = tone_tuple[1]
            f1 = self.FREQUENCY_MAPPINGS[key][0]
            f2 = self.FREQUENCY_MAPPINGS[key][1]
            data += (self.generate_tone(f1, f2, tone_duration))
        return data

    def _save_wave_file(self, raw_data, file_path):
        f = wave.open(file_path, 'w')
        f.setnchannels(self.NUMBER_OF_CHANNELS)
        f.setsampwidth(self.SAMPLE_WIDTH)
        f.setframerate(self.SAMPLE_RATE)
        f.setnframes(len(raw_data))
        f.setcomptype(self.COMPRESSION_TYPE, self.COMPRESSION_NAME)
        for i in raw_data:
            f.writeframes(struct.pack('i', i))
        f.close()

    def _get_silence(self, duration_in_ms=None):
        if duration_in_ms is None:
            duration_in_ms = self.pause
        number_of_samples = int(self.SAMPLE_RATE * duration_in_ms / 1000)
        result = list()
        for i in range(number_of_samples):
            result.append(0)
        return result

    def generate_tone(self, f1, f2, duration_in_ms):
        """
        Generates a single value representing a sample of two combined frequencies.
        :param f1:
        :param f2:
        :param duration_in_ms:
        :return:
        """
        number_of_samples = int(self.SAMPLE_RATE * duration_in_ms / 1000)
        scale = 32767  # signed int / 2

        result = list()
        for i in range(number_of_samples):
            p = i * 1.0 / self.SAMPLE_RATE
            result.append(int((math.sin(p * f1 * math.pi * 2) +
                               math.sin(p * f2 * math.pi * 2)) / 2 * scale))
        return result + self._get_silence()

    def encode_to_wave(self, text_to_encode, file_path):
        hex_encoded = self.hex_encode(text_to_encode)
        raw_data = self._generate_raw_data(hex_encoded)
        self._save_wave_file(raw_data, file_path)

    def dtmf_to_wave(self, dtmf, file_path):
        raw_data = self._generate_raw_data(str(dtmf))
        self._save_wave_file(raw_data, file_path)


class ToneDecoder:
    def __init__(self, sample_rate=16000, goertzel_n=210, min_consecutive=6,
                 hex_decode=True):
        # DEFINE SOME CONSTANTS FOR THE
        # GOERTZEL ALGORITHM
        self.max_bins = 8
        self.goertzel_n = goertzel_n
        self.sample_rate = sample_rate

        # the DTMF frequencies we're looking for
        self.freqs = ToneGenerator.frequencyR + ToneGenerator.frequencyC

        # the coefficients
        self.coefs = [0, 0, 0, 0, 0, 0, 0, 0]

        self.reset()

        self._calc_coeffs()

        self.min_consecutive = min_consecutive
        self.decode = hex_decode

    def reset(self):
        # the index of the current sample being looked at
        self.sample_index = 0

        # the counts of samples we've seen
        self.sample_count = 0

        # first pass
        self.q1 = [0, 0, 0, 0, 0, 0, 0, 0]

        # second pass
        self.q2 = [0, 0, 0, 0, 0, 0, 0, 0]

        # r values
        self.r = [0, 0, 0, 0, 0, 0, 0, 0]

        # this stores the characters seen so far
        # and the times they were seen at for
        # post, post processing
        self.characters = []

        # this stores the final string of characters
        # we believe the audio contains
        self.decoded = ""

    def _postprocess(self):
        # figures out what's a valid signal and what's not
        row = 0
        col = 0
        maxval = 0.0

        row_col_ascii_codes = [["1", "2", "3", "A"], ["4", "5", "6", "B"],
                               ["7", "8", "9", "C"], ["E", "0", "F", "D"]]

        # Find the largest in the row group.
        for i in range(4):
            if self.r[i] > maxval:
                maxval = self.r[i]
                row = i

        # Find the largest in the column group.
        maxval = 0
        for i in range(4, 8):
            if self.r[i] > maxval:
                maxval = self.r[i]
                col = i

        # Check for minimum energy
        if self.r[row] >= 4.0e5 and self.r[col] >= 4.0e5:
            see_digit = True

            # Normal twist
            if self.r[col] > self.r[row]:
                max_index = col
                if self.r[row] < (self.r[col] * 0.398):
                    see_digit = False
            # Reverse twist
            else:
                max_index = row
                if self.r[col] < (self.r[row] * 0.158):
                    see_digit = False

            # signal to noise test
            # AT&T states that the noise must be 16dB down from the signal.
            # Here we count the number of signals above the threshold and
            # there ought to be only two.
            if self.r[max_index] > 1.0e9:
                t = self.r[max_index] * 0.158
            else:
                t = self.r[max_index] * 0.010

            peak_count = 0

            for i in range(8):
                if self.r[i] > t:
                    peak_count = peak_count + 1
            if peak_count > 2:
                see_digit = False

            if see_digit:
                # stores the character found, and the time in the file
                # in seconds in which the file was found
                self.characters.append((row_col_ascii_codes[row][col - 4],
                                        float(self.sample_index) / float(
                                            self.sample_rate)))

    def _cleanup_decoded(self):
        # This takes the number of characters found and figures out what's
        # a distinct characters.

        # example:
        #   "hello world" encoded is "68656c6c6f20776f726c64"
        # The algorithm sees
        #   "666666688888886666666655555556666666CCCCCCC6666666CCCCCCCC6666666FFFFFFF22222220000000777777777777776666666FFFFFFF777777722222226666666CCCCCCC666666664444444"
        # Cleaning up gives you the original encoded string
        chars = [d[0] for d in self.characters]
        decoded = ""

        count = 1
        prev = ""
        for c in chars:
            if c == prev:
                count += 1
                if count >= self.min_consecutive:
                    count = 0
                    decoded += c
                    prev = ""
            else:
                prev = c

        return decoded

    def goertzel(self, sample):
        # the Goertzel algorithm
        # takes in a 16 bit signed sample
        self.sample_count += 1
        self.sample_index += 1

        for i in range(self.max_bins):
            q0 = self.coefs[i] * self.q1[i] - self.q2[i] + sample
            self.q2[i] = self.q1[i]
            self.q1[i] = q0

        if self.sample_count == self.goertzel_n:
            for i in range(self.max_bins):
                self.r[i] = (self.q1[i] * self.q1[i]) + (
                        self.q2[i] * self.q2[i]) - (
                                    self.coefs[i] * self.q1[i] * self.q2[
                                i])
                self.q1[i] = 0
                self.q2[i] = 0
            self._postprocess()
            self.sample_count = 0

    def _calc_coeffs(self):
        for n in range(self.max_bins):
            self.coefs[n] = 2.0 * math.cos(
                2.0 * math.pi * self.freqs[n] / self.sample_rate)

    def decode_wave(self, filename):

        self.reset()  # reset the current state of the detector

        wave_file = wave.open(filename)

        n_frames = wave_file.getnframes()

        count = 0

        while n_frames != count:
            raw = wave_file.readframes(1)
            (sample,) = struct.unpack("h", raw)
            self.goertzel(sample)
            count = count + 1

        wave_file.close()

        hex_encoded = self._cleanup_decoded().lower()
        if self.decode:
            return self.hex_decode(hex_encoded)
        return hex_encoded

    @staticmethod
    def hex_decode(hex_encoded):
        hex_decoded = bytes.fromhex(hex_encoded).decode('ascii')
        return hex_decoded


if __name__ == '__main__':
    text = "hello world"

    d = ToneGenerator()
    d.encode_to_wave(text, file_path='test.wav')

    d = ToneDecoder()
    decoded = d.decode_wave("test.wav")
    assert text == decoded

    # test noisy 8khz (phone)
    goertzel_N = 92
    min_consecutive = 3
    hex_decode = False
    d = ToneDecoder(8000, goertzel_N, min_consecutive, hex_decode)
    decoded = d.decode_wave("phonecall.wav")
    # since this is a phone e -> *  f -> #
    decoded = decoded.lower().replace("e", "*").replace("f", "#")
    assert "05464273316" == decoded
