from bit_stream import BitStream


M = 12
N = 4

WINDOW_LENGTH = 2**M
MIN_WORD_LENGTH = (M + N + 7) // 8
MAX_WORD_LENGTH = MIN_WORD_LENGTH + (2**N - 1)


class _Dictionary(object):
    def __init__(self, window, window_length):
        self._window = window
        self._tree_root_ids = 256 * [None]
        self._tree_node_parent_ids = window_length * [-1]
        self._tree_node_left_child_ids = window_length * [None]
        self._tree_node_right_child_ids = window_length * [None]

    def match_word_and_add_word(self, word_position, word_length):
        x = word_position
        y = self._tree_root_ids[self._window[x]]

        if y is None:
            self._tree_root_ids[self._window[x]] = x
            self._tree_node_parent_ids[x] = None
            self._tree_node_left_child_ids[x] = None
            self._tree_node_right_child_ids[x] = None
            return (-1, 0)
        else:
            match_position = -1
            match_length = 0

            while True:
                i = 1
                delta = 0

                while i < word_length:
                    delta = self._window[x + i] - self._window[y + i]

                    if delta != 0:
                        break
                    else:
                        i += 1

                if i > match_length:
                    match_position = y
                    match_length = i

                if delta == 0:
                    break
                else:
                    if delta < 0:
                        w = self._tree_node_left_child_ids[y]
                    else:
                        w = self._tree_node_right_child_ids[y]

                    if w is None:
                        break
                    else:
                        y = w

            if delta == 0:
                self._replace_tree_node(y, x)
                self._tree_node_parent_ids[y] = -1
            else:
                if delta < 0:
                    self._tree_node_left_child_ids[y] = x
                else:
                    self._tree_node_right_child_ids[y] = x

                self._tree_node_parent_ids[x] = y
                self._tree_node_left_child_ids[x] = None
                self._tree_node_right_child_ids[x] = None

            return (match_position, match_length)

    def remove_word(self, word_position):
        x = word_position

        if self._tree_node_parent_ids[x] != -1:
            if self._tree_node_left_child_ids[x] is None:
                y = x
                z = self._tree_node_right_child_ids[x]
            elif self._tree_node_right_child_ids[x] is None:
                y = x
                z = self._tree_node_left_child_ids[x]
            else:
                y = self._tree_node_left_child_ids[x]

                while True:
                    if self._tree_node_right_child_ids[y] is None:
                        z = self._tree_node_left_child_ids[y]
                        break
                    else:
                        y = self._tree_node_right_child_ids[y]

            w = self._tree_node_parent_ids[y]

            if w is None:
                self._tree_root_ids[self._window[y]] = z
            else:
                if y == self._tree_node_left_child_ids[w]:
                    self._tree_node_left_child_ids[w] = z
                else:
                    self._tree_node_right_child_ids[w] = z

            if not z is None:
                self._tree_node_parent_ids[z] = w

            if y != x:
                self._replace_tree_node(x, y)

            self._tree_node_parent_ids[x] = -1

    def _replace_tree_node(self, x, y):
        w = self._tree_node_parent_ids[x]

        if w is None:
            self._tree_root_ids[self._window[x]] = y
        else:
            if x == self._tree_node_left_child_ids[w]:
                self._tree_node_left_child_ids[w] = y
            else:
                self._tree_node_right_child_ids[w] = y

        self._tree_node_parent_ids[y] = w
        w = self._tree_node_left_child_ids[x]
        self._tree_node_left_child_ids[y] = w

        if not w is None:
            self._tree_node_parent_ids[w] = y

        w = self._tree_node_right_child_ids[x]
        self._tree_node_right_child_ids[y] = w

        if not w is None:
            self._tree_node_parent_ids[w] = y


def encode_file(input_file, output_file):
    bit_stream = BitStream(output_file)
    _encode_file(input_file, bit_stream)


def decode_file(input_file, output_file):
    bit_stream = BitStream(input_file)
    _decode_file(bit_stream, output_file)


def _encode_file(input_file, bit_stream):
    window = bytearray(WINDOW_LENGTH + MAX_WORD_LENGTH)
    dictionary = _Dictionary(window, WINDOW_LENGTH)
    i = 0
    j = 0

    while j < MAX_WORD_LENGTH:
        bytes_ = input_file.read(1)

        if len(bytes_) == 0:
            break
        else:
            window[j] = bytes_[0]
            j += 1

    number_of_skips = 0

    while True:
        data_length = (j - i + WINDOW_LENGTH) % WINDOW_LENGTH

        if data_length == 0:
            break
        else:
            word_position, word_length = dictionary.match_word_and_add_word(i, data_length)

            if number_of_skips == 0:
                if word_length < MIN_WORD_LENGTH:
                    number_of_skips = max(word_length, 1) - 1
                    bit_stream.write_bits(1, 1)
                    bit_stream.write_bits(window[i], 8)
                else:
                    number_of_skips = word_length - 1
                    bit_stream.write_bits(0, 1)
                    bit_stream.write_bits(word_position, M)
                    bit_stream.write_bits(word_length - MIN_WORD_LENGTH, N)
            else:
                number_of_skips -= 1

            i = (i + 1) % WINDOW_LENGTH

            if data_length == MAX_WORD_LENGTH:
                bytes_ = input_file.read(1)

                if len(bytes_) >= 1:
                    dictionary.remove_word(j)
                    window[j] = bytes_[0]

                    if j < MAX_WORD_LENGTH:
                        window[WINDOW_LENGTH + j] = bytes_[0]

                    j = (j + 1) % WINDOW_LENGTH

    bit_stream.write_bits(0, 1)
    bit_stream.write_bits(i, M, True)


def _decode_file(bit_stream, output_file):
    window = bytearray(WINDOW_LENGTH + MAX_WORD_LENGTH)
    dictionary = _Dictionary(window, WINDOW_LENGTH)
    i = 0

    while True:
        flag, number_of_bits = bit_stream.read_bits(1)

        if number_of_bits < 1:
            raise EOFError()

        if flag == 1:
            byte, number_of_bits = bit_stream.read_bits(8)

            if number_of_bits < 8:
                raise EOFError()

            output_file.write(bytes([byte]))
            window[i] = byte

            if i < MAX_WORD_LENGTH:
                window[WINDOW_LENGTH + i] = byte

            i = (i + 1) % WINDOW_LENGTH
        else:
            word_position, number_of_bits = bit_stream.read_bits(M)

            if number_of_bits < M:
                raise EOFError()

            if word_position == i:
                return
            else:
                bits, number_of_bits = bit_stream.read_bits(N)

                if number_of_bits < N:
                    raise EOFError()

                word_length = bits + MIN_WORD_LENGTH

                for j in range(word_position, word_position + word_length):
                    byte = window[j]
                    output_file.write(bytes([byte]))
                    window[i] = byte

                    if i < MAX_WORD_LENGTH:
                        window[WINDOW_LENGTH + i] = byte

                    i = (i + 1) % WINDOW_LENGTH
