
class _Cursor:
    def __init__(self, raw, pos=0):
        self._raw = raw
        self._pos = pos
        self._substs = {}

    def at_end(self):
        return self._pos == len(self._raw)

    def accept(self, delim):
        if self._raw[self._pos:self._pos + len(delim)] == delim:
            self._pos += len(delim)
            return True

    def advance(self, amount):
        if self._pos + amount > len(self._raw):
            return None
        result = self._raw[self._pos:self._pos + amount]
        self._pos += amount
        return result

    def advance_until(self, delim):
        new_pos = self._raw.find(delim, self._pos)
        if new_pos == -1:
            return None
        result = self._raw[self._pos:new_pos]
        self._pos = new_pos + len(delim)
        return result

    def match(self, pattern):
        match = pattern.match(self._raw, self._pos)
        if match:
            self._pos = match.end(0)
        return match

    def add_subst(self, node):
        # print("S[{}] = {}".format(len(self._substs), str(node)))
        if not node in self._substs.values():
            self._substs[len(self._substs)] = node

    def resolve_subst(self, seq_id):
        if seq_id in self._substs:
            return self._substs[seq_id]

    def __repr__(self):
        return "_Cursor({}, {})".format(self._raw[:self._pos] + '→' + self._raw[self._pos:],
                                        self._pos)
