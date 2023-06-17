from __future__ import annotations

import dis
import logging
import types


def format_bytecode(prefix, name, filename, line_no, code):
    return f"{prefix} {name} {filename} line {line_no} \n{dis.Bytecode(code).dis()}\n"


def log_bytecode(prefix, name, filename, line_no, code):
    logging.debug(format_bytecode(prefix, name, filename, line_no, code))


def log_code(code: types.CodeType, prefix=''):
    log_bytecode(prefix, code.co_name, code.co_filename, code.co_firstlineno, code)


def get_instructions(code: types.CodeType):
    return list(dis.get_instructions(code))
