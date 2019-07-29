#!/usr/bin/env python3
# -*- elpy-shell-use-project-root: nil; -*-
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
from textwrap import dedent
from lark import Lark, Transformer
from rangestr import to_numbers


def main(argv):
    """英辞郎テキスト形式の辞書を Lingvo DSL 形式辞書に変換する．

    OUTFILE が省略された場合，infile の拡張子を ".dsl" に置換した名前
    が用いられる．出力エンコーディングは GoldenDict の仕様に合わせて
    *BOM 付き* UTF-8 (utf-8-sig) 固定とする．

    ENCODING には Python におけるエンコーディング名を与える．省略時は
    cp932 が用いられる．変換元辞書のエンコーディングが UTF-8 の場合，
    陽に utf-8 と指定すること．

    LINES は，印刷時のページ範囲指定などで一般に用いられる記法によって
    指定する．この記法は以下の規則に従う．

      - カンマ区切りで行番号 (先頭行は 1 とする) または行の範囲を指定
        する．出力は行番号の昇順にソートされ，重複は排除される．
      - 行の範囲は開始行と終了行をハイフンで結合して指定する．たとえば
        "3-7" は "3,4,5,6,7" と同じ意味である．
      - 開始行と終了行のいずれかは省略できる．それぞれ省略時には辞書の
        先頭行と末尾行を意味する．

    たとえば infile が 10 行のとき，"-2, 4-6, 9-" と "1-2, 4-6, 9-10"，
    および "1,2,4,5,6,9,10" はいずれも同じ意味として扱われる．

    """
    jiro2dsl(parse_args(argv))


def parse_args(argv):
    doc = main.__doc__.splitlines()
    description, epilog = doc[0], dedent('\n'.join(doc[2:]))

    parser = ArgumentParser(description=description, epilog=epilog,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("infile",
                        help="変換元の辞書名 (英辞郎テキスト形式)")
    parser.add_argument("-o", "--outfile",
                        help="変換先の辞書名 (既定: infile から自動生成)")
    parser.add_argument("-e", "--encoding", default="cp932",
                        help="変換元辞書のエンコーディング (既定: cp932)")
    parser.add_argument("-l", "--lines", default="1-",
                        help="変換対象行の範囲 (既定: 変換元辞書全体)")
    return parser.parse_args(argv)


def jiro2dsl(args):
    infile = Path(args.infile)
    outfile = Path(args.outfile or infile.stem + ".dsl")

    header = dedent(f"""\
             #NAME "英辞郎 ({infile.stem})"
             #INDEX_LANGUAGE "English"
             #CONTENTS_LANGUAGE "Japanese"
             """)

    formatter = Jiro2DSL()
    parser = Lark(formatter.rule, parser="lalr", start="article")

    print(f"Reading {infile}... ")
    with open(infile, encoding=args.encoding) as f:
        dictionary = f.readlines()
    print(f"{len(dictionary)} entries found.")

    target = to_numbers(args.lines, begin=1, end=len(dictionary))
    print(f"Procesing entry {args.lines} ({len(target)} entries)...")
    result = [transform(dictionary[i-1], parser, formatter) for i in target]

    print(f"Writing {outfile}... ")
    with open(outfile, "w", encoding="utf-8-sig") as f:
        f.write(header)
        f.writelines(result)
    print("Done.")


class Jiro2DSL(Transformer):
    rule = r"""
    // EBNF rules for parsing Jiro-formatted text dictionary with Lark.

    start: article+
    article: "■" key content example* " "* "\n"

    key: KEYWORD
    content: head? " : " body

    head: pos
    body: tags | translation? comment*

    pos: ("{" | "  {" | "  {{") WORD "}"+  // workaround for "amygdalo-"

    tags: tag (" "* "、"? tag)*
    tag: tagname " "? [desc pos? comment?]

    tagname: "【"+ WORD "】"+  // workaround for "cerium"

    translation: (desc | ref) ("、"? term)* "、"? " "?

    comment: "◆" " "? term ("、"? term)*
    example: "■・" desc comment*

    term: desc | ref | tag | pos
    desc: DESCRIPTION
    ref: "<→" " "* KEYWORD " "* ">"

    DESCRIPTION: WORD (/[、 ]+/ WORD)*
    KEYWORD: PLAIN+ (":" PLAIN* | " "+ PLAIN+)*
    WORD: /<[^→]/? (PLAIN | ":")+ ">"?  // hacks for "<deletia>", "<3"
    PLAIN: /[^:<>{}◆■【】、 \n]/
    """
    _m1 = (" [m1]", "[/m]\n")
    _m2 = ("  [m2]", "[/m]\n")
    tagconf = {'content': [_m1],
               'head': [("", ") ")],
               'pos': ["b", "c"],
               'body': ["trn"],
               'tagname': ["b", (" [c brown]", "[/c] ")],
               'example': [_m2, "ex"],
               # 'comment': [(" [com]◆", "[/com]")],
               'comment': ["com", (" [c gray]◆", "[/c]")],
               'ref': [(" <<", ">>")], }

    def __init__(self):
        self.lastword = ""
        self.count = 0

    def __default__(self, data, children, meta):
        return self._entag("".join(children), self.tagconf.get(data, []))

    def _entag(self, content, tags):
        if not tags:
            return content
        if type(tags[0]) is tuple:
            left, right = tags[0]
        else:
            left, right = f"[{tags[0]}]", f"[/{tags[0]}]"
        return f"{left}{self._entag(content, tags[1:])}{right}"

    def article(self, args):
        self.count += 1
        if self.count % 10000 == 0:
            print(f"Processed {self.count} words (now: {self.lastword}).")
        return "".join(args)

    def key(self, args):
        if args[0] == self.lastword:
            return ""
        else:
            self.lastword = args[0]
            return args[0] + "\n"


def transform(entry, parser, formatter):
    try:
        result = formatter.transform(parser.parse(entry))
    except Exception as e:
        raise ValueError("Cannot parse: " + entry) from e
    return result


test_arg = "-e utf-8 -l -10000 EIJIRO-1445-utf8.txt"
argv = sys.argv[1:] if sys.argv[0] else test_arg.split()

main(argv)
