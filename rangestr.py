#!/usr/bin/env python3
# -*- elpy-shell-use-project-root: nil; -*-

"""数値の範囲を表す文字列を解釈し，リストに変換する．

文字列は，印刷時のページ範囲指定などで一般に使われる記法に従う:

- カンマ区切りで数値もしくは連続した数値範囲を指定する (数値は自然数)．
- 数値範囲は下限値と上限値をハイフンで繋ぐことにより指定する (3-7 など)．
- 下限値または上限値は省略可能であり，省略時にはそれぞれ begin および
  end が用いられる．たとえば begin=3 のとき '-5' は '3-5' と等価であり，
  同様に end=10 のとき '5-' は '5-10' と等価である．
"""

import re
from itertools import chain


def to_ranges(s, begin, end):
    """数値範囲を表す文字列を，range オブジェクトのリストに変換する．"""
    return [_match2range(i, begin=begin, end=end) for i in s.split(",")]


def to_numbers(s, begin, end):
    """数値範囲を表す文字列を，重複を除去して昇順の数値リストに変換する．"""
    return sorted(set(chain(*to_ranges(s, begin=begin, end=end))))


def _match2range(m, begin, end):
    ranged = re.fullmatch(r"\s*(\d*)-(\d*)\s*", m)
    single = re.fullmatch(r"\s*(\d*)\s*", m)
    if ranged:
        b = int(ranged.group(1)) if ranged.group(1) else begin
        e = int(ranged.group(2)) if ranged.group(2) else end
        return range(b, e+1)
    elif single:
        return range(int(single.group(1)), int(single.group(1))+1)
    else:
        raise ValueError(f"Cannot recognize: '{m}'.")
