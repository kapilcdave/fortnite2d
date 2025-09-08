import pygame  # Imports the pygame library for game development
import random  # For generating random numbers (used for positions, directions, etc.)
import math    # For mathematical functions (used for angles, distances)

# --- Constants ---
SCREEN_WIDTH = 800      # Width of the game window
SCREEN_HEIGHT = 600     # Height of the game window
FPS = 60                # Frames per second (game speed)

# --- Colors ---
WHITE = (255, 255, 255)     # RGB color for white
BLACK = (0, 0, 0)           # RGB color for black
RED = (255, 0, 0)           # RGB color for red
GREEN = (0, 255, 0)         # RGB color for green
BLUE = (0, 0, 255)          # RGB color for blue
BROWN = (139, 69, 19)       # RGB color for brown (used for wood)
GRAY = (128, 128, 128)      # RGB color for gray
LIGHT_BLUE = (173, 216, 230)# RGB color for light blue (background)
YELLOW = (255, 255, 0)      # RGB color for yellow (ammo)
PURPLE = (128, 0, 128)      # RGB color for purple (storm overlay)

# --- Game Settings ---
PLAYER_SIZE = 40            # Size of the player sprite
PLAYER_SPEED = 5            # Movement speed of the player
PLAYER_HEALTH = 100         # Starting health of the player
BULLET_SIZE = 10            # Size of bullets
BULLET_SPEED = 10           # Speed of bullets
WALL_SIZE = 50              # Size of walls built by player
BUILD_COST = 10             # Wood cost to build a wall
RESOURCE_SIZE = 60          # Size of resource objects
RESOURCE_HEALTH = 50        # Health of resource objects (not used here)
ENEMY_SIZE = 40             # Size of enemy sprites
ENEMY_SPEED = 2             # Movement speed of enemies
ENEMY_HEALTH = 50           # Starting health of enemies
DROPPED_RESOURCE_SIZE = 20  # Size of dropped resource items
PICKUP_RADIUS = 50          # Distance within which player can pick up items
STORM_DAMAGE = 1            # Damage taken per tick outside the storm zone
STORM_DAMAGE_INTERVAL = 1000  # Damage interval in milliseconds (1000 ms = 1 second)

# --- Resource Types ---
WOOD = 'wood'               # String identifier for wood resource
AMMO = 'ammo'               # String identifier for ammo resource

# --- Storm Class ---
class Storm:
    # Handles the shrinking storm zone logic
    def __init__(self):
        self.rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)  # Initial storm covers whole screen
        self.damage = STORM_DAMAGE      # Damage dealt by storm
        self.active = True              # Whether the storm is active
        self.shrink_per_frame_x = SCREEN_WIDTH / (120 * FPS)
        self.shrink_per_frame_y = SCREEN_HEIGHT / (120 * FPS)

    def update(self):
        # Updates storm state and handles shrinking animation
        if not self.active:
            return

        if self.rect.width > 0:
            self.rect.width -= self.shrink_per_frame_x
        else:
            self.rect.width = 0

        if self.rect.height > 0:
            self.rect.height -= self.shrink_per_frame_y
        else:
            self.rect.height = 0

        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        if self.rect.width == 0 and self.rect.height == 0:
            self.active = False

    def draw(self, surface):
        # Draws the storm overlay and border (rectangle)
        if self.active:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((128, 0, 128, 100))  # Semi-transparent purple overlay
            pygame.draw.rect(overlay, (0, 0, 0, 0), self.rect)  # Cut out the safe zone
            surface.blit(overlay, (0, 0))    # Draw overlay on screen
            pygame.draw.rect(surface, PURPLE, self.rect, 2)  # Draw storm border

# --- Player Class ---
class Player(pygame.sprite.Sprite):
    # Handles player movement, shooting, building, picking up items, and taking damage
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([PLAYER_SIZE, PLAYER_SIZE])  # Player sprite
        self.image.fill(BLUE)                                    # Player color
        self.rect = self.image.get_rect()
        self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)  # Start at center
        self.speed_x = 0
        self.speed_y = 0
        self.wood = 50           # Starting wood resource
        self.ammo = 20           # Starting ammo
        self.health = PLAYER_HEALTH  # Starting health

    def update(self):
        # Handles player movement based on key input
        self.speed_x = 0
        self.speed_y = 0
        keystate = pygame.key.get_pressed()
        if keystate[pygame.K_a]:
            self.speed_x = -PLAYER_SPEED   # Move left
        if keystate[pygame.K_d]:
            self.speed_x = PLAYER_SPEED    # Move right
        if keystate[pygame.K_w]:
            self.speed_y = -PLAYER_SPEED   # Move up
        if keystate[pygame.K_s]:
            self.speed_y = PLAYER_SPEED    # Move down

        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

        # Keep player within screen bounds
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
        if self.rect.top < 0:
            self.rect.top = 0

    def shoot(self):
        # Shoots a bullet towards mouse position if player has ammo
        if self.ammo > 0:
            self.ammo -= 1
            mouse_x, mouse_y = pygame.mouse.get_pos()
            angle = math.atan2(mouse_y - self.rect.centery, mouse_x - self.rect.centerx)
            bullet = Bullet(self.rect.centerx, self.rect.centery, angle)
            all_sprites.add(bullet)
            bullets.add(bullet)

    def build_wall(self):
        # Builds a wall at mouse position if player has enough wood
        if self.wood >= BUILD_COST:
            self.wood -= BUILD_COST
            mouse_x, mouse_y = pygame.mouse.get_pos()
            wall = Wall(mouse_x, mouse_y)
            all_sprites.add(wall)
            walls.add(wall)

    def pickup_item(self):
        # Picks up nearby dropped resources (wood or ammo)
        for item in dropped_resources:
            dist = math.hypot(self.rect.centerx - item.rect.centerx, self.rect.centery - item.rect.centery)
            if dist < PICKUP_RADIUS:
                if item.resource_type == WOOD:
                    self.wood += 10
                elif item.resource_type == AMMO:
                    self.ammo += 5
                item.kill()  # Remove item from game

    def take_damage(self, amount):
        # Reduces player health, kills player if health <= 0
        self.health -= amount
        if self.health <= 0:
            self.kill()
            return True
        return False

# --- Enemy Class ---
class Enemy(pygame.sprite.Sprite):
    # Handles enemy movement, wall collision, and taking damage
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([ENEMY_SIZE, ENEMY_SIZE])
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(SCREEN_HEIGHT - self.rect.height)
        self.health = ENEMY_HEALTH
        self.change_direction_time = pygame.time.get_ticks() + random.randrange(1000, 3000)
        self.speed_x = random.choice([-ENEMY_SPEED, ENEMY_SPEED])
        self.speed_y = random.choice([-ENEMY_SPEED, ENEMY_SPEED])

    def update(self):
        # Moves enemy and handles wall collisions
        now = pygame.time.get_ticks()
        if now > self.change_direction_time:
            self.change_direction_time = now + random.randrange(1000, 3000)
            self.speed_x = random.choice([-ENEMY_SPEED, ENEMY_SPEED])
            self.speed_y = random.choice([-ENEMY_SPEED, ENEMY_SPEED])

        self.rect.x += self.speed_x
        hit_walls_x = pygame.sprite.spritecollide(self, walls, False)
        for wall in hit_walls_x:
            if self.speed_x > 0:
                self.rect.right = wall.rect.left
            elif self.speed_x < 0:
                self.rect.left = wall.rect.right
            self.speed_x *= -1

        # Bounce off player (horizontal)
        hit_players_x = pygame.sprite.spritecollide(self, players, False)
        for p in hit_players_x:
            if self.speed_x > 0:
                self.rect.right = p.rect.left
            elif self.speed_x < 0:
                self.rect.left = p.rect.right
            self.speed_x *= -1

        self.rect.y += self.speed_y
        hit_walls_y = pygame.sprite.spritecollide(self, walls, False)
        for wall in hit_walls_y:
            if self.speed_y > 0:
                self.rect.bottom = wall.rect.top
            elif self.speed_y < 0:
                self.rect.top = wall.rect.bottom
            self.speed_y *= -1

        # Bounce off player (vertical)
        hit_players_y = pygame.sprite.spritecollide(self, players, False)
        for p in hit_players_y:
            if self.speed_y > 0:
                self.rect.bottom = p.rect.top
            elif self.speed_y < 0:
                self.rect.top = p.rect.bottom
            self.speed_y *= -1

        # Keep enemy within screen bounds
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.speed_x *= -1
        if self.rect.left < 0:
            self.rect.left = 0
            self.speed_x *= -1
        if self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.speed_y *= -1
        if self.rect.top < 0:
            self.rect.top = 0
            self.speed_y *= -1

    def take_damage(self, amount):
        # Reduces enemy health, kills enemy if health <= 0
        self.health -= amount
        if self.health <= 0:
            self.kill()
            return True
        return False

# --- Bullet Class ---
class Bullet(pygame.sprite.Sprite):
    # Handles bullet movement and removal when off-screen
    def __init__(self, x, y, angle):
        super().__init__()
        self.image = pygame.Surface([BULLET_SIZE, BULLET_SIZE])
        self.image.fill(BLACK)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed_x = math.cos(angle) * BULLET_SPEED
        self.speed_y = math.sin(angle) * BULLET_SPEED

    def update(self):
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y
        # Remove bullet if it goes off-screen
        if self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT or self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()

# --- Wall Class ---
class Wall(pygame.sprite.Sprite):
    # Represents a wall built by the player
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([WALL_SIZE, WALL_SIZE])
        self.image.fill(BROWN)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

# --- Dropped Resource Class ---
class DroppedResource(pygame.sprite.Sprite):
    # Represents a dropped resource (wood or ammo) that can be picked up
    def __init__(self, center, resource_type):
        super().__init__()
        self.resource_type = resource_type
        self.image = pygame.Surface([DROPPED_RESOURCE_SIZE, DROPPED_RESOURCE_SIZE])
        if self.resource_type == WOOD:
            self.image.fill(BROWN)
        elif self.resource_type == AMMO:
            self.image.fill(YELLOW)
        self.rect = self.image.get_rect()
        self.rect.center = center

# --- UI Function ---
def draw_text(surf, text, size, x, y, color):
    # Draws text on the screen at given position
    font = pygame.font.Font(None, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.topleft = (x, y)
    surf.blit(text_surface, text_rect)

# --- Game Initialization ---
pygame.init()  # Initializes pygame modules
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))  # Creates game window
pygame.display.set_caption("2D Fortnite")  # Sets window title
clock = pygame.time.Clock()  # Creates clock for controlling FPS

# --- Sprite Groups ---
all_sprites = pygame.sprite.Group()      # All game sprites
players = pygame.sprite.Group()          # Player sprites
enemies = pygame.sprite.Group()          # Enemy sprites
bullets = pygame.sprite.Group()          # Bullet sprites
walls = pygame.sprite.Group()            # Wall sprites
dropped_resources = pygame.sprite.Group()# Dropped resource sprites

player = Player()            # Create player object
all_sprites.add(player)      # Add player to all sprites
players.add(player)          # Add player to player group

storm = Storm()              # Create storm object

# Spawn initial wood resources
for i in range(10):
    x = random.randrange(SCREEN_WIDTH)
    y = random.randrange(SCREEN_HEIGHT)
    wood = DroppedResource((x, y), WOOD)
    all_sprites.add(wood)
    dropped_resources.add(wood)

# Spawn initial ammo resources
for i in range(5):
    x = random.randrange(SCREEN_WIDTH)
    y = random.randrange(SCREEN_HEIGHT)
    ammo_pack = DroppedResource((x, y), AMMO)
    all_sprites.add(ammo_pack)
    dropped_resources.add(ammo_pack)

# Spawn initial enemies
for i in range(3):
    e = Enemy()
    all_sprites.add(e)
    enemies.add(e)

# --- Game States ---
START_SCREEN = 0
GAME_RUNNING = 1
GAME_OVER = 2

game_state = START_SCREEN

# --- Game Loop ---
running = True
while running:
    clock.tick(FPS)  # Maintain FPS

    if game_state == START_SCREEN:
        screen.fill(LIGHT_BLUE)
        draw_text(screen, "Fortnite 2D", 64, SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 4, BLACK)
        draw_text(screen, "Press ENTER to start", 32, SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2, BLACK)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    game_state = GAME_RUNNING

    elif game_state == GAME_RUNNING:
        for event in pygame.event.get():
            # Handle events (keyboard, mouse, quit)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    player.shoot()        # Left click to shoot
                elif event.button == 3:
                    player.build_wall()   # Right click to build wall
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    player.pickup_item()  # 'E' to pick up items
                elif event.key == pygame.K_q:
                    player.build_wall()   # 'Q' to build wall

        all_sprites.update()  # Update all sprites
        storm.update()        # Update storm

        # Storm damage: if player is outside storm zone (rectangle), take damage
        for p in players:
            if not storm.rect.colliderect(p.rect):
                if p.take_damage(storm.damage):
                    game_state = GAME_OVER


        # Bullet collisions with enemies
        for bullet in bullets:
            hit_enemies = pygame.sprite.spritecollide(bullet, enemies, False)
            for enemy in hit_enemies:
                bullet.kill()
                if enemy.take_damage(10):
                    # Drop ammo when enemy dies
                    drop = DroppedResource(enemy.rect.center, AMMO)
                    all_sprites.add(drop)
                    dropped_resources.add(drop)

        screen.fill(LIGHT_BLUE)       # Fill background
        all_sprites.draw(screen)      # Draw all sprites
        storm.draw(screen)            # Draw storm overlay

        # Draw UI elements (health, wood, ammo, storm zone)
        draw_text(screen, f"Health: {player.health}", 30, 10, 10, BLACK)
        draw_text(screen, f"Wood: {player.wood}", 30, 10, 40, BLACK)
        draw_text(screen, f"Ammo: {player.ammo}", 30, 10, 70, BLACK)

        # Show pickup prompt if player is near a dropped resource
        show_pickup_prompt = False
        for item in dropped_resources:
            dist = math.hypot(player.rect.centerx - item.rect.centerx, player.rect.centery - item.rect.centery)
            if dist < PICKUP_RADIUS:
                show_pickup_prompt = True
                break
        if show_pickup_prompt:
            draw_text(screen, "Press 'E' to pick up", 24, SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 40, WHITE)

        # Show victory message if all enemies are defeated
        if len(enemies) == 0:
            draw_text(screen, "Victory Royale!", 64, SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 32, GREEN)
            game_state = GAME_OVER


        # Show game over message if player is dead (no player sprites alive)
        if len(players) == 0:
            game_state = GAME_OVER

        pygame.display.flip()  # Update display

    elif game_state == GAME_OVER:
        screen.fill(LIGHT_BLUE)
        if len(enemies) == 0:
            draw_text(screen, "Victory Royale!", 64, SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 32, GREEN)
        else:
            draw_text(screen, "Game Over!", 64, SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 32, RED)
        draw_text(screen, "Press ENTER to play again", 32, SCREEN_WIDTH // 2 - 170, SCREEN_HEIGHT // 2 + 50, BLACK)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # Reset game
                    all_sprites.empty()
                    players.empty()
                    enemies.empty()
                    bullets.empty()
                    walls.empty()
                    dropped_resources.empty()

                    player = Player()
                    all_sprites.add(player)
                    players.add(player)

                    storm = Storm()

                    for i in range(10):
                        x = random.randrange(SCREEN_WIDTH)
                        y = random.randrange(SCREEN_HEIGHT)
                        wood = DroppedResource((x, y), WOOD)
                        all_sprites.add(wood)
                        dropped_resources.add(wood)

                    for i in range(5):
                        x = random.randrange(SCREEN_WIDTH)
                        y = random.randrange(SCREEN_HEIGHT)
                        ammo_pack = DroppedResource((x, y), AMMO)
                        all_sprites.add(ammo_pack)
                        dropped_resources.add(ammo_pack)

                    for i in range(3):
                        e = Enemy()
                        all_sprites.add(e)
                        enemies.add(e)

                    game_state = GAME_RUNNING


pygame.quit()  # Quit pygame when game ends
