import heapq

from bit_stream import BitStream


class _TreeNodeHeap(object):
    def __init__(self, tree_node_weights):
        self._data = []

        for tree_node_id, tree_node_weight in enumerate(tree_node_weights):
            if tree_node_weight >= 1:
                self._data.append((tree_node_weight, tree_node_id))

        heapq.heapify(self._data)

    def pop_tree_node(self):
        tree_node_weight, tree_node_id = heapq.heappop(self._data)
        return tree_node_id, tree_node_weight

    def push_tree_node(self, tree_node_id, tree_node_weight):
        heapq.heappush(self._data, (tree_node_weight, tree_node_id))

    def get_number_of_nodes(self):
        return len(self._data)


def encode_file(input_file, output_file):
    tree_leaf_weights = _calculate_tree_leaf_weights(input_file)
    tree = _make_tree(tree_leaf_weights)
    bit_stream = BitStream(output_file)
    _dump_tree(*tree, bit_stream)
    input_size = sum(tree_leaf_weights)
    _dump_size(input_size, bit_stream)
    input_file.seek(0, 0)
    code_table = _make_code_table(*tree)
    _encode_file(input_file, input_size, code_table, bit_stream)
    bit_stream.write_bits(0, 0, True)


def decode_file(input_file, output_file):
    bit_stream = BitStream(input_file)
    tree = _load_tree(bit_stream)
    output_size = _load_size(bit_stream)
    _decode_file(bit_stream, *tree, output_file, output_size)


def _calculate_tree_leaf_weights(file_):
    tree_leaf_weights = 256 * [0]

    for bytes_ in iter(lambda: file_.read(1), b''):
        tree_leaf_id = bytes_[0]
        tree_leaf_weights[tree_leaf_id] += 1

    return tree_leaf_weights


def _make_tree(tree_leaf_weights):
    tree_node_left_child_ids = 511 * [None]
    tree_node_right_child_ids = 511 * [None]
    tree_node_weights = tree_leaf_weights + 255 * [0]
    next_tree_node_id = 256
    tree_node_heap = _TreeNodeHeap(tree_leaf_weights)

    while True:
        tree_node_left_child_id, tree_node_left_child_weight = tree_node_heap.pop_tree_node()
        tree_node_right_child_id, tree_node_right_child_weight = tree_node_heap.pop_tree_node()
        tree_node_id = next_tree_node_id
        next_tree_node_id += 1
        tree_node_weight = tree_node_left_child_weight + tree_node_right_child_weight
        tree_node_weights[tree_node_id] = tree_node_weight
        tree_node_left_child_ids[tree_node_id] = tree_node_left_child_id
        tree_node_right_child_ids[tree_node_id] = tree_node_right_child_id

        if tree_node_heap.get_number_of_nodes() == 0:
            break
        else:
            tree_node_heap.push_tree_node(tree_node_id, tree_node_weight)

    return (tree_node_id, tree_node_left_child_ids, tree_node_right_child_ids)


def _tree_node_is_tree_leaf(tree_node_id):
    return tree_node_id < 256


def _dump_tree(tree_root_id, tree_node_left_child_ids, tree_node_right_child_ids, bit_stream):
    def walk_tree(tree_node_id):
        if _tree_node_is_tree_leaf(tree_node_id):
            bit_stream.write_bits(1, 1)
            bit_stream.write_bits(tree_node_id, 8)
        else:
            bit_stream.write_bits(0, 1)
            walk_tree(tree_node_left_child_ids[tree_node_id])
            walk_tree(tree_node_right_child_ids[tree_node_id])

    walk_tree(tree_root_id)


def _load_tree(bit_stream):
    tree_node_left_child_ids = 511 * [None]
    tree_node_right_child_ids = 511 * [None]
    next_tree_node_id = 256

    def make_tree():
        nonlocal next_tree_node_id

        flag, number_of_bits = bit_stream.read_bits(1)

        if number_of_bits < 1:
            raise EOFError()

        if flag == 1:
            tree_node_id, number_of_bits = bit_stream.read_bits(8)

            if number_of_bits < 8:
                raise EOFError()

            return tree_node_id
        else:
            tree_node_id = next_tree_node_id
            next_tree_node_id += 1
            tree_node_left_child_ids[tree_node_id] = make_tree()
            tree_node_right_child_ids[tree_node_id] = make_tree()
            return tree_node_id

    tree_root_id = make_tree()
    return (tree_root_id, tree_node_left_child_ids, tree_node_right_child_ids)


def _dump_size(size, bit_stream):
    while True:
        bits = size & 0xFF
        size >>= 8
        bit_stream.write_bits(bits, 8)

        if size == 0:
            bit_stream.write_bits(1, 1)
            return
        else:
            bit_stream.write_bits(0, 1)


def _load_size(bit_stream):
    size = 0
    i = 0

    while True:
        bits, number_of_bits = bit_stream.read_bits(8)

        if number_of_bits < 8:
            raise EOFError()

        size |= bits << i
        i += 8

        flag, number_of_bits = bit_stream.read_bits(1)

        if number_of_bits < 1:
            raise EOFError()

        if flag == 1:
            return size


def _make_code_table(tree_root_id, tree_node_left_child_ids, tree_node_right_child_ids):
    code_table = 256 * [None]

    def walk_tree(tree_node_id, code, code_length):
        if _tree_node_is_tree_leaf(tree_node_id):
            code_table[tree_node_id] = (code, code_length)
        else:
            walk_tree(tree_node_left_child_ids[tree_node_id], code, code_length + 1)
            walk_tree(tree_node_right_child_ids[tree_node_id], code | (1 << code_length)
                      , code_length + 1)

    walk_tree(tree_root_id, 0, 0)
    return code_table


def _encode_file(input_file, input_size, code_table, bit_stream):
    for _ in range(input_size):
        i = input_file.read(1)[0]
        code, code_length = code_table[i]
        bit_stream.write_bits(code, code_length)


def _decode_file(bit_stream, tree_root_id, tree_node_left_child_ids, tree_node_right_child_ids
                 , output_file, output_size):
    for _ in range(output_size):
        tree_node_id = tree_root_id

        while True:
            flag, number_of_bits = bit_stream.read_bits(1)

            if number_of_bits < 1:
                raise EOFError()

            if flag == 0:
                tree_node_id = tree_node_left_child_ids[tree_node_id]
            else:
                tree_node_id = tree_node_right_child_ids[tree_node_id]

            if _tree_node_is_tree_leaf(tree_node_id):
                break

        output_file.write(bytes([tree_node_id]))
