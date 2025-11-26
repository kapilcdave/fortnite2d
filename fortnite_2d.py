import pygame
import math
import random
import sys

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
WORLD_SIZE = 2048
TILE_SIZE = 32
FPS = 60

# Colors (rarity)
COLORS = {
    'common': (128, 128, 128), 'uncommon': (0, 255, 0), 'rare': (0, 128, 255),
    'epic': (128, 0, 255), 'legendary': (255, 215, 0)
}
GRASS = (34, 139, 34)
WATER = (0, 100, 200)
TREE = (0, 100, 0)
ROCK = (128, 128, 128)
BUILD_WOOD = (139, 69, 19)

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Fortnite 2D")
clock = pygame.time.Clock()
font = pygame.font.SysFont('arial', 24)
small_font = pygame.font.SysFont('arial', 16)

class Vector2(pygame.math.Vector2):
    pass

class Camera:
    def __init__(self):
        self.pos = Vector2(0, 0)
        self.zoom = 1.0

    def update(self, target):
        self.pos.x = target.x - SCREEN_WIDTH / 2 / self.zoom
        self.pos.y = target.y - SCREEN_HEIGHT / 2 / self.zoom
        self.pos.x = max(0, min(WORLD_SIZE - SCREEN_WIDTH / self.zoom, self.pos.x))
        self.pos.y = max(0, min(WORLD_SIZE - SCREEN_HEIGHT / self.zoom, self.pos.y))

    def world_to_screen(self, world_pos):
        return (world_pos.x - self.pos.x) * self.zoom, (world_pos.y - self.pos.y) * self.zoom

class Entity:
    def __init__(self, pos, size=20):
        self.pos = Vector2(pos)
        self.size = size
        self.rect = pygame.Rect(0, 0, size, size)
        self.vel = Vector2(0, 0)
        self.health = 100
        self.shield = 0
        self.max_health = 100
        self.max_shield = 100
        self.alive = True
        self.inventory = []  # list of items
        self.hotbar = [None] * 5
        self.materials = {'wood': 0, 'brick': 0, 'metal': 0}
        self.kills = 0
        self.fall_dist = 0

    def update_rect(self):
        self.rect.topleft = self.pos.x - self.size // 2, self.pos.y - self.size // 2

    def take_damage(self, dmg):
        if self.shield > 0:
            self.shield = max(0, self.shield - dmg)
            return
        self.health = max(0, self.health - dmg)
        if self.health <= 0:
            self.alive = False

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def shield_up(self, amount):
        self.shield = min(self.max_shield, self.shield + amount)

class Player(Entity):
    def __init__(self, pos):
        super().__init__(pos)
        self.speed = 200
        self.sprint_mult = 1.5
        self.jump_vel = -400
        self.gravity = 980
        self.on_ground = False
        self.crouch = False
        self.size_crouch = 12
        self.build_mode = False
        self.edit_mode = False
        self.selected_slot = 0
        self.reloading = 0
        self.last_shot = 0
        self.angle = 0
        self.parachuting = True
        self.zoom = 1.0

    def update(self, dt, keys, mouse, world, camera, game):
        self.vel.x *= 0.9  # friction

        # Movement
        speed = self.speed * (self.sprint_mult if keys[pygame.K_LSHIFT] else 1.0)
        if self.crouch:
            speed *= 0.5
            self.size = self.size_crouch
        else:
            self.size = 20

        if keys[pygame.K_a]: self.vel.x -= speed * dt
        if keys[pygame.K_d]: self.vel.x += speed * dt
        if keys[pygame.K_w]: self.vel.y -= speed * dt
        if keys[pygame.K_s]: self.vel.y += speed * dt

        # Jump
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel.y = self.jump_vel
            self.on_ground = False

        # Crouch
        self.crouch = keys[pygame.K_c]

        # Gravity & fall
        self.vel.y += self.gravity * dt
        self.pos += self.vel * dt
        self.fall_dist += abs(self.vel.y) * dt

        # Collision with world (simple ground/trees/buildings)
        self.on_ground = False
        if self.pos.y >= WORLD_SIZE - 50:
            self.pos.y = WORLD_SIZE - 50
            self.vel.y = 0
            self.on_ground = True
            if self.fall_dist > 300:
                self.take_damage(math.sqrt(self.fall_dist) * 0.1)
            self.fall_dist = 0

        # Parachute
        if self.parachuting:
            self.vel.y = min(self.vel.y, 100)  # slow fall
            self.gravity = 200
            if self.pos.y >= WORLD_SIZE - 100:
                self.parachuting = False
                self.gravity = 980

        # Inventory switch
        for i in range(5):
            if keys[pygame.K_1 + i]:
                self.selected_slot = i

        # Shoot
        if mouse[0] and pygame.time.get_ticks() - self.last_shot > max(50, 1000 / self.hotbar[self.selected_slot].get('fire_rate', 600) if self.hotbar[self.selected_slot] else 99999):
            self.shoot(mouse_pos=camera.pos + Vector2(mouse) / camera.zoom, world=world, game=game)
            self.last_shot = pygame.time.get_ticks()

        # Reload
        if keys[pygame.K_r] and self.reloading == 0:
            self.reloading = 2000  # 2 sec

        if self.reloading > 0:
            self.reloading -= dt * 1000

        # Build/Edit
        if keys[pygame.K_b]:
            self.build_mode = True
            self.edit_mode = False
        if keys[pygame.K_e]:
            self.edit_mode = True
            self.build_mode = False

        # Grenade throw
        if keys[pygame.K_g] and self.hotbar[4]:
            if self.hotbar[4]['type'] == 'grenade':
                world.projectiles.append(Grenade(self.pos + Vector2(20 * math.cos(self.angle), 20 * math.sin(self.angle)), self.angle, game))
                self.hotbar[4] = None

        # Update rect
        self.update_rect()

    def shoot(self, mouse_pos, world, game):
        weapon = self.hotbar[self.selected_slot]
        if not weapon: return
        angle = math.atan2(mouse_pos.y - self.pos.y, mouse_pos.x - self.pos.x)
        self.angle = angle

        if weapon['type'] == 'shotgun':
            for _ in range(8):
                spread = random.uniform(-0.3, 0.3)
                world.bullets.append(Bullet(self.pos, angle + spread, weapon))
        else:
            world.bullets.append(Bullet(self.pos, angle, weapon))

        weapon['ammo'] -= 1
        if weapon['ammo'] <= 0:
            weapon['ammo'] = weapon['max_ammo']

    def draw(self, screen, camera):
        color = (255, 255, 0)  # player yellow
        s_pos = camera.world_to_screen(self.pos)
        pygame.draw.circle(screen, color, s_pos, self.size // 2)
        if self.parachuting:
            p_pos = (s_pos[0], s_pos[1] - 15)
            pygame.draw.polygon(screen, (255, 255, 255), [(p_pos[0]-15, p_pos[1]), (p_pos[0]+15, p_pos[1]), (p_pos[0], p_pos[1]-20)])

class Bot(Entity):
    def __init__(self, pos, difficulty='easy'):
        super().__init__(pos)
        self.difficulty = difficulty
        self.speed = {'easy': 150, 'medium': 220, 'hard': 280}[difficulty]
        self.ai_state = 'wander'  # wander, chase, build
        self.target = Vector2(random.randint(0, WORLD_SIZE), random.randint(0, WORLD_SIZE))
        self.shoot_timer = 0
        self.build_timer = 0
        self.parachuting = True
        self.last_target_check = 0

    def update(self, dt, player, world, game):
        if not self.alive: return

        self.vel *= 0.9

        dist_to_storm = game.storm.distance_to(self.pos)
        if dist_to_storm > game.storm_radius:
            # Flee storm
            dir_to_center = (game.storm_center - self.pos).normalize()
            self.vel += dir_to_center * self.speed * dt

        # State logic
        if pygame.time.get_ticks() - self.last_target_check > 1000:
            nearest = min((e for e in game.entities if e.alive and e != self), key=lambda e: (e.pos - self.pos).length(), default=None)
            if nearest and (nearest.pos - self.pos).length() < 300:
                self.ai_state = 'chase'
                self.target = nearest.pos
            else:
                self.ai_state = 'wander'
                self.target = Vector2(random.randint(0, WORLD_SIZE), random.randint(0, WORLD_SIZE))
            self.last_target_check = pygame.time.get_ticks()

        if self.ai_state == 'chase' or self.ai_state == 'wander':
            dir = (self.target - self.pos).normalize()
            self.vel += dir * self.speed * dt

            # Shoot if chase and close
            if self.ai_state == 'chase':
                angle = math.atan2(self.target.y - self.pos.y, self.target.x - self.pos.x)
                self.shoot_timer += dt * 1000
                if self.shoot_timer > 800 and self.hotbar and self.hotbar[0]:
                    self.shoot(angle, world, game)
                    self.shoot_timer = 0

        # Build if hard and low health
        if self.difficulty == 'hard' and self.health < 50 and self.build_timer <= 0:
            self.ai_state = 'build'
            self.build_timer = random.uniform(2, 5)

        if self.ai_state == 'build':
            self.build_timer -= dt
            if self.build_timer <= 0:
                self.ai_state = 'wander'
                # Place wall toward threat

        # Gravity/fall/parachute same as player
        self.vel.y += 980 * dt
        self.pos += self.vel * dt
        if self.parachuting:
            self.vel.y = min(self.vel.y, 100)
            if self.pos.y >= WORLD_SIZE - 100:
                self.parachuting = False
        if self.pos.y >= WORLD_SIZE - 50:
            self.pos.y = WORLD_SIZE - 50
            self.vel.y = 0
            self.fall_dist = 0
        self.pos.x = max(self.size//2, min(WORLD_SIZE - self.size//2, self.pos.x))
        self.pos.y = max(self.size//2, min(WORLD_SIZE - self.size//2, self.pos.y))

        self.update_rect()

    def shoot(self, angle, world, game):
        weapon = self.hotbar[0] if self.hotbar else None
        if weapon:
            world.bullets.append(Bullet(self.pos, angle, weapon))
            weapon['ammo'] -= 1

    def draw(self, screen, camera):
        color = {'easy': (100,100,255), 'medium': (255,100,100), 'hard': (255,0,0)}[self.difficulty]
        s_pos = camera.world_to_screen(self.pos)
        pygame.draw.circle(screen, color, s_pos, self.size // 2)

class Bullet:
    def __init__(self, pos, angle, weapon):
        self.pos = Vector2(pos)
        self.vel = Vector2(math.cos(angle), math.sin(angle)) * weapon.get('bullet_speed', 800)
        self.weapon = weapon
        self.life = 3.0  # sec
        self.gravity = weapon.get('gravity', 0)
        self.damage = weapon['damage']
        self.range_max = weapon['range']

    def update(self, dt, world):
        self.vel.y += self.gravity * dt
        self.pos += self.vel * dt
        self.life -= dt
        dist_trav = self.pos.length()  # approx
        if dist_trav > self.range_max or self.life <= 0 or not (0 <= self.pos.x <= WORLD_SIZE and 0 <= self.pos.y <= WORLD_SIZE):
            return False
        return True

    def draw(self, screen, camera):
        s_pos = camera.world_to_screen(self.pos)
        color = COLORS[self.weapon['rarity']]
        pygame.draw.circle(screen, color, s_pos, 3)

class Grenade:
    def __init__(self, pos, angle, game):
        self.pos = Vector2(pos)
        self.vel = Vector2(math.cos(angle), math.sin(angle)) * 400 + Vector2(0, -100)
        self.life = 3.0
        self.gravity = 980
        self.radius = 0
        self.game = game

    def update(self, dt):
        self.vel.y += self.gravity * dt
        self.pos += self.vel * dt
        self.life -= dt
        if self.life <= 0:
            self.explode()
            return False
        if self.pos.y > WORLD_SIZE:
            return False
        return True

    def explode(self):
        for entity in self.game.entities:
            if entity.alive and (entity.pos - self.pos).length() < 80:
                entity.take_damage(80)
        # Damage structures too

    def draw(self, screen, camera):
        s_pos = camera.world_to_screen(self.pos)
        pygame.draw.circle(screen, (200, 200, 0), s_pos, 8)

class Structure:
    def __init__(self, grid_pos, type='wall', material='wood'):
        self.grid_pos = Vector2(grid_pos)
        self.pos = self.grid_pos * TILE_SIZE + Vector2(TILE_SIZE/2)
        self.type = type  # wall, floor, ramp, roof
        self.material = material
        self.hp = {'wood': 100, 'brick': 150, 'metal': 200}[material]
        self.max_hp = self.hp
        self.edited = False  # for holes etc.

    def draw(self, screen, camera):
        s_pos = camera.world_to_screen(self.pos)
        color = {'wood': BUILD_WOOD, 'brick': (165, 42, 42), 'metal': (169, 169, 169)}[self.material]
        size = TILE_SIZE / 2
        if self.type == 'wall':
            pygame.draw.rect(screen, color, (s_pos[0]-size/2, s_pos[1]-size, size, size*2))
        elif self.type == 'floor':
            pygame.draw.rect(screen, color, (s_pos[0]-size/2, s_pos[1]-size/2, size, size))
        # etc for ramp/roof

class Item:
    def __init__(self, pos, item_data):
        self.pos = Vector2(pos)
        self.data = item_data.copy()  # {'type': 'ar', 'rarity': 'rare', ...}
        self.size = 12

    def draw(self, screen, camera):
        s_pos = camera.world_to_screen(self.pos)
        color = COLORS[self.data['rarity']]
        pygame.draw.rect(screen, color, (s_pos[0]-self.size/2, s_pos[1]-self.size/2, self.size, self.size))

class World:
    def __init__(self, game):
        self.game = game
        self.tiles = [[0 for _ in range(WORLD_SIZE//TILE_SIZE)] for _ in range(WORLD_SIZE//TILE_SIZE)]  # 0 grass, 1 water, 2 tree, 3 rock
        self.generate_map()
        self.items = []
        self.chests = []
        self.structures = []
        self.resources = []  # trees/rocks
        self.projectiles = []  # grenades etc.
        self.bullets = []
        self.supply_drop_timer = random.randint(30, 60) * FPS

    def generate_map(self):
        # Procedural: perlin-like noise for terrain
        for x in range(0, WORLD_SIZE, TILE_SIZE):
            for y in range(0, WORLD_SIZE, TILE_SIZE):
                gx, gy = x//TILE_SIZE, y//TILE_SIZE
                noise = (math.sin(gx*0.1) + math.cos(gy*0.1)) * 0.5 + 0.5
                if noise < 0.1:
                    self.tiles[gx][gy] = 1  # water
                elif random.random() < 0.05:
                    self.tiles[gx][gy] = 2  # tree
                    self.resources.append((Vector2(x + TILE_SIZE/2, y + TILE_SIZE/2), 'tree'))
                elif random.random() < 0.03:
                    self.tiles[gx][gy] = 3  # rock
                    self.resources.append((Vector2(x + TILE_SIZE/2, y + TILE_SIZE/2), 'rock'))

        # POIs: 10 buildings
        for _ in range(10):
            px = random.randint(200, WORLD_SIZE-400)
            py = random.randint(200, WORLD_SIZE-400)
            for dx in range(-3,4):
                for dy in range(-3,4):
                    if abs(dx)+abs(dy) < 6:
                        self.tiles[int((px+dx*TILE_SIZE)/TILE_SIZE)][int((py+dy*TILE_SIZE)/TILE_SIZE)] = 4  # building floor

        # Spawn loot
        self.spawn_loot(50)
        self.spawn_chests(20)

    def spawn_loot(self, count):
        for _ in range(count):
            pos = Vector2(random.randint(100, WORLD_SIZE-100), random.randint(100, WORLD_SIZE-100))
            rarity = random.choice(list(COLORS.keys()))
            types = ['pistol', 'smg', 'ar', 'shotgun', 'sniper', 'medkit', 'shield', 'grenade']
            item_type = random.choice(types)
            data = self.generate_item(item_type, rarity)
            self.items.append(Item(pos, data))

    def spawn_chests(self, count):
        for _ in range(count):
            pos = Vector2(random.randint(100, WORLD_SIZE-100), random.randint(100, WORLD_SIZE-100))
            self.chests.append({'pos': pos, 'open': False, 'loot': []})

    def generate_item(self, itype, rarity):
        base = {
            'pistol': {'type': 'pistol', 'damage': 25, 'range': 300, 'bullet_speed': 600, 'fire_rate': 400, 'ammo': 12, 'max_ammo': 12, 'gravity': 0},
            'smg': {'type': 'smg', 'damage': 18, 'range': 400, 'bullet_speed': 700, 'fire_rate': 800, 'ammo': 30, 'max_ammo': 30, 'gravity': 100},
            'ar': {'type': 'ar', 'damage': 30, 'range': 600, 'bullet_speed': 900, 'fire_rate': 600, 'ammo': 30, 'max_ammo': 30, 'gravity': 200},
            'shotgun': {'type': 'shotgun', 'damage': 70, 'range': 150, 'bullet_speed': 500, 'fire_rate': 1000, 'ammo': 8, 'max_ammo': 8, 'gravity': 0},
            'sniper': {'type': 'sniper', 'damage': 90, 'range': 1000, 'bullet_speed': 1200, 'fire_rate': 1200, 'ammo': 7, 'max_ammo': 7, 'gravity': 400},
            'medkit': {'type': 'medkit', 'heal': 100},
            'shield': {'type': 'shield_small', 'shield': 25},
            'grenade': {'type': 'grenade'}
        }
        data = base[itype].copy()
        data['rarity'] = rarity
        mult = {'common': 1.0, 'uncommon': 1.1, 'rare': 1.3, 'epic': 1.5, 'legendary': 2.0}[rarity]
        if 'damage' in data: data['damage'] *= mult
        if 'heal' in data: data['heal'] *= mult
        if 'shield' in data: data['shield'] *= mult
        data['ammo'] = data['max_ammo']
        return data

    def update(self, dt, player):
        # Bullets
        self.bullets = [b for b in self.bullets if b.update(dt, self)]

        # Hit detection
        for b in self.bullets[:]:
            for e in self.game.entities:
                if e.alive and e.rect.collidepoint(b.pos):
                    # Falloff
                    dist = (b.pos - e.pos).length()  # approx
                    falloff_dmg = b.damage * max(0, 1 - dist / b.weapon['range'] * 0.5)
                    e.take_damage(falloff_dmg)
                    b.life = 0
                    if not e.alive:
                        for other in self.game.entities:
                            if other.alive and other != e:
                                other.kills += 1
                    break

        # Projectiles (grenades)
        self.projectiles = [p for p in self.projectiles if p.update(dt)]

        # Pickup
        for item in self.items[:]:
            if player.rect.collidepoint(item.pos):
                self.add_to_inventory(player, item.data)
                self.items.remove(item)

        # Chest loot
        for chest in self.chests:
            if player.rect.collidepoint(chest['pos']) and not chest['open']:
                chest['open'] = True
                for _ in range(3):
                    data = self.generate_item(random.choice(['ar', 'shotgun', 'medkit', 'shield']), random.choice(['rare', 'epic']))
                    self.items.append(Item(chest['pos'] + Vector2(random.randint(-20,20), random.randint(-20,20)), data))

        # Supply drop
        self.supply_drop_timer -= 1
        if self.supply_drop_timer <= 0:
            # Plane drop
            drop_pos = Vector2(random.randint(500, WORLD_SIZE-500), random.randint(100, 300))
            chest = {'pos': drop_pos, 'open': False, 'loot': []}
            for _ in range(4):
                data = self.generate_item(random.choice(['sniper', 'ar']), 'legendary')
                chest['loot'].append(data)
            self.chests.append(chest)
            self.supply_drop_timer = random.randint(60, 120) * FPS

        # Harvest
        mouse_pos = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:  # LMB harvest
            wp = camera.pos + Vector2(mouse_pos) / camera.zoom
            for res in self.resources[:]:
                r_pos, r_type = res
                if (r_pos - wp).length() < 50:
                    amt = {'tree': ('wood', 50), 'rock': ('brick', 75)}[r_type]
                    player.materials[amt[0]] += amt[1]
                    self.resources.remove(res)
                    break

    def add_to_inventory(self, entity, data):
        # Simple: add to hotbar if weapon/consumable
        if data['type'] in ['pistol', 'smg', 'ar', 'shotgun', 'sniper', 'grenade']:
            for slot in range(5):
                if entity.hotbar[slot] is None:
                    entity.hotbar[slot] = data
                    return
        elif data['type'] == 'medkit':
            entity.heal(data['heal'])
        elif 'shield' in data['type']:
            entity.shield_up(data['shield'])
        # Drop if full

    def draw(self, screen, camera):
        # Tiles
        start_tile_x = int(camera.pos.x / TILE_SIZE)
        end_tile_x = start_tile_x + int(SCREEN_WIDTH / TILE_SIZE / camera.zoom) + 2
        start_tile_y = int(camera.pos.y / TILE_SIZE)
        end_tile_y = start_tile_y + int(SCREEN_HEIGHT / TILE_SIZE / camera.zoom) + 2

        for tx in range(max(0, start_tile_x), min(len(self.tiles), end_tile_x)):
            for ty in range(max(0, start_tile_y), min(len(self.tiles[0]), end_tile_y)):
                pos = Vector2(tx * TILE_SIZE, ty * TILE_SIZE)
                s_pos = camera.world_to_screen(pos)
                tile = self.tiles[tx][ty]
                color = {0: GRASS, 1: WATER, 2: TREE, 3: ROCK}.get(tile, GRASS)
                pygame.draw.rect(screen, color, (s_pos[0], s_pos[1], TILE_SIZE * camera.zoom, TILE_SIZE * camera.zoom))

        # Items
        for item in self.items:
            item.draw(screen, camera)

        # Chests
        for chest in self.chests:
            s_pos = camera.world_to_screen(chest['pos'])
            pygame.draw.rect(screen, (255, 215, 0), (s_pos[0]-16, s_pos[1]-16, 32, 32))
            if chest['open']:
                pygame.draw.line(screen, (255,0,0), s_pos, (s_pos[0]+20, s_pos[1]+20), 3)

        # Structures
        for struct in self.structures:
            struct.draw(screen, camera)

        # Resources
        for res in self.resources:
            r_pos, _ = res
            s_pos = camera.world_to_screen(r_pos)
            pygame.draw.circle(screen, TREE if 'tree' in res[1] else ROCK, s_pos, 16 * camera.zoom)

class Storm:
    def __init__(self):
        self.center = Vector2(WORLD_SIZE/2, WORLD_SIZE/2) + Vector2(random.randint(-200,200), random.randint(-200,200))
        self.radius = WORLD_SIZE * 0.8
        self.max_radius = self.radius
        self.shrink_speed = [50, 80, 120, 160, 200]  # phases
        self.phase = 0
        self.damage = 5

    def update(self, dt):
        if self.phase < 5:
            shrink = self.shrink_speed[self.phase] * dt
            self.radius -= shrink
            if self.radius < self.max_radius * (5 - self.phase)/5:
                self.phase += 1
                self.damage += 5

    def is_inside(self, pos):
        return (pos - self.center).length() < self.radius

    def distance_to(self, pos):
        return max(0, (pos - self.center).length() - self.radius)

    def draw(self, screen, camera):
        # Outer circle
        s_center = camera.world_to_screen(self.center)
        if self.radius > 0:
            pygame.draw.circle(screen, (255, 0, 0, 100), s_center, self.radius * camera.zoom, 4)
            # Gradient damage zone
            for r in range(int(self.radius * camera.zoom), 0, -20):
                alpha = 255 * (1 - r / (self.radius * camera.zoom))
                surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 0, 0, int(alpha * 0.3)), (r, r), r)
                screen.blit(surf, (s_center[0] - r, s_center[1] - r), special_flags=pygame.BLEND_RGBA_ADD)

class Game:
    def __init__(self):
        self.player = None
        self.entities = []
        self.bots_alive = 0
        self.world = None
        self.storm = None
        self.camera = Camera()
        self.running = True
        self.victory = False
        self.reset()

    def reset(self):
        self.player = Player((200, 100))
        self.entities = [self.player]
        num_bots = 99
        diffs = ['easy']*70 + ['medium']*20 + ['hard']*9
        random.shuffle(diffs)
        for i, diff in enumerate(diffs):
            self.entities.append(Bot((250 + i*10, 100), diff))
        self.bots_alive = num_bots
        self.world = World(self)
        self.storm = Storm()
        self.camera = Camera()
        self.victory = False

    def update(self, dt):
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        mx, my = pygame.mouse.get_pos()

        if not self.victory:
            self.player.update(dt, keys, mouse, self.world, self.camera, self)

            for bot in self.entities[1:]:
                if bot.alive:
                    bot.update(dt, self.player, self.world, self)

            self.world.update(dt, self.player)

            # Storm damage
            for entity in self.entities:
                if entity.alive and not self.storm.is_inside(entity.pos):
                    entity.take_damage(self.storm.damage * dt * 10)

            self.storm.update(dt)

            # Check alive
            alive_count = sum(1 for e in self.entities if e.alive)
            if alive_count == 1 and self.player.alive:
                self.victory = True

            # Update camera
            self.camera.update(self.player.pos)

        # Check restart
        if keys[pygame.K_r] and self.victory:
            self.reset()

    def draw_ui(self, screen):
        # Health/Shield
        bar_w = 200
        h = 20
        hx = 10
        sy = 10
        hy = sy + 30
        pygame.draw.rect(screen, (0,255,0), (hx, hy, (self.player.health / self.player.max_health) * bar_w, h))
        pygame.draw.rect(screen, (0,0,255), (hx, sy, (self.player.shield / self.player.max_shield) * bar_w, h))
        pygame.draw.rect(screen, (255,255,255), (hx, sy, bar_w, h), 2)

        # Kills
        kills_text = font.render(f"Kills: {self.player.kills}", True, (255,255,255))
        screen.blit(kills_text, (hx, hy + 40))

        # Hotbar
        for i, item in enumerate(self.player.hotbar):
            x = SCREEN_WIDTH / 2 - 100 + i * 45
            pygame.draw.rect(screen, (50,50,50), (x, SCREEN_HEIGHT - 60, 40, 40), 2)
            if item:
                color = COLORS[item['rarity']]
                pygame.draw.rect(screen, color, (x+4, SCREEN_HEIGHT - 56, 32, 32))
                ammo = font.render(str(item['ammo']), True, (255,255,255))
                screen.blit(ammo, (x+25, SCREEN_HEIGHT - 45))

        # Minimap
        map_scale = 0.1
        mx = SCREEN_WIDTH - 220
        my = 10
        pygame.draw.rect(screen, GRASS, (mx, my, 200*map_scale, 200*map_scale))
        p_s = ((self.player.pos / WORLD_SIZE) * 200 * map_scale)
        pygame.draw.circle(screen, (255,255,0), (mx + p_s.x, my + p_s.y), 3)
        s_r = (self.storm.radius / WORLD_SIZE) * 200 * map_scale
        pygame.draw.circle(screen, (255,0,0), (mx + (self.storm.center.x / WORLD_SIZE)*200*map_scale, my + (self.storm.center.y / WORLD_SIZE)*200*map_scale), s_r, 2)

        if self.victory:
            vic_text = font.render("VICTORY ROYALE!", True, (0,255,0))
            screen.blit(vic_text, (SCREEN_WIDTH/2 - 100, SCREEN_HEIGHT/2))
            restart_text = small_font.render("Press R to play again", True, (255,255,255))
            screen.blit(restart_text, (SCREEN_WIDTH/2 - 80, SCREEN_HEIGHT/2 + 40))

        # Build/Edit indicator
        if self.player.build_mode:
            pygame.draw.rect(screen, (0,255,0), (10, SCREEN_HEIGHT - 100, 150, 30))
            screen.blit(small_font.render("BUILD MODE (B)", True, (0,0,0)), (15, SCREEN_HEIGHT - 97))
        if self.player.edit_mode:
            pygame.draw.rect(screen, (255,255,0), (10, SCREEN_HEIGHT - 70, 150, 30))
            screen.blit(small_font.render("EDIT MODE (E)", True, (0,0,0)), (15, SCREEN_HEIGHT - 67))

    def draw(self, screen):
        screen.fill((135, 206, 235))  # sky
        self.world.draw(screen, self.camera)
        for proj in self.world.projectiles:
            proj.draw(screen, self.camera)
        for bullet in self.world.bullets:
            bullet.draw(screen, self.camera)
        self.storm.draw(screen, self.camera)
        for entity in self.entities:
            if entity.alive:
                entity.draw(screen, self.camera)
        self.draw_ui(screen)

    def run(self):
        while self.running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                if event.type == pygame.MOUSEWHEEL:
                    self.camera.zoom += event.y * 0.1
                    self.camera.zoom = max(0.5, min(2.0, self.camera.zoom))

            self.update(dt)
            self.draw(screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()