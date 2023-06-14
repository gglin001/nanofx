from __future__ import annotations

import dis


def format_bytecode(prefix, name, filename, line_no, code):
    return f"{prefix} {name} {filename} line {line_no} \n{dis.Bytecode(code).dis()}\n"


def print_bytecode(prefix, name, filename, line_no, code):
    print(format_bytecode(prefix, name, filename, line_no, code))
