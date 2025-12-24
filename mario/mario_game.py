import pygame
import json
import sys
import os

# Inicializar Pygame
pygame.init()
pygame.mixer.init()

# Constantes
WIDTH, HEIGHT = 800, 600
FPS = 60
GRAVITY = 0.8
JUMP_FORCE = -15
PLAYER_SPEED = 5
FIREBALL_SPEED = 10

# Colores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
SKY_BLUE = (135, 206, 235)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario Adventure")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 24)

# Cargar datos del juego
with open('levels.json', 'r', encoding='utf-8') as f:
    game_data = json.load(f)

current_level_id = 1
level_data = next(l for l in game_data["game"]["levels"] if l["id"] == current_level_id)

# Variables del jugador
score = 0
coins = 0
lives = game_data["game"]["player"]["lives"]
time_left = game_data["game"]["settings"]["time_per_level"]
player_state = "normal"  # normal, big, fire, invincible
invincible_timer = 0

camera_x = 0

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.state = player_state
        self.size = 32 if self.state == "normal" else 64
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = level_data["start_position"]["x"]
        self.rect.bottom = HEIGHT - 100  # suelo base
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.can_shoot = False

    def update(self):
        global player_state, invincible_timer, camera_x

        # Movimiento horizontal
        keys = pygame.key.get_pressed()
        self.vel_x = 0
        if keys[pygame.K_LEFT]:
            self.vel_x = -PLAYER_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT]:
            self.vel_x = PLAYER_SPEED
            self.facing_right = True

        # Salto
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = JUMP_FORCE
            self.on_ground = False

        # Disparo (solo con flor)
        if keys[pygame.K_LCTRL] and player_state == "fire" and self.can_shoot:
            fireball = Fireball(self.rect.centerx, self.rect.centery, self.facing_right)
            all_sprites.add(fireball)
            fireballs.add(fireball)
            self.can_shoot = False
        if not keys[pygame.K_LCTRL]:
            self.can_shoot = True

        # Gravedad
        self.vel_y += GRAVITY
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

        # Límites del suelo y muerte por caída
        if self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y = 0
            self.on_ground = True
        if self.rect.top > HEIGHT:
            self.die()

        # Cámara sigue al jugador
        camera_x = max(0, self.rect.centerx - WIDTH // 2)

        # Invencibilidad temporal
        if invincible_timer > 0:
            invincible_timer -= 1
            if invincible_timer == 0:
                player_state = "big" if player_state == "invincible" else player_state

    def get_powerup(self, type):
        global player_state
        if type == "mushroom" and player_state == "normal":
            player_state = "big"
        elif type == "flower":
            player_state = "fire"
        elif type == "star":
            player_state = "invincible"
            invincible_timer = 600  # 10 segundos a 60 FPS

        self.update_size()

    def update_size(self):
        self.size = 64 if player_state in ["big", "fire", "invincible"] else 32
        old_center = self.rect.center
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(RED if player_state != "fire" else YELLOW)
        self.rect = self.image.get_rect(center=old_center)

    def die(self):
        global lives
        lives -= 1
        if lives <= 0:
            game_over()
        else:
            self.reset_position()

    def reset_position(self):
        self.rect.x = level_data["start_position"]["x"]
        self.rect.bottom = HEIGHT - 100
        self.vel_x = self.vel_y = 0
        player_state = "normal"
        self.update_size()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, type="Goomba"):
        super().__init__()
        self.type = type
        self.image = pygame.Surface((32, 32))
        self.image.fill((139, 69, 19) if type == "Goomba" else (0, 128, 0))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.bottom = HEIGHT - 100
        self.vel_x = -2 if type == "Goomba" else -1
        self.direction = -1

    def update(self):
        self.rect.x += self.vel_x
        if self.rect.left < camera_x or self.rect.right > camera_x + WIDTH + 100:
            return
        # Cambio de dirección simple
        if self.rect.x <= 0 or self.rect.x >= level_data["length"]:
            self.vel_x *= -1

class Fireball(pygame.sprite.Sprite):
    def __init__(self, x, y, facing_right):
        super().__init__()
        self.image = pygame.Surface((12, 12))
        self.image.fill((255, 165, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.vel_x = FIREBALL_SPEED if facing_right else -FIREBALL_SPEED

    def update(self):
        self.rect.x += self.vel_x
        if self.rect.right < camera_x or self.rect.left > camera_x + WIDTH:
            self.kill()

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        self.image.fill(YELLOW)
        pygame.draw.circle(self.image, YELLOW, (10, 10), 10)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y + 50)

    def collect(self):
        global coins, score
        coins += 1
        score += 100
        if coins >= 100:
            global lives
            lives = min(lives + 1, game_data["game"]["settings"]["max_lives"])
            coins = 0
        self.kill()

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, type):
        super().__init__()
        color = {"mushroom": (255, 0, 0), "flower": (255, 105, 180), "star": (255, 215, 0)}[type]
        self.type = type
        self.image = pygame.Surface((32, 32))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y + 50)

# Grupos de sprites
all_sprites = pygame.sprite.Group()
enemies = pygame.sprite.Group()
coins_group = pygame.sprite.Group()
powerups = pygame.sprite.Group()
fireballs = pygame.sprite.Group()

player = Player()
all_sprites.add(player)

# Generar elementos del nivel actual
def load_level(level_id):
    global level_data, time_left, camera_x
    level_data = next(l for l in game_data["game"]["levels"] if l["id"] == level_id)
    time_left = game_data["game"]["settings"]["time_per_level"]
    camera_x = 0

    # Limpiar sprites antiguos
    for group in [enemies, coins_group, powerups, fireballs]:
        group.empty()

    # Enemigos
    for enemy in level_data["enemies"]:
        if enemy["type"] != "Bowser":
            for i in range(enemy["count"]):
                ex = enemy["position"]["x"] + i * 100
                ey = enemy["position"]["y"]
                e = Enemy(ex, ey, enemy["type"])
                all_sprites.add(e)
                enemies.add(e)

    # Monedas
    for pu in level_data["power_ups"]:
        if pu["type"] == "coin":
            for i in range(pu.get("count", 1)):
                cx = pu["position"]["x"] + i * 50
                cy = pu["position"]["y"]
                coin = Coin(cx, cy)
                all_sprites.add(coin)
                coins_group.add(coin)
        else:
            px = pu["position"]["x"]
            py = pu["position"]["y"]
            power = PowerUp(px, py, pu["type"])
            all_sprites.add(power)
            powerups.add(power)

load_level(current_level_id)

def draw_hud():
    score_text = font.render(f"Score: {score}", True, WHITE)
    coins_text = font.render(f"Coins: {coins}", True, YELLOW)
    lives_text = font.render(f"Lives: {lives}", True, WHITE)
    time_text = font.render(f"Time: {int(time_left)}", True, WHITE)
    level_text = font.render(f"Level {current_level_id}", True, WHITE)

    screen.blit(score_text, (10, 10))
    screen.blit(coins_text, (10, 40))
    screen.blit(lives_text, (10, 70))
    screen.blit(time_text, (WIDTH - 150, 10))
    screen.blit(level_text, (WIDTH // 2 - 50, 10))

def game_over():
    screen.fill(BLACK)
    go_text = font.render("GAME OVER", True, RED)
    screen.blit(go_text, (WIDTH // 2 - 100, HEIGHT // 2))
    pygame.display.flip()
    pygame.time.wait(3000)
    pygame.quit()
    sys.exit()

def level_complete():
    global current_level_id
    screen.fill(BLACK)
    win_text = font.render("Nivel Completado!", True, WHITE)
    screen.blit(win_text, (WIDTH // 2 - 150, HEIGHT // 2))
    pygame.display.flip()
    pygame.time.wait(2000)

    current_level_id += 1
    if current_level_id > 5:
        screen.fill(BLACK)
        final_text = font.render("¡FELICIDADES! Has completado el juego!", True, YELLOW)
        screen.blit(final_text, (WIDTH // 2 - 250, HEIGHT // 2))
        pygame.display.flip()
        pygame.time.wait(5000)
        pygame.quit()
        sys.exit()
    else:
        load_level(current_level_id)
        player.reset_position()

# Bucle principal
running = True
while running:
    dt = clock.tick(FPS) / 1000
    time_left -= dt

    if time_left <= 0:
        player.die()
        time_left = game_data["game"]["settings"]["time_per_level"]

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    all_sprites.update()

    # Colisiones
    # Enemigos
    enemy_hits = pygame.sprite.spritecollide(player, enemies, False)
    for enemy in enemy_hits:
        if player.vel_y > 0 and player.rect.bottom < enemy.rect.centery:  # salto encima
            enemy.kill()
            score += 200
            player.vel_y = JUMP_FORCE // 2
        elif player_state != "invincible":
            player.die()

    # Bolas de fuego vs enemigos
    for fb in fireballs:
        fb_hits = pygame.sprite.spritecollide(fb, enemies, True)
        for hit in fb_hits:
            score += 200
            fb.kill()

    # Monedas
    coin_hits = pygame.sprite.spritecollide(player, coins_group, True)
    for coin in coin_hits:
        coin.collect()

    # Power-ups
    power_hits = pygame.sprite.spritecollide(player, powerups, True)
    for power in power_hits:
        player.get_powerup(power.type)

    # Victoria del nivel
    if player.rect.right >= level_data["flag_position"]["x"]:
        if current_level_id == 5:
            score += 5000  # Derrotar a Bowser (simplificado)
        level_complete()

    # Dibujar
    screen.fill(SKY_BLUE)
    # Fondo simple por tema
    if level_data["theme"] == "underground":
        screen.fill((0, 0, 50))
    elif level_data["theme"] == "castle":
        screen.fill((50, 0, 0))

    # Dibujar sprites con cámara
    for sprite in all_sprites:
        if sprite.rect.right > camera_x and sprite.rect.left < camera_x + WIDTH:
            screen.blit(sprite.image, (sprite.rect.x - camera_x, sprite.rect.y))

    draw_hud()
    pygame.display.flip()

pygame.quit()
