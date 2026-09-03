from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

IR_VERSION_DEFAULT = "0.1"


class IRParam(BaseModel):
    name: str
    type: str


class IRReturn(BaseModel):
    type: str


class IRLoopSignature(BaseModel):
    type: str
    init: Optional[str] = ""
    guard: Optional[str] = ""
    update: Optional[str] = ""
    body_summary: Optional[Dict[str, Any]] = None
    bounds: Optional[Dict[str, Any]] = None

    loop_id: Optional[str] = None
    loop_index: Optional[int] = None
    node_id: Optional[int] = None
    parent_node_id: Optional[int] = None
    category: Optional[str] = None
    depth: Optional[int] = None
    index_direction: Optional[str] = None

    src: Optional[str] = None
    body_src: Optional[str] = None
    init_src: Optional[str] = None
    body_is_block: Optional[bool] = None


class IRStorageTouch(BaseModel):
    var: str
    # Optional so plain variables can be represented without a key, e.g. {"var": "totalSupply"}
    key: Optional[str] = None
    # How the variable was written: assign, element, push, pop, or clear.
    kind: Optional[str] = None


class IRLengthEffect(BaseModel):
    """How one call changes the length of a state array."""

    var: str
    op: str
    count: str = "1"
    in_loop: bool = False
    loop_bound: str = ""
    conditional: bool = False
    element_source: Dict[str, Any] = Field(default_factory=dict)


class IRStorageAlias(BaseModel):
    """A local storage pointer and the state variable it refers to."""

    name: str
    base: str
    via: str = "direct"
    index: Optional[str] = None
    type: str = ""


class IRFunction(BaseModel):
    contract: str
    name: str
    visibility: str
    mutability: str
    modifiers: List[str] = Field(default_factory=list)
    params: List[IRParam] = Field(default_factory=list)
    returns: List[IRReturn] = Field(default_factory=list)  # NEW
    loops: List[IRLoopSignature] = Field(default_factory=list)
    requires: List[str] = Field(default_factory=list)

    # Effects (per paper expectations)
    reads: List[str] = Field(default_factory=list)
    writes: List[str] = Field(default_factory=list)
    member_accesses: List[str] = Field(default_factory=list)
    internal_calls: List[str] = Field(default_factory=list)
    external_calls: List[str] = Field(default_factory=list)
    events_emitted: List[str] = Field(default_factory=list)

    # Storage interactions with keys/indices
    storage_reads: List[IRStorageTouch] = Field(default_factory=list)
    storage_writes: List[IRStorageTouch] = Field(default_factory=list)

    # Length changes and local storage pointers, used to turn a counterexample
    # about data shape into calls that produce that shape.
    length_effects: List[IRLengthEffect] = Field(default_factory=list)
    storage_aliases: List[IRStorageAlias] = Field(default_factory=list)

    # Source spans for probe placement
    src: Optional[str] = None
    body_src: Optional[str] = None
    return_srcs: List[str] = Field(default_factory=list)

    # True when this entry is a synthesized/public getter
    synthetic: bool = False  # NEW


class IRStateVar(BaseModel):
    contract: str
    name: str
    type: str


class IRMapping(BaseModel):
    contract: str
    name: str
    key: str
    value: str


class IRStructField(BaseModel):
    name: str
    type: str


class IRStruct(BaseModel):
    """A struct definition, so its fields can be observed one at a time."""

    contract: str
    name: str
    fields: List[IRStructField] = Field(default_factory=list)


class IRState(BaseModel):
    variables: List[IRStateVar] = Field(default_factory=list)
    mappings: List[IRMapping] = Field(default_factory=list)
    structs: List[IRStruct] = Field(default_factory=list)


class IRAccessEdge(BaseModel):
    contract: str
    function: str
    modifier: str
    role: str


class IRAccessDependency(BaseModel):
    function: str
    source: str            # e.g., "modifier:onlyOwner" or "require"
    condition: str         # e.g., "msg.sender == owner"
    role: Optional[str] = None


class IRContract(BaseModel):
    name: str
    solidity_version: Optional[str] = None
    functions: List[IRFunction] = Field(default_factory=list)
    state: IRState = Field(default_factory=IRState)
    access_control: List[IRAccessEdge] = Field(default_factory=list)
    access_dependencies: List[IRAccessDependency] = Field(default_factory=list)  # derived edges for prank setup, etc.


class IRDoc(BaseModel):
    ir_version: str = IR_VERSION_DEFAULT
    contract: IRContract


def to_dict(model: BaseModel) -> Dict[str, Any]:
    return model.model_dump()
