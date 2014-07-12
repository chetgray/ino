# -*- coding: utf-8; -*-

import sys
import re

from ino.commands.base import Command
from ino.exc import Abort


class Preprocess(Command):
    """
    Preprocess an .ino or .pde sketch file and produce ready-to-compile .cpp source.

    Ino mimics steps that are performed by official Arduino Software to
    produce similar result:

        * Either #include <Arduino.h> or <WProgram.h> is prepended
        * Function prototypes are added at the beginning of file
    """

    name = 'preproc'
    help_line = "Transform a sketch file into valid C++ source"

    def setup_arg_parser(self, parser):
        super(Preprocess, self).setup_arg_parser(parser)
        self.e.add_arduino_dist_arg(parser)
        parser.add_argument('sketch', help='Input sketch file name')
        parser.add_argument('-o', '--output', default='-', help='Output source file name (default: use stdout)')

    def run(self, args):
        if args.output == '-':
            out = sys.stdout
        else:
            out = open(args.output, 'wt')

        sketch = open(args.sketch, 'rt').read()
        prototypes = self.prototypes(sketch)

        out.write('#line 1 "%s"\n' % args.sketch)

        prototype_insertion_point = self.first_statement(sketch)
        out.write(sketch[:prototype_insertion_point])

        header = 'Arduino.h' if self.e.arduino_lib_version.major else 'WProgram.h'
        out.write('#include <%s>\n' % header)

        out.write('\n'.join(prototypes))
        out.write('\n')

        lines = sketch[:prototype_insertion_point].split('\n')
        out.write('#line %d\n' % len(lines))
        out.write(sketch[prototype_insertion_point:])

    def prototypes(self, src):
        src = self.collapse_braces(self.strip(src))
        regex = re.compile("[\\w\\[\\]\\*]+\\s+[&\\[\\]\\*\\w\\s]+\\([&,\\[\\]\\*\\w\\s]*\\)(?=\\s*\\{)")
        matches = regex.findall(src)
        return [m + ';' for m in matches]

    def first_statement(self, src):
        """
        Return the index of the first character that's not whitespace,
        a comment or a pre-processor directive.

        Adapted from PdePreprocessor.java, part of the Wiring project
        Copyright (c) 2004-05 Hernando Barragan
        """
        # whitespace
        p = "\\s+"

        # multi-line and single-line comment
        p += "|(/\\*[^*]*(?:\\*(?!/)[^*]*)*\\*/)|(//.*?$)"

        # pre-processor directive
        p += "|(#(?:\\\\\\n|.)*)"

        regex = re.compile(p, re.MULTILINE)
        i = 0
        for match in regex.finditer(src):
            if match.start() != i:
		break
            i = match.end()

        return i

    def collapse_braces(self, src):
        """
        Remove the contents of all top-level curly brace pairs {}.
        """
        result = []
        nesting = 0;

        for c in src:
            if not nesting:
                result.append(c)
            if c == '{':
                nesting += 1
            elif c == '}':
                nesting -= 1
                result.append(c)
        
        return ''.join(result)

    def strip(self, src):
        """
        Strips comments, pre-processor directives, single- and double-quoted
        strings from a string.
        """
        # single-quoted character
        p = "('.')"
        
        # double-quoted string
        p += "|(\"(?:[^\"\\\\]|\\\\.)*\")"
        
        # single and multi-line comment
        p += "|(//.*?$)|(/\\*[^*]*(?:\\*(?!/)[^*]*)*\\*/)"
        
        # pre-processor directive
        p += "|" + "(^\\s*#.*?$)"

        regex = re.compile(p, re.MULTILINE)
        return regex.sub(' ', src)
