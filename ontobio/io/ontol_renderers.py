"""
Various classes for rendering of ontology graphs
"""

import networkx as nx
from networkx.drawing.nx_pydot import write_dot
import tempfile
import os
import subprocess
import json
import logging

class GraphRendererConfig():
    """
    configuration parameters
    """
    def __init__(self,
                 relsymbolmap={
                     'subClassOf': '%',
                     'BFO:0000050': '<',
                     'RO:0002202': '~',
                 }):
        self.relsymbolmap = relsymbolmap
        

class GraphRenderer():
    """
    base class for writing networkx graphs
    """
    def __init__(self,
                 outfile=None,
                 config=None,
                 **args):
        self.outfile = outfile
        if config is None:
            config = GraphRendererConfig()
        self.config = config
        
    
    def render(self, ontol, **args):
        """
        Render a `ontology` object
        """
        pass

    def write(self, ontol, **args):
        """
        Write a `ontology` object
        """
        s = self.render(ontol, **args)
        if self.outfile is None:
            print(s)
        else:
            f = open(self.outfile, 'w')
            f.write(s)
            f.close()

    def render_subgraph(self, ontol, nodes, **args):
        """
        Render a `ontology` object after inducing a subgraph
        """
        subont = ontol.subontology(nodes)
        return self.render(subont, **args)
    
    def write_subgraph(self, ontol, nodes, **args):
        """
        Write a `ontology` object after inducing a subgraph
        """
        subont = ontol.subontology(nodes)
        self.write(subont, **args)

    def render_relation(self, r, **args):
        """
        Render an object property
        """
        if r is None:
            return "."
        m = self.config.relsymbolmap
        if r in m:
            return m[r]
        return r
    
    def render_noderef(self, ontol, n, query_ids=[], **args):
        """
        Render a node object
        """
        marker = ""
        if n in query_ids:
            marker = " * "
        label = ontol.label(n)
        if label is not None:
            return '{} ! {}{}'.format(str(n),
                                      label,
                                      marker)
        else:
            return str(n)
        
    @staticmethod
    def create(fmt):
        """
        Creates a GraphRenderer
        """
        w = None
        if fmt == 'tree':
            w = AsciiTreeGraphRenderer()
        elif fmt == 'dot':
            w = DotGraphRenderer(image_format='dot')
        elif fmt == 'png':
            w = DotGraphRenderer(image_format='png')
        elif fmt == 'ndot':
            w = NativeDotGraphRenderer()
        elif fmt == 'obo':
            w = OboFormatGraphRenderer()
        elif fmt == 'obog':
            w = OboJsonGraphRenderer()
        else:
            w = SimpleListGraphRenderer()
        return w
        
class NativeDotGraphRenderer(GraphRenderer):
    """
    writes as dot (graphviz format) files
    """
    def __init__(self, **args):
        super().__init__(**args)

    def render(self, ontol, **args):
        g = ontol.get_graph()
        _, fn = tempfile.mkstemp(suffix='dot')
        write_dot(g, fn)
        f = open(fn, 'r')
        s = f.read()
        f.close()
        return s

    def write(self, ontol, **args):
        g = ontol.get_graph()        
        fn = self.outfile
        if fn is None:
            _, fn = tempfile.mkstemp(suffix='dot')
        write_dot(g, fn)
        if self.outfile is None:
            f = open(fn, 'r')
            print(f.read())
            f.close()
            os.remove(fn)

class DotGraphRenderer(GraphRenderer):
    """
    uses js lib to generate png from dot

    This requires you install the node package [obographsviz](https://github.com/cmungall/obographviz)
    """
    def __init__(self,
                 image_format='png',
                 **args):
        super().__init__(**args)
        self.image_format = image_format
        # obographviz makes use of OboJson, so we leverage this here
        self.ojgr = OboJsonGraphRenderer(**args)

    # TODO: currently render and write are equivalent
    def render(self, ontol, query_ids=[], container_predicates=[], **args):
        g = ontol.get_graph()
        # create json object to pass to og2dot
        _, fn = tempfile.mkstemp(suffix='.json')
        self.ojgr.outfile = fn
        self.ojgr.write(ontol, **args)

        # call og2dot
        cmdtoks = ['og2dot.js']
        if query_ids is not None:
            for q in query_ids:
                cmdtoks.append('-H')
                cmdtoks.append(q)
        cmdtoks.append('-t')
        cmdtoks.append(self.image_format)
        if container_predicates is not None and len(container_predicates)>0:
            for p in container_predicates:
                cmdtoks.append('-c')
                cmdtoks.append(p)
        if self.outfile is not None:
            cmdtoks.append('-o')
            cmdtoks.append(self.outfile)
        cmdtoks.append(fn)
        cp = subprocess.run(cmdtoks, check=True)
        logging.info(cp)
        os.remove(fn)
        
    def write(self, ontol, **args):
        self.render(ontol, **args)
            

class SimpleListGraphRenderer(GraphRenderer):
    """
    renders a graph as a simple flat list of nodes
    """
    def __init__(self, **args):
        super().__init__(**args)

    def render(self, ontol, **args):
        g = ontol.get_graph() # TODO - use ontol methods directly
        s = ""
        for n in ontol.nodes():
            s += self.render_noderef(ontol, n, **args) + "\n"
            for n2 in ontol.parents(n):
                for _,ea in g[n2][n].items():
                    s += '  {} {}'.format(str(ea['pred']), self.render_noderef(ontol, n2, **args))
                    s += "\n"
        return s
        
class AsciiTreeGraphRenderer(GraphRenderer):
    """
    Denormalized indented-text tree rendering
    """
    def __init__(self, **args):
        super().__init__(**args)
        
    def render(self, ontol, **args):
        #g = ontol.get_graph()
        #ts = nx.topological_sort(g)
        #roots = [n for n in ts if len(g.predecessors(n))==0]
        roots = ontol.get_roots()
        logging.info("Drawing ascii tree, using roots: {}".format(roots))
        if len(roots) == 0:
            logging.error("No roots in {}".format(ontol))
        s=""
        for n in roots:
            s += self._show_tree_node(None, n, ontol, 0, path=[], **args) + "\n"
        return s

    def _show_tree_node(self, rel, n, ontol, depth=0, path=[], **args):
        g = ontol.get_graph() # TODO - use ontol methods directly
        s = " " * depth + self.render_relation(rel) + " " +self.render_noderef(ontol, n, **args)
        if n in path:
            logging.warn("CYCLE: {} already visited in {}".format(n, path))
            return s + " <-- CYCLE\n"
        s += "\n"
        for c in ontol.children(n):
            preds = []
            for _,ea in g[n][c].items():
                preds.append(ea['pred'])
            s+= self._show_tree_node(",".join(preds), c, ontol, depth+1, path+[n], **args)
        return s

class OboFormatGraphRenderer(GraphRenderer):
    """
    Render as obo format
    """
    def __init__(self, **args):
        super().__init__(**args)
        
    def render(self, ontol, **args):
        g = ontol.get_graph() # TODO - use ontol methods directly
        ts = nx.topological_sort(g)
        s = "ontology: auto\n\n"
        for n in ts:
            s += self.render_noderef(self, n, ontol, **args)
        return s

    def render(self, ontol, **args):
        g = ontol.get_graph() # TODO - use ontol methods directly
        ts = nx.topological_sort(g)
        s = "ontology: auto\n\n"
        for n in ts:
            s += self.render_node(n, ontol, **args)
        return s
    
    def render_node(self, nid, ontol, **args):
        g = ontol.get_graph() # TODO - use ontol methods directly
        n = g.node[nid]
        s = "[Term]\n";
        s += self.tag('id', nid)
        s += self.tag('name', n['label'])
        for p in g.predecessors(nid):
            for _,ea in g[p][nid].items():
                pred = ea['pred']
                if p in g and 'label' in g.node[p]:
                    p = '{} ! {}'.format(p, g.node[p]['label'])
                if pred == 'subClassOf':
                    s += self.tag('is_a', p)
                else:
                    s += self.tag('relationship', pred, p)
        for ld in ontol.logical_definitions(nid):
            for gen in ld.genus_ids:
                s += self.tag('intersection_of', gen)
            for pred,filler in ld.restrictions:
                s += self.tag('intersection_of', pred, filler)
                
        s += "\n"
        return s

    # TODO
    def render_xrefs(self, nid, ontol, **args):
        g = ontol.xref_graph # TODO - use ontol methods directly
        n = g.node[nid]
        s = "[Term]\n";
        s += self.tag('id ! TODO', nid)
        s += self.tag('name', n['label'])
        for p in g.predecessors(nid):
            for _,ea in g[p][nid].items():
                pred = ea['pred']
                if p in g and 'label' in g.node[p]:
                    p = '{} ! {}'.format(p, g.node[p]['label'])
                if pred == 'subClassOf':
                    s += self.tag('is_a', p)
                else:
                    s += self.tag('relationship', pred, p)
        s += "\n"
        return s
    
    def tag(self, t, *vs):
        v = " ".join(vs)
        return t + ': ' + v + "\n"
    
class OboJsonGraphRenderer(GraphRenderer):
    """
    Render as obographs json
    """
    def __init__(self, **args):
        super().__init__(**args)
        
    def to_json(self, ontol, **args):
        g = ontol.get_graph() # TODO - use ontol methods directly
        obj = {}
        node_objs = []
        for n in ontol.nodes():
            node_objs.append(self.node_to_json(n, ontol, **args))
        obj['nodes'] = node_objs
        edge_objs = []
        for e in g.edges_iter(data=True):
            edge_objs.append(self.edge_to_json(e, ontol, **args))
        obj['edges'] = edge_objs
        return {'graphs' : [obj]}

    def render(self, ontol, **args):
        obj = self.to_json(ontol, **args)
        return json.dumps(obj)
    
    def node_to_json(self, nid, ontol, **args):
        label = ontol.label(nid)
        return {'id' : nid,
                'lbl' : label}
    
    def edge_to_json(self, e, ontol, **args):
        (obj,sub,meta) = e
        return {'sub' : sub,
                'obj' : obj,
                'pred' : meta['pred']}

    def tag(self, t, *vs):
        v = " ".join(vs)
        return t + ': ' + v + "\n"
    
