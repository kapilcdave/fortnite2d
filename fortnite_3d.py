"""
FORTNITE 3D - SIMPLIFIED BATTLE ROYALE
Clean, fun, easy-to-see 3D battle royale game!

Controls:
    WASD - Move
    Mouse - Look
    Space - Jump
    Shift - Sprint
    LClick - Shoot
    RClick - Build
    E - Pickup
    1-5 - Switch weapons
    Q/F/C - Wall/Floor/Ramp
    Z/X/B - Wood/Brick/Metalw
"""
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math

# === SETTINGS ===
MAP_SIZE = 80
BOT_COUNT = 15
BUILD_SIZE = 2

# Simple weapon data [damage, fire_rate, mag, ammo_type]
WEAPONS = {
    'AR': [30, 0.15, 30, 'medium'],
    'Shotgun': [80, 0.8, 8, 'shells'],
    'SMG': [18, 0.08, 35, 'light'],
    'Sniper': [120, 1.5, 5, 'heavy'],
    'Pistol': [25, 0.2, 16, 'light'],
}

RARITY_COLORS = {
    'common': color.gray,
    'rare': color.blue,
    'epic': color.violet,
    'legendary': color.orange
}

# === PLAYER ===
class Player(FirstPersonController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.health = 100
        self.shield = 0
        self.alive = True
        
        self.weapons = {0: ('AR', 'common')}
        self.current_slot = 0
        self.ammo = {'light': 200, 'medium': 150, 'heavy': 30, 'shells': 40}
        self.last_shot = 0
        
        self.materials = {'wood': 100, 'brick': 50, 'metal': 50}
        self.current_material = 'wood'
        self.current_structure = 'wall'
        
        self.kills = 0
        self.speed = 5
        
    def update(self):
        super().update()
        self.speed = 7 if held_keys['shift'] else 5
        self.x = clamp(self.x, -MAP_SIZE//2, MAP_SIZE//2)
        self.z = clamp(self.z, -MAP_SIZE//2, MAP_SIZE//2)
    
    def take_damage(self, dmg):
        if self.shield > 0:
            if self.shield >= dmg:
                self.shield -= dmg
            else:
                dmg -= self.shield
                self.shield = 0
                self.health -= dmg
        else:
            self.health -= dmg
        
        if self.health <= 0:
            self.die()
    
    def die(self):
        self.alive = False
        self.position = (0, -50, 0)
    
    def shoot(self):
        weapon = self.weapons.get(self.current_slot)
        if not weapon:
            return
        
        name, rarity = weapon
        if name not in WEAPONS:
            return
        
        damage, fire_rate, mag, ammo_type = WEAPONS[name]
        
        if time.time() - self.last_shot < fire_rate:
            return
        if self.ammo[ammo_type] <= 0:
            return
        
        self.ammo[ammo_type] -= 1
        self.last_shot = time.time()
        
        # Shoot raycast
        hit = raycast(camera.world_position, camera.forward, distance=150, ignore=[self])
        
        if hit.hit:
            # Hit bot
            if hasattr(hit.entity, 'is_bot'):
                is_head = hit.world_point.y - hit.entity.y > 1.2
                final_dmg = damage * (2.0 if is_head else 1.0)
                hit.entity.take_damage(final_dmg, self)
                
                # Show damage number
                DamageText(hit.world_point, int(final_dmg), is_head)
            
            # Hit structure
            elif hasattr(hit.entity, 'is_structure'):
                hit.entity.take_damage(damage)
        
        # Muzzle flash
        flash = Entity(model='sphere', color=color.yellow, scale=0.2, 
                      position=camera.world_position + camera.forward * 1, unlit=True)
        destroy(flash, delay=0.05)
    
    def build(self):
        if self.materials[self.current_material] < 10:
            return
        
        # Find build position
        hit = raycast(camera.world_position, camera.forward, distance=6, ignore=[self])
        
        if hit.hit:
            # Snap to grid
            pos = hit.world_point
            x = round(pos.x / BUILD_SIZE) * BUILD_SIZE
            y = round(pos.y / BUILD_SIZE) * BUILD_SIZE
            z = round(pos.z / BUILD_SIZE) * BUILD_SIZE
            
            BuildStructure((x, y, z), self.current_structure, self.current_material)
            self.materials[self.current_material] -= 10

# === BOT ===
class Bot(Entity):
    def __init__(self, pos):
        super().__init__(
            model='cube',
            color=color.red,
            position=pos,
            scale=(0.6, 1.6, 0.6),
            collider='box'
        )
        
        self.is_bot = True
        self.health = 100
        self.shield = random.choice([0, 50])
        self.alive = True
        
        self.move_timer = random.uniform(1, 3)
        self.shoot_timer = random.uniform(0.5, 2)
        self.speed = random.uniform(1, 2)
        
    def update(self):
        if not self.alive:
            return
        
        self.move_timer -= time.dt
        self.shoot_timer -= time.dt
        
        # Random movement
        if self.move_timer <= 0:
            self.move_timer = random.uniform(2, 4)
            
            # Move towards center (safe zone)
            if hasattr(game, 'storm'):
                to_center = (game.storm.center - self.position).normalized()
                self.position += to_center * self.speed * time.dt * 15
            else:
                angle = random.uniform(0, 6.28)
                self.position += Vec3(math.cos(angle), 0, math.sin(angle)) * self.speed * time.dt * 10
        
        # Keep in bounds
        self.x = clamp(self.x, -MAP_SIZE//2, MAP_SIZE//2)
        self.z = clamp(self.z, -MAP_SIZE//2, MAP_SIZE//2)
        if self.y < 0.8:
            self.y = 0.8
        
        # Shoot at player
        if hasattr(game, 'player') and game.player.alive:
            dist = distance(self.position, game.player.position)
            if dist < 30 and self.shoot_timer <= 0:
                self.shoot_timer = random.uniform(1, 3)
                
                direction = (game.player.position - self.position).normalized()
                hit = raycast(self.position + Vec3(0, 0.8, 0), direction, distance=50, ignore=[self])
                
                if hit.hit and hit.entity == game.player:
                    dmg = random.randint(8, 20)
                    game.player.take_damage(dmg)
    
    def take_damage(self, dmg, attacker):
        if self.shield > 0:
            if self.shield >= dmg:
                self.shield -= dmg
            else:
                dmg -= self.shield
                self.shield = 0
                self.health -= dmg
        else:
            self.health -= dmg
        
        if self.health <= 0:
            self.die(attacker)
    
    def die(self, killer):
        self.alive = False
        if killer and hasattr(killer, 'kills'):
            killer.kills += 1
        destroy(self)

# === STRUCTURES ===
class BuildStructure(Entity):
    def __init__(self, pos, stype, mat):
        self.is_structure = True
        self.build_mat = mat
        
        # Material colors
        mat_colors = {
            'wood': color.rgb(160, 82, 45),
            'brick': color.rgb(205, 92, 92),
            'metal': color.rgb(192, 192, 192)
        }
        
        # HP values
        hp_values = {'wood': 150, 'brick': 250, 'metal': 350}
        self.max_hp = hp_values[mat]
        self.hp = self.max_hp
        
        # Simple cube for all structures
        super().__init__(
            model='cube',
            color=mat_colors[mat],
            position=pos,
            scale=(BUILD_SIZE, BUILD_SIZE, BUILD_SIZE * 0.3) if stype == 'wall' 
                  else (BUILD_SIZE, BUILD_SIZE * 0.2, BUILD_SIZE) if stype == 'floor'
                  else (BUILD_SIZE, BUILD_SIZE, BUILD_SIZE),
            collider='box',
            texture='white_cube'
        )
        
        if stype == 'ramp':
            self.rotation_x = -30
    
    def take_damage(self, dmg):
        self.hp -= dmg
        
        # Show damage
        if self.hp / self.max_hp < 0.5:
            self.color = color.rgb(80, 40, 40)
        
        if self.hp <= 0:
            destroy(self)

# === ITEMS ===
class Item(Entity):
    def __init__(self, pos, itype):
        item_colors = {
            'weapon': color.blue,
            'ammo': color.yellow,
            'shield': color.cyan,
            'health': color.green
        }
        
        super().__init__(
            model='sphere',
            color=item_colors.get(itype, color.white),
            position=Vec3(*pos) + Vec3(0, 0.5, 0),
            scale=0.4,
            collider='box',
            unlit=True
        )
        
        self.item_type = itype
        self.start_y = self.y
    
    def update(self):
        self.rotation_y += 80 * time.dt
        self.y = self.start_y + math.sin(time.time() * 3) * 0.15

# === CHEST ===
class Chest(Entity):
    def __init__(self, pos):
        super().__init__(
            model='cube',
            color=color.gold,
            position=pos,
            scale=(0.7, 0.5, 0.7),
            collider='box',
            texture='white_cube',
            unlit=True
        )
        
        self.is_chest = True
        self.opened = False
    
    def open(self):
        if self.opened:
            return
        
        self.opened = True
        
        # Spawn loot around chest
        for i in range(random.randint(2, 4)):
            angle = random.uniform(0, 6.28)
            offset = Vec3(math.cos(angle) * 1.5, 0, math.sin(angle) * 1.5)
            Item(self.position + offset, random.choice(['weapon', 'ammo', 'shield', 'health']))
        
        destroy(self)

# === STORM ===
class Storm:
    def __init__(self):
        self.radius = MAP_SIZE * 0.9
        self.target_radius = MAP_SIZE * 0.6
        self.center = Vec3(0, 0, 0)
        self.damage = 2
        self.phase = 0
        
        # Visible storm wall
        self.wall = Entity(
            model='sphere',
            color=color.rgba(150, 0, 255, 100),
            scale=self.radius * 2,
            position=self.center,
            double_sided=True,
            unlit=True
        )
        self.wall.alpha = 0.3
    
    def update(self):
        # Shrink
        if self.radius > self.target_radius:
            self.radius -= 0.3 * time.dt
            self.wall.scale = self.radius * 2
        else:
            # Next phase
            self.phase += 1
            self.target_radius = max(5, self.target_radius * 0.7)
            self.damage += 1
        
        # Damage player if outside
        if hasattr(game, 'player') and game.player.alive:
            dist = distance_2d(game.player.position, self.center)
            if dist > self.radius:
                if int(time.time() * 2) % 2 == 0:
                    game.player.take_damage(self.damage)

# === DAMAGE TEXT ===
class DamageText(Entity):
    def __init__(self, pos, dmg, is_head):
        self.txt = Text(
            text=str(dmg),
            position=camera.world_to_screen_point(pos + Vec3(0, 1, 0)),
            scale=2.5,
            color=color.yellow if is_head else color.white,
            origin=(0, 0)
        )
        self.timer = 1
        invoke(self.remove, delay=1)
    
    def update(self):
        self.timer -= time.dt
        if hasattr(self, 'txt'):
            self.txt.y += time.dt * 0.5
            self.txt.alpha = self.timer
    
    def remove(self):
        if hasattr(self, 'txt'):
            destroy(self.txt)
        destroy(self)

# === GAME ===
class Game:
    def __init__(self):
        self.state = 'menu'
        self.player = None
        self.bots = []
        self.storm = None
    
    def start(self):
        self.state = 'playing'
        
        # Create player
        self.player = Player(position=(0, 2, 0))
        camera.fov = 90
        
        # Create bots
        for i in range(BOT_COUNT):
            x = random.uniform(-MAP_SIZE//2 + 5, MAP_SIZE//2 - 5)
            z = random.uniform(-MAP_SIZE//2 + 5, MAP_SIZE//2 - 5)
            self.bots.append(Bot((x, 0.8, z)))
        
        # Storm
        self.storm = Storm()
        
        # Spawn chests
        for i in range(25):
            x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            Chest((x, 0.25, z))
        
        # Spawn items
        for i in range(40):
            x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            Item((x, 0, z), random.choice(['weapon', 'ammo', 'shield', 'health']))
        
        self.create_hud()
    
    def create_hud(self):
        self.hp_txt = Text('HP: 100', position=(-0.85, 0.46), scale=2, color=color.green)
        self.shield_txt = Text('Shield: 0', position=(-0.85, 0.42), scale=2, color=color.cyan)
        self.mat_txt = Text('Wood: 100 | Brick: 50 | Metal: 50', position=(-0.85, 0.37), scale=1.5, color=color.orange)
        self.weapon_txt = Text('AR (common) | Ammo: 150', position=(-0.85, 0.32), scale=1.5, color=color.white)
        self.kills_txt = Text('Kills: 0', position=(-0.85, 0.27), scale=1.5, color=color.yellow)
        self.players_txt = Text(f'Alive: {BOT_COUNT + 1}', position=(0, 0.48), scale=2.5, color=color.white)
        self.crosshair = Entity(model='quad', color=color.white, scale=0.01, position=(0, 0, 1), parent=camera.ui)
    
    def update_hud(self):
        if not self.player:
            return
        
        self.hp_txt.text = f'HP: {int(self.player.health)}'
        self.hp_txt.color = color.green if self.player.health > 50 else color.red
        
        self.shield_txt.text = f'Shield: {int(self.player.shield)}'
        
        self.mat_txt.text = f"Wood: {self.player.materials['wood']} | Brick: {self.player.materials['brick']} | Metal: {self.player.materials['metal']}"
        
        weapon = self.player.weapons.get(self.player.current_slot)
        if weapon:
            name, rarity = weapon
            if name in WEAPONS:
                ammo_type = WEAPONS[name][3]
                self.weapon_txt.text = f'{name} ({rarity}) | Ammo: {self.player.ammo[ammo_type]}'
                self.weapon_txt.color = RARITY_COLORS.get(rarity, color.white)
        
        self.kills_txt.text = f'Kills: {self.player.kills}'
        
        alive = sum(1 for b in self.bots if b.alive) + (1 if self.player.alive else 0)
        self.players_txt.text = f'Alive: {alive}'
        
        # Check win
        if alive == 1 and self.player.alive and self.state == 'playing':
            self.victory()
        elif not self.player.alive and self.state == 'playing':
            self.defeat()
    
    def victory(self):
        self.state = 'victory'
        Text('VICTORY ROYALE!', position=(0, 0.1), scale=5, color=color.gold, origin=(0, 0))
        Text(f'Kills: {self.player.kills}', position=(0, -0.05), scale=3, color=color.white, origin=(0, 0))
    
    def defeat(self):
        self.state = 'defeat'
        Text('ELIMINATED', position=(0, 0.1), scale=5, color=color.red, origin=(0, 0))
        Text(f'Kills: {self.player.kills}', position=(0, -0.05), scale=3, color=color.white, origin=(0, 0))

# === MAIN ===
app = Ursina()

# Ground
ground = Entity(
    model='plane',
    texture='white_cube',
    color=color.rgb(100, 180, 100),
    scale=(MAP_SIZE, 1, MAP_SIZE),
    collider='box'
)

# Trees (fewer, colorful)
for i in range(30):
    x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
    z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
    
    # Trunk
    Entity(model='cube', color=color.rgb(101, 67, 33), position=(x, 1.5, z), scale=(0.4, 3, 0.4))
    
    # Leaves
    Entity(model='sphere', color=color.rgb(50, 200, 50), position=(x, 4, z), scale=1.5, unlit=True)

# Rocks (colorful)
for i in range(20):
    x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
    z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
    Entity(model='sphere', color=color.gray, position=(x, 0.4, z), scale=random.uniform(0.6, 1.2), collider='box')

# Sky
Sky(color=color.rgb(135, 206, 250))

# Lighting
DirectionalLight(y=2, z=3)
AmbientLight(color=color.rgba(255, 255, 255, 0.3))

# Game
game = Game()

# Menu
menu_title = Text('FORTNITE 3D - SIMPLIFIED', position=(0, 0.2), scale=3, color=color.cyan, origin=(0, 0))
menu_start = Text('Press ENTER to Start', position=(0, 0), scale=2.5, color=color.white, origin=(0, 0))
menu_info = Text(f'{BOT_COUNT} Bots | Clean Graphics | Fun Gameplay', position=(0, -0.15), scale=1.5, color=color.light_gray, origin=(0, 0))

def input(key):
    if game.state == 'menu' and key == 'enter':
        destroy(menu_title)
        destroy(menu_start)
        destroy(menu_info)
        game.start()
    
    elif game.state == 'playing' and game.player:
        if key == 'left mouse down':
            game.player.shoot()
        elif key == 'right mouse down':
            game.player.build()
        elif key == 'q':
            game.player.current_structure = 'wall'
        elif key == 'f':
            game.player.current_structure = 'floor'
        elif key == 'c':
            game.player.current_structure = 'ramp'
        elif key == 'z':
            game.player.current_material = 'wood'
        elif key == 'x':
            game.player.current_material = 'brick'
        elif key == 'b':
            game.player.current_material = 'metal'
        elif key in '12345':
            game.player.current_slot = int(key) - 1
        elif key == 'e':
            # Pickup items
            for ent in scene.entities:
                if hasattr(ent, 'item_type') and distance(game.player.position, ent.position) < 3:
                    itype = ent.item_type
                    if itype == 'weapon':
                        weapon = random.choice(list(WEAPONS.keys()))
                        rarity = random.choice(['common', 'rare', 'epic', 'legendary'])
                        game.player.weapons[game.player.current_slot] = (weapon, rarity)
                    elif itype == 'ammo':
                        for atype in game.player.ammo:
                            game.player.ammo[atype] = min(game.player.ammo[atype] + 30, 999)
                    elif itype == 'shield':
                        game.player.shield = min(100, game.player.shield + 50)
                    elif itype == 'health':
                        game.player.health = min(100, game.player.health + 50)
                    destroy(ent)
                
                # Open chests
                elif hasattr(ent, 'is_chest') and distance(game.player.position, ent.position) < 3:
                    ent.open()

def update():
    if game.state == 'playing':
        for bot in game.bots:
            if bot.alive:
                bot.update()
        
        if game.storm:
            game.storm.update()
        
        game.update_hud()

app.run()
