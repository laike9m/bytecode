import textwrap
import types
import unittest

from bytecode import (UNSET, Label, Instr, ConcreteInstr,
                      Bytecode, BytecodeBlocks, ConcreteBytecode)


# FIXME: remove these functions
def LOAD_CONST(arg):
    return Instr('LOAD_CONST', arg, lineno=1)

def STORE_NAME(arg):
    return Instr('STORE_NAME', arg, lineno=1)

def NOP():
    return Instr('NOP', lineno=1)

def RETURN_VALUE():
    return Instr('RETURN_VALUE', lineno=1)


def _format_instr_list(block, labels):
    instr_list = []
    for instr in block:
        if not isinstance(instr, Label):
            if isinstance(instr, ConcreteInstr):
                cls_name = 'ConcreteInstr'
            else:
                cls_name = 'Instr'
            arg = instr.arg
            if arg is not UNSET:
                if isinstance(arg, Label):
                    arg = labels[arg]
                else:
                    arg = repr(arg)
                text = '%s(%r, %s, lineno=%s)' % (cls_name, instr.name, arg, instr.lineno)
            else:
                text = '%s(%r, lineno=%s)' % (cls_name, instr.name, instr.lineno)
        else:
            text = labels[instr]
        instr_list.append(text)
    return '[%s]'  % ',\n '.join(instr_list)

def dump_code(code):
    """
    Use this function to write unit tests: copy/paste its output to
    write a self.assertBlocksEqual() check.
    """
    print()

    if isinstance(code, (Bytecode, ConcreteBytecode)):
        is_concrete = isinstance(code, ConcreteBytecode)
        if is_concrete:
            block = list(code)
        else:
            block = code

        indent = ' ' * 8
        labels = {}
        for index, instr in enumerate(block):
            if isinstance(instr, Label):
                name = 'label_instr%s' % index
                labels[instr] = name


        if is_concrete:
            name = 'ConcreteBytecode'
        else:
            name = 'Bytecode'
        print(indent + 'code = %s()' % name)
        if code.argcount:
            print(indent + 'code.argcount = %s' % code.argcount)
        if code.kw_only_argcount:
            print(indent + 'code.argcount = %s' % code.kw_only_argcount)
        print(indent + 'code.flags = %#x' % code.flags)

        if is_concrete:
            if code.consts:
                print(indent + 'code.consts = %r' % code.consts)
            if code.names:
                print(indent + 'code.names = %r' % code.names)
            if code.varnames:
                print(indent + 'code.varnames = %r' % code.varnames)

        for name in sorted(labels.values()):
            print(indent + '%s = Label()' % name)

        text = indent + 'code.extend('
        indent = ' ' * len(text)

        lines = _format_instr_list(code, labels).splitlines()
        last_line = len(lines) - 1
        for index, line in enumerate(lines):
            if index == 0:
                print(text + lines[0])
            elif index == last_line:
                print(indent + line + ')')
            else:
                print(indent + line)

        print()
    else:
        labels = {}
        for block_index, block in enumerate(code):
            labels[block.label] = 'code[%s].label' % block_index

        for block_index, block in enumerate(code):
            text = _format_instr_list(block, labels)
            if block_index != len(code) - 1:
                text += ','
            print(text)
            print()

def get_code(source, *, filename="<string>", function=False):
    source = textwrap.dedent(source).strip()
    code = compile(source, filename, "exec")
    if function:
        sub_code = [const for const in code.co_consts
                    if isinstance(const, types.CodeType)]
        if len(sub_code) != 1:
            raise ValueError("unable to find function code")
        code = sub_code[0]
    return code

def disassemble(source, *, filename="<string>", function=False,
                remove_last_return_none=False):
    code = get_code(source, filename=filename, function=function)

    bytecode = BytecodeBlocks.from_code(code)
    if remove_last_return_none:
        # drop LOAD_CONST+RETURN_VALUE to only keep 2 instructions,
        # to make unit tests shorter
        block = bytecode[-1]
        test = (block[-2].name == "LOAD_CONST"
                and block[-2].arg is None
                and block[-1].name == "RETURN_VALUE")
        if not test:
            raise ValueError("unable to find implicit RETURN_VALUE <None>: %s"
                             % block[-2:])
        del block[-2:]
    return bytecode


class TestCase(unittest.TestCase):
    def assertBlocksEqual(self, code, *expected_blocks):
        blocks = [list(block) for block in code]
        self.assertEqual(len(blocks), len(expected_blocks))
        for block, expected_block in zip(blocks, expected_blocks):
            self.assertListEqual(block, list(expected_block))