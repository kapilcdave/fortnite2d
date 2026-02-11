import pygame
import math
import random

# === INITIALIZATION ===
pygame.init()

# Settings
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN_GRASS = (50, 200, 50)
GREEN_DARK = (30, 160, 30)
BLUE_PLAYER = (50, 100, 255)
RED_ENEMY = (255, 60, 60)
BROWN_WOOD = (160, 82, 45)
GRAY_STONE = (128, 128, 128)
YELLOW_BULLET = (255, 255, 0)
PURPLE_STORM = (100, 0, 150)
UI_BG_COLOR = (30, 30, 30, 200)

# Setup Screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Fortnite 2D - Overhaul")
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
        
    def apply_pos(self, pos):
        return (pos[0] + self.camera.x, pos[1] + self.camera.y)

    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)
        
        # Optional: Limit scrolling to map size? (Infinite for now)
        self.camera = pygame.Rect(x, y, self.width, self.height)

# === CLASSES ===

class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, color, size, life):
        super().__init__()
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size//2, size//2), size//2)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(random.uniform(-2, 2), random.uniform(-2, 2))
        self.life = life
        self.original_life = life

    def update(self):
        self.pos += self.vel
        self.rect.center = self.pos
        self.life -= 1
        
        # Fade out
        alpha = int(255 * (self.life / self.original_life))
        self.image.set_alpha(alpha)
        
        if self.life <= 0:
            self.kill()

class Weapon:
    def __init__(self, name, damage, fire_rate, spread, count, color):
        self.name = name
        self.damage = damage
        self.fire_rate = fire_rate # Frames between shots
        self.spread = spread
        self.projectile_count = count
        self.color = color
        self.cooldown = 0
    
    def can_shoot(self):
        return self.cooldown <= 0
        
    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1

class Pistol(Weapon):
    def __init__(self):
        super().__init__("Pistol", 15, 20, 0.05, 1, (200, 200, 200))

class AR(Weapon):
    def __init__(self):
        super().__init__("Assault Rifle", 10, 8, 0.1, 1, (50, 50, 50))

class Shotgun(Weapon):
    def __init__(self):
        super().__init__("Shotgun", 8, 60, 0.4, 5, (100, 0, 0))

class Player(pygame.sprite.Sprite):
    def __init__(self, pos=(0,0)):
        super().__init__()
        self.create_image()
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.speed = 5
        self.health = 100
        self.materials = 50
        self.kills = 0
        
        self.weapons = [Pistol(), AR(), Shotgun()]
        self.current_weapon_index = 0
        self.current_weapon = self.weapons[0]

    def create_image(self):
        # Draw a more complex player: Body + 'Hands' holding weapon
        size = 40
        self.original_image = pygame.Surface((size, size), pygame.SRCALPHA)
        # Body
        pygame.draw.circle(self.original_image, BLUE_PLAYER, (20, 20), 15)
        # Helmet/Head center
        pygame.draw.circle(self.original_image, (30, 80, 220), (20, 20), 10)
        # Hands (visual only, just sticking out)
        pygame.draw.circle(self.original_image, (20, 60, 200), (35, 25), 6)
        pygame.draw.circle(self.original_image, (20, 60, 200), (35, 15), 6)
        
        self.image = self.original_image

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
        
        # Weapon Switching
        if keys[pygame.K_1]: self.switch_weapon(0)
        if keys[pygame.K_2]: self.switch_weapon(1)
        if keys[pygame.K_3]: self.switch_weapon(2)

    def switch_weapon(self, index):
        if 0 <= index < len(self.weapons):
            self.current_weapon_index = index
            self.current_weapon = self.weapons[index]

    def rotate(self, camera_offset):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Adjust mouse pos for camera
        rel_x = mouse_x - (self.rect.centerx + camera_offset[0])
        rel_y = mouse_y - (self.rect.centery + camera_offset[1])
        angle = (180 / math.pi) * -math.atan2(rel_y, rel_x)
        
        self.image = pygame.transform.rotate(self.original_image, int(angle))
        self.rect = self.image.get_rect(center=self.rect.center)
    
    def shoot(self, target_pos, group_bullets, group_all):
        if self.current_weapon.can_shoot():
            self.current_weapon.cooldown = self.current_weapon.fire_rate
            
            # Vector to target
            direction = target_pos - self.pos
            if direction.length() > 0:
                base_dir = direction.normalize()
                
                for _ in range(self.current_weapon.projectile_count):
                    # Apply spread
                    angle = random.uniform(-self.current_weapon.spread, self.current_weapon.spread)
                    rotated_dir = base_dir.rotate_rad(angle)
                    
                    bullet = Bullet(self.rect.center, rotated_dir, self.current_weapon.damage, True, YELLOW_BULLET)
                    group_bullets.add(bullet)
                    group_all.add(bullet)

    def update(self, camera_offset=None):
        self.current_weapon.update()
        self.get_input()
        if camera_offset:
            self.rotate(camera_offset)

class Bot(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        size = 40
        self.original_image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.original_image, RED_ENEMY, (20, 20), 15)
        pygame.draw.circle(self.original_image, (200, 50, 50), (20, 20), 10) # lighter center
        
        self.image = self.original_image
        self.rect = self.image.get_rect()
        
        spawn_range = 1500
        self.pos = pygame.math.Vector2(random.uniform(-spawn_range, spawn_range), random.uniform(-spawn_range, spawn_range))
        self.rect.center = self.pos
        
        self.speed = 3.5
        self.health = 100
        
        # AI State
        self.weapon = AR() # Bots use ARs
        self.state = "WANDER" # WANDER, CHASE, FLEE
        self.target = None
        self.change_dir_timer = 0
        self.wander_dir = pygame.math.Vector2(1, 0)

    def update(self, player_pos, storm_radius):
        self.weapon.update()
        
        dist_to_player = self.pos.distance_to(player_pos)
        dist_to_center = self.pos.length()
        
        # Storm Logic overrides everything
        if dist_to_center > storm_radius * 0.9:
            self.state = "FLEE_STORM"
        elif dist_to_player < 600:
            self.state = "CHASE"
        else:
            self.state = "WANDER"
            
        if self.state == "FLEE_STORM":
            # Move towards center (0,0)
            direction = -self.pos
            if direction.length() > 0:
                self.pos += direction.normalize() * self.speed
                
        elif self.state == "CHASE":
            direction = player_pos - self.pos
            if direction.length() > 0:
                self.pos += direction.normalize() * self.speed
                
            # Shoot
            if self.weapon.can_shoot() and dist_to_player < 500:
                # Random chance to shoot to simulate reaction time
                if random.random() < 0.05:
                     return True # Signal to game to spawn bullet
                
        elif self.state == "WANDER":
            self.change_dir_timer -= 1
            if self.change_dir_timer <= 0:
                self.change_dir_timer = random.randint(60, 200)
                self.wander_dir = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                if self.wander_dir.length() > 0:
                    self.wander_dir = self.wander_dir.normalize()
            
            self.pos += self.wander_dir * (self.speed * 0.5)

        self.rect.center = self.pos
        # Simple rotation towards movement
        # (omitted for bots to keep performance high, they track player in logic anyway)
        return False

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.kill()
            return True # Dead
        return False

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, direction, damage, from_player, color):
        super().__init__()
        self.image = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (5, 5), 4)
        self.rect = self.image.get_rect(center=pos)
        
        self.pos = pygame.math.Vector2(pos)
        self.direction = direction
        self.speed = 20
        self.damage = damage
        self.from_player = from_player
        self.lifetime = 120 

    def update(self):
        self.pos += self.direction * self.speed
        self.rect.center = self.pos
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()

class Wall(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((50, 50))
        self.image.fill(BROWN_WOOD)
        # Add texture/plank lines
        pygame.draw.line(self.image, (100, 50, 20), (0, 10), (50, 10), 2)
        pygame.draw.line(self.image, (100, 50, 20), (0, 25), (50, 25), 2)
        pygame.draw.line(self.image, (100, 50, 20), (0, 40), (50, 40), 2)
        
        self.rect = self.image.get_rect(center=pos)
        self.health = 100
        
    def take_damage(self, amount):
        self.health -= amount
        # Darken to show damage
        damage_tint = 255 - int((self.health / 100) * 255)
        # Note: simplistic re-coloring, real games use overlay
        if self.health <= 0:
            self.kill()

class Tree(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        scale = random.randint(60, 90)
        self.image = pygame.Surface((scale, scale), pygame.SRCALPHA)
        
        # Trunk
        pygame.draw.rect(self.image, (101, 67, 33), (scale//2 - 5, scale//2, 10, scale//2))
        # Leaves (layered circles)
        pygame.draw.circle(self.image, GREEN_DARK, (scale//2, scale//3), scale//3)
        pygame.draw.circle(self.image, (40, 180, 40), (scale//2 + 5, scale//3 - 5), scale//4)
        
        self.rect = self.image.get_rect()
        spawn_range = 1500
        self.pos = (random.uniform(-spawn_range, spawn_range), random.uniform(-spawn_range, spawn_range))
        self.rect.center = self.pos
        self.health = 50
    
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.kill()
            return True # Give wood
        return False

class Rock(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        scale = random.randint(40, 70)
        self.image = pygame.Surface((scale, scale), pygame.SRCALPHA)
        pygame.draw.circle(self.image, GRAY_STONE, (scale//2, scale//2), scale//2)
        # Detail
        pygame.draw.circle(self.image, (100, 100, 100), (scale//3, scale//3), scale//5)
        
        self.rect = self.image.get_rect()
        spawn_range = 1500
        self.pos = (random.uniform(-spawn_range, spawn_range), random.uniform(-spawn_range, spawn_range))
        self.rect.center = self.pos
        self.health = 80
        
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.kill()
            return True # Give stone (just mat count for now)
        return False

class Storm:
    def __init__(self):
        self.radius = 2500
        self.min_radius = 200
        self.shrink_speed = 0.8
        self.center = (0, 0)
        self.damage_timer = 0
        
    def update(self):
        if self.radius > self.min_radius:
            self.radius -= self.shrink_speed
            
    def check_damage(self, player):
        dist = player.pos.length()
        if dist > self.radius:
             self.damage_timer += 1
             if self.damage_timer > 30: # 2 ticks per sec approx
                 player.health -= 2
                 self.damage_timer = 0
                 return True
        return False
        
    def draw(self, surface, camera):
        # Draw huge donut or just the line. Drawing a massive surface is laggy in Pygame.
        # We will draw a clear circle boundary.
        center_screen = camera.apply_pos(self.center)
        pygame.draw.circle(surface, PURPLE_STORM, (int(center_screen[0]), int(center_screen[1])), int(self.radius), 10)

# === MAIN GAME CLASS ===

def main():
    # Groups
    all_sprites = pygame.sprite.Group()
    players_group = pygame.sprite.Group() # Contains single player
    bots_group = pygame.sprite.Group()
    bullets_group = pygame.sprite.Group()
    walls_group = pygame.sprite.Group()
    nature_group = pygame.sprite.Group() # Trees/Rocks
    particles_group = pygame.sprite.Group()
    
    # Objects
    player = Player()
    all_sprites.add(player)
    players_group.add(player)
    
    camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
    storm = Storm()
    
    # Spawn World
    for _ in range(20):
        bot = Bot()
        all_sprites.add(bot)
        bots_group.add(bot)
        
    for _ in range(50):
        tree = Tree()
        all_sprites.add(tree)
        nature_group.add(tree)
        
    for _ in range(30):
        rock = Rock()
        all_sprites.add(rock)
        nature_group.add(rock)
        
    # Fonts
    font_ui = pygame.font.SysFont("Segoe UI", 20, bold=True)
    font_big = pygame.font.SysFont("Arial", 60, bold=True)

    running = True
    game_over = False
    victory = False
    
    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if not game_over:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # Left Click: Shoot / Harvest
                        # Check harvest first (short range)
                        mx, my = pygame.mouse.get_pos()
                        world_pos = pygame.math.Vector2(mx - camera.camera.x, my - camera.camera.y)
                        
                        # Check click on nature
                        clicked_sprites = [s for s in nature_group if s.rect.collidepoint(world_pos)]
                        harvested = False
                        
                        for nature in clicked_sprites:
                            if player.pos.distance_to(nature.pos) < 150: # Range check
                                if nature.take_damage(25):
                                    player.materials += 10
                                    # Particle
                                    for _ in range(5):
                                        p = Particle(nature.rect.center, BROWN_WOOD if isinstance(nature, Tree) else GRAY_STONE, 8, 30)
                                        all_sprites.add(p)
                                        particles_group.add(p)
                                harvested = True
                                
                        if not harvested:
                            player.shoot(world_pos, bullets_group, all_sprites)
                            
                    if event.button == 3: # Right Click: Build
                        if player.materials >= 10:
                            mx, my = pygame.mouse.get_pos()
                            world_x = mx - camera.camera.x
                            world_y = my - camera.camera.y
                            
                            grid_x = round(world_x / 50) * 50
                            grid_y = round(world_y / 50) * 50
                            
                            new_rect = pygame.Rect(0, 0, 50, 50)
                            new_rect.center = (grid_x, grid_y)
                            
                            # Valid placement check
                            collides = False
                            for sprite in all_sprites:
                                if sprite != player and sprite.rect.colliderect(new_rect):
                                    collides = True
                                    break
                            
                            if not collides and not new_rect.colliderect(player.rect):
                                wall = Wall((grid_x, grid_y))
                                walls_group.add(wall)
                                all_sprites.add(wall)
                                player.materials -= 10

        if game_over:
            screen.fill(BLACK)
            txt = "VICTORY ROYALE!" if victory else "ELIMINATED"
            col = (255, 215, 0) if victory else RED_ENEMY
            label = font_big.render(txt, True, col)
            screen.blit(label, (SCREEN_WIDTH//2 - label.get_width()//2, SCREEN_HEIGHT//2 - 50))
            
            sub = font_ui.render("Press R to Restart", True, WHITE)
            screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, SCREEN_HEIGHT//2 + 20))
            
            pygame.display.flip()
            
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                main() # Lazy restart: recursion (careful) or just break to loop. 
                return # Better to structure properly, but this works for simple scripts
                
            clock.tick(FPS)
            continue

        # 2. Update
        player.update(camera.camera.topleft)
        particles_group.update()
        
        # Bot Logic
        for bot in bots_group:
            should_shoot = bot.update(player.pos, storm.radius)
            if should_shoot:
                # Bot shoots at player
                direction = (player.pos - bot.pos).normalize()
                # Bot inaccuracy
                direction = direction.rotate_rad(random.uniform(-0.1, 0.1))
                bullet = Bullet(bot.rect.center, direction, 8, False, (255, 100, 100))
                bullets_group.add(bullet)
                all_sprites.add(bullet)

        camera.update(player)
        storm.update()
        
        # Collisions
        # Bullets hit Walls
        hits = pygame.sprite.groupcollide(bullets_group, walls_group, True, False)
        for bullet, walls in hits.items():
            for wall in walls:
                wall.take_damage(bullet.damage)
                # Particles
                p = Particle(bullet.rect.center, BROWN_WOOD, 5, 20)
                all_sprites.add(p)
                particles_group.add(p)
                
        # Bullets hit Nature (Trees/Rocks) -> Optional: Damage them? Yes
        hits = pygame.sprite.groupcollide(bullets_group, nature_group, True, False)
        for bullet, natures in hits.items():
            for n in natures:
                n.take_damage(bullet.damage)
                
        # Bullets hit Bots
        hits = pygame.sprite.groupcollide(bots_group, bullets_group, False, False)
        for bot, bullets_hit in hits.items():
            for bullet in bullets_hit:
                if bullet.from_player:
                    if bot.take_damage(bullet.damage):
                        player.kills += 1
                    bullet.kill()
                    # Blood particle
                    p = Particle(bot.rect.center, RED_ENEMY, 6, 30)
                    all_sprites.add(p)
                    particles_group.add(p)

        # Bullets hit Player
        hits = pygame.sprite.spritecollide(player, bullets_group, False)
        for bullet in hits:
            if not bullet.from_player:
                player.health -= bullet.damage
                bullet.kill()
                # Blood particle
                p = Particle(player.rect.center, BLUE_PLAYER, 6, 30)
                all_sprites.add(p)
                particles_group.add(p)

        # Storm Damage
        if storm.check_damage(player):
            # Visual feedback?
            pass

        # Game Over Conditions
        if player.health <= 0:
            game_over = True
            victory = False
        
        if len(bots_group) == 0:
            game_over = True
            victory = True

        # 3. Draw
        screen.fill(GREEN_GRASS)
        
        # Draw Background Grid
        cam_x, cam_y = camera.camera.topleft
        grid_size = 100
        start_x = -cam_x % grid_size
        start_y = -cam_y % grid_size
        
        for i in range(0, SCREEN_WIDTH + grid_size, grid_size):
            pygame.draw.line(screen, GREEN_DARK, (start_x + i, 0), (start_x + i, SCREEN_HEIGHT), 1)
        for i in range(0, SCREEN_HEIGHT + grid_size, grid_size):
            pygame.draw.line(screen, GREEN_DARK, (0, start_y + i), (SCREEN_WIDTH, start_y + i), 1)

        # Draw Sprites
        for sprite in walls_group: screen.blit(sprite.image, camera.apply(sprite))
        for sprite in nature_group: screen.blit(sprite.image, camera.apply(sprite))
        for sprite in bots_group: screen.blit(sprite.image, camera.apply(sprite))
        for sprite in players_group: screen.blit(sprite.image, camera.apply(sprite))
        for sprite in bullets_group: screen.blit(sprite.image, camera.apply(sprite))
        for sprite in particles_group: screen.blit(sprite.image, camera.apply(sprite))
        
        storm.draw(screen, camera)
        
        # Draw UI
        # Background Panel
        ui_rect = pygame.Rect(10, 10, 260, 140)
        s = pygame.Surface((ui_rect.width, ui_rect.height), pygame.SRCALPHA)
        s.fill(UI_BG_COLOR)
        screen.blit(s, ui_rect.topleft)
        
        # Health Bar
        pygame.draw.rect(screen, (50, 0, 0), (20, 20, 200, 20))
        hp_width = int(200 * (max(0, player.health) / 100))
        pygame.draw.rect(screen, (0, 255, 0), (20, 20, hp_width, 20))
        hp_txt = font_ui.render(f"HP: {int(player.health)}", True, WHITE)
        screen.blit(hp_txt, (230, 18))
        
        # Materials
        mat_txt = font_ui.render(f"Mats: {player.materials}", True, WHITE)
        screen.blit(mat_txt, (20, 50))
        
        # Weapon
        wpn_txt = font_ui.render(f"Weapon: {player.current_weapon.name}", True, YELLOW_BULLET)
        screen.blit(wpn_txt, (20, 80))
        
        # Kills/Alive
        kill_txt = font_ui.render(f"Kills: {player.kills} | Alive: {len(bots_group)+1}", True, WHITE)
        screen.blit(kill_txt, (20, 110))
        
        # Controls Hint
        hint = font_ui.render("WASD=Move | Click=Shoot | RightClk=Build | 1-3=Weapon", True, (200, 200, 200))
        screen.blit(hint, (10, SCREEN_HEIGHT - 30))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
