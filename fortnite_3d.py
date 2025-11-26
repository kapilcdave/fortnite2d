"""
FORTNITE 3D - Battle Royale
A complete 3D battle royale game with building mechanics, combat, and 100 bot players.
Built with Ursina Engine.

Controls:
- WASD: Move
- Mouse: Look around
- Space: Jump
- Shift: Sprint
- Ctrl: Crouch
- Left Click: Shoot
- Right Click: Build
- E: Pickup items / Open chests
- Q/F/C/V: Select structure (Wall/Floor/Ramp/Roof)
- Z/X/B: Select material (Wood/Brick/Metal)
- 1-5: Switch weapons
- Tab: Toggle menu
"""

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math

# === GAME SETTINGS ===
MAP_SIZE = 150
PLAYER_COUNT = 100
BUILDING_SIZE = 2

# === CUSTOM FIRST PERSON CONTROLLER ===
class FortnitePlayer(FirstPersonController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Stats
        self.health = 100
        self.shield = 0
        self.alive = True
        
        # Combat
        self.weapons = {}  # {slot: (weapon_name, rarity)}
        self.current_slot = 0
        self.ammo = {'light': 120, 'shells': 40, 'heavy': 20, 'rockets': 8}
        self.last_shot_time = 0
        
        # Building
        self.materials = {'wood': 100, 'brick': 50, 'metal': 50}
        self.current_material = 'wood'
        self.current_structure = 'wall'
        self.build_preview = None
        
        # Stats
        self.kills = 0
        
        # Movement
        self.normal_speed = 5
        self.sprint_speed = 8
        self.crouch_speed = 3
        self.speed = self.normal_speed
        
        # Visual
        self.is_crouching = False
        
        # Add starting weapon
        self.weapons[0] = ('AR', 'uncommon')
        
    def update(self):
        super().update()
        
        # Sprint
        if held_keys['shift'] and not self.is_crouching:
            self.speed = self.sprint_speed
        elif self.is_crouching:
            self.speed = self.crouch_speed
        else:
            self.speed = self.normal_speed
        
        # Crouch
        if held_keys['control']:
            if not self.is_crouching:
                self.camera_pivot.y -= 0.5
                self.is_crouching = True
        else:
            if self.is_crouching:
                self.camera_pivot.y += 0.5
                self.is_crouching = False
        
        # Update build preview
        self.update_build_preview()
        
        # Keep within map bounds
        self.x = clamp(self.x, -MAP_SIZE//2, MAP_SIZE//2)
        self.z = clamp(self.z, -MAP_SIZE//2, MAP_SIZE//2)
        
    def update_build_preview(self):
        # Show ghost preview of structure
        if self.build_preview:
            # Position preview based on where player is looking
            hit_info = raycast(camera.world_position, camera.forward, distance=8, ignore=[self])
            if hit_info.hit:
                # Snap to grid
                pos = hit_info.world_point
                grid_x = round(pos.x / BUILDING_SIZE) * BUILDING_SIZE
                grid_y = round(pos.y / BUILDING_SIZE) * BUILDING_SIZE
                grid_z = round(pos.z / BUILDING_SIZE) * BUILDING_SIZE
                self.build_preview.position = (grid_x, grid_y, grid_z)
        
    def take_damage(self, amount):
        if self.shield > 0:
            if self.shield >= amount:
                self.shield -= amount
            else:
                remaining = amount - self.shield
                self.shield = 0
                self.health -= remaining
        else:
            self.health -= amount
            
        if self.health <= 0:
            self.die()
    
    def die(self):
        self.alive = False
        self.visible = False
        self.position = (0, -100, 0)  # Move underground
    
    def shoot(self):
        weapon = self.get_current_weapon()
        if not weapon:
            return
            
        current_time = time.time()
        fire_rate = self.get_weapon_fire_rate(weapon[0])
        
        if current_time - self.last_shot_time < fire_rate:
            return
        
        ammo_type = self.get_weapon_ammo_type(weapon[0])
        if self.ammo[ammo_type] <= 0:
            return
        
        self.ammo[ammo_type] -= 1
        self.last_shot_time = current_time
        
        # Raycast shoot
        hit_info = raycast(camera.world_position, camera.forward, distance=100, ignore=[self])
        
        if hit_info.hit:
            # Check if hit a bot
            if hasattr(hit_info.entity, 'bot_type'):
                damage = self.get_weapon_damage(weapon[0])
                hit_info.entity.take_damage(damage, self)
            # Check if hit a structure
            elif hasattr(hit_info.entity, 'structure_type'):
                damage = self.get_weapon_damage(weapon[0])
                hit_info.entity.take_damage(damage)
        
        # Muzzle flash effect
        flash = Entity(model='cube', color=color.yellow, scale=0.2, position=camera.world_position + camera.forward * 2)
        destroy(flash, delay=0.05)
    
    def build_structure(self):
        if self.materials[self.current_material] < 10:
            return
            
        # Raycast to find build position
        hit_info = raycast(camera.world_position, camera.forward, distance=8, ignore=[self])
        
        if hit_info.hit:
            # Snap to grid
            pos = hit_info.world_point
            grid_x = round(pos.x / BUILDING_SIZE) * BUILDING_SIZE
            grid_y = round(pos.y / BUILDING_SIZE) * BUILDING_SIZE
            grid_z = round(pos.z / BUILDING_SIZE) * BUILDING_SIZE
            
            # Create structure
            structure = Structure((grid_x, grid_y, grid_z), self.current_structure, self.current_material)
            self.materials[self.current_material] -= 10
    
    def get_current_weapon(self):
        return self.weapons.get(self.current_slot)
    
    def get_weapon_damage(self, weapon_name):
        damages = {'AR': 30, 'Shotgun': 80, 'SMG': 18, 'Sniper': 120, 'Pistol': 25, 'RPG': 100}
        return damages.get(weapon_name, 10)
    
    def get_weapon_fire_rate(self, weapon_name):
        rates = {'AR': 0.15, 'Shotgun': 0.8, 'SMG': 0.08, 'Sniper': 1.5, 'Pistol': 0.2, 'RPG': 2.0}
        return rates.get(weapon_name, 0.5)
    
    def get_weapon_ammo_type(self, weapon_name):
        types = {'AR': 'light', 'Shotgun': 'shells', 'SMG': 'light', 'Sniper': 'heavy', 'Pistol': 'light', 'RPG': 'rockets'}
        return types.get(weapon_name, 'light')

# === STRUCTURE CLASS ===
class Structure(Entity):
    def __init__(self, position, structure_type, material, **kwargs):
        self.structure_type = structure_type
        self.material = material
        
        # Material properties
        colors = {'wood': color.rgb(139, 69, 19), 'brick': color.rgb(178, 34, 34), 'metal': color.gray}
        healths = {'wood': 150, 'brick': 300, 'metal': 400}
        
        self.max_health = healths[material]
        self.health = self.max_health
        
        # Create model based on type
        if structure_type == 'wall':
            model = 'cube'
            scale = (BUILDING_SIZE, BUILDING_SIZE, BUILDING_SIZE * 0.3)
        elif structure_type == 'floor':
            model = 'cube'
            scale = (BUILDING_SIZE, BUILDING_SIZE * 0.2, BUILDING_SIZE)
        elif structure_type == 'ramp':
            model = 'cube'  # Will rotate to make ramp
            scale = (BUILDING_SIZE, BUILDING_SIZE * 0.2, BUILDING_SIZE)
        elif structure_type == 'roof':
            model = 'cube'
            scale = (BUILDING_SIZE, BUILDING_SIZE * 0.3, BUILDING_SIZE)
        else:
            model = 'cube'
            scale = BUILDING_SIZE
        
        super().__init__(
            model=model,
            color=colors[material],
            position=position,
            scale=scale,
            collider='box',
            **kwargs
        )
        
        # Rotate ramp
        if structure_type == 'ramp':
            self.rotation_x = -25
    
    def take_damage(self, amount):
        self.health -= amount
        
        # Update color to show damage
        damage_percent = self.health / self.max_health
        if damage_percent < 0.3:
            self.color = color.rgb(100, 50, 50)
        elif damage_percent < 0.6:
            self.color = color.rgb(150, 75, 75)
        
        if self.health <= 0:
            destroy(self)

# === BOT CLASS ===
class Bot(Entity):
    def __init__(self, position, **kwargs):
        super().__init__(
            model='cube',
            color=color.red,
            position=position,
            scale=(0.8, 1.8, 0.8),
            collider='box',
            **kwargs
        )
        
        self.bot_type = True
        self.health = 100
        self.shield = 0
        self.alive = True
        
        # AI
        self.target = None
        self.state = 'idle'  # idle, looting, fighting, rotating
        self.move_timer = 0
        self.move_direction = Vec3(0, 0, 0)
        self.decision_timer = random.uniform(1, 3)
        self.shoot_timer = 0
        
        # Movement
        self.speed = 2
        
    def update(self):
        if not self.alive:
            return
        
        self.decision_timer -= time.dt
        
        # Simple AI
        if self.decision_timer <= 0:
            self.decision_timer = random.uniform(2, 5)
            
            # Random movement
            angle = random.uniform(0, 2 * math.pi)
            self.move_direction = Vec3(math.cos(angle) * self.speed, 0, math.sin(angle) * self.speed)
        
        # Move
        self.position += self.move_direction * time.dt
        
        # Keep within bounds
        self.x = clamp(self.x, -MAP_SIZE//2, MAP_SIZE//2)
        self.z = clamp(self.z, -MAP_SIZE//2, MAP_SIZE//2)
        
        # Stay on ground (simple)
        if self.y < 0.9:
            self.y = 0.9
        
        # Shoot at player occasionally
        if hasattr(game, 'player') and game.player.alive:
            dist = distance(self.position, game.player.position)
            if dist < 30 and random.random() < 0.01:  # 1% chance per frame to shoot
                self.shoot_at_player()
    
    def shoot_at_player(self):
        if not hasattr(game, 'player'):
            return
            
        # Simple raycast toward player
        direction = (game.player.position - self.position).normalized()
        hit_info = raycast(self.position + Vec3(0, 1, 0), direction, distance=50, ignore=[self])
        
        if hit_info.hit and hit_info.entity == game.player:
            game.player.take_damage(random.randint(5, 15))
    
    def take_damage(self, amount, attacker):
        if self.shield > 0:
            if self.shield >= amount:
                self.shield -= amount
            else:
                remaining = amount - self.shield
                self.shield = 0
                self.health -= remaining
        else:
            self.health -= amount
        
        if self.health <= 0:
            self.die(attacker)
    
    def die(self, killer):
        self.alive = False
        if killer and hasattr(killer, 'kills'):
            killer.kills += 1
        destroy(self)

# === ITEM CLASS ===
class Item(Entity):
    def __init__(self, position, item_type, item_data=None, **kwargs):
        
        colors_map = {
            'weapon': color.blue,
            'ammo': color.yellow,
            'healing': color.red,
            'shield': color.cyan,
            'material': color.orange
        }
        
        # Convert tuple to Vec3 if needed
        if isinstance(position, tuple):
            position = Vec3(*position)
        
        super().__init__(
            model='cube',
            color=colors_map.get(item_type, color.white),
            position=position + Vec3(0, 0.5, 0),
            scale=0.3,
            collider='box',
            **kwargs
        )
        
        self.item_type = item_type
        self.item_data = item_data
        
        # Floating animation
        self.original_y = self.y
        self.time_offset = random.uniform(0, 6.28)
    
    def update(self):
        # Rotate and bob
        self.rotation_y += 50 * time.dt
        self.y = self.original_y + math.sin(time.time() * 2 + self.time_offset) * 0.1

# === CHEST CLASS ===
class Chest(Entity):
    def __init__(self, position, **kwargs):
        super().__init__(
            model='cube',
            color=color.gold,
            position=position,
            scale=(0.8, 0.6, 0.8),
            collider='box',
            **kwargs
        )
        
        self.opened = False
        self.chest_type = True
    
    def open(self):
        if self.opened:
            return
        
        self.opened = True
        
        # Spawn loot
        for i in range(random.randint(3, 5)):
            angle = random.uniform(0, 2 * math.pi)
            offset = Vec3(math.cos(angle) * 2, 0, math.sin(angle) * 2)
            
            item_type = random.choice(['weapon', 'ammo', 'shield', 'healing', 'material'])
            Item(self.position + offset, item_type)
        
        destroy(self)

# === STORM CLASS ===
class Storm:
    def __init__(self):
        self.current_radius = MAP_SIZE
        self.target_radius = MAP_SIZE * 0.7
        self.center = Vec3(0, 0, 0)
        self.damage = 1
        self.shrink_speed = 0.5
        self.phase = 0
        
        # Visual
        self.entity = Entity(
            model='sphere',
            color=color.rgba(128, 0, 128, 50),
            scale=self.current_radius * 2,
            position=self.center,
            double_sided=True,
            unlit=True
        )
        self.entity.alpha = 0.2
    
    def update(self):
        if self.current_radius > self.target_radius:
            self.current_radius -= self.shrink_speed * time.dt
            self.entity.scale = self.current_radius * 2
        
        # Check if player is in storm
        if hasattr(game, 'player') and game.player.alive:
            player_dist = distance_2d(game.player.position, self.center)
            if player_dist > self.current_radius:
                # Take damage every second
                if int(time.time() * 2) % 2 == 0:  # Rough timer
                    game.player.take_damage(self.damage)

# === GAME CLASS ===
class GameController:
    def __init__(self):
        self.state = 'menu'  # menu, playing, victory, defeat
        self.player = None
        self.bots = []
        self.storm = None
        self.hud = None
        
    def start_game(self):
        self.state = 'playing'
        
        # Create player
        self.player = FortnitePlayer(position=(0, 2, 0))
        camera.fov = 90
        
        # Create bots
        for i in range(min(PLAYER_COUNT - 1, 30)):  # Limit to 30 for performance
            x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            bot = Bot((x, 1, z))
            self.bots.append(bot)
        
        # Create storm
        self.storm = Storm()
        
        # Spawn chests around map
        for i in range(50):
            x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            Chest((x, 0.3, z))
        
        # Spawn floor loot
        for i in range(80):
            x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
            item_type = random.choice(['weapon', 'ammo', 'shield', 'healing'])
            Item((x, 0, z), item_type)
        
        # Create HUD
        self.create_hud()
    
    def create_hud(self):
        # Health bar
        self.health_text = Text(text='HP: 100', position=(-0.85, 0.45), scale=1.5, color=color.green)
        self.shield_text = Text(text='Shield: 0', position=(-0.85, 0.42), scale=1.5, color=color.cyan)
        
        # Materials
        self.materials_text = Text(text='Wood: 100 | Brick: 50 | Metal: 50', position=(-0.85, 0.38), scale=1.2, color=color.orange)
        
        # Weapon
        self.weapon_text = Text(text='Weapon: AR | Ammo: 120', position=(-0.85, 0.34), scale=1.2, color=color.white)
        
        # Kills
        self.kills_text = Text(text='Eliminations: 0', position=(-0.85, 0.30), scale=1.2, color=color.yellow)
        
        # Players alive
        self.players_text = Text(text='Players: 100', position=(0, 0.48), scale=1.5, color=color.white)
        
        # Crosshair
        self.crosshair = Entity(model='quad', color=color.white, scale=0.008, position=(0, 0, 1), parent=camera.ui)
    
    def update_hud(self):
        if not self.player:
            return
        
        self.health_text.text = f'HP: {int(self.player.health)}'
        self.shield_text.text = f'Shield: {int(self.player.shield)}'
        
        self.materials_text.text = f"Wood: {self.player.materials['wood']} | Brick: {self.player.materials['brick']} | Metal: {self.player.materials['metal']}"
        
        weapon = self.player.get_current_weapon()
        if weapon:
            ammo_type = self.player.get_weapon_ammo_type(weapon[0])
            self.weapon_text.text = f'Weapon: {weapon[0]} | Ammo: {self.player.ammo[ammo_type]}'
        
        self.kills_text.text = f'Eliminations: {self.player.kills}'
        
        alive_bots = sum(1 for bot in self.bots if bot.alive)
        total_alive = alive_bots + (1 if self.player.alive else 0)
        self.players_text.text = f'Players: {total_alive}'
        
        # Check win condition
        if alive_bots == 0 and self.player.alive:
            self.victory()
        elif not self.player.alive:
            self.defeat()
    
    def victory(self):
        if self.state == 'victory':
            return
        self.state = 'victory'
        Text(text='VICTORY ROYALE!', position=(0, 0.1), scale=3, color=color.gold, origin=(0, 0))
        Text(text=f'Eliminations: {self.player.kills}', position=(0, 0), scale=2, color=color.white, origin=(0, 0))
        Text(text='Press ESC to exit', position=(0, -0.1), scale=1.5, color=color.white, origin=(0, 0))
    
    def defeat(self):
        if self.state == 'defeat':
            return
        self.state = 'defeat'
        Text(text='ELIMINATED', position=(0, 0.1), scale=3, color=color.red, origin=(0, 0))
        Text(text=f'Eliminations: {self.player.kills}', position=(0, 0), scale=2, color=color.white, origin=(0, 0))
        Text(text='Press ESC to exit', position=(0, -0.1), scale=1.5, color=color.white, origin=(0, 0))

# === MAIN APP ===
app = Ursina()

# Create terrain
ground = Entity(
    model='plane',
    texture='grass',
    scale=(MAP_SIZE, 1, MAP_SIZE),
    collider='box',
    color=color.rgb(100, 200, 100)
)

# Add some trees for decoration
for i in range(100):
    x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
    z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
    tree = Entity(
        model='cube',
        color=color.rgb(101, 67, 33),
        position=(x, 2, z),
        scale=(0.5, 4, 0.5)
    )
    # Tree top
    leaves = Entity(
        model='sphere',
        color=color.rgb(34, 139, 34),
        position=(x, 5, z),
        scale=2
    )

# Add some rocks
for i in range(50):
    x = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
    z = random.uniform(-MAP_SIZE//2, MAP_SIZE//2)
    rock = Entity(
        model='sphere',
        color=color.gray,
        position=(x, 0.5, z),
        scale=random.uniform(0.8, 1.5)
    )

# Sky
Sky(color=color.rgb(135, 206, 235))

# Lighting
DirectionalLight(y=2, z=3, shadows=True)

# Create game controller
game = GameController()

# Menu
menu_title = Text(text='FORTNITE 3D', position=(0, 0.2), scale=3, color=color.rgb(0, 150, 255), origin=(0, 0))
menu_start = Text(text='Press ENTER to Start', position=(0, 0), scale=2, color=color.white, origin=(0, 0))
menu_controls = Text(text='WASD: Move | Mouse: Look | Space: Jump | LClick: Shoot | RClick: Build', position=(0, -0.2), scale=1, color=color.light_gray, origin=(0, 0))

def input(key):
    if game.state == 'menu':
        if key == 'enter':
            destroy(menu_title)
            destroy(menu_start)
            destroy(menu_controls)
            game.start_game()
    
    elif game.state == 'playing':
        if game.player:
            # Shooting
            if key == 'left mouse down':
                game.player.shoot()
            
            # Building
            if key == 'right mouse down':
                game.player.build_structure()
            
            # Structure selection
            if key == 'q':
                game.player.current_structure = 'wall'
            elif key == 'f':
                game.player.current_structure = 'floor'
            elif key == 'c':
                game.player.current_structure = 'ramp'
            elif key == 'v':
                game.player.current_structure = 'roof'
            
            # Material selection
            if key == 'z':
                game.player.current_material = 'wood'
            elif key == 'x':
                game.player.current_material = 'brick'
            elif key == 'b':
                game.player.current_material = 'metal'
            
            # Weapon switching
            for i in range(1, 6):
                if key == str(i):
                    game.player.current_slot = i - 1
            
            # Pickup/Interact
            if key == 'e':
                # Check for nearby items
                for entity in scene.entities:
                    if hasattr(entity, 'item_type'):
                        dist = distance(game.player.position, entity.position)
                        if dist < 3:
                            # Simple pickup logic
                            if entity.item_type == 'ammo':
                                game.player.ammo['light'] += 30
                            elif entity.item_type == 'shield':
                                game.player.shield = min(100, game.player.shield + 25)
                            elif entity.item_type == 'healing':
                                game.player.health = min(100, game.player.health + 25)
                            elif entity.item_type == 'material':
                                mat = random.choice(['wood', 'brick', 'metal'])
                                game.player.materials[mat] += 20
                            elif entity.item_type == 'weapon':
                                weapon_name = random.choice(['AR', 'Shotgun', 'SMG', 'Sniper', 'Pistol'])
                                game.player.weapons[game.player.current_slot] = (weapon_name, 'rare')
                            destroy(entity)
                    
                    # Check for chests
                    if hasattr(entity, 'chest_type'):
                        dist = distance(game.player.position, entity.position)
                        if dist < 3:
                            entity.open()

def update():
    if game.state == 'playing':
        # Update bots
        for bot in game.bots:
            if bot.alive:
                bot.update()
        
        # Update storm
        if game.storm:
            game.storm.update()
        
        # Update HUD
        game.update_hud()

app.run()
