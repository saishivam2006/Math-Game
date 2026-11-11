import csv


README.mdimport csv
import os
import random
import sqlite3
import sys
import time
from pathlib import Path

import pygame

WIDTH, HEIGHT = 1040, 700
FPS = 60
BG = (17, 28, 49)
PANEL = (30, 46, 72)
INK = (241, 246, 255)
MUTED = (174, 192, 217)
GOLD = (255, 203, 86)
MINT = (90, 224, 173)
CORAL = (255, 119, 112)
BLUE = (104, 173, 255)

STAGES = [
    {"name": "Number Forest", "topic": "BODMAS & number skills", "crystal": "🌿", "color": (74, 174, 128)},
    {"name": "Fraction Falls", "topic": "Fractions & sharing", "crystal": "💧", "color": (76, 164, 224)},
    {"name": "Algebra Peaks", "topic": "Patterns & early algebra", "crystal": "🔷", "color": (165, 127, 226)},
    {"name": "Shape Sun Temple", "topic": "Shapes & everyday maths", "crystal": "☀", "color": (230, 163, 72)},
]

FIXED = {
    (0, 0): ("6 + 3 × 4", 18, "Do multiplication before addition: 3 × 4, then add 6."),
    (0, 1): ("24 ÷ 6 + 5", 9, "Divide first: 24 ÷ 6 = 4, then add 5."),
    (0, 2): ("(8 + 4) ÷ 3", 4, "Brackets first: 8 + 4 = 12. Then divide by 3."),
    (0, 3): ("30 − 2 × 7", 16, "Multiply first: 2 × 7 = 14. Then subtract from 30."),
    (0, 4): ("18 ÷ 3 × 2", 12, "Division and multiplication go left to right."),
    (1, 0): ("½ of 18 mangoes", 9, "Half means split into 2 equal groups."),
    (1, 1): ("¼ of 20 ladoos", 5, "One quarter means divide by 4."),
    (1, 2): ("½ + ¼ = how many quarters?", 3, "One half is the same as two quarters."),
    (1, 3): ("3/5 of 20 beads", 12, "Find one fifth (20 ÷ 5), then take 3 groups."),
    (1, 4): ("A 10 rupee snack costs 7. Change?", 3, "Subtract the cost from 10."),
    (2, 0): ("□ + 5 = 12. What is □?", 7, "Undo +5 by subtracting 5 from both sides."),
    (2, 1): ("3 × □ = 21", 7, "What number multiplied by 3 makes 21?"),
    (2, 2): ("x − 4 = 9. Find x.", 13, "Undo −4 by adding 4."),
    (2, 3): ("2 × x = 16. Find x.", 8, "Divide 16 into 2 equal groups."),
    (2, 4): ("A pattern goes 4, 7, 10, __", 13, "The pattern adds 3 each time."),
    (3, 0): ("A square has sides of 5 cm. Perimeter?", 20, "A square has 4 equal sides."),
    (3, 1): ("How many sides has a triangle?", 3, "Tri means three."),
    (3, 2): ("2 rows of 6 seeds. How many seeds?", 12, "Add 6 + 6 or multiply 2 × 6."),
    (3, 3): ("A bus has 24 seats. 6 are empty. How many are used?", 18, "Subtract the empty seats."),
    (3, 4): ("One notebook costs 8 rupees. Cost of 3?", 24, "Add 8 three times or multiply 8 × 3."),
}


def question_for(stage, level):
    if (stage, level) in FIXED:
        return FIXED[(stage, level)]
    return FIXED[(stage, level)]


def db_path():
    root = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "MathQuest"
    root.mkdir(parents=True, exist_ok=True)
    return root / "mathquest.sqlite3"


def connect_db():
    con = sqlite3.connect(db_path())
    con.execute("""CREATE TABLE IF NOT EXISTS players(
        email TEXT PRIMARY KEY, display_name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        unlocked_stage INTEGER NOT NULL DEFAULT 0, xp INTEGER NOT NULL DEFAULT 0, coins INTEGER NOT NULL DEFAULT 0,
        completed_levels TEXT NOT NULL DEFAULT '')""")
    con.execute("""CREATE TABLE IF NOT EXISTS answers(
        id INTEGER PRIMARY KEY, email TEXT NOT NULL, stage INTEGER NOT NULL, level INTEGER NOT NULL,
        topic TEXT NOT NULL, question TEXT NOT NULL, expected_answer TEXT NOT NULL,
        submitted_answer TEXT NOT NULL, correct INTEGER NOT NULL, response_ms INTEGER NOT NULL,
        attempt_number INTEGER NOT NULL, hint_used INTEGER NOT NULL, answered_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    con.commit()
    return con


def get_player(con, email):
    return con.execute("SELECT email,display_name,unlocked_stage,xp,coins,completed_levels FROM players WHERE email=?", (email,)).fetchone()


def parse_completed(value):
    return {tuple(map(int, x.split("-"))) for x in value.split(",") if x}


def save_completed(con, email, done):
    val = ",".join(f"{s}-{l}" for s, l in sorted(done))
    con.execute("UPDATE players SET completed_levels=? WHERE email=?", (val, email))
    con.commit()


def export_csv(con, email):
    target = Path.home() / "Documents" / "MathQuest" / "exports"
    target.mkdir(parents=True, exist_ok=True)
    name = "math_quest_answers.csv"
    path = target / name
    rows = con.execute("SELECT answered_at,stage,level,topic,question,submitted_answer,expected_answer,correct,response_ms,attempt_number,hint_used FROM answers WHERE email=? ORDER BY id", (email,)).fetchall()
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["answered_at", "stage", "level", "topic", "question", "submitted_answer", "expected_answer", "correct", "response_ms", "attempt_number", "hint_used"])
        w.writerows(rows)
    return path


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Math Quest — The Adventure of Numbers")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui,arial", 24)
        self.small = pygame.font.SysFont("segoeui,arial", 18)
        self.big = pygame.font.SysFont("segoeui,arial", 45, bold=True)
        self.title = pygame.font.SysFont("segoeui,arial", 32, bold=True)
        self.db = connect_db()
        self.email, self.player = "", None
        self.screen_name = "login"
        self.email_input, self.name_input = "", ""
        self.focus = "email"
        self.stage, self.level = 0, 0
        self.done, self.attempts, self.hint_used = set(), 0, False
        self.feedback, self.feedback_color = "", MINT
        self.started = time.perf_counter()
        self.option_values = []
        self.rewards_shown = False

    def text(self, value, x, y, color=INK, font=None, center=False):
        surf = (font or self.font).render(str(value), True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surf, rect)

    def panel(self, rect, color=PANEL, radius=18):
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)

    def button(self, label, rect, color=BLUE, text_color=BG):
        rect = pygame.Rect(rect)
        pygame.draw.rect(self.screen, color, rect, border_radius=14)
        self.text(label, rect.centerx, rect.centery, text_color, self.font, True)

    def draw_header(self, subtitle=""):
        self.text("MATH QUEST", 34, 24, GOLD, self.title)
        self.text(subtitle, 36, 64, MUTED, self.small)
        if self.player:
            self.text(f"{self.player[1]}   ✦ {self.player[3]} XP   ● {self.player[4]} coins", 650, 35, INK, self.small)

    def draw_login(self):
        self.screen.fill(BG)
        self.text("A little maths. A big adventure.", WIDTH//2, 135, GOLD, self.big, True)
        self.text("Your progress stays on this computer. Play offline anytime.", WIDTH//2, 190, MUTED, self.font, True)
        self.panel((260, 245, 520, 300))
        self.text("PLAYER LOGIN", 300, 272, INK, self.title)
        self.text("Email ID", 300, 330, MUTED, self.small)
        self.panel((300, 354, 440, 48), (45, 64, 94), 10)
        self.text(self.email_input + ("▏" if self.focus == "email" else ""), 314, 365, INK, self.font)
        self.text("Player name", 300, 417, MUTED, self.small)
        self.panel((300, 441, 440, 48), (45, 64, 94), 10)
        self.text(self.name_input + ("▏" if self.focus == "name" else ""), 314, 452, INK, self.font)
        self.button("ENTER ADVENTURE   ↵", (370, 510, 300, 52), GOLD, BG)
        if self.feedback:
            self.text(self.feedback, WIDTH//2, 575, self.feedback_color, self.small, True)
        self.text("Click a box to type • Enter to continue • Email is saved only on this device", WIDTH//2, 635, MUTED, self.small, True)

    def login(self):
        email = self.email_input.strip().lower()
        name = self.name_input.strip() or (email.split("@")[0] if "@" in email else "Adventurer")
        if "@" not in email or "." not in email.split("@")[-1]:
            self.feedback, self.feedback_color = "Please enter a valid email address.", CORAL
            return
        old = get_player(self.db, email)
        if not old:
            self.db.execute("INSERT INTO players(email,display_name) VALUES (?,?)", (email, name))
            self.db.commit()
        else:
            self.db.execute("UPDATE players SET display_name=? WHERE email=?", (name, email))
            self.db.commit()
        self.email, self.player = email, get_player(self.db, email)
        self.done = parse_completed(self.player[5])
        self.screen_name = "home"

    def draw_home(self):
        self.screen.fill(BG)
        self.draw_header("The Number Master has scattered four crystals. Can you bring them home?")
        self.text("Choose your next trail", WIDTH//2, 145, INK, self.big, True)
        for i, s in enumerate(STAGES):
            x, y = 90 + i*235, 235
            unlocked = i <= self.player[2]
            self.panel((x, y, 205, 215), (35, 58, 77) if unlocked else (34, 39, 53))
            self.text(["I", "II", "III", "IV"][i], x+102, y+34, GOLD if unlocked else MUTED, self.title, True)
            self.text(s["name"], x+102, y+86, INK if unlocked else MUTED, self.small, True)
            self.text(s["topic"], x+102, y+121, MUTED, self.small, True)
            count = sum((i,l) in self.done for l in range(5))
            self.text(f"{count}/5 trails complete" if unlocked else "🔒 Finish the stage before", x+102, y+170, MINT if count == 5 else MUTED, self.small, True)
            if not unlocked:
                self.text("this one", x+102, y+194, MUTED, self.small, True)
            pygame.draw.rect(self.screen, s["color"], (x, y, 205, 9), border_radius=5)
        self.button("PLAY / CONTINUE", (350, 500, 340, 58), GOLD, BG)
        self.button("MY PROGRESS", (215, 590, 250, 48), BLUE, BG)
        self.button("HOW TO PLAY", (495, 590, 250, 48), BLUE, BG)
        self.text("Esc: return to title", 860, 655, MUTED, self.small)

    def new_level(self, stage, level):
        self.stage, self.level = stage, level
        self.attempts, self.hint_used, self.feedback = 0, False, ""
        self.started = time.perf_counter()
        self.world_width = 2360
        self.gate_x = 2240
        self.player_x, self.player_y, self.player_vy = 90.0, 0.0, 0.0
        self.player_w, self.player_h = 38, 54
        self.camera_x = 0
        self.grounded = False
        self.health = 3
        self.coins_in_level = [
            [180, 470], [270, 400], [370, 465], [620, 430], [760, 365],
            [910, 465], [1160, 430], [1330, 380], [1510, 465], [1770, 425],
            [1940, 365], [2100, 465],
        ]
        self.hazards = [350, 700, 930, 1240, 1530, 1810, 2050]
        self.platforms = [
            pygame.Rect(0, 560, 470, 180), pygame.Rect(560, 560, 440, 180),
            pygame.Rect(1080, 560, 500, 180), pygame.Rect(1660, 560, 700, 180),
            pygame.Rect(230, 475, 130, 18), pygame.Rect(615, 425, 150, 18),
            pygame.Rect(840, 475, 130, 18), pygame.Rect(1165, 425, 150, 18),
            pygame.Rect(1400, 475, 130, 18), pygame.Rect(1770, 425, 150, 18),
            pygame.Rect(1980, 475, 130, 18),
        ]
        self.make_options()
        self.screen_name = "platformer"

    def update_platformer(self):
        keys = pygame.key.get_pressed()
        speed = 5.2
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.player_x -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.player_x += speed
        self.player_x = max(0, min(self.player_x, self.world_width - self.player_w))

        old_bottom = self.player_y + self.player_h
        self.player_vy = min(self.player_vy + 0.65, 14)
        self.player_y += self.player_vy
        self.grounded = False
        player_rect = pygame.Rect(int(self.player_x), int(self.player_y), self.player_w, self.player_h)
        for platform in self.platforms:
            overlaps = player_rect.right > platform.left and player_rect.left < platform.right
            new_bottom = self.player_y + self.player_h
            if overlaps and self.player_vy >= 0 and old_bottom <= platform.top and new_bottom >= platform.top:
                self.player_y = platform.top - self.player_h
                self.player_vy = 0
                self.grounded = True
                player_rect.y = int(self.player_y)

        if self.player_y > HEIGHT + 90:
            self.hit_hazard()
            return

        for coin in self.coins_in_level[:]:
            coin_rect = pygame.Rect(coin[0]-10, coin[1]-10, 20, 20)
            if player_rect.colliderect(coin_rect):
                self.coins_in_level.remove(coin)
                self.db.execute("UPDATE players SET coins=coins+1 WHERE email=?", (self.email,))
                self.db.commit()
                self.player = get_player(self.db, self.email)

        for hx in self.hazards:
            hazard_rect = pygame.Rect(hx, 528, 42, 32)
            if player_rect.colliderect(hazard_rect):
                self.hit_hazard()
                return

        self.camera_x = max(0, min(int(self.player_x - WIDTH * 0.34), self.world_width - WIDTH))
        if self.player_x + self.player_w >= self.gate_x:
            self.started = time.perf_counter()
            self.make_options()
            self.screen_name = "question"

    def hit_hazard(self):
        self.health -= 1
        self.player_x, self.player_y, self.player_vy = 90.0, 506.0, 0.0
        self.camera_x = 0
        if self.health <= 0:
            self.health = 3
            self.feedback = "Checkpoint! Take a breath and try the trail again."

    def draw_platformer(self):
        stage = STAGES[self.stage]
        sky_colors = [(147, 212, 230), (246, 211, 145), (160, 197, 236), (250, 212, 123)]
        self.screen.fill(sky_colors[self.stage])
        # Distant scenery moves more slowly than the trail.
        for i in range(7):
            x = (i * 230 - int(self.camera_x * 0.24)) % (WIDTH + 260) - 130
            pygame.draw.ellipse(self.screen, (207, 226, 200), (x, 310 + (i%2)*36, 300, 170))
        for i in range(9):
            x = (i * 180 - int(self.camera_x * 0.5)) % (WIDTH + 220) - 110
            pygame.draw.ellipse(self.screen, stage["color"], (x, 425 + (i%3)*18, 240, 130))

        for platform in self.platforms:
            rect = pygame.Rect(platform.x-self.camera_x, platform.y, platform.width, platform.height)
            if platform.top >= 550:
                pygame.draw.rect(self.screen, (112, 78, 55), rect)
                pygame.draw.rect(self.screen, stage["color"], (rect.x, rect.y, rect.width, 14), border_radius=5)
                for tile_x in range(rect.x+10, rect.right, 46):
                    pygame.draw.line(self.screen, (136, 99, 67), (tile_x, rect.y+35), (tile_x, HEIGHT), 2)
            else:
                pygame.draw.rect(self.screen, (115, 83, 57), rect, border_radius=8)
                pygame.draw.rect(self.screen, stage["color"], (rect.x, rect.y, rect.width, 8), border_radius=4)

        for coin_x, coin_y in self.coins_in_level:
            sx = coin_x-self.camera_x
            if -30 < sx < WIDTH+30:
                pygame.draw.ellipse(self.screen, GOLD, (sx-10, coin_y-14, 20, 28))
                pygame.draw.ellipse(self.screen, (255, 235, 162), (sx-4, coin_y-9, 5, 18))

        for hx in self.hazards:
            sx = hx-self.camera_x
            if -60 < sx < WIDTH+60:
                pygame.draw.polygon(self.screen, CORAL, [(sx,560),(sx+21,524),(sx+42,560)])
                pygame.draw.polygon(self.screen, (255,188,145), [(sx+15,550),(sx+21,536),(sx+27,550)])

        gate_screen_x = self.gate_x-self.camera_x
        pygame.draw.rect(self.screen, (82, 58, 95), (gate_screen_x, 430, 52, 130), border_radius=14)
        pygame.draw.rect(self.screen, GOLD, (gate_screen_x+11, 445, 30, 115), border_radius=12)
        pygame.draw.circle(self.screen, INK, (gate_screen_x+26, 475), 7)

        sx, sy = int(self.player_x-self.camera_x), int(self.player_y)
        # Original little trail explorer: scarf, tunic, boots, and a round backpack.
        pygame.draw.ellipse(self.screen, (38,57,75), (sx-4, sy+self.player_h-3, 48, 12))
        pygame.draw.rect(self.screen, (31, 126, 132), (sx+5, sy+20, 29, 29), border_radius=9)
        pygame.draw.rect(self.screen, (244, 115, 87), (sx-2, sy+23, 13, 8), border_radius=4)
        pygame.draw.circle(self.screen, (196, 124, 82), (sx+20, sy+13), 14)
        pygame.draw.arc(self.screen, (57, 43, 39), (sx+7, sy+1, 28, 22), 3.14, 6.2, 5)
        pygame.draw.rect(self.screen, (71, 62, 97), (sx+3, sy+46, 14, 8), border_radius=4)
        pygame.draw.rect(self.screen, (71, 62, 97), (sx+23, sy+46, 14, 8), border_radius=4)
        pygame.draw.circle(self.screen, INK, (sx+24, sy+12), 2)

        self.panel((18, 14, WIDTH-36, 78), (24, 45, 66, 235), 15)
        self.text(f"{stage['name']}  •  Trail {self.level+1}/5", 38, 27, INK, self.title)
        self.text(f"Coins {self.player[4]}   ✦ {self.player[3]} XP   ♥ {max(self.health,0)}", 40, 63, GOLD, self.small)
        self.text("← → / A D move     SPACE / ↑ jump     reach the golden gate", 555, 45, INK, self.small)
        if self.feedback:
            self.text(self.feedback, WIDTH//2, 640, CORAL, self.font, True)

    def make_options(self):
        answer = question_for(self.stage, self.level)[1]
        vals = {answer}
        while len(vals) < 4:
            vals.add(max(0, answer + random.choice([-8, -5, -3, -2, -1, 1, 2, 3, 5, 8])))
        self.option_values = list(vals)
        random.shuffle(self.option_values)

    def draw_question(self):
        self.screen.fill(BG)
        s = STAGES[self.stage]
        self.draw_header(f"{s['name']}  /  Trail {self.level+1} of 5")
        self.panel((105, 132, 830, 480))
        self.text(f"TRAIL {self.level+1}   •   {s['topic']}", WIDTH//2, 183, s["color"], self.title, True)
        expression = question_for(self.stage, self.level)[0]
        self.text(expression, WIDTH//2, 265, INK, self.big, True)
        self.text("Choose an answer. Take your time — you can try again!", WIDTH//2, 314, MUTED, self.font, True)
        for i, value in enumerate(self.option_values):
            rect = pygame.Rect(270+(i%2)*260, 365+(i//2)*76, 230, 58)
            self.button(f"{i+1}     {value}", rect, (57, 87, 122), INK)
        self.text("Press 1, 2, 3 or 4 to answer", WIDTH//2, 535, MUTED, self.small, True)
        self.button("HINT", (240, 565, 160, 42), GOLD, BG)
        self.button("BACK TO TRAILS", (640, 565, 200, 42), BLUE, BG)
        if self.feedback:
            self.text(self.feedback, WIDTH//2, 625, self.feedback_color, self.small, True)

    def record(self, answer):
        question, expected, _ = question_for(self.stage, self.level)
        self.attempts += 1
        correct = int(str(answer).strip().lower() == str(expected).lower())
        elapsed = int((time.perf_counter() - self.started) * 1000)
        self.db.execute("INSERT INTO answers(email,stage,level,topic,question,expected_answer,submitted_answer,correct,response_ms,attempt_number,hint_used) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (self.email, self.stage+1, self.level+1, STAGES[self.stage]["topic"], question, str(expected), str(answer), correct, elapsed, self.attempts, int(self.hint_used)))
        if correct:
            if (self.stage, self.level) not in self.done:
                bonus = max(5, 20 - self.attempts*3) + (5 if not self.hint_used else 0)
                self.done.add((self.stage, self.level))
                unlocked = self.player[2]
                new_unlocked = min(3, self.stage + 1) if self.level == 4 else unlocked
                self.db.execute("UPDATE players SET xp=xp+?, coins=coins+?, unlocked_stage=? WHERE email=?", (bonus, 5, max(unlocked, new_unlocked), self.email))
                save_completed(self.db, self.email, self.done)
            self.db.commit()
            self.player = get_player(self.db, self.email)
            self.feedback = "Brilliant! The path is open. ✨"
            self.feedback_color = MINT
            self.screen_name = "success"
        else:
            self.db.commit()
            self.feedback = "Nearly! Try once more. Use HINT if you need a clue."
            self.feedback_color = GOLD
            self.started = time.perf_counter()

    def draw_success(self):
        self.screen.fill(BG)
        self.draw_header("A trail cleared!")
        self.panel((180, 150, 680, 430))
        self.text("GREAT WORK!", WIDTH//2, 220, GOLD, self.big, True)
        self.text(f"Trail {self.level+1} is complete", WIDTH//2, 288, INK, self.title, True)
        self.text("+5 coins    •    XP added    •    Keep your crystal glowing!", WIDTH//2, 342, MINT, self.font, True)
        next_level = self.level + 1
        if next_level < 5:
            self.button("NEXT TRAIL   →", (370, 410, 300, 58), GOLD, BG)
        else:
            self.text(f"All five trails of {STAGES[self.stage]['name']} are complete!", WIDTH//2, 415, GOLD, self.font, True)
            self.text("You earned the stage crystal!", WIDTH//2, 451, MINT, self.font, True)
            if self.stage < 3:
                self.button("EXPLORE NEXT STAGE   →", (340, 500, 360, 58), GOLD, BG)
            else:
                self.button("MEET THE NUMBER MASTER   →", (320, 500, 400, 58), GOLD, BG)
        self.button("TRAIL MAP", (410, 590, 220, 46), BLUE, BG)

    def draw_progress(self):
        self.screen.fill(BG)
        self.draw_header("Your learning journey")
        total = self.db.execute("SELECT COUNT(*),COALESCE(SUM(correct),0),COALESCE(AVG(response_ms),0) FROM answers WHERE email=?", (self.email,)).fetchone()
        accuracy = (100*total[1]/total[0]) if total[0] else 0
        self.panel((105, 130, 830, 150))
        self.text(f"Questions tried: {total[0]}     Correct answers: {total[1]}     Accuracy: {accuracy:.0f}%", WIDTH//2, 180, INK, self.title, True)
        self.text(f"Average response time: {total[2]/1000:.1f} seconds     •     Hints used are recorded too", WIDTH//2, 230, MUTED, self.font, True)
        for i,s in enumerate(STAGES):
            count = sum((i,l) in self.done for l in range(5))
            self.panel((130, 310+i*63, 780, 48), (40, 65, 82))
            self.text(s["name"], 155, 320+i*63, INK, self.font)
            self.text(f"{count}/5 trails", 700, 320+i*63, MINT if count==5 else MUTED, self.font)
        self.button("EXPORT ANSWERS CSV", (290, 585, 260, 50), GOLD, BG)
        self.button("BACK", (590, 585, 160, 50), BLUE, BG)

    def draw_how(self):
        self.screen.fill(BG)
        self.draw_header("A friendly guide")
        self.panel((115, 125, 810, 480))
        lines = ["HOW TO PLAY", "1. Run with ← → or A / D. Jump with SPACE or ↑.", "2. Explore the trail, collect coins and avoid the thorny hazards.", "3. Reach the golden gate and solve its maths challenge.", "4. Wrong answers are safe. Use H for a hint and try again.", "5. Clear five trails to earn a crystal and unlock the next stage.", "", "Stages move from BODMAS to fractions, algebra and shapes.", "Progress and answers are saved on this computer only.", "Use My Progress to review accuracy and export a CSV.", "Esc returns to the map."]
        for i,line in enumerate(lines): self.text(line, 165, 165+i*34, GOLD if i==0 else INK, self.title if i==0 else self.font)
        self.button("BACK", (425, 565, 190, 48), BLUE, BG)

    def hint(self):
        tip = question_for(self.stage, self.level)[2]
        self.hint_used = True
        self.feedback, self.feedback_color = "Hint: " + tip, GOLD

    def run(self):
        while True:
            self.clock.tick(FPS)
            mouse = pygame.mouse.get_pos()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.db.close(); pygame.quit(); return
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.screen_name = "home" if self.player else "login"
                    if self.screen_name == "login":
                        if e.key == pygame.K_TAB: self.focus = "name" if self.focus=="email" else "email"
                        elif e.key == pygame.K_RETURN: self.login()
                        elif e.key == pygame.K_BACKSPACE:
                            if self.focus=="email": self.email_input=self.email_input[:-1]
                            else: self.name_input=self.name_input[:-1]
                        elif e.unicode.isprintable():
                            if self.focus=="email": self.email_input+=e.unicode
                            else: self.name_input+=e.unicode
                    elif self.screen_name == "question":
                        if e.key == pygame.K_h: self.hint()
                        if e.key in [pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4]: self.record(self.option_values[e.key-pygame.K_1])
                    elif self.screen_name == "platformer" and e.key in [pygame.K_SPACE, pygame.K_UP, pygame.K_w]:
                        if self.grounded:
                            self.player_vy = -13.2
                            self.grounded = False
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    x,y=mouse
                    if self.screen_name == "login":
                        if 300<=x<=740 and 354<=y<=402: self.focus="email"
                        elif 300<=x<=740 and 441<=y<=489: self.focus="name"
                        elif 370<=x<=670 and 510<=y<=562: self.login()
                    elif self.screen_name == "home":
                        if 350<=x<=690 and 500<=y<=558:
                            stage=min(self.player[2],3)
                            level=next((l for l in range(5) if (stage,l) not in self.done), 0)
                            self.new_level(stage,level)
                        elif 215<=x<=465 and 590<=y<=638: self.screen_name="progress"
                        elif 495<=x<=745 and 590<=y<=638: self.screen_name="how"
                    elif self.screen_name == "question":
                        if 240<=x<=400 and 565<=y<=607: self.hint()
                        elif 640<=x<=840 and 565<=y<=607: self.screen_name="home"
                        else:
                            for i in range(4):
                                rect=pygame.Rect(270+(i%2)*260,365+(i//2)*76,230,58)
                                if rect.collidepoint(x,y): self.record(self.option_values[i])
                    elif self.screen_name == "success":
                        if 410<=x<=630 and 590<=y<=636: self.screen_name="home"
                        elif self.level<4 and 370<=x<=670 and 410<=y<=468: self.new_level(self.stage,self.level+1)
                        elif self.level==4 and 300<=x<=740 and 490<=y<=558:
                            if self.stage<3: self.new_level(self.stage+1,0)
                            else: self.screen_name="finalboss"
                    elif self.screen_name == "progress":
                        if 290<=x<=550 and 585<=y<=635:
                            path=export_csv(self.db,self.email); self.feedback=f"Saved: {path}"
                        elif 590<=x<=750 and 585<=y<=635: self.screen_name="home"
                    elif self.screen_name == "how" and 425<=x<=615 and 565<=y<=613: self.screen_name="home"
                    elif self.screen_name == "finalboss": self.screen_name="home"
            if self.screen_name=="platformer":
                self.update_platformer()
                self.draw_platformer()
            elif self.screen_name=="login": self.draw_login()
            elif self.screen_name=="home": self.draw_home()
            elif self.screen_name=="question": self.draw_question()
            elif self.screen_name=="success": self.draw_success()
            elif self.screen_name=="progress":
                self.draw_progress()
                if self.feedback: self.text(self.feedback, WIDTH//2, 660, MINT, self.small, True)
            elif self.screen_name=="how": self.draw_how()
            elif self.screen_name=="finalboss":
                self.screen.fill(BG); self.draw_header("The Number Master awaits")
                self.panel((150,150,740,400)); self.text("THE CRYSTALS ARE HOME!",WIDTH//2,250,GOLD,self.big,True)
                self.text("You are a true Math Quest champion.",WIDTH//2,330,INK,self.title,True)
                self.text("Keep practising to make your skills shine brighter.",WIDTH//2,385,MUTED,self.font,True)
                self.button("RETURN TO MAP",(390,470,260,55),GOLD,BG)
            pygame.display.flip()


if __name__ == "__main__":
    try:
        Game().run()
    except Exception as exc:
        print("Math Quest could not start:", exc)
        print("Install dependencies with: py -m pip install -r requirements.txt")
        sys.exit(1)
