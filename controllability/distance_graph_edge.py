__author__ = 'yupeng'

class EdgeType(object):
    SIMPLE = 1
    LOWER_CASE = 2
    UPPER_CASE = 3

class DistanceGraphEdge(object):
    def __init__(self, fro, to, value, edge_type, maybe_letter=None, renaming=None):
        self.fro = fro
        self.to = to
        self.value = value
        self.edge_type = edge_type
        self.maybe_letter = maybe_letter
        self.renaming = renaming

    def hash(self):
        return hash((self.fro, self.to, self.value, self.edge_type, self.maybe_letter))

    def _printit(self, fro, to, maybe_letter):
        type_str = ''
        if self.edge_type == EdgeType.UPPER_CASE:
            type_str = 'UC(%s):' % maybe_letter
        elif self.edge_type == EdgeType.LOWER_CASE:
            type_str = 'LC(%s):' % maybe_letter
        return '%s\t\t---[%s%.1f]---> \t\t%s' % (fro,
                                    type_str,
                                    self.value,
                                    to)

    def __unicode__(self):
        if self.renaming is None:
            return self._printit(self.fro, self.to, self.maybe_letter)
        else:
            return self._printit(self.renaming[self.fro],
                          self.renaming[self.to],
                          self.renaming[self.maybe_letter]
                          if self.maybe_letter is not None else None)


    def __str__(self):
        return self.__unicode__()