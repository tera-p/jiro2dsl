#!/usr/bin/env python3
# -*- elpy-shell-use-project-root: nil; -*-

"""数値範囲を表す文字列を，対応する数値(範囲)のリストに変換する (Lark 版)．

文字列は，印刷時のページ範囲指定などで一般に使われる記法に従う．カンマ
区切りで数値もしくは数値の範囲を指定し，範囲は下限値と上限値をハイフン
で繋いで表す (3-7 など)．下限値または上限値は省略可能であり，省略時に
はそれぞれ begin および end の値が用いられる．例えば -5 は begin から
5 まで，5- は 5 から end までを指定したことになる．
"""

from lark import Lark, Transformer
from itertools import chain


def to_ranges(s, begin=1, end=1):
    """数値範囲を表す文字列を，range オブジェクトのリストに変換する．"""
    return Lark(RangeList.rule, parser="lalr",
                transformer=RangeList(begin=begin, end=end)).parse(s)


def to_numbers(s, begin=1, end=1):
    """数値範囲を表す文字列を，重複を除去して昇順の数値リストに変換する．"""
    return sorted(set(chain(to_ranges(s, begin=begin, end=end))))


class RangeList(Transformer):
    rule = r"""
    start: [token ("," token)*]
    token: INT "-" INT
         | INT "-"     -> open_end
         | "-" INT     -> open_start
         | INT         -> single
    %import common.INT
    %import common.WS
    %ignore WS
    """

    def __init__(self, begin, end):  # ignores open-end by default.
        self.begin, self.end = begin, end

    def start(self, args):
        return args

    def token(self, args):
        return range(int(args[0]), int(args[1]) + 1)

    def open_end(self, args):
        return self.token((args[0], self.end))

    def open_start(self, args):
        return self.token((self.begin, args[0]))

    def single(self, args):
        return self.token((args[0], args[0]))
