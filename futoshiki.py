#!/usr/bin/env python3
"""futoshiki 不等式数独：生成谜题 + 回溯求解。

规则：n×n 棋盘，每行每列恰好填入 1..n（拉丁方），
相邻格之间的不等号（< > ^ v，尖端指向较小的一方）必须成立。
空白格为 0。

纯标准库：argparse / random / sys。
"""

import argparse
import random
import sys

EMPTY = 0


# ---------- 拉丁方 ----------

def latin_square(n, rng):
    """随机 n×n 拉丁方：循环方阵 + 打乱行/列/符号。"""
    base = list(range(1, n + 1))
    rows = [base[i:] + base[:i] for i in range(n)]
    rng.shuffle(rows)
    cols = list(zip(*rows))
    rng.shuffle(cols)
    grid = [list(r) for r in zip(*cols)]
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    return [[perm[v - 1] for v in row] for row in grid]


# ---------- 生成 ----------

def generate(n, rng, givens_ratio=0.35, sign_prob=0.35):
    """生成谜题。返回 (grid, h, v, solution)。

    h[r][c] in {'<','>'}: grid[r][c] 与 grid[r][c+1] 的关系；
    v[r][c] in {'v','^'}: grid[r][c] 与 grid[r+1][c] 的关系，
    'v' 表示上 < 下，'^' 表示上 > 下（尖端指向小的一方）。
    不等号全部从答案导出，保证谜题可解。
    """
    sol = latin_square(n, rng)
    h = [[None] * (n - 1) for _ in range(n)]
    v = [[None] * n for _ in range(n - 1)]
    for r in range(n):
        for c in range(n - 1):
            if rng.random() < sign_prob:
                h[r][c] = '<' if sol[r][c] < sol[r][c + 1] else '>'
    for r in range(n - 1):
        for c in range(n):
            if rng.random() < sign_prob:
                v[r][c] = 'v' if sol[r][c] < sol[r + 1][c] else '^'
    grid = [[EMPTY] * n for _ in range(n)]
    cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(cells)
    k = max(n, int(n * n * givens_ratio))
    for r, c in cells[:k]:
        grid[r][c] = sol[r][c]
    return grid, h, v, sol


# ---------- 求解 ----------

def _consistent(g, h, v, n, r, c, val):
    for cc in range(n):
        if cc != c and g[r][cc] == val:
            return False
    for rr in range(n):
        if rr != r and g[rr][c] == val:
            return False
    if c > 0 and h[r][c - 1]:
        o = g[r][c - 1]
        if o != EMPTY:
            if h[r][c - 1] == '<' and not o < val:
                return False
            if h[r][c - 1] == '>' and not o > val:
                return False
    if c < n - 1 and h[r][c]:
        o = g[r][c + 1]
        if o != EMPTY:
            if h[r][c] == '<' and not val < o:
                return False
            if h[r][c] == '>' and not val > o:
                return False
    if r > 0 and v[r - 1][c]:
        o = g[r - 1][c]
        if o != EMPTY:
            if v[r - 1][c] == 'v' and not o < val:
                return False
            if v[r - 1][c] == '^' and not o > val:
                return False
    if r < n - 1 and v[r][c]:
        o = g[r + 1][c]
        if o != EMPTY:
            if v[r][c] == 'v' and not val < o:
                return False
            if v[r][c] == '^' and not val > o:
                return False
    return True


def solve_all(grid, h, v, limit=2):
    """回溯求解，至多返回 limit 个解。"""
    n = len(grid)
    g = [row[:] for row in grid]
    cells = [(r, c) for r in range(n) for c in range(n) if g[r][c] == EMPTY]
    sols = []

    def bt(i):
        if len(sols) >= limit:
            return True
        if i == len(cells):
            sols.append([row[:] for row in g])
            return len(sols) >= limit
        r, c = cells[i]
        for val in range(1, n + 1):
            if _consistent(g, h, v, n, r, c, val):
                g[r][c] = val
                if bt(i + 1):
                    return True
                g[r][c] = EMPTY
        return False

    bt(0)
    return sols


def check_solution(grid, h, v, sol):
    """验证解：给定数一致、每行每列 1..n、不等号成立。返回 (ok, 原因)。"""
    n = len(grid)
    want = set(range(1, n + 1))
    for r in range(n):
        for c in range(n):
            if grid[r][c] != EMPTY and sol[r][c] != grid[r][c]:
                return False, f"给定数不一致 ({r + 1},{c + 1})"
    for r in range(n):
        if set(sol[r]) != want:
            return False, f"第 {r + 1} 行不是 1..{n}"
    for c in range(n):
        if {sol[r][c] for r in range(n)} != want:
            return False, f"第 {c + 1} 列不是 1..{n}"
    for r in range(n):
        for c in range(n - 1):
            if h[r][c] == '<' and not sol[r][c] < sol[r][c + 1]:
                return False, f"横向不等号违反 ({r + 1},{c + 1})"
            if h[r][c] == '>' and not sol[r][c] > sol[r][c + 1]:
                return False, f"横向不等号违反 ({r + 1},{c + 1})"
    for r in range(n - 1):
        for c in range(n):
            if v[r][c] == 'v' and not sol[r][c] < sol[r + 1][c]:
                return False, f"纵向不等号违反 ({r + 1},{c + 1})"
            if v[r][c] == '^' and not sol[r][c] > sol[r + 1][c]:
                return False, f"纵向不等号违反 ({r + 1},{c + 1})"
    return True, "合法"


# ---------- 文本格式 ----------

def save_puzzle(path, grid, h, v):
    n = len(grid)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{n}\n")
        for row in grid:
            f.write(" ".join(map(str, row)) + "\n")
        for row in h:
            f.write("".join(s if s else "." for s in row) + "\n")
        for row in v:
            f.write("".join(s if s else "." for s in row) + "\n")


def load_puzzle(path):
    with open(path, encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
    n = int(lines[0])
    grid = [list(map(int, lines[1 + r].split())) for r in range(n)]
    h = [[s if s != "." else None for s in lines[1 + n + r].strip()] for r in range(n)]
    v = [[s if s != "." else None for s in lines[1 + 2 * n + r].strip()]
         for r in range(n - 1)]
    return grid, h, v


# ---------- 渲染 ----------

def render(grid, h, v):
    n = len(grid)
    lines = []
    for r in range(n):
        parts = []
        for c in range(n):
            parts.append(str(grid[r][c]) if grid[r][c] else ".")
            if c < n - 1:
                s = h[r][c]
                parts.append(" < " if s == "<" else " > " if s == ">" else "   ")
        lines.append("".join(parts))
        if r < n - 1:
            parts = []
            for c in range(n):
                s = v[r][c]
                parts.append(" v " if s == "v" else " ^ " if s == "^" else "   ")
                if c < n - 1:
                    parts.append("   ")
            lines.append("".join(parts).rstrip())
    return "\n".join(lines)


# ---------- CLI ----------

def main(argv=None):
    ap = argparse.ArgumentParser(prog="futoshiki", description="不等式数独：生成与求解")
    ap.add_argument("--size", type=int, choices=[4, 5], default=5, help="棋盘大小")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--solution", action="store_true", help="同时打印答案")
    ap.add_argument("--save", metavar="FILE", default=None, help="保存谜题到文件")
    ap.add_argument("--load", metavar="FILE", default=None, help="从文件读谜题")
    ap.add_argument("--solve", action="store_true", help="求解（对生成或 --load 的谜题）")
    ap.add_argument("--count", action="store_true", help="统计解的个数（上限2，用于检查唯一性）")
    args = ap.parse_args(argv)

    if args.load:
        grid, h, v = load_puzzle(args.load)
        n = len(grid)
        print(f"从 {args.load} 读入 {n}x{n} 谜题：")
        print(render(grid, h, v))
        sols = solve_all(grid, h, v, limit=2 if args.count else 1)
        if args.count:
            print(f"\n解的个数（上限2）: {len(sols)}")
        if sols:
            print("\n答案：")
            print(render(sols[0], h, v))
        else:
            print("\n无解。")
        return 0

    rng = random.Random(args.seed)
    grid, h, v, sol = generate(args.size, rng)
    seed_info = f" (seed={args.seed})" if args.seed is not None else ""
    print(f"futoshiki {args.size}x{args.size}{seed_info}:")
    print(render(grid, h, v))
    if args.save:
        save_puzzle(args.save, grid, h, v)
        print(f"\n已保存到 {args.save}")
    if args.solution or args.solve:
        print("\n答案：")
        print(render(sol, h, v))
    if args.count:
        sols = solve_all(grid, h, v, limit=2)
        print(f"\n解的个数（上限2）: {len(sols)}（生成器不保证唯一解）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
