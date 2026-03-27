#!/usr/bin/env python3
"""
Compact JSON compression for session save files.
Based on https://github.com/dzineer/fork-compress-json (BSD-2-Clause)

Deduplicates repeated values, base62-encodes numbers, and stores
everything as a flat array with index references. Typically saves 25-40%
on structured data with repeated keys/values (like tasks.json, memory.json).

Usage:
  # As a library
  from compress_json import compress, decompress

  # CLI: compress
  python3 compress_json.py compress input.json output.json

  # CLI: decompress
  python3 compress_json.py decompress input.json output.json

  # CLI: stdin/stdout
  cat data.json | python3 compress_json.py compress - -
"""
import json
import math
import sys

# --- types ---
dict_class = type({})
list_class = type([])
int_class = type(1)
float_class = type(1.0)
str_class = type('')
bool_class = type(True)

# --- config ---
SORT_KEYS = False

# --- base62 number encoding ---
_i_to_s = ''
for _i in range(10):
    _i_to_s += str(_i)
for _i in range(26):
    _i_to_s += chr(65 + _i)
for _i in range(26):
    _i_to_s += chr(97 + _i)

_N = len(_i_to_s)

_s_to_i = {}
for _i in range(_N):
    _s_to_i[_i_to_s[_i]] = _i

_max_int = 2**53


def _int_to_s(integer):
    if integer == 0:
        return _i_to_s[0]
    acc = []
    while integer != 0:
        i = integer % _N
        if type(i) == float:
            int_val = int(i)
            if i != float(int_val):
                raise Exception(f"precision loss when int_to_s({integer})")
            i = int_val
        acc.append(_i_to_s[i])
        integer //= _N
    return ''.join(acc[::-1])


def _s_to_int(s):
    acc = 0
    pw = 1
    for i in range(len(s) - 1, -1, -1):
        acc += _s_to_i[s[i]] * pw
        pw *= _N
    return acc


def _int_str_to_s(int_str):
    integer = int(int_str)
    if integer <= _max_int:
        return _int_to_s(integer)
    return ':' + _int_to_s(integer)


def _s_to_int_str(s):
    if s[0] == ':':
        s = s[1:]
    return str(_s_to_int(s))


def _num_to_s(num):
    if num < 0:
        return '-' + _num_to_s(-num)
    parts = str(float(num)).split('.')
    if len(parts) == 1:
        if 'e' in parts[0]:
            a = parts[0]
            a1, a2 = a.split('e')
            a = a1
            b = '0e' + a2
        else:
            return _int_to_s(num)
    else:
        a, b = parts
    if b == '0':
        if type(num) == int_class:
            return _int_to_s(num)
        return _int_str_to_s(a)
    parts = b.split('e')
    if len(parts) == 1:
        c = '0'
    else:
        b, c = parts
    a = _int_str_to_s(a)
    b = _int_str_to_s(b[::-1])
    string = a + '.' + b
    if c != '0':
        string += '.'
        if c[0] == '+':
            c = c[1:]
        elif c[0] == '-':
            string += '-'
            c = c[1:]
        string += _int_str_to_s(c)
    return string


def _s_to_num(s):
    if s[0] == '-':
        return -_s_to_num(s[1:])
    parts = s.split('.')
    length = len(parts)
    if length == 1:
        return _s_to_int(s)
    a = _s_to_int_str(parts[0])
    b = _s_to_int_str(parts[1])[::-1]
    string = a + '.' + b
    if length == 3:
        string += 'e'
        neg = False
        c = parts[2]
        if c[0] == '-':
            neg = True
            c = c[1:]
        c = _s_to_int_str(c)
        string += ('-' + c) if neg else c
    return float(string) if '.' in string else int(string)


# --- encode/decode primitives ---
def _encode_num(num):
    if num == float('inf'):
        return 'N|+'
    if num == float('-inf'):
        return 'N|-'
    if math.isnan(num):
        return 'N|0'
    return 'n|' + _num_to_s(num)


def _decode_num(s):
    if s == 'N|+': return float('inf')
    if s == 'N|-': return float('-inf')
    if s == 'N|0': return float('nan')
    return _s_to_num(s[2:])


def _decode_key(key):
    if type(key) == int_class:
        return key
    if type(key) == float_class:
        return int(key)
    return _s_to_int(key)


def _encode_str(string):
    prefix = string[0:2]
    if prefix in ('b|', 'o|', 'n|', 'a|', 's|'):
        return 's|' + string
    return string


def _decode_str(string):
    return string[2:] if string[0:2] == 's|' else string


def _encode_bool(b):
    return 'b|T' if b else 'b|F'


def _decode_bool(s):
    return True if s == 'b|T' else False


# --- memory store (value deduplication) ---
class _Memory:
    def __init__(self):
        self.store = []
        self.cache = {}
        self.key_count = 0


def _get_value_key(mem, value):
    if value in mem.cache:
        return mem.cache[value]
    key = _int_to_s(mem.key_count)
    mem.key_count += 1
    mem.store.append(value)
    mem.cache[value] = key
    return key


def _is_sparse_array(array):
    return len(array) > 0 and array[-1] is not None


def _add_value(mem, o):
    if o is None:
        return ''
    data_class = type(o)

    if data_class == list_class:
        acc = 'a'
        empty_value = '' if _is_sparse_array(o) else '_'
        for v in o:
            key = empty_value if v is None else _add_value(mem, v)
            acc += '|' + key
        if acc == 'a':
            acc = 'a|'
        return _get_value_key(mem, acc)

    if data_class == dict_class:
        keys = list(o.keys())
        if len(keys) == 0:
            return _get_value_key(mem, 'o|')
        acc = 'o'
        if SORT_KEYS:
            keys = sorted(keys)
        schema = ','.join(keys)
        key_id = _add_value(mem, keys)
        acc += '|' + key_id
        for key in keys:
            acc += '|' + _add_value(mem, o[key])
        return _get_value_key(mem, acc)

    if data_class == bool_class:
        return _get_value_key(mem, _encode_bool(o))

    if data_class == int_class or data_class == float_class:
        return _get_value_key(mem, _encode_num(o))

    if data_class == str_class:
        return _get_value_key(mem, _encode_str(o))

    raise Exception(f'unknown data type: {data_class}, o: {o}')


# --- public API ---
def compress(o):
    """Compress a JSON-compatible Python object into a compact array format."""
    mem = _Memory()
    root = _add_value(mem, o)
    return [mem.store, root]


def decompress(c):
    """Decompress a previously compressed object back to its original form."""
    values, root = c
    return _decode(values, root)


def _decode(values, key):
    if key == '' or key == '_':
        return None
    idx = _decode_key(key)
    v = values[idx]
    if v is None:
        return v
    data_class = type(v)
    if data_class == int_class or data_class == float_class:
        return v
    if data_class == str_class:
        prefix = v[0:2]
        if prefix == 'b|': return _decode_bool(v)
        if prefix == 'o|': return _decode_object(values, v)
        if prefix == 'n|': return _decode_num(v)
        if prefix == 'a|': return _decode_array(values, v)
        return _decode_str(v)
    raise Exception(f"unknown data type: {data_class}, v: {v}")


def _decode_object(values, s):
    if s == 'o|':
        return {}
    o = {}
    vs = s.split('|')
    keys = _decode(values, vs[1])
    n = len(vs)
    if n - 2 == 1 and type(keys) != list_class:
        keys = [keys]
    for i in range(2, n):
        o[keys[i - 2]] = _decode(values, vs[i])
    return o


def _decode_array(values, s):
    if s == 'a|':
        return []
    vs = s.split('|')
    return [_decode(values, vs[i + 1]) for i in range(len(vs) - 1)]


# --- CLI ---
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: compress_json.py <compress|decompress> [input] [output]")
        print("  Use '-' for stdin/stdout")
        sys.exit(1)

    action = sys.argv[1]
    infile = sys.argv[2] if len(sys.argv) > 2 else '-'
    outfile = sys.argv[3] if len(sys.argv) > 3 else '-'

    # Read input
    if infile == '-':
        data = json.loads(sys.stdin.read())
    else:
        with open(infile) as f:
            data = json.load(f)

    # Process
    if action == 'compress':
        result = compress(data)
    elif action == 'decompress':
        result = decompress(data)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

    # Write output
    output = json.dumps(result, separators=(',', ':'))
    if outfile == '-':
        print(output)
    else:
        with open(outfile, 'w') as f:
            f.write(output)

    # Stats to stderr
    input_size = len(json.dumps(data, separators=(',', ':')))
    output_size = len(output)
    pct = 100 - (output_size * 100 // input_size) if input_size > 0 else 0
    print(f"{input_size} -> {output_size} bytes ({pct}% savings)", file=sys.stderr)
