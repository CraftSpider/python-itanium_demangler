# encoding:utf-8
name = "cxx_demangler"

"""
This module implements a C++ Itanium ABI demangler.

The demangler provides a single entry point, `demangle`, and returns either `None`
or an abstract syntax tree. All nodes have, at least, a `kind` field.

Name nodes:
    * `name`: `node.value` (`str`) holds an unqualified name
    * `ctor`: `node.value` is one of `"complete"`, `"base"`, or `"allocating"`, specifying
      the type of constructor
    * `dtor`: `node.value` is one of `"deleting"`, `"complete"`, or `"base"`, specifying
      the type of destructor
    * `oper`: `node.value` (`str`) holds a symbolic operator name, without the keyword
      "operator"
    * `oper_cast`: `node.value` holds a type node
    * `tpl_args`: `node.value` (`tuple`) holds a sequence of type nodes
    * `qual_name`: `node.value` (`tuple`) holds a sequence of `name` and `tpl_args` nodes,
      possibly ending in a `ctor`, `dtor` or `operator` node
    * `abi`: `node.value` holds a name node, `node.qual` (`frozenset`) holds a set of ABI tags

Type nodes:
    * `name` and `qual_name` specify a type by its name
    * `builtin`: `node.value` (`str`) specifies a builtin type by its name
    * `pointer`, `lvalue` and `rvalue`: `node.value` holds a pointee type node
    * `cv_qual`: `node.value` holds a type node, `node.qual` (`frozenset`) is any of
      `"const"`, `"volatile"`, or `"restrict"`
    * `literal`: `node.value` (`str`) holds the literal representation as-is,
      `node.ty` holds a type node specifying the type of the literal
    * `function`: `node.name` holds a name node specifying the function name,
      `node.ret_ty` holds a type node specifying the return type of a template function,
      if any, or `None`, ``node.arg_tys` (`tuple`) holds a sequence of type nodes
      specifying thefunction arguments

Special nodes:
    * `vtable`, `vtt`, `typeinfo`, and `typeinfo_name`: `node.value` holds a type node
      specifying the type described by this RTTI data structure
    * `nonvirt_thunk`, `virt_thunk`: `node.value` holds a function node specifying
      the function to which the thunk dispatches
"""

from cxx_demangler.nodes import *


def parse(raw, format=None):
    # TODO
    raise NotImplementedError("Parse type guessing not yet implemented")


# ================================================================================================


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        while True:
            name = sys.stdin.readline()
            if not name:
                break
            print(parse(name.strip()))
    else:
        for name in sys.argv[1:]:
            ast = parse(name)
            print(repr(ast))
            print(ast)
