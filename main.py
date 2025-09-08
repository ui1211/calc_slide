import heapq
import random

import pyxel


class SlideCalc:
    def __init__(self, scale_input=2):
        pyxel.init(210, 270, title="Slide Calc", quit_key=pyxel.KEY_Q)

        # --- 効果音 ---
        pyxel.sound(0).set("c3", "p", "7", "n", 5)  # 数字など
        pyxel.sound(1).set("g2", "p", "7", "n", 8)  # 四則演算子
        pyxel.sound(2).set("c3e3g3c4 g3c4", "p", "7", "n", 8)  # ゴール時ファンファーレ  # --- ゴール状態 ---

        #
        self.goal = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", "D", " ", "+"],  # D=delete, C=clear(非表示)
        ]
        self.board = [row[:] for row in self.goal]
        ex, ey = self.find_empty()
        self.board[ey][ex] = "="
        # self.shuffle_board()

        # 入力・計算状態
        self.result = None
        self.current_operator = None
        self.current_number = ""
        self.history = []
        self.equal_revealed = True
        self.final_score = 0

        # ドラッグ状態
        self.dragging = False
        self.drag_tile = None
        self.drag_start = None
        self.drag_offset = (0, 0)
        self.drag_dir = None

        # デバッグソルバー
        self.zero_count = 0
        self.solver_path = []
        self.solver_index = 0
        self.solver_speed = 5
        self.solver_counter = 0

        # 表示設定
        self.scale_input = scale_input
        pyxel.run(self.update, self.draw)

    # ============================================================
    # ゲーム進行
    # ============================================================
    def start_new_game(self):
        self.result = None
        self.current_operator = None
        self.current_number = ""
        self.history = []
        self.equal_revealed = False
        self.final_score = None
        self.shuffle_board()

    # ============================================================
    # パズル関連
    # ============================================================
    def shuffle_board(self, steps=30, min_score=15):
        """正解からランダムにsteps回動かす → solvable確定。
        さらに元の位置から離す & 演算子分散を条件に。
        """
        while True:
            self.board = [row[:] for row in self.goal]
            ex, ey = self.find_empty()
            prev = None

            for i in range(steps):
                neighbors = self.get_neighbors(ex, ey)

                # --- 改善ポイント ---
                # 端タイルを優先的に動かすため、ランダム選択に重みをつける
                weighted_neighbors = []
                for nx, ny in neighbors:
                    tile = self.board[ny][nx]
                    weight = 1
                    if tile in "74":  # 固定化しやすいタイルを重み付け
                        weight = 3
                    weighted_neighbors.extend([(nx, ny)] * weight)

                # 直前の位置には戻りにくくする
                if prev and prev in weighted_neighbors and len(weighted_neighbors) > 1:
                    weighted_neighbors = [p for p in weighted_neighbors if p != prev]

                nx, ny = random.choice(weighted_neighbors)
                self.board[ey][ex], self.board[ny][nx] = self.board[ny][nx], self.board[ey][ex]
                prev = (ex, ey)
                ex, ey = nx, ny

            # --- 条件チェック ---
            if self.operators_are_scattered() and self.shuffle_score() >= min_score:
                break

    def shuffle_score(self):
        """現在の盤面が「元の配置からどれだけ離れているか」をスコア化"""
        score = 0
        ops = "+-*/"

        for y in range(4):
            for x in range(4):
                tile = self.board[y][x]
                if tile == " ":
                    continue
                # 元の位置を探す
                for gy in range(4):
                    for gx in range(4):
                        if self.goal[gy][gx] == tile:
                            dist = abs(x - gx) + abs(y - gy)
                            # 四則演算子は重み2倍
                            if tile in ops:
                                score += dist * 2
                            else:
                                score += dist
                            break
        return score

    def operators_are_scattered(self):
        """四則演算子が上下左右で隣接していないかを判定"""
        ops = "+-*/"
        for y in range(4):
            for x in range(4):
                if self.board[y][x] in ops:
                    for nx, ny in self.get_neighbors(x, y):
                        if self.board[ny][nx] in ops:
                            return False
        return True

    def find_empty(self):
        for y in range(4):
            for x in range(4):
                if self.board[y][x] == " ":
                    return x, y
        return None

    def get_neighbors(self, x, y):
        moves = []
        if x > 0:
            moves.append((x - 1, y))
        if x < 3:
            moves.append((x + 1, y))
        if y > 0:
            moves.append((x, y - 1))
        if y < 3:
            moves.append((x, y + 1))
        return moves

    # ============================================================
    # 自動ソルバー（デバッグ）
    # ============================================================
    def auto_solve(self):
        """A*探索で必ず正解に到達する手順を返す"""
        start = tuple(tuple(r) for r in self.board)
        goal = tuple(tuple(r) for r in self.goal)

        # --- ヒューリスティック関数（マンハッタン距離 + 線形衝突）---
        def heuristic(state):
            dist = 0
            for y in range(4):
                for x in range(4):
                    tile = state[y][x]
                    if tile == " ":
                        continue
                    # ゴール位置
                    for gy in range(4):
                        for gx in range(4):
                            if goal[gy][gx] == tile:
                                dist += abs(x - gx) + abs(y - gy)
                                # --- 線形衝突 (同じ行や列で順序が逆のとき追加ペナルティ) ---
                                if y == gy:
                                    for xx in range(x + 1, 4):
                                        other = state[y][xx]
                                        if other != " ":
                                            for gyy in range(4):
                                                for gxx in range(4):
                                                    if goal[gyy][gxx] == other and gyy == gy and gxx < gx:
                                                        dist += 2
                                if x == gx:
                                    for yy in range(y + 1, 4):
                                        other = state[yy][x]
                                        if other != " ":
                                            for gyy in range(4):
                                                for gxx in range(4):
                                                    if goal[gyy][gxx] == other and gxx == gx and gyy < gy:
                                                        dist += 2
                                break
            return dist

        # --- open set (優先度付きキュー) ---
        open_set = [(heuristic(start), 0, start, [])]
        visited = {start: 0}

        while open_set:
            _, cost, state, path = heapq.heappop(open_set)

            # --- ゴールに到達 ---
            if state == goal:
                return path

            # 空白位置
            ex, ey = [(x, y) for y in range(4) for x in range(4) if state[y][x] == " "][0]

            # 隣接展開
            for nx, ny in self.get_neighbors(ex, ey):
                new_state = [list(r) for r in state]
                new_state[ey][ex], new_state[ny][nx] = new_state[ny][nx], new_state[ey][ex]
                new_state = tuple(tuple(r) for r in new_state)

                new_cost = cost + 1
                if new_state not in visited or new_cost < visited[new_state]:
                    visited[new_state] = new_cost
                    priority = new_cost + heuristic(new_state)
                    heapq.heappush(open_set, (priority, new_cost, new_state, path + [(nx, ny, ex, ey)]))

        # ここに来ることは理論上あり得ない（必ず解ける）
        return []

    # ============================================================
    # 計算処理
    # ============================================================
    def compute(self, a, b, op):
        try:
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
            if op == "/":
                return a / b if b != 0 else float("inf")
        except Exception:
            return None

    def apply_input(self, label):
        """タイル入力処理"""

        if label in "0123456789.DC":
            pyxel.play(0, 0)  # 通常音
        elif label in "+-*/":
            pyxel.play(0, 1)  # 演算子用音
        elif label in "=":
            pyxel.play(0, 2)

        # デバッグ：0を5回連続入力でソルバー起動
        if label == "0":
            self.zero_count += 1
            if self.zero_count >= 5:
                self.zero_count = 0
                self.solver_path = self.auto_solve() or []
                self.solver_index = 0
                return
        else:
            self.zero_count = 0

        if label in "0123456789.":
            self.current_number += label

        elif label in "+-*/":
            if self.current_number:
                num = float(self.current_number)
                self.result = num if self.result is None else self.compute(self.result, num, self.current_operator)
                self.current_number = ""
            self.current_operator = label

        elif label == "=":
            if self.equal_revealed:
                self.start_new_game()

        elif label == "C":
            self.result, self.current_operator, self.current_number, self.history = None, None, "", []

        elif label == "D":
            self.current_number = self.current_number[:-1]

    # ============================================================
    # 更新処理
    # ============================================================
    def update(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y

        # 自動ソルバー
        if self.solver_path and self.solver_index < len(self.solver_path):
            self.solver_counter += 1
            if self.solver_counter >= self.solver_speed:
                self.solver_counter = 0
                nx, ny, ex, ey = self.solver_path[self.solver_index]
                moved_tile = self.board[ny][nx]
                self.board[ey][ex], self.board[ny][nx] = moved_tile, " "
                if moved_tile.strip():
                    self.apply_input(moved_tile)
                self.solver_index += 1
            return

        # --- 通常ドラッグ操作 ---
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            for y in range(4):
                for x in range(4):
                    bx, by = 10 + x * 50, 60 + y * 50
                    if bx <= mx <= bx + 40 and by <= my <= by + 40:
                        label = self.board[y][x]
                        if label == "=":
                            self.apply_input("=")
                            return

        # ドラッグ開始
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and not self.dragging:
            for y in range(4):
                for x in range(4):
                    bx, by = 10 + x * 50, 60 + y * 50
                    if bx <= mx <= bx + 40 and by <= my <= by + 40:
                        empty = self.find_empty()
                        if empty and (x, y) in self.get_neighbors(*empty):
                            self.dragging = True
                            self.drag_tile = self.board[y][x]
                            self.drag_start = (x, y)
                            self.drag_offset = (mx - bx, my - by)
                            self.drag_dir = "y" if x == empty[0] else "x"

        # ドラッグ終了
        if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT) and self.dragging:
            empty = self.find_empty()
            if empty:
                ex, ey = empty
                sx, sy = self.drag_start
                self.board[ey][ex], self.board[sy][sx] = self.drag_tile, " "
                self.apply_input(self.drag_tile)
            self.dragging, self.drag_tile, self.drag_dir = False, None, None

        # --- ゴールチェック ---
        if self.board == self.goal and not self.equal_revealed:
            empty = self.find_empty()
            if empty:
                ex, ey = empty
                self.board[ey][ex] = "="  # 「＝」を出す
                # --- スコア確定処理 ---
                if self.current_number and self.current_operator:
                    num = float(self.current_number)
                    self.result = self.compute(self.result, num, self.current_operator)
                    self.current_number = ""
                self.final_score = self.result
                self.equal_revealed = True

                pyxel.play(0, 2)

    # ============================================================
    # 描画処理
    # ============================================================
    def draw_scaled_text(self, x, y, text, col, scale=1):
        scale = int(scale)
        for i, ch in enumerate(text):
            for sy in range(scale):
                for sx in range(scale):
                    pyxel.text(x + i * 4 * scale + sx, y + sy, ch, col)

    def draw_goal_preview(self, x=10, y=10, scale=0.5):
        """右下などに正解配置のミニプレビューを表示"""
        for gy in range(4):
            for gx in range(4):
                goal_label = self.goal[gy][gx]

                # ゴール判定済みなら "=" を代入して表示
                if self.equal_revealed and goal_label == " ":
                    goal_label = "="

                if goal_label == " ":
                    continue

                current_label = self.board[gy][gx]

                # 色の決定
                if current_label == goal_label:
                    bg_col = 11  # 正解位置：水色系
                    txt_col = 0
                else:
                    bg_col = 2  # 不一致：薄緑系
                    txt_col = 6

                bx = x + int(gx * 20 * scale)
                by = y + int(gy * 20 * scale)
                pyxel.rect(bx, by, int(18 * scale), int(18 * scale), bg_col)
                pyxel.text(bx + 4, by + 4, goal_label, txt_col)

    def draw(self):
        pyxel.cls(0)

        # ディスプレイ
        pyxel.rect(10, 10, 190, 40, 1)
        display_right, y_upper, y_lower = 200, 18, 30

        # 上段：中間結果 → 演算子
        parts = []
        if self.result is not None:
            parts.append(("result", str(self.result)))
        if self.current_operator:
            parts.append(("op", self.current_operator))
        total_width = sum(len(t) * 4 + 4 for _, t in parts) - 4 if parts else 0
        x = display_right - total_width
        for kind, text in parts:
            pyxel.text(x, y_upper, text, 9 if kind == "result" else 10)
            x += len(text) * 4 + 4

        # 下段：入力中 or 最終スコア
        if self.equal_revealed and self.final_score is not None:
            text = str(self.final_score)
            x_pos = display_right - len(text) * 4
            self.draw_scaled_text(x_pos, y_lower, text, 13, 1)
        elif self.current_number:
            text = self.current_number
            x_pos = display_right - len(text) * 4
            self.draw_scaled_text(x_pos, y_lower, text, 12, 1)

        # ボタン描画
        for gy in range(4):
            for gx in range(4):
                label = self.board[gy][gx]
                if self.dragging and (gx, gy) == self.drag_start:
                    continue
                if label == " ":
                    continue
                bx, by = 10 + gx * 50, 60 + gy * 50
                color = (
                    5
                    if label in "0123456789."
                    else 9 if label in "+-*/" else 8 if label in "CD" else 12 if label == "=" else 7
                )
                pyxel.rect(bx, by, 40, 40, color)
                pyxel.rectb(bx, by, 40, 40, 7)
                pyxel.text(bx + 12, by + 14, label, 0)
                pyxel.text(bx + 13, by + 15, label, 7)

        # ドラッグ中のタイル
        if self.dragging and self.drag_tile:
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            sx, sy = self.drag_start
            bx, by = 10 + sx * 50, 60 + sy * 50
            if self.drag_dir == "x":
                bx = mx - self.drag_offset[0]
            elif self.drag_dir == "y":
                by = my - self.drag_offset[1]
            pyxel.rectb(bx, by, 40, 40, 10)
            pyxel.text(bx + 16, by + 16, self.drag_tile, 10)

        # マウスカーソル
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        pyxel.circ(mx, my, 1, 7)

        # --- 正解のミニプレビュー ---
        self.draw_goal_preview(x=10, y=10, scale=0.5)


if __name__ == "__main__":
    SlideCalc()
