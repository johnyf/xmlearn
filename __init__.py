"""Routines to parse mpd's protocol documentation."""

class LXML_Dumper(object):
    """Dump an lxml.etree tree starting at `element`.
    
    Attributes:
        maxdepth: the maximum recursion level.
        width: the width at which text will be wrapped.
        rules: either a string matching one of the keys of rulesets,
                 or a Mapping containing such a ruleset.

    For now, this function is just useful for sussing out the shape of the XML.

    Setup:
        >>> import lxml.etree as etree
        >>> book = etree.parse('protocol.xml').getroot()
        >>> dumper = LXML_Dumper(maxdepth=2)
        >>> dumper.dump(book)
        The Music Player Daemon protocol (/book):
        [title] (/book/title): The Music Player Daemon protocol
        General protocol syntax (/book/chapter[1]):
            [title] (/book/chapter[1]/title): General protocol syntax
            Requests (/book/chapter[1]/section[1])
            Responses (/book/chapter[1]/section[2])
            Command lists (/book/chapter[1]/section[3])
            Ranges (/book/chapter[1]/section[4])
        Command reference (/book/chapter[2]):
            [title] (/book/chapter[2]/title): Command reference
            [note] (/book/chapter[2]/note):
            Querying MPD's status (/book/chapter[2]/section[1])
            Playback options (/book/chapter[2]/section[2])
            Controlling playback (/book/chapter[2]/section[3])
            The current playlist (/book/chapter[2]/section[4])
            Stored playlists (/book/chapter[2]/section[5])
            The music database (/book/chapter[2]/section[6])
            Stickers (/book/chapter[2]/section[7])
            Connection settings (/book/chapter[2]/section[8])
            Audio output devices (/book/chapter[2]/section[9])
            Reflection (/book/chapter[2]/section[10])
        >>> for c in book.iterdescendants('section'):
        ...     dumper.dump(c, maxdepth=0, rules='full')
        Requests (/book/chapter[1]/section[1]):
        Responses (/book/chapter[1]/section[2]):
        Command lists (/book/chapter[1]/section[3]):
        Ranges (/book/chapter[1]/section[4]):
        Querying MPD's status (/book/chapter[2]/section[1]):
        Playback options (/book/chapter[2]/section[2]):
        Controlling playback (/book/chapter[2]/section[3]):
        The current playlist (/book/chapter[2]/section[4]):
        Stored playlists (/book/chapter[2]/section[5]):
        The music database (/book/chapter[2]/section[6]):
        Stickers (/book/chapter[2]/section[7]):
        Connection settings (/book/chapter[2]/section[8]):
        Audio output devices (/book/chapter[2]/section[9]):
        Reflection (/book/chapter[2]/section[10]):

    """

    # Each ruleset maps tags to kwargs for `format_element`.
    rulesets = {'book': {'section': {'with_text': False},
                         'para': {'linebreak': True},
                         None: {'recurse': True}},
                'full': {None: {'recurse': True}}}

    maxdepth = None
    width = 80
    rules = rulesets['book']

    def __init__(self, **kwargs):
        """Initialize object attributes documented in the class docstring."""
        self.__dict__.update(kwargs)

    def relwrap(self, *args, **kwargs):
        """Wrap the text with an indent relative to the `depth` keyword arg.

        The text is indented 4 spaces for each level of depth.
        Wrapped lines are indented an extra 2 spaces.
        """
        from textwrap import wrap
        depth = kwargs.pop('depth', 0)
        wrap_kwargs = dict({'initial_indent': '    ' * depth,
                            'subsequent_indent': '    ' * depth + '  '})
        if hasattr(self, 'width'):
            wrap_kwargs.update(width=self.width)
        wrap_kwargs.update(kwargs)
        return "\n".join(wrap(*args, **wrap_kwargs))

    def format_element(self, element, depth, linebreak=False, with_text=True):
        from textwrap import dedent
        title = getattr(element.find('title'), 'text', '')
        title = title if title else '[{0}]'.format(element.tag)
        path = element.getroottree().getpath(element)
        eltext = getattr(element, 'text', '')
        eltext = dedent(eltext if eltext else '')
        if linebreak:
            summary = "{0} ({1}):".format(title, path)
            return "\n".join([self.relwrap(summary, depth=depth),
                              self.relwrap(eltext, depth=depth+1)])
        else:
            fmt = "{0} ({1}): {2}" if with_text else "{0} ({1})"
            return self.relwrap(fmt.format(title, path, eltext), depth=depth)

    def dump(self, element, **kwargs):
        """Dump `element` according to `rules`.
        
        Keyword arguments:
            depth: the initial depth of the dump.  Normally this will be 0.

            Additionally, the `maxdepth` and `rules` object keyword arguments
              can be overridden.
        """
        from copy import copy
        from collections import Mapping

        depth = kwargs.pop('depth', 0)
        maxdepth, rules = (kwargs.pop(a, getattr(self, a))
                           for a in ('maxdepth', 'rules'))

        if isinstance(rules, Mapping):
            pass
        elif isinstance(rules, basestring):
            rules = self.rulesets[rules]
        assert isinstance(rules, Mapping)

        def _dump(element, depth=0):
            for rule in rules.iteritems():
                if rule[0] == None:
                    default = copy(rule[1])
                elif rule[0] == element.tag:
                    kwargs = copy(rule[1])
                    break
            else:
                assert vars().has_key('default')
                kwargs = default

            recurse = kwargs.pop('recurse', False)
            print self.format_element(element, depth, **kwargs)
            if recurse:
                if (maxdepth is None or maxdepth > depth):
                    for child in element.getchildren():
                        _dump(child, depth + 1)

        _dump(element, depth=depth)
                    
    def iter_unique_child_tags(self, root, tag):
        """Iterates through unique child tags for all instances of `tag`.

        Iteration starts at `root`.
        """
        found_child_tags = set()
        instances = root.iterdescendants(tag)
        from itertools import chain
        child_nodes = chain.from_iterable(i.getchildren() for i in instances)
        child_tags = (n.tag for n in child_nodes)
        for t in child_tags:
            if t not in found_child_tags:
                found_child_tags.add(t)
                yield t

    def iter_tag_list(self, root):
        """List all unique tags at and under the `root` node."""
        found_tags = set()
        tags = (n.tag for n in root.iterdescendants() if hasattr(n, 'tag'))
        for t in tags:
            if t not in found_tags:
                found_tags.add(t)
                yield t

    def build_tag_graph(self, root):
        """Build a python-graph graph of the tag relationships."""
        from pygraph.classes.digraph import digraph

        g = digraph()

        tags = list(self.iter_tag_list(root))
        g.add_nodes(tags)

        for parent in tags:
            for child in self.iter_unique_child_tags(root, parent):
                g.add_edge((parent, child))

        return g

    def write_graph(self, graph, filename, format='png'):
        """Write a python-graph graph as an image.

        `format` can be any of those supported by pydot.Dot.write().
        """
        from pygraph.readwrite.dot import write
        dotdata = write(graph)

        from pydot import graph_from_dot_data
        dotgraph = graph_from_dot_data(dotdata)
        dotgraph.write(filename, format=format)

    def write_tag_graph(self, root, filename, format='png'):
        graph = self.build_tag_graph(root)
        self.write_graph(graph, filename, format=format)
