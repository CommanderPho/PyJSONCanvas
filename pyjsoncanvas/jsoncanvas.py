# jsoncanvas.py
from copy import deepcopy
from typing import Dict, List, Tuple, Set, Optional, Callable, Union, Any
from dataclasses import dataclass
from .models import (
    Edge,
    NodeType,
    GenericNode,
    TextNode,
    FileNode,
    LinkNode,
    GroupNode,
)
from typing import List, Dict, Any, Optional, Tuple
from .exceptions import (
    InvalidNodeTypeError,
    InvalidEdgeAttributeError,
    OrphanEdgeError,
    CanvasValidationError,
    NodeIDConflictError,
    EdgeIDConflictError,
    NodeNotFoundError,
    EdgeNotFoundError,
    InvalidJsonError,
)
from json import dumps, loads, JSONDecodeError
from .encoder import CustomEncoder

from .validate import validate_node, validate_edge


@dataclass
class Canvas:
    nodes: List[GenericNode]
    edges: List[Edge]

    def to_json(self) -> str:
        return dumps(
            {
                "nodes": [node.to_dict() for node in self.nodes],
                "edges": [edge.to_dict() for edge in self.edges],
            },
            cls=CustomEncoder,
        )

    @staticmethod
    def from_json(json_str: str) -> "Canvas":
        try:
            canvas_dict = loads(json_str)
            nodes = []
            edges = []
            for node in canvas_dict["nodes"]:
                # if node.type == NodeType.TEXT:
                if node["type"] == NodeType.TEXT.value:
                    nodes.append(TextNode(**node))
                # elif node.type == NodeType.FILE:
                elif node["type"] == NodeType.FILE.value:
                    nodes.append(FileNode(**node))
                # elif node.type == NodeType.LINK:
                elif node["type"] == NodeType.LINK.value:
                    nodes.append(LinkNode(**node))
                # elif node.type == NodeType.GROUP:
                elif node["type"] == NodeType.GROUP.value:
                    nodes.append(GroupNode(**node))
                else:
                    raise InvalidNodeTypeError(
                        f"Invalid or unsupported node type.The node {node['id']} has an invalid or unsupported type {node['type']}."
                    )
            for edge in canvas_dict["edges"]:
                edges.append(Edge(**edge))
            return Canvas(nodes=nodes, edges=edges)
        except JSONDecodeError as e:
            raise InvalidJsonError("Invalid or malformed JSON.") from e

    def export(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            f.write(self.to_json())

    def validate(self) -> bool:
        try:
            if not all(
                isinstance(node, (TextNode, FileNode, LinkNode, GroupNode))
                and validate_node(node)
                for node in self.nodes
            ):
                raise InvalidNodeTypeError("Invalid or unsupported node type found.")
            if not all(isinstance(edge, Edge) for edge in self.edges):
                raise InvalidEdgeAttributeError(
                    "Invalid or missing edge attribute found."
                )
            for edge in self.edges:
                validate_edge(edge)
                if edge.fromNode not in [
                    node.id for node in self.nodes
                ] or edge.toNode not in [node.id for node in self.nodes]:
                    raise OrphanEdgeError("Edge is orphan.")
            return True
        except (InvalidNodeTypeError, InvalidEdgeAttributeError, OrphanEdgeError) as e:
            raise CanvasValidationError("Canvas validation failed.") from e

    def get_node(self, node_id: str) -> GenericNode:
        for node in self.nodes:
            if node.id == node_id:
                return node
        else:
            raise NodeNotFoundError("Node with id does not exist")

    def get_edge(self, edge_id: str) -> GenericNode:
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        else:
            raise EdgeNotFoundError("Edge with id does not exist")

    def add_node(self, node: GenericNode) -> None:
        validate_node(node)
        if node.id in [n.id for n in self.nodes]:
            raise NodeIDConflictError("Node with id already exists")
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        validate_edge(edge)
        if edge.id in [e.id for e in self.edges]:
            raise EdgeIDConflictError("Edge with id already exists")
        self.edges.append(edge)

    def remove_node(self, node_id: str) -> bool:
        node_exists = False
        nodes = self.nodes
        self.nodes = [node for node in self.nodes if node.id != node_id]
        if len(self.nodes) != len(nodes):
            node_exists = True
        self.edges = [
            edge
            for edge in self.edges
            if edge.fromNode != node_id and edge.toNode != node_id
        ]
        if not node_exists:
            raise NodeNotFoundError(f"Node with id {node_id} does not exist.")
        return node_exists

    def remove_edge(self, edge_id: str) -> None:
        edge_exists = False
        edges = self.edges
        self.edges = [edge for edge in self.edges if edge.id != edge_id]
        if len(self.edges) != len(edges):
            edge_exists = True
        if not edge_exists:
            raise EdgeNotFoundError(f"Edge with id {edge_id} does not exist.")

    def get_connections(self, node_id: str) -> List[Edge]:
        return [
            edge
            for edge in self.edges
            if edge.fromNode == node_id or edge.toNode == node_id
        ]

    def get_edge_nodes(self, edge_id: str) -> Tuple[GenericNode, GenericNode]:
        edge = self.get_edge(edge_id)
        return [self.get_node(edge.fromNode), self.get_node(edge.toNode)]

    def get_adjacent_nodes(self, node_id: str) -> List[GenericNode]:
        return [
            self.get_node(edge.fromNode)
            for edge in self.edges
            if edge.toNode == node_id
        ] + [
            self.get_node(edge.toNode)
            for edge in self.edges
            if edge.fromNode == node_id
        ]


    @classmethod
    def find_group_node_with_label(cls, loaded_group_nodes: List[GroupNode], search_group_node_label: str) -> Optional[GroupNode]:
        """ finds and returns the group node with the specified label
        """
        found_group_node = None
        for a_group_node in loaded_group_nodes:
            if found_group_node is None: ## not yet found
                if (a_group_node.label == search_group_node_label):
                    ## found match
                    found_group_node = deepcopy(a_group_node)


        return found_group_node


    @classmethod
    def recurrsively_find_nested_groups(cls, a_group_node: GroupNode, remaining_canvas_nodes: Set[GenericNode]) -> Dict:
        if len(remaining_canvas_nodes) == 0:
            return {}
        else:
            _out_dict = {}
            found_children_nodes = a_group_node.find_children(remaining_canvas_nodes)
            ## find group nodes
            curr_found_subgroup_nodes: Set[GroupNode] = set([v for v in found_children_nodes if (v.type.value == NodeType.GROUP.value)])
            _out_dict.update({v:cls.recurrsively_find_nested_groups(a_group_node=v, remaining_canvas_nodes=found_children_nodes) for v in found_children_nodes if (v.type.value == NodeType.GROUP.value)})

            _out_dict[a_group_node] = found_group_children ## need to recurrsively search for group nodes and therefore children here
            return _out_dict
