# models.py
import sys
from dataclasses import field
from typing import Any, Dict, List, Set, Tuple, Optional, Union

# Check Python version
PY_310_OR_HIGHER = sys.version_info >= (3, 10)

# Use conditional dataclass decorator based on Python version
if PY_310_OR_HIGHER:
    def version_compatible_dataclass(*args, **kwargs):
        from dataclasses import dataclass
        return dataclass(*args, **kwargs)
else:
    def version_compatible_dataclass(*args, **kwargs):
        """Emulate kw_only behavior for Python < 3.10"""
        from dataclasses import dataclass, _MISSING_TYPE
        
        # Store if kw_only was requested
        kw_only_requested = kwargs.pop('kw_only', False)
        
        # Define a class decorator that will process the class
        def wrap(cls):
            # Apply standard dataclass decorator first
            dc_cls = dataclass(**kwargs)(cls)
            
            # If kw_only was requested, we need to modify the __init__ method
            if kw_only_requested or True: ## always allow extra fields
                # Get the original __init__ method
                orig_init = dc_cls.__init__
                
                # Get the field names from the dataclass
                field_names = set(f.name for f in dc_cls.__dataclass_fields__.values())
                
                # Create a new __init__ that emulates keyword-only arguments
                # and ignores extra keywords
                def __init__(self, **kwargs):
                    # Filter out kwargs that aren't fields in the dataclass
                    filtered_kwargs = {k: v for k, v in kwargs.items() if k in field_names}
                    # Call the original __init__ with filtered keyword arguments
                    orig_init(self, **filtered_kwargs)
                
                # Replace the __init__ method
                dc_cls.__init__ = __init__
                
                # Add a marker to indicate this class uses kw_only
                setattr(dc_cls, '_kw_only', True)
            
            return dc_cls
        
        # If called with a class, apply the decorator directly
        if args and isinstance(args[0], type):
            return wrap(args[0])
        
        # Otherwise, return the decorator
        return wrap
    

from enum import Enum
from .exceptions import InvalidColorValueError
import uuid

from . import validate_node, validate_edge


class ColorPreset(Enum):
    RED = 1
    ORANGE = 2
    YELLOW = 3
    GREEN = 4
    CYAN = 5
    PURPLE = 6


class PresetOrHex(Enum):
    PRESET = 1
    HEX = 2


def validate_hex_code(hexcode):
    return len(hexcode) == 6 and all(
        c.isdigit() or c.lower() in "abcdef" for c in hexcode
    )


class Color:
    def __init__(self, color: str):
        if color.startswith("#"):
            if not validate_hex_code(color[1:]):
                raise InvalidColorValueError("Invalid hex code.")
        # check if the color is one of the integer values of the ColorPreset enum
        elif color.isdigit():
            if int(color) not in [color.value for color in ColorPreset]:
                raise InvalidColorValueError("Invalid color preset.")
        else:
            raise InvalidColorValueError("Invalid color value.")
        self.color = color
        self.preset_or_hex = PresetOrHex.PRESET if color.isdigit() else PresetOrHex.HEX


class NodeType(Enum):
    TEXT = "text"
    FILE = "file"
    LINK = "link"
    GROUP = "group"


class EdgesFromSideValue(Enum):
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"


class EdgesFromEndValue(Enum):
    NONE = "none"
    ARROW = "arrow"


class EdgesToSideValue(Enum):
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"


class EdgesToEndValue(Enum):
    NONE = "none"
    ARROW = "arrow"


class GroupNodeBackgroundStyle(Enum):
    COVER = "cover"
    RATIO = "ratio"
    REPEAT = "repeat"


@version_compatible_dataclass
class Edge:
    fromNode: str
    toNode: str
    fromSide: EdgesFromSideValue = None
    fromEnd: EdgesFromEndValue = None
    toSide: EdgesToSideValue = None
    toEnd: EdgesToEndValue = None
    color: Color = None
    label: str = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def __post_init__(self):
        if isinstance(self.fromSide, str):
            self.fromSide = EdgesFromSideValue(self.fromSide)
        if isinstance(self.fromEnd, str):
            self.fromEnd = EdgesFromEndValue(self.fromEnd)
        if isinstance(self.toSide, str):
            self.toSide = EdgesToSideValue(self.toSide)
        if isinstance(self.toEnd, str):
            self.toEnd = EdgesToEndValue(self.toEnd)
        if isinstance(self.color, str):
            self.color = Color(self.color)
        validate_edge(self)

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return self.id == other.id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fromNode": self.fromNode,
            "fromSide": self.fromSide,
            "fromEnd": self.fromEnd,
            "toNode": self.toNode,
            "toSide": self.toSide,
            "toEnd": self.toEnd,
            "color": self.color,
            "label": self.label,
        }


@version_compatible_dataclass
class GenericNode:
    type: NodeType = field()
    x: int = field(default=0)
    y: int = field(default=0)
    width: int = field(default=400)
    height: int = field(default=100)
    color: Color = field(default=None)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    
    @property
    def x1(self) -> int:
        """The right x-position of the node."""
        return self.x + self.width

    @property
    def y1(self) -> int:
        """The bottom y-position of the node."""
        return self.y + self.height


    def __post_init__(self):
        if isinstance(self.color, str):
            self.color = Color(self.color)

    def __eq__(self, other):
        if not isinstance(other, GenericNode):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def to_dict(self, include_computed:bool=False) -> Dict[str, Any]:
        if not include_computed:
            return {
                "type": self.type,
                "id": self.id,
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
                "color": self.color,
            }
        else:
            return {
                "type": self.type,
                "id": self.id,
                "x": self.x,
                "y": self.y,
                "x1": self.x1,
                "y1": self.y1,
                "width": self.width,
                "height": self.height,
                "color": self.color,
            }



@version_compatible_dataclass(kw_only=True)
class TextNode(GenericNode):
    text: str = field(default="", init=True)
    type: NodeType = field(default=NodeType.TEXT)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.type, str):
            self.type = NodeType("text")
        validate_node(self)

    def __hash__(self):
        return hash(self.id)
    
    def to_dict(self, include_computed:bool=False) -> Dict[str, Any]:
        return super().to_dict(include_computed=include_computed) | {"text": self.text}


@version_compatible_dataclass(kw_only=True)
class FileNode(GenericNode):
    file: str = field(default='')
    type: NodeType = field(default=NodeType.FILE)
    subpath: str = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.type, str):
            self.type = NodeType("file")
        validate_node(self)

    def __hash__(self):
        return hash(self.id)
    
    def to_dict(self, include_computed:bool=False) -> Dict[str, Any]:
        return super().to_dict(include_computed=include_computed) | {"file": self.file, "subpath": self.subpath}


@version_compatible_dataclass(kw_only=True)
class LinkNode(GenericNode):
    url: str = field(default='')
    type: NodeType = field(default=NodeType.LINK)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.type, str):
            self.type = NodeType("link")
        validate_node(self)

    def __hash__(self):
        return hash(self.id)
    
    def to_dict(self, include_computed:bool=False) -> Dict[str, Any]:
        return super().to_dict(include_computed=include_computed) | {"url": self.url}


@version_compatible_dataclass(kw_only=True)
class GroupNode(GenericNode):
    type: NodeType = field(default=NodeType.GROUP)
    label: str = field(default=None)
    background: str = field(default=None)
    backgroundStyle: GroupNodeBackgroundStyle = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.type, str):
            self.type = NodeType("group")
        if isinstance(self.backgroundStyle, str):
            self.backgroundStyle = GroupNodeBackgroundStyle(self.backgroundStyle)
        validate_node(self)

    def __hash__(self):
        return hash(self.id)
    
    def to_dict(self, include_computed:bool=False) -> Dict[str, Any]:
        return super().to_dict(include_computed=include_computed) | {
            "label": self.label,
            "background": self.background,
            "backgroundStyle": self.backgroundStyle,
        }


    def does_contain(self, putative_child_node: GenericNode) -> bool:
        """ returns True IFF the putative_child_node is completely contained within this GroupNode's bounds. 
        """
        if (self.id == putative_child_node.id):
            return False ## definitionally, a node will not contain itself
    
        if (putative_child_node.x < self.x):
            return False ## child's left edge is outside to the left
        elif (putative_child_node.x1 > self.x1):
            return False ## child's right edge is outside to the right
        elif (putative_child_node.y < self.y):
            return False ## child's bottom edge is outside below
        elif (putative_child_node.y1 > self.y1):
            return False ## child's top-edge is outside above
        else:
            return True
        

    def find_children(self, putative_child_nodes: List[GenericNode]) -> List[GenericNode]:
        """ for the list of potentially contained nodes, returns the filtered list of only those nodes completely contained within this GroupNode's bounds (e.g. children). 
        """
        found_children_list = []
        for a_putative_child in putative_child_nodes:
            if self.does_contain(putative_child_node=a_putative_child):
                found_children_list.append(a_putative_child)
                
        return found_children_list


    # def find_children_recurrsively(self, putative_child_nodes: List[GenericNode]) -> List[Union[GenericNode, Dict[GroupNode, Dict[GroupNode, GenericNode]]]]:
    #     """ for the list of potentially contained nodes, returns the filtered list of only those nodes completely contained within this GroupNode's bounds (e.g. children). 
    #     """
    #     found_children_list = []
    #     for a_putative_child in putative_child_nodes:
    #         if self.does_contain(putative_child_node=a_putative_child):
    #             if a_putative_child.type.value == NodeType.GROUP.value:
    #                 # found_children_list.append(a_putative_child)
    #                 if a_putative_child.find_children_recurrsively(putative_child_nodes=putative_child_nodes)
    #                 found_children_list.append(a_putative_child)
    #             else:
    #                 ## non-group, just add the child:
    #                 found_children_list.append(a_putative_child)


    #     return found_children_list



