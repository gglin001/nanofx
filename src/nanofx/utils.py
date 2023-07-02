from __future__ import annotations

import dis
import logging
import types

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bytecode_transformation import Instruction


def format_bytecode(prefix, name, filename, line_no, code):
    return f"{prefix} {name} {filename} line {line_no} \n{dis.Bytecode(code).dis()}\n"


def log_bytecode(prefix, name, filename, line_no, code):
    logging.debug(format_bytecode(prefix, name, filename, line_no, code))


def log_code(code: types.CodeType, prefix=''):
    log_bytecode(prefix, code.co_name, code.co_filename, code.co_firstlineno, code)


def log_instructions(
    instructions: list[dis.Instruction] | list[Instruction], prefix=''
):
    def format_instruction(inst: dis.Instruction | Instruction):
        if inst.arg is None:
            return f"{'': <15} {inst.opname: <25} {'': <2} ({inst.argval})"
        else:
            return f"{'': <15} {inst.opname: <25} {inst.arg: <2} ({inst.argval})"

    logging.debug(f"{prefix}")
    for inst in instructions:
        logging.debug(format_instruction(inst))


def get_instructions(code: types.CodeType):
    return list(dis.get_instructions(code))
