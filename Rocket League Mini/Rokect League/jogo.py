# Rocket League Mini
# Run with: python jogo.py

import math
import random

import pgzrun
from pygame import Rect


WIDTH = 960
HEIGHT = 540
TITLE = "Rocket League Mini"

FIELD = Rect((42, 70), (876, 390))
GOAL_HEIGHT = 132
PLAYER_START = (190, 350)
BALL_START = (WIDTH / 2, HEIGHT / 2)

MENU = "menu"
PLAYING = "playing"
GAME_OVER = "game_over"

music_enabled = True
sound_enabled = True
game_state = MENU
winner_text = ""
background_channel = None


class AnimationSystem:
    """Small timer-based sprite animation helper."""

    def __init__(self, idle_frames, move_frames, frame_time=0.16):
        self.idle_frames = idle_frames
        self.move_frames = move_frames
        self.frame_time = frame_time
        self.timer = 0
        self.index = 0

    def update(self, dt, moving):
        self.timer += dt
        frames = self.move_frames if moving else self.idle_frames
        if self.timer >= self.frame_time:
            self.timer = 0
            self.index = (self.index + 1) % len(frames)
        return frames[self.index]


class MovementSystem:
    """Keeps car movement and arena limits in one place."""

    def __init__(self, speed, friction):
        self.speed = speed
        self.friction = friction

    def move_car(self, car, dt, x_axis, y_axis):
        if x_axis or y_axis:
            length = max(1, math.sqrt(x_axis * x_axis + y_axis * y_axis))
            car.vx += (x_axis / length) * self.speed * dt
            car.vy += (y_axis / length) * self.speed * dt
            car.angle = math.degrees(math.atan2(-y_axis, x_axis))

        car.vx *= self.friction
        car.vy *= self.friction
        car.x += car.vx * dt
        car.y += car.vy * dt

        car.x = max(FIELD.left + 22, min(FIELD.right - 22, car.x))
        car.y = max(FIELD.top + 24, min(FIELD.bottom - 24, car.y))


class Car:
    def __init__(self, x, y, idle_frames, move_frames):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.angle = 0
        self.actor = Actor(idle_frames[0], center=(x, y))
        self.animation = AnimationSystem(idle_frames, move_frames)
        self.movement = MovementSystem(1500, 0.90)

    @property
    def moving(self):
        return abs(self.vx) + abs(self.vy) > 30

    def update_actor(self, dt):
        self.actor.image = self.animation.update(dt, self.moving)
        self.actor.center = (self.x, self.y)
        self.actor.angle = self.angle

    def draw(self):
        self.actor.draw()


class Hero(Car):
    def __init__(self):
        super().__init__(
            PLAYER_START[0],
            PLAYER_START[1],
            ["hero_idle_0", "hero_idle_1", "hero_idle_2"],
            ["hero_move_0", "hero_move_1", "hero_move_2"],
        )

    def update(self, dt):
        x_axis = keyboard.d - keyboard.a + keyboard.right - keyboard.left
        y_axis = keyboard.s - keyboard.w + keyboard.down - keyboard.up
        self.movement.move_car(self, dt, x_axis, y_axis)
        self.update_actor(dt)


class Enemy(Car):
    def __init__(self, x, y, territory):
        super().__init__(
            x,
            y,
            ["enemy_idle_0", "enemy_idle_1", "enemy_idle_2"],
            ["enemy_move_0", "enemy_move_1", "enemy_move_2"],
        )
        self.territory = territory
        self.target = (x, y)
        self.change_target()

    def change_target(self):
        self.target = (
            random.randint(self.territory.left + 35, self.territory.right - 35),
            random.randint(self.territory.top + 35, self.territory.bottom - 35),
        )

    def update(self, dt, ball):
        chase_ball = random.random() < 0.015
        target_x, target_y = ball.x, ball.y
        if not chase_ball and distance(self.x, self.y, *self.target) < 35:
            self.change_target()

        if not chase_ball:
            target_x, target_y = self.target

        x_axis = target_x - self.x
        y_axis = target_y - self.y
        self.movement.move_car(self, dt, sign(x_axis), sign(y_axis))

        self.x = max(self.territory.left + 22, min(self.territory.right - 22, self.x))
        self.y = max(self.territory.top + 24, min(self.territory.bottom - 24, self.y))
        self.update_actor(dt)


class Ball:
    def __init__(self):
        self.x = BALL_START[0]
        self.y = BALL_START[1]
        self.vx = 0
        self.vy = 0
        self.actor = Actor("ball", center=BALL_START)

    def reset(self):
        self.x = BALL_START[0]
        self.y = BALL_START[1]
        self.vx = random.choice([-220, 220])
        self.vy = random.choice([-80, 80])

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.992
        self.vy *= 0.992

        if self.y < FIELD.top + 15 or self.y > FIELD.bottom - 15:
            self.vy *= -0.92
            play_sound("bounce")

        if self.x < FIELD.left + 15 and not in_goal_area(self.y):
            self.x = FIELD.left + 15
            self.vx *= -0.92
            play_sound("bounce")

        if self.x > FIELD.right - 15 and not in_goal_area(self.y):
            self.x = FIELD.right - 15
            self.vx *= -0.92
            play_sound("bounce")

        self.y = max(FIELD.top + 15, min(FIELD.bottom - 15, self.y))
        self.actor.center = (self.x, self.y)
        self.actor.angle += (abs(self.vx) + abs(self.vy)) * dt * 0.08

    def draw(self):
        self.actor.draw()


class Button:
    def __init__(self, text, y, action):
        self.text = text
        self.rect = Rect((WIDTH / 2 - 220, y), (440, 52))
        self.action = action

    def draw(self):
        color = (242, 190, 72) if self.rect.collidepoint(mouse_pos) else (32, 108, 160)
        screen.draw.filled_rect(self.rect, color)
        screen.draw.rect(self.rect, (255, 255, 255))
        screen.draw.text(
            self.text,
            center=self.rect.center,
            fontsize=30,
            color="white",
            owidth=1,
            ocolor="black",
        )

    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.action()


def sign(value):
    if value > 8:
        return 1
    if value < -8:
        return -1
    return 0


def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def in_goal_area(y):
    return HEIGHT / 2 - GOAL_HEIGHT / 2 < y < HEIGHT / 2 + GOAL_HEIGHT / 2


def play_sound(name):
    if not sound_enabled:
        return

    try:
        getattr(sounds, name).play()
    except Exception:
        pass


def start_music():
    global background_channel
    try:
        if background_channel:
            background_channel.stop()
            background_channel = None

        if music_enabled:
            sounds.stadium_loop.set_volume(0.28)
            background_channel = sounds.stadium_loop.play(-1)
    except Exception:
        background_channel = None


def start_game():
    global game_state, winner_text, score_player, score_enemy
    game_state = PLAYING
    winner_text = ""
    score_player = 0
    score_enemy = 0
    reset_round()
    play_sound("start")


def toggle_audio():
    global music_enabled, sound_enabled
    music_enabled = not music_enabled
    sound_enabled = music_enabled
    start_music()


def quit_game():
    raise SystemExit


def reset_round():
    hero.x, hero.y = PLAYER_START
    hero.vx = hero.vy = 0
    for enemy in enemies:
        enemy.vx = enemy.vy = 0
        enemy.change_target()
    ball.reset()


def handle_car_ball_collision(car):
    gap = distance(car.x, car.y, ball.x, ball.y)
    if gap < 38:
        dx = ball.x - car.x
        dy = ball.y - car.y
        length = max(1, math.sqrt(dx * dx + dy * dy))
        ball.vx = (dx / length) * 470 + car.vx * 0.22
        ball.vy = (dy / length) * 470 + car.vy * 0.22
        ball.x = car.x + (dx / length) * 39
        ball.y = car.y + (dy / length) * 39
        play_sound("kick")


def check_goal():
    global game_state, winner_text, score_player, score_enemy
    if ball.x < FIELD.left - 18 and in_goal_area(ball.y):
        score_enemy += 1
        play_sound("goal")
        reset_round()
    elif ball.x > FIELD.right + 18 and in_goal_area(ball.y):
        score_player += 1
        play_sound("goal")
        reset_round()

    if score_player >= 3:
        game_state = GAME_OVER
        winner_text = "Victory! Your team won 3 goals."
    elif score_enemy >= 3:
        game_state = GAME_OVER
        winner_text = "Defeat! The rivals scored 3 goals."


def draw_field():
    screen.fill((22, 111, 68))
    screen.draw.filled_rect(FIELD, (36, 138, 82))
    screen.draw.rect(FIELD, (232, 244, 232))
    screen.draw.line((WIDTH / 2, FIELD.top), (WIDTH / 2, FIELD.bottom), "white")
    screen.draw.circle((WIDTH / 2, HEIGHT / 2), 62, "white")

    left_goal = Rect((FIELD.left - 30, HEIGHT / 2 - GOAL_HEIGHT / 2), (30, GOAL_HEIGHT))
    right_goal = Rect((FIELD.right, HEIGHT / 2 - GOAL_HEIGHT / 2), (30, GOAL_HEIGHT))
    screen.draw.filled_rect(left_goal, (196, 55, 55))
    screen.draw.filled_rect(right_goal, (53, 112, 202))
    screen.draw.text(f"{score_player}  -  {score_enemy}", center=(WIDTH / 2, 35), fontsize=46)


def draw_menu():
    screen.fill((18, 46, 62))
    screen.draw.text(
        "Rocket League Mini",
        center=(WIDTH / 2, 95),
        fontsize=64,
        color=(242, 190, 72),
        owidth=2,
        ocolor="black",
    )
    screen.draw.text(
        "Score 3 goals before the rival cars.",
        center=(WIDTH / 2, 155),
        fontsize=26,
        color="white",
    )
    for button in buttons:
        button.draw()


def draw_game_over():
    draw_field()
    ball.draw()
    hero.draw()
    for enemy in enemies:
        enemy.draw()
    panel = Rect((WIDTH / 2 - 235, HEIGHT / 2 - 85), (470, 170))
    screen.draw.filled_rect(panel, (18, 46, 62))
    screen.draw.rect(panel, "white")
    screen.draw.text(winner_text, center=(WIDTH / 2, HEIGHT / 2 - 25), fontsize=30)
    screen.draw.text("Click to return to menu", center=(WIDTH / 2, HEIGHT / 2 + 30), fontsize=24)


def update(dt):
    if game_state != PLAYING:
        return

    hero.update(dt)
    for enemy in enemies:
        enemy.update(dt, ball)

    ball.update(dt)
    handle_car_ball_collision(hero)
    for enemy in enemies:
        handle_car_ball_collision(enemy)
    check_goal()


def draw():
    if game_state == MENU:
        draw_menu()
    elif game_state == PLAYING:
        draw_field()
        ball.draw()
        hero.draw()
        for enemy in enemies:
            enemy.draw()
    else:
        draw_game_over()


def on_mouse_move(pos):
    global mouse_pos
    mouse_pos = pos


def on_mouse_down(pos):
    global game_state
    if game_state == MENU:
        for button in buttons:
            button.click(pos)
    elif game_state == GAME_OVER:
        game_state = MENU


mouse_pos = (0, 0)
hero = Hero()
ball = Ball()
enemies = [
    Enemy(690, 185, Rect((520, 90), (360, 165))),
    Enemy(705, 360, Rect((520, 275), (360, 165))),
    Enemy(480, 270, Rect((360, 150), (240, 250))),
]
score_player = 0
score_enemy = 0
buttons = [
    Button("Iniciar Jogo", 220, start_game),
    Button("Ativar/Desativar Musica e Sons", 292, toggle_audio),
    Button("Sair", 364, quit_game),
]

start_music()

pgzrun.go()
