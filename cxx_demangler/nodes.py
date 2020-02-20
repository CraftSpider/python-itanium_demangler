
from collections import namedtuple


class Node(namedtuple('Node', 'kind value')):
    def __repr__(self):
        return "<Node {} {}>".format(self.kind, repr(self.value))

    def __str__(self):
        if self.kind in ('name', 'builtin'):
            return self.value
        elif self.kind == 'qual_name':
            result = ''
            for node in self.value:
                if result != '' and node.kind != 'tpl_args':
                    result += '::'
                result += str(node)
            return result
        elif self.kind == 'tpl_args':
            return '<' + ', '.join(map(str, self.value)) + '>'
        elif self.kind == 'ctor':
            if self.value == 'complete':
                return '{ctor}'
            elif self.value == 'base':
                return '{base ctor}'
            elif self.value == 'allocating':
                return '{allocating ctor}'
            else:
                assert False
        elif self.kind == 'dtor':
            if self.value == 'deleting':
                return '{deleting dtor}'
            elif self.value == 'complete':
                return '{dtor}'
            elif self.value == 'base':
                return '{base dtor}'
            else:
                assert False
        elif self.kind == 'oper':
            if self.value.startswith('new') or self.value.startswith('delete'):
                return 'operator ' + self.value
            else:
                return 'operator' + self.value
        elif self.kind == 'oper_cast':
            return 'operator ' + str(self.value)
        elif self.kind == 'pointer':
            return self.value.left() + '*' + self.value.right()
        elif self.kind == 'lvalue':
            return self.value.left() + '&' + self.value.right()
        elif self.kind == 'rvalue':
            return self.value.left() + '&&' + self.value.right()
        elif self.kind == 'tpl_param':
            return '{T' + str(self.value) + '}'
        elif self.kind == 'subst':
            return '{S' + str(self.value) + '}'
        elif self.kind == 'vtable':
            return 'vtable for ' + str(self.value)
        elif self.kind == 'vtt':
            return 'vtt for ' + str(self.value)
        elif self.kind == 'typeinfo':
            return 'typeinfo for ' + str(self.value)
        elif self.kind == 'typeinfo_name':
            return 'typeinfo name for ' + str(self.value)
        elif self.kind == 'nonvirt_thunk':
            return 'non-virtual thunk for ' + str(self.value)
        elif self.kind == 'virt_thunk':
            return 'virtual thunk for ' + str(self.value)
        elif self.kind == 'guard_variable':
            return 'guard variable for ' + str(self.value)
        elif self.kind == 'transaction_clone':
            return 'transaction clone for ' + str(self.value)
        else:
            return repr(self)

    def left(self):
        if self.kind == "pointer":
            return self.value.left() + "*"
        elif self.kind == "lvalue":
            return self.value.left() + "&"
        elif self.kind == "rvalue":
            return self.value.left() + "&&"
        else:
            return str(self)

    def right(self):
        if self.kind in ("pointer", "lvalue", "rvalue"):
            return self.value.right()
        else:
            return ""

    def map(self, f):
        if self.kind in ('oper_cast', 'pointer', 'lvalue', 'rvalue', 'expand_arg_pack',
                         'vtable', 'vtt', 'typeinfo', 'typeinfo_name'):
            return self._replace(value=f(self.value))
        elif self.kind in ('qual_name', 'tpl_args', 'tpl_arg_pack'):
            return self._replace(value=tuple(map(f, self.value)))
        else:
            return self


class QualNode(namedtuple('QualNode', 'kind value qual')):
    def __repr__(self):
        return "<QualNode {} {} {}>".format(self.kind, repr(self.qual), repr(self.value))

    def __str__(self):
        if self.kind == 'abi':
            return str(self.value) + "".join(['[abi:' + tag + ']' for tag in self.qual])
        elif self.kind == 'cv_qual':
            return ' '.join([str(self.value)] + list(self.qual))
        else:
            return repr(self)

    def left(self):
        return str(self)

    def right(self):
        return ""

    def map(self, f):
        if self.kind == 'cv_qual':
            return self._replace(value=f(self.value))
        else:
            return self


class CastNode(namedtuple('CastNode', 'kind value ty')):
    def __repr__(self):
        return "<CastNode {} {} {}>".format(self.kind, repr(self.ty), repr(self.value))

    def __str__(self):
        if self.kind == 'literal':
            return '(' + str(self.ty) + ')' + str(self.value)
        else:
            return repr(self)

    def left(self):
        return str(self)

    def right(self):
        return ""

    def map(self, f):
        if self.kind == 'literal':
            return self._replace(ty=f(self.ty))
        else:
            return self


class FuncNode(namedtuple('FuncNode', 'kind name arg_tys ret_ty')):
    def __repr__(self):
        return "<FuncNode {} {} {} {}>".format(self.kind, repr(self.name),
                                               repr(self.arg_tys), repr(self.ret_ty))

    def __str__(self):
        if self.kind == 'func':
            result = ""
            if self.ret_ty is not None:
                result += str(self.ret_ty) + ' '
            if self.name is not None:
                result += str(self.name)
            if self.arg_tys == (Node('builtin', 'void'),):
                result += '()'
            else:
                result += '(' + ', '.join(map(str, self.arg_tys)) + ')'
            return result
        else:
            return repr(self)

    def left(self):
        if self.kind == 'func':
            result = ""
            if self.ret_ty is not None:
                result += str(self.ret_ty) + ' '
            result += "("
            if self.name is not None:
                result += str(self.name)
            return result
        else:
            return str(self)

    def right(self):
        if self.kind == 'func':
            result = ")"
            if self.arg_tys == (Node('builtin', 'void'),):
                result += '()'
            else:
                result += '(' + ', '.join(map(str, self.arg_tys)) + ')'
            return result
        else:
            return ""

    def map(self, f):
        if self.kind == 'func':
            return self._replace(name=f(self.name) if self.name else None,
                                 arg_tys=tuple(map(f, self.arg_tys)),
                                 ret_ty=f(self.ret_ty) if self.ret_ty else None)
        else:
            return self


class ArrayNode(namedtuple('ArrayNode', 'kind dimension ty')):
    def __repr__(self):
        return "<ArrayNode {} {} {}>".format(self.kind, repr(self.dimension), repr(self.ty))

    def __str__(self):
        if self.kind == 'array':
            result = ""
            result += str(self.ty)
            result += "[" + str(self.dimension) + "]"
            return result
        else:
            return repr(self)

    def left(self):
        if self.kind == 'array':
            result = str(self.ty) + "("
            return result
        else:
            return str(self)

    def right(self):
        if self.kind == 'array':
            result = ")[" + str(self.dimension) + "]"
            return result
        else:
            return ""

    def map(self, f):
        if self.kind == 'array':
            return self._replace(dimension=f(self.dimension) if self.dimension else None,
                                 ty=f(self.ty) if self.ty else None)
        else:
            return self


class MemberNode(namedtuple('MemberNode', 'kind cls_ty member_ty')):
    def __repr__(self):
        return "<MemberNode {} {} {}>".format(self.kind, repr(self.cls_ty), repr(self.member_ty))

    def __str__(self):
        if self.kind == 'data':
            result = str(self.member_ty) + " " + str(self.cls_ty) + "::*"
            return result
        elif self.kind == 'method':
            result = self.member_ty.left() + str(self.cls_ty) + "::*" + self.member_ty.right()
            return result
        else:
            return repr(self)

    def left(self):
        if self.kind == 'method':
            return self.member_ty.left() + str(self.cls_ty) + "::*"
        else:
            return str(self)

    def right(self):
        if self.kind == 'method':
            return self.member_ty.right()
        else:
            return ""

    def map(self, f):
        if self.kind in ('data', 'func'):
            return self._replace(cls_ty=f(self.cls_ty) if self.cls_ty else None,
                                 member_ty=f(self.member_ty) if self.member_ty else None)
        else:
            return self
