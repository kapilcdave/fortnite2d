import pygame
import math
import random

# === INITIALIZATION ===
pygame.init()

# Settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (34, 139, 34)      # Grass
BLUE = (0, 0, 255)         # Player
RED = (255, 0, 0)          # Bot/Enemy
BROWN = (139, 69, 19)      # Wood/Wall
YELLOW = (255, 255, 0)     # Bullet
PURPLE = (128, 0, 128)     # Storm
GRAY = (128, 128, 128)     # UI BG

# Setup Screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Fortnite 2D - Pygame Edition")
clock = pygame.time.Clock()

# Camera
class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)
        self.camera = pygame.Rect(x, y, self.width, self.height)

# === CLASSES ===

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(self.original_image, BLUE, (15, 15), 15)
        # Add a "gun" pointer
        pygame.draw.rect(self.original_image, BLACK, (25, 12, 10, 6))
        
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(0, 0))
        
        self.pos = pygame.math.Vector2(0, 0)
        self.speed = 5
        self.health = 100
        self.materials = 50
        self.kills = 0
        
    def get_input(self):
        keys = pygame.key.get_pressed()
        move = pygame.math.Vector2(0, 0)
        
        if keys[pygame.K_w]: move.y = -1
        if keys[pygame.K_s]: move.y = 1
        if keys[pygame.K_a]: move.x = -1
        if keys[pygame.K_d]: move.x = 1
        
        if move.length() > 0:
            move = move.normalize() * self.speed
            self.pos += move
            
        self.rect.center = self.pos

    def rotate(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Adjust mouse pos for camera
        rel_x, rel_y = mouse_x - (self.rect.centerx + camera.camera.x), mouse_y - (self.rect.centery + camera.camera.y)
        angle = (180 / math.pi) * -math.atan2(rel_y, rel_x)
        
        self.image = pygame.transform.rotate(self.original_image, int(angle))
        self.rect = self.image.get_rect(center=self.rect.center)

    def update(self):
        self.get_input()
        self.rotate()

class Bot(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(self.image, RED, (15, 15), 15)
        self.rect = self.image.get_rect()
        
        # Spawn random position
        spawn_range = 1000
        self.pos = pygame.math.Vector2(random.uniform(-spawn_range, spawn_range), random.uniform(-spawn_range, spawn_range))
        self.rect.center = self.pos
        
        self.speed = 3
        self.health = 100
        self.shoot_timer = 0
        self.change_dir_timer = 0
        self.wander_dir = pygame.math.Vector2(0, 0)

    def update(self):
        # Calculate distance to player
        dist_vec = player.pos - self.pos
        dist = dist_vec.length()
        
        if dist < 400: # Aggro range
            if dist > 0:
                direction = dist_vec.normalize()
                self.pos += direction * self.speed
                
                # Shoot
                self.shoot_timer += 1
                if self.shoot_timer > 60: # Fire every sec
                    self.shoot_timer = 0
                    bullet = Bullet(self.rect.center, direction, False)
                    all_sprites.add(bullet)
                    bullets.add(bullet)
        else:
            # Wander / Stay in safe zone
            if storm:
                 # Move towards center if far
                 if self.pos.length() > storm.radius * 0.8:
                     dir_to_center = -self.pos
                     if dir_to_center.length() > 0:
                        self.pos += dir_to_center.normalize() * self.speed
                 else:
                     # Random wander
                     self.change_dir_timer -= 1
                     if self.change_dir_timer <= 0:
                         self.change_dir_timer = random.randint(60, 180)
                         self.wander_dir = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
                     self.pos += self.wander_dir * (self.speed * 0.5)

        self.rect.center = self.pos
        
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            player.kills += 1
            self.kill()

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, direction, from_player):
        super().__init__()
        self.image = pygame.Surface((8, 8))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=pos)
        
        self.pos = pygame.math.Vector2(pos)
        self.direction = direction
        self.speed = 15
        self.from_player = from_player
        self.lifetime = 100 # Frames

    def update(self):
        self.pos += self.direction * self.speed
        self.rect.center = self.pos
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
            
        # Wall Collision
        hits = pygame.sprite.spritecollide(self, walls, False)
        for wall in hits:
            wall.take_damage(25)
            self.kill()
            return

        # Entity Collision
        if self.from_player:
            hits = pygame.sprite.spritecollide(self, bots, False)
            for bot in hits:
                bot.take_damage(25)
                self.kill()
                return
        else:
            if self.rect.colliderect(player.rect):
                player.health -= 10
                self.kill()
                return

class Wall(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((40, 40))
        self.image.fill(BROWN)
        self.rect = self.image.get_rect(center=pos)
        self.health = 100
        
    def take_damage(self, amount):
        self.health -= amount
        # Darken color based on health
        color_val = max(50, int(139 * (self.health / 100)))
        self.image.fill((color_val, 69 // 2 if color_val < 100 else 69, 19 // 2 if color_val < 100 else 19))
        
        if self.health <= 0:
            self.kill()

class Storm:
    def __init__(self):
        self.radius = 2000
        self.min_radius = 200
        self.shrink_speed = 0.5
        self.damage = 1
        self.center = (0, 0)
        
    def update(self):
        if self.radius > self.min_radius:
            self.radius -= self.shrink_speed
            
        # Check player damage
        dist = player.pos.length()
        if dist > self.radius:
             if pygame.time.get_ticks() % 60 == 0: # Approx 1 dmg per sec logic handled via frame check? No, let's use a simpler timer.
                 pass
             player.health -= 0.05 # Drain health slowly
             
    def draw(self, surface, camera):
        # Draw huge circle (inverse is hard in simple pygame without masks, so let's draw the 'safe zone' outline)
        # Just drawing the circle border
        center_screen = camera.apply_rect(pygame.Rect(self.center[0], self.center[1], 0, 0)).center
        pygame.draw.circle(surface, PURPLE, center_screen, int(self.radius), 5)
        
        # If outside, draw full screen red tint maybe? 
        # For now, just the line is enough indicator.

# === SETUP ===
all_sprites = pygame.sprite.Group()
walls = pygame.sprite.Group()
bots = pygame.sprite.Group()
bullets = pygame.sprite.Group()

player = Player()
all_sprites.add(player)

for _ in range(10):
    bot = Bot()
    all_sprites.add(bot)
    bots.add(bot)

camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
storm = Storm()

font = pygame.font.SysFont("Arial", 24)
big_font = pygame.font.SysFont("Arial", 64)

running = True
game_over = False

# === MAIN LOOP ===
while running:
    # 1. Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.MOUSEBUTTONDOWN and not game_over:
            if event.button == 1: # Left Click: Shoot
                mx, my = pygame.mouse.get_pos()
                # Calculate direction from player center to mouse (world space logic handled inside rotate/update usually, 
                # but let's recalculate for bullet launch)
                
                # We need true mouse pos in world
                rel_x = mx - (player.rect.centerx + camera.camera.x)
                rel_y = my - (player.rect.centery + camera.camera.y)
                direction = pygame.math.Vector2(rel_x, rel_y).normalize()
                
                bullet = Bullet(player.rect.center, direction, True)
                all_sprites.add(bullet)
                bullets.add(bullet)
                
            if event.button == 3: # Right Click: Build
                if player.materials >= 10:
                    mx, my = pygame.mouse.get_pos()
                    # Snap to grid somewhat
                    world_x = mx - camera.camera.x
                    world_y = my - camera.camera.y
                    
                    grid_x = round(world_x / 40) * 40
                    grid_y = round(world_y / 40) * 40
                    
                    # Check overlap with player
                    build_rect = pygame.Rect(0, 0, 40, 40)
                    build_rect.center = (grid_x, grid_y)
                    
                    if not build_rect.colliderect(player.rect):
                        wall = Wall((grid_x, grid_y))
                        walls.add(wall)
                        all_sprites.add(wall)
                        player.materials -= 10

    if game_over:
        screen.fill(BLACK)
        text = big_font.render(game_over_text, True, RED if "ELIMINATED" in game_over_text else (255, 215, 0))
        screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2))
        pygame.display.flip()
        continue

    # 2. Update
    all_sprites.update()
    camera.update(player)
    storm.update()
    
    # Check Game Over
    if player.health <= 0:
        game_over = True
        game_over_text = "ELIMINATED"
        
    if len(bots) == 0:
        game_over = True
        game_over_text = "VICTORY ROYALE"

    # 3. Draw
    screen.fill(GREEN)
    
    # Grid lines for "floor" effect
    cam_x, cam_y = camera.camera.topleft
    grid_size = 100
    start_x = -cam_x % grid_size
    start_y = -cam_y % grid_size
    
    for i in range(0, SCREEN_WIDTH + grid_size, grid_size):
        pygame.draw.line(screen, (30, 130, 30), (start_x + i, 0), (start_x + i, SCREEN_HEIGHT))
    for i in range(0, SCREEN_HEIGHT + grid_size, grid_size):
        pygame.draw.line(screen, (30, 130, 30), (0, start_y + i), (SCREEN_WIDTH, start_y + i))

    # Draw all sprites with camera offset
    for sprite in all_sprites:
        screen.blit(sprite.image, camera.apply(sprite))
        
    # Draw Storm
    storm.draw(screen, camera)
    
    # Draw UI
    pygame.draw.rect(screen, GRAY, (10, 10, 200, 100))
    hp_text = font.render(f"HP: {int(player.health)}", True, RED)
    mat_text = font.render(f"Materials: {player.materials}", True, BROWN)
    kill_text = font.render(f"Kills: {player.kills}", True, BLACK)
    alive_text = font.render(f"Alive: {len(bots)+1}", True, BLUE)
    
    screen.blit(hp_text, (20, 20))
    screen.blit(mat_text, (20, 50))
    screen.blit(kill_text, (20, 80))
    screen.blit(alive_text, (SCREEN_WIDTH - 150, 20))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
