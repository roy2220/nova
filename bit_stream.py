class BitStream(object):
    def __init__(self, file_):
        self._file = file_
        self._data = 0
        self._data_length = 0
        self._buffer = 0
        self._buffer_length = 8

    def _refresh(self):
        self._file.seek(-1, 1)
        bytes_ = self._file.read(1)
        self._data = bytes_[0]

    def read_bits(self, bit_count, refresh=False):
        if self._data_length == 0:
            bits = 0
            number_of_bits = 0
        else:
            if refresh:
                self._refresh()

            bits = self._data >> (8 - self._data_length)
            n = min(self._data_length, bit_count)
            bits &= (1 << n) - 1
            number_of_bits = n
            self._data_length -= n

            if self._data_length >= 1:
                return (bits, number_of_bits)

        while number_of_bits < bit_count:
            bytes_ = self._file.read(1)

            if len(bytes_) == 0:
                return (bits, number_of_bits)
            else:
                bits |= bytes_[0] << number_of_bits
                number_of_bits += 8

        if number_of_bits > bit_count:
            self._data = bytes_[0]
            self._data_length = number_of_bits - bit_count
            bits &= (1 << bit_count) - 1
            number_of_bits = bit_count

        return (bits, number_of_bits)

    def _flush(self):
        self._file.write(bytes([self._buffer]))
        self._file.seek(-1, 1)

    def write_bits(self, bits, number_of_bits, flush=False):
        if self._buffer_length < 8:
            self._buffer = ((bits << (8 - self._buffer_length)) | self._buffer) & 0xFF
            n = min(self._buffer_length, number_of_bits)
            self._buffer_length -= n

            if self._buffer_length == 0:
                bits >>= n
                number_of_bits -= n
                self._file.write(bytes([self._buffer]))
                self._buffer = 0
                self._buffer_length = 8
            else:
                if flush:
                    self._flush();

                return

        while number_of_bits >= 8:
            self._file.write(bytes([bits & 0xFF]))
            bits >>= 8
            number_of_bits -= 8

        if number_of_bits >= 1:
            self._buffer = bits
            self._buffer_length = 8 - number_of_bits

            if flush:
                self._flush();
