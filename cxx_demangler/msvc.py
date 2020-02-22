
import re

from.nodes import *
from ._cursor import _Cursor


_builtin_types = {
    'C': Node('builtin', 'signed char'),
    'D': Node('builtin', 'char'),
    'E': Node('builtin', 'unsigned char'),
    'F': Node('builtin', 'short'),
    'G': Node('builtin', 'unsigned short'),
    'H': Node('builtin', 'int'),
    'I': Node('builtin', 'unsigned int'),
    'J': Node('builtin', 'long'),
    'K': Node('builtin', 'unsigned long'),
    'M': Node('builtin', 'float'),
    'N': Node('builtin', 'double'),
    'O': Node('builtin', 'long double'),
    'X': Node('builtin', 'void'),
    'Z': Node('builtin', '...'),
    '_D': Node('builtin', '__int8'),
    '_E': Node('builtin', 'unsigned __int8'),
    '_F': Node('builtin', '__int16'),
    '_G': Node('builtin', 'unsigned __int16'),
    '_H': Node('builtin', '__int32'),
    '_I': Node('builtin', 'unsigned __int32'),
    '_J': Node('builtin', '__int64'),
    '_K': Node('builtin', 'unsigned __int64'),
    '_L': Node('builtin', '__int128'),
    '_M': Node('builtin', 'unsigned __int128'),
    '_N': Node('builtin', 'bool'),
    '_S': Node('builtin', 'char16_t'),
    '_U': Node('builtin', 'char32_t'),
    '_W': Node('builtin', 'wchar_t')
}


_operators = {
    '2': 'new',
    '_U': 'new[]',
    '3': 'delete',
    '_V': 'delete[]',
    '4': '=',
    '5': '>>',
    '6': '<<',
    '7': '!',
    '8': '==',
    '9': '!=',
    'A': '[]',
    'B': 'returntype',  # MSVC special thing, not sure what it's used for
    'C': '->',
    'D': '*',
    'E': '++',
    'F': '--',
    'G': '-',
    'H': '+',
    'I': '&',
    'J': '->*',
    'K': '/',
    'L': '%',
    'M': '<',
    'N': '<=',
    'O': '>',
    'P': '>=',
    'Q': ',',
    'R': '()',
    'S': '~',
    'T': '^',
    'U': '|',
    'V': '&&',
    'W': '||',
    'X': '*=',
    'Y': '+=',
    'Z': '-=',
    '_0': '/=',
    '_1': '%=',
    '_2': '>>=',
    '_3': '<<=',
    '_4': '&=',
    '_5': '|=',
    '_6': '^='
}


_special_char_map = {
    '0': ',',
    '1': '/',
    '2': '\\',
    '3': ':',
    '4': '.',
    '5': ' ',
    '6': '\x0B',
    '7': '\x0A',
    '8': '\'',
    '9': '-'
}


def _encoded_hex_to_num(s):
    num = 0
    for index, char in enumerate(s):
        num += (ord(char) - ord('A')) * (len(s) - index)
    return num


_ENCODED_NUMBER_RE = re.compile(r"""
(?P<zero_sym>           @)
(?P<digit_sym>          [0-9])
(?P<hex_sym>            [A-P]+@)
""", re.X)


def _parse_encoded_number(cursor):
    negative = False
    if cursor.accept('?'):
        negative = True

    match = cursor.match(_ENCODED_NUMBER_RE)
    if match is None:
        return None
    elif match.group('zero_sym') is not None:
        num = 0
    elif match.group('digit_sym') is not None:
        num = int(match.group('digit_sym')) + 1
    elif match.group('hex_sym') is not None:
        num = _encoded_hex_to_num(match.group('hex_sym'))
    else:
        return None

    if negative:
        num = -num

    return num


_ENCODED_CHAR_RE = re.compile(r"""
(?P<hex_byte>           \?$) |
(?P<char_literal>       \?\d) |
(?P<far_ascii>          \?) |
(?P<literal_char>       .)
""", re.X)


def _parse_char(cursor):
    match = cursor.match(_ENCODED_CHAR_RE)
    if match is None:
        return None
    elif match.group('hex_byte') is not None:
        byte = chr(_encoded_hex_to_num(match.group('hex_byte')))
    elif match.group('char_literal') is not None:
        byte = _special_char_map[match.group('char_literal')]
    elif match.group('far_ascii') is not None:
        byte = chr(_encoded_hex_to_num(match.group('far_ascii')) + 128)
    elif match.group('literal_char') is not None:
        byte = match.group('literal_char')
    else:
        return None
    return byte


_OPERATORS_KEYS = "|".join(_operators.keys())


_SPECIAL_NAME_RE = re.compile(r"""
(?P<ctor_name>          0) |
(?P<dtor_name>          1) |
(?P<operator_name>      """ + _OPERATORS_KEYS + """)
""", re.X)


def _parse_special_name(cursor):
    match = cursor.match(_SPECIAL_NAME_RE)

    if match.group('ctor_name') is not None:
        node = Node('ctor', 'complete')
    elif match.group('dtor_name') is not None:
        node = Node('dtor', 'complete')
    elif match.group('operator_name') is not None:
        node = Node('oper', _operators[match.group('operator_name')])
    else:
        return None

    return node


def _parse_template_type(cursor):  # TODO
    pass


def _parse_numbered_namespace(cursor):  # TODO
    pass


def _parse_substitution(cursor):  # TODO
    pass


_BASIC_NAME_RE = re.compile(r"""
(?P<name_fragment>      [a-zA-Z0-9_]+@) |
(?P<template_name>      \?$) |
(?P<special_name>       \?)
""", re.X)


_NAME_RE = re.compile(r"""
(?P<name_fragment>      [a-zA-Z0-9_]+@) |
(?P<template_name>      \?$) |
(?P<numbered_namespace> \?[A-P]) |
(?P<substitution>       \d)
""", re.X)


def _parse_name(cursor):
    nodes = []

    match = cursor.match(_BASIC_NAME_RE)
    if match.group('name_fragment') is not None:
        name = match.group('name_fragment')[:-1]
        nodes.append(Node('name', name))
    elif match.group('special_name') is not None:
        node = _parse_special_name(cursor)
        if node is None:
            return None
        nodes.append(node)
    elif match.group('template_name') is not None:
        node = _parse_template_type(cursor)
        if node is None:
            return None
        nodes.append(node)
    else:
        return None

    while not cursor.accept('@'):
        match = cursor.match(_NAME_RE)
        if match is None:
            return None
        elif match.group('name_fragment') is not None:
            name = match.group('name_fragment')[:-1]
            node = Node('name', name)
        elif match.group('template_name') is not None:
            node = _parse_template_type(cursor)
        elif match.group('numbered_namespace') is not None:
            node = _parse_numbered_namespace(cursor)
        elif match.group('substitution') is not None:
            node = _parse_substitution(cursor)
        else:
            return None

        if node is None:
            return None
        nodes.append(node)

    nodes.reverse()

    if len(nodes) > 1:
        return Node('qual_name', tuple(nodes))
    else:
        return nodes[0]


_ENCODING_RE = re.compile(r"""
(?P<name_only>          $) |
(?P<data_encoding>      \d) |
(?P<function_encoding>  [A-Z])
""", re.X)


def _parse_encoding(cursor):
    name = _parse_name(cursor)
    if name is None:
        return None

    match = cursor.match(_ENCODING_RE)
    if match is None:
        return None
    elif match.group('name_only') is not None:
        return name
    elif match.group('data_encoding') is not None:
        pass  # TODO: Parse data
    elif match.group('function_encoding') is not None:
        pass  # TODO: Parse function
    else:
        return None

    return name


_MANGLED_NAME_RE = re.compile(r"""
(?P<mangled_name>       @?\?)
""", re.X)


def _parse_mangled_name(cursor):
    match = cursor.match(_MANGLED_NAME_RE)
    if match is None:
        return None
    return _parse_encoding(cursor)


def _expand_pack_args(ast):
    pass


def parse(raw):
    ast = _parse_mangled_name(_Cursor(raw))
    if ast is not None:
        _expand_pack_args(ast)
    return ast
