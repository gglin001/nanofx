from __future__ import annotations

import dataclasses
import dis
import sys

from typing import Any


@dataclasses.dataclass
class Instruction:
    """A mutable version of dis.Instruction."""

    opcode: int
    opname: str
    arg: int | None
    argval: Any
    # argrepr: str
    offset: int | None = None
    starts_line: int | None = None
    is_jump_target: bool = False

    # extra fields to make modification easier:
    target: Instruction | None = None
    exn_tab_entry = None

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)


def convert_instruction(i: dis.Instruction):
    return Instruction(
        i.opcode,
        i.opname,
        i.arg,
        i.argval,
        i.offset,
        i.starts_line,
        i.is_jump_target,
    )


class _NotProvided:
    def __repr__(self):
        return "_NotProvided"


def create_instruction(name, *, arg=None, argval=_NotProvided, target=None):
    return Instruction(
        opcode=dis.opmap[name], opname=name, arg=arg, argval=argval, target=target
    )


def create_jump_absolute(target):
    inst = "JUMP_FORWARD" if sys.version_info >= (3, 11) else "JUMP_ABSOLUTE"
    return create_instruction(inst, target=target)


def create_load_global(name, push_null):
    return Instruction(
        opcode=dis.opmap["LOAD_GLOBAL"],
        opname="LOAD_GLOBAL",
        arg=push_null,
        argval=name,
    )
