from __future__ import annotations

import dataclasses
import dis

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

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)


def create_instruction(name, *, arg=None, argval=None, target=None):
    return Instruction(
        opcode=dis.opmap[name], opname=name, arg=arg, argval=argval, target=target
    )
