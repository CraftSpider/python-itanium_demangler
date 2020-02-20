
import re

from .nodes import *
from ._cursor import _Cursor

_ctor_dtor_map = {
    'C1': 'complete',
    'C2': 'base',
    'C3': 'allocating',
    'D0': 'deleting',
    'D1': 'complete',
    'D2': 'base'
}

_std_names = {
    'St': [Node('name', 'std')],
    'Sa': [Node('name', 'std'), Node('name', 'allocator')],
    'Sb': [Node('name', 'std'), Node('name', 'basic_string')],
    'Ss': [Node('name', 'std'), Node('name', 'string')],
    'Si': [Node('name', 'std'), Node('name', 'istream')],
    'So': [Node('name', 'std'), Node('name', 'ostream')],
    'Sd': [Node('name', 'std'), Node('name', 'iostream')],
}

_operators = {
    'nw': 'new',
    'na': 'new[]',
    'dl': 'delete',
    'da': 'delete[]',
    'ps': '+', # (unary)
    'ng': '-', # (unary)
    'ad': '&', # (unary)
    'de': '*', # (unary)
    'co': '~',
    'pl': '+',
    'mi': '-',
    'ml': '*',
    'dv': '/',
    'rm': '%',
    'an': '&',
    'or': '|',
    'eo': '^',
    'aS': '=',
    'pL': '+=',
    'mI': '-=',
    'mL': '*=',
    'dV': '/=',
    'rM': '%=',
    'aN': '&=',
    'oR': '|=',
    'eO': '^=',
    'ls': '<<',
    'rs': '>>',
    'lS': '<<=',
    'rS': '>>=',
    'eq': '==',
    'ne': '!=',
    'lt': '<',
    'gt': '>',
    'le': '<=',
    'ge': '>=',
    'nt': '!',
    'aa': '&&',
    'oo': '||',
    'pp': '++', # (postfix in <expression> context)
    'mm': '--', # (postfix in <expression> context)
    'cm': ',',
    'pm': '->*',
    'pt': '->',
    'cl': '()',
    'ix': '[]',
    'qu': '?',
}

_builtin_types = {
    'v':  Node('builtin', 'void'),
    'w':  Node('builtin', 'wchar_t'),
    'b':  Node('builtin', 'bool'),
    'c':  Node('builtin', 'char'),
    'a':  Node('builtin', 'signed char'),
    'h':  Node('builtin', 'unsigned char'),
    's':  Node('builtin', 'short'),
    't':  Node('builtin', 'unsigned short'),
    'i':  Node('builtin', 'int'),
    'j':  Node('builtin', 'unsigned int'),
    'l':  Node('builtin', 'long'),
    'm':  Node('builtin', 'unsigned long'),
    'x':  Node('builtin', 'long long'),
    'y':  Node('builtin', 'unsigned long long'),
    'n':  Node('builtin', '__int128'),
    'o':  Node('builtin', 'unsigned __int128'),
    'f':  Node('builtin', 'float'),
    'd':  Node('builtin', 'double'),
    'e':  Node('builtin', '__float80'),
    'g':  Node('builtin', '__float128'),
    'z':  Node('builtin', '...'),
    'Dd': Node('builtin', '_Decimal64'),
    'De': Node('builtin', '_Decimal128'),
    'Df': Node('builtin', '_Decimal32'),
    'Dh': Node('builtin', '_Float16'),
    'Di': Node('builtin', 'char32_t'),
    'Ds': Node('builtin', 'char16_t'),
    'Da': Node('builtin', 'auto'),
    'Dn': Node('qual_name', (Node('name', 'std'), Node('builtin', 'nullptr_t')))
}


def _handle_cv(qualifiers, node):
    qualifier_set = set()
    if 'r' in qualifiers:
        qualifier_set.add('restrict')
    if 'V' in qualifiers:
        qualifier_set.add('volatile')
    if 'K' in qualifiers:
        qualifier_set.add('const')
    if qualifier_set:
        return QualNode('cv_qual', node, frozenset(qualifier_set))
    return node

def _handle_indirect(qualifier, node):
    if qualifier == 'P':
        return Node('pointer', node)
    elif qualifier == 'R':
        return Node('lvalue', node)
    elif qualifier == 'O':
        return Node('rvalue', node)
    return node


_NUMBER_RE = re.compile(r"\d+")

def _parse_number(cursor):
    match = cursor.match(_NUMBER_RE)
    if match is None:
        return None
    return int(match.group(0))

def _parse_seq_id(cursor):
    seq_id = cursor.advance_until('_')
    if seq_id is None:
        return None
    if seq_id == '':
        return 0
    else:
        return 1 + int(seq_id, 36)

def _parse_until_end(cursor, kind, fn):
    nodes = []
    while not cursor.accept('E'):
        node = fn(cursor)
        if node is None or cursor.at_end():
            return None
        nodes.append(node)
    return Node(kind, tuple(nodes))


_SOURCE_NAME_RE = re.compile(r"\d+")

def _parse_source_name(cursor):
    match = cursor.match(_SOURCE_NAME_RE)
    name_len = int(match.group(0))
    name = cursor.advance(name_len)
    if name is None:
        return None
    return name


_NAME_RE = re.compile(r"""
(?P<source_name>        (?= \d)) |
(?P<ctor_name>          C[123]) |
(?P<dtor_name>          D[012]) |
(?P<std_name>           S[absiod]) |
(?P<operator_name>      nw|na|dl|da|ps|ng|ad|de|co|pl|mi|ml|dv|rm|an|or|
                        eo|aS|pL|mI|mL|dV|rM|aN|oR|eO|ls|rs|lS|rS|eq|ne|
                        lt|gt|le|ge|nt|aa|oo|pp|mm|cm|pm|pt|cl|ix|qu) |
(?P<operator_cv>        cv) |
(?P<std_prefix>         St) |
(?P<substitution>       S) |
(?P<nested_name>        N (?P<cv_qual> [rVK]*) (?P<ref_qual> [RO]?)) |
(?P<template_param>     T) |
(?P<template_args>      I) |
(?P<constant>           L) |
(?P<local_name>         Z) |
(?P<unnamed_type>       Ut) |
(?P<closure_type>       Ul)
""", re.X)

def _parse_name(cursor, is_nested=False):
    match = cursor.match(_NAME_RE)
    if match is None:
        return None
    elif match.group('source_name') is not None:
        name = _parse_source_name(cursor)
        if name is None:
            return None
        node = Node('name', name)
    elif match.group('ctor_name') is not None:
        node = Node('ctor', _ctor_dtor_map[match.group('ctor_name')])
    elif match.group('dtor_name') is not None:
        node = Node('dtor', _ctor_dtor_map[match.group('dtor_name')])
    elif match.group('std_name') is not None:
        node = Node('qual_name', _std_names[match.group('std_name')])
    elif match.group('operator_name') is not None:
        node = Node('oper', _operators[match.group('operator_name')])
    elif match.group('operator_cv') is not None:
        ty = _parse_type(cursor)
        if ty is None:
            return None
        node = Node('oper_cast', ty)
    elif match.group('std_prefix') is not None:
        name = _parse_name(cursor, is_nested=True)
        if name is None:
            return None
        if name.kind == 'qual_name':
            node = Node('qual_name', (Node('name', 'std'),) + name.value)
        else:
            node = Node('qual_name', (Node('name', 'std'), name))
    elif match.group('substitution') is not None:
        seq_id = _parse_seq_id(cursor)
        if seq_id is None:
            return None
        node = cursor.resolve_subst(seq_id)
        if node is None:
            return None
    elif match.group('nested_name') is not None:
        nodes = []
        while True:
            name = _parse_name(cursor, is_nested=True)
            if name is None or cursor.at_end():
                return None
            if name.kind == 'qual_name':
                nodes += name.value
            else:
                nodes.append(name)
            if cursor.accept('E'):
                break
            else:
                cursor.add_subst(Node('qual_name', tuple(nodes)))
        node = Node('qual_name', tuple(nodes))
        node = _handle_cv(match.group('cv_qual'), node)
        node = _handle_indirect(match.group('ref_qual'), node)
    elif match.group('template_param') is not None:
        seq_id = _parse_seq_id(cursor)
        if seq_id is None:
            return None
        node = Node('tpl_param', seq_id)
        cursor.add_subst(node)
    elif match.group('template_args') is not None:
        node = _parse_until_end(cursor, 'tpl_args', _parse_type)
    elif match.group('constant') is not None:
        # not in the ABI doc, but probably means `const`
        return _parse_name(cursor, is_nested)
    elif match.group('local_name') is not None:
        raise NotImplementedError("local names are not supported")
    elif match.group('unnamed_type') is not None:
        raise NotImplementedError("unnamed types are not supported")
    elif match.group('closure_type') is not None:
        raise NotImplementedError("closure (lambda) types are not supported")
    if node is None:
        return None

    abi_tags = []
    while cursor.accept('B'):
        abi_tags.append(_parse_source_name(cursor))
    if abi_tags:
        node = QualNode('abi', node, frozenset(abi_tags))

    if not is_nested and cursor.accept('I') and (
            node.kind in ('name', 'oper', 'oper_cast') or
            match.group('std_prefix') is not None or
            match.group('std_name') is not None or
            match.group('substitution') is not None):
        if node.kind in ('name', 'oper', 'oper_cast') or match.group('std_prefix') is not None:
            cursor.add_subst(node) # <unscoped-template-name> ::= <substitution>
        templ_args = _parse_until_end(cursor, 'tpl_args', _parse_type)
        if templ_args is None:
            return None
        node = Node('qual_name', (node, templ_args))
        if ((match.group('std_prefix') is not None or
                match.group('std_name') is not None) and
                node.value[0].value[1].kind not in ('oper', 'oper_cast')):
            cursor.add_subst(node)

    return node


_TYPE_RE = re.compile(r"""
(?P<builtin_type>       v|w|b|c|a|h|s|t|i|j|l|m|x|y|n|o|f|d|e|g|z|
                        Dd|De|Df|Dh|DF|Di|Ds|Da|Dc|Dn) |
(?P<qualified_type>     [rVK]+) |
(?P<indirect_type>      [PRO]) |
(?P<function_type>      F) |
(?P<expression>         X) |
(?P<expr_primary>       (?= L)) |
(?P<template_arg_pack>  J) |
(?P<arg_pack_expansion> Dp) |
(?P<decltype>           D[tT]) |
(?P<array_type>         A) |
(?P<member_type>        M)
""", re.X)

def _parse_type(cursor):
    match = cursor.match(_TYPE_RE)
    if match is None:
        node = _parse_name(cursor)
        cursor.add_subst(node)
    elif match.group('builtin_type') is not None:
        node = _builtin_types[match.group('builtin_type')]
    elif match.group('qualified_type') is not None:
        ty = _parse_type(cursor)
        if ty is None:
            return None
        node = _handle_cv(match.group('qualified_type'), ty)
        cursor.add_subst(node)
    elif match.group('indirect_type') is not None:
        ty = _parse_type(cursor)
        if ty is None:
            return None
        node = _handle_indirect(match.group('indirect_type'), ty)
        cursor.add_subst(node)
    elif match.group('function_type') is not None:
        ret_ty = _parse_type(cursor)
        if ret_ty is None:
            return None
        arg_tys = []
        while not cursor.accept('E'):
            arg_ty = _parse_type(cursor)
            if arg_ty is None:
                return None
            arg_tys.append(arg_ty)
        node = FuncNode('func', None, tuple(arg_tys), ret_ty)
        cursor.add_subst(node)
    elif match.group('expression') is not None:
        raise NotImplementedError("expressions are not supported")
    elif match.group('expr_primary') is not None:
        node = _parse_expr_primary(cursor)
    elif match.group('template_arg_pack') is not None:
        node = _parse_until_end(cursor, 'tpl_arg_pack', _parse_type)
    elif match.group('arg_pack_expansion') is not None:
        node = _parse_type(cursor)
        node = Node('expand_arg_pack', node)
    elif match.group('decltype') is not None:
        raise NotImplementedError("decltype is not supported")
    elif match.group('array_type') is not None:
        dimension = _parse_number(cursor)
        if dimension is None:
            return None
        else:
            dimension = CastNode('literal', dimension, Node('builtin', 'int'))
        if not cursor.accept('_'):
            return None
        type = _parse_type(cursor)
        node = ArrayNode('array', dimension, type)
        cursor.add_subst(node)
    elif match.group('member_type') is not None:
        cls_ty = _parse_type(cursor)
        member_ty = _parse_type(cursor)
        if member_ty.kind == 'func':
            kind = "method"
        else:
            kind = "data"
        node = MemberNode(kind, cls_ty, member_ty)
    else:
        return None
    return node


_EXPR_PRIMARY_RE = re.compile(r"""
(?P<mangled_name>       L (?= _Z)) |
(?P<literal>            L)
""", re.X)

def _parse_expr_primary(cursor):
    match = cursor.match(_EXPR_PRIMARY_RE)
    if match is None:
        return None
    elif match.group('mangled_name') is not None:
        mangled_name = cursor.advance_until('E')
        return _parse_mangled_name(_Cursor(mangled_name))
    elif match.group('literal') is not None:
        ty = _parse_type(cursor)
        if ty is None:
            return None
        value = cursor.advance_until('E')
        if value is None:
            return None
        return CastNode('literal', value, ty)


def _expand_template_args(func):
    if func.name.kind == 'qual_name':
        name_suffix = func.name.value[-1]
        if name_suffix.kind == 'tpl_args':
            tpl_args = name_suffix.value
            def mapper(node):
                if node.kind == 'tpl_param' and node.value < len(tpl_args):
                    return tpl_args[node.value]
                return node.map(mapper)
            return mapper(func)
    return func

def _parse_encoding(cursor):
    name = _parse_name(cursor)
    if name is None:
        return None
    if cursor.at_end():
        return name

    if name.kind == 'qual_name' \
            and name.value[-1].kind == 'tpl_args' \
            and name.value[-2].kind not in ('ctor', 'dtor', 'oper_cast'):
        ret_ty = _parse_type(cursor)
        if ret_ty is None:
            return None
    else:
        ret_ty = None

    arg_tys = []
    while not cursor.at_end():
        arg_ty = _parse_type(cursor)
        if arg_ty is None:
            return None
        arg_tys.append(arg_ty)

    if arg_tys:
        func = FuncNode('func', name, tuple(arg_tys), ret_ty)
        return _expand_template_args(func)
    else:
        return name


_SPECIAL_RE = re.compile(r"""
(?P<rtti>               T (?P<kind> [VTIS])) |
(?P<nonvirtual_thunk>   Th (?P<nv_offset> n? \d+) _) |
(?P<virtual_thunk>      Tv (?P<v_offset> n? \d+) _ (?P<vcall_offset> n? \d+) _) |
(?P<covariant_thunk>    Tc) |
(?P<guard_variable>     GV) |
(?P<extended_temporary> GR) |
(?P<transaction_clone>  GTt)
""", re.X)

def _parse_special(cursor):
    match = cursor.match(_SPECIAL_RE)
    if match is None:
        return None
    elif match.group('rtti') is not None:
        name = _parse_type(cursor)
        if name is None:
            return None
        if match.group('kind') == 'V':
            return Node('vtable', name)
        elif match.group('kind') == 'T':
            return Node('vtt', name)
        elif match.group('kind') == 'I':
            return Node('typeinfo', name)
        elif match.group('kind') == 'S':
            return Node('typeinfo_name', name)
    elif match.group('nonvirtual_thunk') is not None:
        func = _parse_encoding(cursor)
        if func is None:
            return None
        return Node('nonvirt_thunk', func)
    elif match.group('virtual_thunk') is not None:
        func = _parse_encoding(cursor)
        if func is None:
            return None
        return Node('virt_thunk', func)
    elif match.group('covariant_thunk') is not None:
        raise NotImplementedError("covariant thunks are not supported")
    elif match.group('guard_variable'):
        name = _parse_type(cursor)
        if name is None:
            return None
        return Node('guard_variable', name)
    elif match.group('extended_temporary'):
        raise NotImplementedError("extended temporaries are not supported")
    elif match.group('transaction_clone'):
        func = _parse_encoding(cursor)
        if func is None:
            return None
        return Node('transaction_clone', func)


_MANGLED_NAME_RE = re.compile(r"""
(?P<mangled_name>       _?_Z)
""", re.X)

def _parse_mangled_name(cursor):
    match = cursor.match(_MANGLED_NAME_RE)
    if match is None:
        return None
    else:
        special = _parse_special(cursor)
        if special is not None:
            return special

        return _parse_encoding(cursor)


def _expand_arg_packs(ast):
    def mapper(node):
        if node.kind == 'tpl_args':
            exp_args = []
            for arg in node.value:
                if arg.kind in ['tpl_arg_pack', 'tpl_args']:
                    exp_args += arg.value
                else:
                    exp_args.append(arg)
            return Node('tpl_args', tuple(map(mapper, exp_args)))
        elif node.kind == 'func':
            node = node.map(mapper)
            exp_arg_tys = []
            for arg_ty in node.arg_tys:
                if arg_ty.kind == 'expand_arg_pack' and \
                        arg_ty.value.kind == 'rvalue' and \
                            arg_ty.value.value.kind in ['tpl_arg_pack', 'tpl_args']:
                    exp_arg_tys += arg_ty.value.value.value
                else:
                    exp_arg_tys.append(arg_ty)
            return node._replace(arg_tys=tuple(exp_arg_tys))
        else:
            return node.map(mapper)
    return mapper(ast)

def parse(raw):
    ast = _parse_mangled_name(_Cursor(raw))
    if ast is not None:
        ast = _expand_arg_packs(ast)
    return ast
