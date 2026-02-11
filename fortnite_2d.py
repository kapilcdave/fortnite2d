from ursina import *
import random
import math

# === INITIAL SETTINGS ===
app = Ursina()

# Window Setup
window.title = "Fortnite 2D Classic"
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Camera Setup (2D Orthographic)
camera.orthographic = True
camera.fov = 20
camera.position = (0, 0)

# Colors
GRASS_COLOR = color.rgb(100, 180, 100)
PLAYER_COLOR = color.blue
BOT_COLOR = color.red
WALL_COLOR = color.rgb(139, 69, 19) # Brown
BULLET_COLOR = color.yellow

# Game Variables
MAP_SIZE = 50
players_speed = 7
bullet_speed = 20

# === CLASSES ===

class Bullet(Entity):
    def __init__(self, shooter, position, direction, **kwargs):
        super().__init__(
            model='quad',
            color=BULLET_COLOR,
            scale=(0.3, 0.3),
            position=position,
            collider='box',
            **kwargs
        )
        self.shooter = shooter
        self.direction = direction
        self.damage = 25
        self.life_time = 2.0
        
    def update(self):
        self.position += self.direction * bullet_speed * time.dt
        self.life_time -= time.dt
        
        if self.life_time <= 0:
            destroy(self)
            return

        # Collision detection
        hit_info = self.intersects()
        if hit_info.hit:
            if hit_info.entity != self.shooter:
                if hasattr(hit_info.entity, 'take_damage'):
                    hit_info.entity.take_damage(self.damage)
                destroy(self)

class Wall(Entity):
    def __init__(self, position):
        super().__init__(
            model='quad',
            color=WALL_COLOR,
            scale=(1, 1),
            position=position,
            collider='box'
        )
        self.health = 100
        
    def take_damage(self, damage):
        self.health -= damage
        self.color = color.rgb(139, 69, 19, a=self.health/100 * 255) # Encode alpha in rgb not supported directly sometimes, depend on shader, but simple color shift works
        self.color = color.lerp(color.black, WALL_COLOR, self.health/100)
        
        if self.health <= 0:
            destroy(self)

class Character(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='circle',
            scale=(1, 1),
            collider='box',
            **kwargs
        )
        self.health = 100
        self.speed = players_speed
        self.weapon_cooldown = 0
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            destroy(self)
            if self == player:
                print("Game Over!")
                application.quit()
            
    def shoot(self, target_pos=None):
        if self.weapon_cooldown > 0:
            return
            
        self.weapon_cooldown = 0.2
        
        # Calculate direction
        start_pos = self.position
        if target_pos:
            direction = (target_pos - start_pos).normalized()
        else:
             # Shoot towards mouse for player
            mouse_pos = mouse.world_point
            if mouse_pos:
               direction = (mouse_pos - start_pos).normalized()
               direction.z = 0 # Ensure 2D
        
        Bullet(shooter=self, position=start_pos, direction=direction)

class Player(Character):
    def __init__(self):
        super().__init__(color=PLAYER_COLOR, position=(0, 0, 0))
        self.score = 0
        self.mats = 50
        
    def update(self):
        # Movement
        move_direction = Vec3(
            held_keys['d'] - held_keys['a'],
            held_keys['w'] - held_keys['s'],
            0
        ).normalized()
        
        self.position += move_direction * self.speed * time.dt
        
        # Camera follow
        camera.position = (self.x, self.y)
        
        # Cooldowns
        if self.weapon_cooldown > 0:
            self.weapon_cooldown -= time.dt
            
        # Shooting
        if held_keys['left mouse']:
            self.shoot()
            
        # Building
        if held_keys['right mouse'] and self.mats >= 10:
            mouse_pos = mouse.world_point
            if mouse_pos:
                build_pos = (round(mouse_pos.x), round(mouse_pos.y), 0)
                # Check distance to build
                if distance(self.position, build_pos) < 5:
                    # Check if empty (very basic check)
                    if not any(e.position == build_pos for e in scene.entities if isinstance(e, Wall)):
                        Wall(position=build_pos)
                        self.mats -= 10

class Bot(Character):
    def __init__(self):
        x = random.uniform(-MAP_SIZE/2, MAP_SIZE/2)
        y = random.uniform(-MAP_SIZE/2, MAP_SIZE/2)
        super().__init__(color=BOT_COLOR, position=(x, y, 0))
        self.change_dir_time = 0
        self.move_dir = Vec3(0,0,0)
        
    def update(self):
        # AI Logic
        dist_to_player = distance(self.position, player.position)
        
        if dist_to_player < 10:
            # Chase and Shoot
            self.move_dir = (player.position - self.position).normalized()
            self.shoot(target_pos=player.position)
        else:
            # Roam
            if time.time() > self.change_dir_time:
                self.change_dir_time = time.time() + random.uniform(1, 3)
                self.move_dir = Vec3(random.uniform(-1,1), random.uniform(-1,1), 0).normalized()
                
            # Stay in Storm
            if storm:
                dist_from_center = distance(self.position, storm.position)
                if dist_from_center > storm.scale_x / 2:
                    self.move_dir = (storm.position - self.position).normalized()

        self.position += self.move_dir * (self.speed * 0.5) * time.dt
        
        if self.weapon_cooldown > 0:
            self.weapon_cooldown -= time.dt

# === GAME OBJECTS ===

# Background
Entity(model='quad', scale=(MAP_SIZE*2, MAP_SIZE*2), color=GRASS_COLOR, z=1)

# Storm
storm = Entity(
    model='circle',
    color=color.rgba(100, 0, 255, 50),
    scale=(MAP_SIZE * 1.5, MAP_SIZE * 1.5),
    position=(0,0,-0.1) # slightly above background
)
storm_target_scale = 0

def update_storm():
    global storm_target_scale
    if storm.scale_x > 5:
        storm.scale -= Vec3(1, 1, 0) * time.dt * 0.5
    
    # Storm Damage
    if player and distance(player.position, storm.position) > storm.scale_x / 2:
        player.take_damage(5 * time.dt)

# Setup Game
player = Player()

bots = []
for i in range(10):
    bots.append(Bot())

# UI
health_bar = Text(text='HP: 100', position=(-0.85, 0.45), scale=2, color=color.red)
mats_text = Text(text='Mats: 50', position=(-0.85, 0.40), scale=2, color=color.brown)

def update():
    update_storm()
    
    # Check win
    remaining_bots = [b for b in bots if b.enabled] # b.enabled becomes False when destroyed? No, destroy removes from scene.
    # Ursina destroy removes from scene entities list usually.
    # Let's count manually.
    current_bot_count = 0 
    for e in scene.entities:
        if isinstance(e, Bot):
            current_bot_count += 1
            
    if current_bot_count == 0:
        Text(text='VICTORY ROYALE!', scale=3, origin=(0,0), color=color.gold)
        application.pause()

    # UI Update
    health_bar.text = f'HP: {int(player.health)}'
    mats_text.text = f'Mats: {player.mats}'

app.run()
