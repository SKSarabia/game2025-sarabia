"""
Ninja Fate - Main.py
---------------------

Juego arcade desarrollado en Python con Pygame.
Controlas a un ninja que debe sobrevivir oleadas de enemigos.

Este archivo contiene:
- Bucle principal del juego
- Menu de inicio y configuracion
- Logica de combate, movimiento y oleadas
- Sistema de inteligencia para enemigos
- Carga de sprites, musica y configuracion persistente

Requisitos:
- Python 3.10
- Pygame 2.0

Estructura del proyecto:
- imagenes/: sprites y fondo
- musica/: musica de fondo
- config.db: base de datos SQLite para configuracion

Autor: Luis Sarabia
Repositorio: https://github.com/SKSarabia/game2025-sarabia
"""


import pygame
import sys
import math
import random
import sqlite3
import os


# Directorio de trabajo: asegurarse de que las rutas funcionen (Python me odia)
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Inicializacion de pygame y el mixer
pygame.init()
pygame.mixer.init()


# Funciones de SQLite
def cargar_volumen():
    """Carga el volumen guardado en la base de datos `config.db`.

    Si no existe la fila de configuracion, crea una por defecto con volumen 0.2.
    Devuelve un float con el volumen (0.0 - 1.0).
    """
    conn = sqlite3.connect('config.db')
    cur = conn.cursor()

    # Asegurarse que la tabla exista
    cur.execute('CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY, volumen REAL)')

    # Leer la fila con id=1
    cur.execute('SELECT volumen FROM config WHERE id=1')
    fila = cur.fetchone()
    if fila is None:
        # Valor por defecto si no existe
        cur.execute('INSERT INTO config (id, volumen) VALUES (1, 1.0)')
        conn.commit()
        fila = (1.0,)

    conn.close()
    return fila[0]

# Guardar volumen
def guardar_volumen(vol):
    """Actualiza el volumen guardado en la base de datos.

    Parametros:
    - vol: float (0.0 - 1.0)
    """
    conn = sqlite3.connect('config.db')
    cur = conn.cursor()
    cur.execute('UPDATE config SET volumen=? WHERE id=1', (vol,))
    conn.commit()
    conn.close()

# Funciones de puntuaciones
def ensure_scores_table():
    conn = sqlite3.connect('config.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        score INTEGER NOT NULL,
        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def load_leaderboard(limit=5):
    ensure_scores_table()
    conn = sqlite3.connect('config.db')
    cur = conn.cursor()
    cur.execute('SELECT name, score FROM scores ORDER BY score DESC, ts ASC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def save_score(name, score):
    if not name:
        return
    ensure_scores_table()
    conn = sqlite3.connect('config.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO scores (name, score) VALUES (?, ?)', (name, int(score)))
    conn.commit()
    conn.close()


# Configuracion de pantalla
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ninja Fate")
icon = pygame.image.load('imagenes/icon.png').convert_alpha()
pygame.display.set_icon(icon)


# Colores
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
BROWN_LIGHT = (193, 154, 107)
BROWN_DARK  = (92, 64, 51)

# Variables globales
player_speed = 5
player_radius = 12
katana_length = 35
katana_speed = 30
katana_angle = 0
katana_direction = 1
shuriken_speed = 10
shuriken_cooldown = 0.5  # segundos

# Alerta global para enemigos
GLOBAL_ALERT = {"pos": None, "time": 0.0, "active": False, "duration": 6.0}

# HABITACION: paredes a los lados, arriba, abajo y pilares
obstacles = [
    pygame.Rect(0, 0, WIDTH, 32),         # pared arriba
    pygame.Rect(0, HEIGHT-32, WIDTH, 32), # pared abajo
    pygame.Rect(0, 0, 32, HEIGHT),        # pared izq
    pygame.Rect(WIDTH-32, 0, 32, HEIGHT), # pared der
    pygame.Rect(170, 170, 34, 100),       # pilar izq sup
    pygame.Rect(WIDTH-170-34, 300, 34, 100), # pilar der inf
    pygame.Rect(330, 80, 140, 34),        # barra central sup
    pygame.Rect(330, HEIGHT-80-34, 140, 34)  # barra central inf
]

# Fuentes y botones del menu
font_big = pygame.font.SysFont(None, 48)
font_small = pygame.font.SysFont(None, 36)
btn_jugar = pygame.Rect(300, 220, 200, 50)
btn_conf = pygame.Rect(300, 295, 200, 50)
btn_salir = pygame.Rect(300, 370, 200, 50)
btn_conf_mas = pygame.Rect(520, 180, 40, 40)
btn_conf_menos = pygame.Rect(240, 180, 40, 40)
btn_conf_volver = pygame.Rect(320, 330, 160, 45)

# Musica de fondo
volumen = cargar_volumen()
def iniciar_musica(nivel=1):
    """Inicia la musica del nivel especificado respetando el volumen configurado.
    
    Parametros:
    - nivel: 1 para lvl1.mp3, 2 para lvl2.mp3
    """
    music_path = f'musica/lvl{nivel}.mp3'
    try:
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(volumen)
        pygame.mixer.music.play(-1)
    except:
        pass  # Si no existe el archivo, continuar sin musica
def detener_musica():
    pygame.mixer.music.stop()

# Cargar spritesheet del ninja
SPRITESHEET_PATH = 'imagenes/Ninja_attack_R.png'
FRAME_W, FRAME_H, NUM_FRAMES = 128, 128, 9
spritesheet = pygame.image.load(SPRITESHEET_PATH).convert_alpha()

# Lista de frames del ninja extraida del spritesheet
ninja_frames = [
    spritesheet.subsurface(pygame.Rect(ix * FRAME_W, 0, FRAME_W, FRAME_H))
    for ix in range(NUM_FRAMES)
]

# Cargar spritesheet de enemigos (color rojo)
ENEMY_SPRITESHEET_PATH = 'imagenes/Enemy_attack_R.png'
enemy_spritesheet = pygame.image.load(ENEMY_SPRITESHEET_PATH).convert_alpha()
enemy_frames = [
    enemy_spritesheet.subsurface(pygame.Rect(ix * FRAME_W, 0, FRAME_W, FRAME_H))
    for ix in range(NUM_FRAMES)
]

# Cargar spritesheet del ShurikenEnemy (color negro)
SHURIKEN_ENEMY_SPRITESHEET_PATH = 'imagenes/ShurikenEnemy_attack_R.png'
shuriken_enemy_spritesheet = pygame.image.load(SHURIKEN_ENEMY_SPRITESHEET_PATH).convert_alpha()
shuriken_enemy_frames = [
    shuriken_enemy_spritesheet.subsurface(pygame.Rect(ix * FRAME_W, 0, FRAME_W, FRAME_H))
    for ix in range(NUM_FRAMES)
]

# Cargar imagen del shuriken
SHURIKEN_PATH = 'imagenes/Shuriken.png'
shuriken_img = None
try:
    shuriken_img = pygame.image.load(SHURIKEN_PATH).convert_alpha()
    shuriken_img = pygame.transform.scale(shuriken_img, (16, 16))
except Exception:
    shuriken_img = None



# Funciones de colision y geometria
def ccw(A, B, C):
    """Helper para comprobar orientacion de tres puntos (counter-clockwise).
    Usada por la funcion de interseccion de lineas."""
    return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

def lines_intersect(A, B, C, D):
    """Comprueba si las lineas AB y CD se intersectan (algoritmo ccw)."""
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

def line_intersects_rect(p1, p2, rect):
    """Comprueba si la linea p1-p2 intersecta alguno de los lados de `rect`."""
    rect_lines = [
        ((rect.left, rect.top), (rect.right, rect.top)),
        ((rect.right, rect.top), (rect.right, rect.bottom)),
        ((rect.right, rect.bottom), (rect.left, rect.bottom)),
        ((rect.left, rect.bottom), (rect.left, rect.top)),
    ]
    return any(lines_intersect(p1, p2, r1, r2) for r1, r2 in rect_lines)

def resolve_player_collisions(px, py, dx, dy):
    """Resuelve colisiones del jugador contra los obstaculos.
    Se prueba el movimiento en X y Y por separado y se anula el componente
    de movimiento que produciria una colision con cualquiera de los rects
    definidos en `obstacles`."""
    rect = pygame.Rect(0, 0, player_radius*2, player_radius*2)

    # Probar movimiento en X
    rect.center = (px + dx, py)
    for obs in obstacles:
        if rect.colliderect(obs):
            dx = 0

    # Probar movimiento en Y
    rect.center = (px, py + dy)
    for obs in obstacles:
        if rect.colliderect(obs):
            dy = 0

    return dx, dy

# Clase para enemigos
class Enemy:
    """Representa un enemigo del modo horda.

    Estado y comportamiento principales:
    - `pos`: posicion (x,y) en pantalla.
    - patrullan por waypoints cuando no detectan al jugador.
    - si detectan al jugador (FOV + line-of-sight) persigue con velocidad aumentada
      y notifica una `GLOBAL_ALERT` para que otros enemigos investiguen.
    - si llega a una `last_seen_pos` la investiga durante `search_time`.

    Nota: muchos parametros como `base_speed`, `search_time` y `response_delay`
    son aleatorios para variar el comportamiento entre enemigos.
    """

    def __init__(self, x, y):
        """Inicializa un enemigo en `(x, y)`.

        Parametros:
        - x, y: coordenadas iniciales.
        """
        self.pos = [x, y]
        self.size = 50  # Hitbox cuadrada (pixels)
        self.angle = random.uniform(0, math.pi * 2)
        # velocidad base de patrulla (pixels/frame)
        self.base_speed = random.uniform(1.8, 2.4)
        # campo de vision (grados) y radio de vision (pixeles)
        self.fov = 90
        self.radius = 200
        self.body_rect = pygame.Rect(0, 0, self.size, self.size)
        # Animacion del enemigo: usar el mismo spritesheet que el jugador
        self.anim = 0
        self.sees_player = False
        # comportamiento de patrulla/busqueda
        self.target = None
        self.last_seen_pos = None
        self.search_timer = 0.0
        self.search_time = 2.0  # segundos a buscar en last_seen_pos
        self.arrive_dist = 12
        # helpers para detectar estancamiento
        self._last_pos = self.pos[:]
        self._stuck_time = 0.0
        # retardo antes de responder a una alerta global (segundos)
        self.response_delay = random.uniform(0.0, 1.5)

    def can_see_player(self, player_pos):
        """Comprueba si el jugador es visible para este enemigo.

        Verifica distancia dentro de `radius`, angulo dentro de `fov` y
        linea de vision sin obstaculos (usa `line_intersects_rect`).

        Devuelve `True` si el jugador esta visible, `False` en caso contrario.
        """
        dx = player_pos[0] - self.pos[0]; dy = player_pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist > self.radius:
            return False
        dir_vec = (math.cos(self.angle), math.sin(self.angle))
        to_player = (dx/dist, dy/dist) if dist > 0 else (0, 0)
        dot = dir_vec[0] * to_player[0] + dir_vec[1] * to_player[1]
        # clamp y conversion a grados
        angle_to_player = math.degrees(math.acos(max(-1, min(1, dot))))
        if angle_to_player > self.fov / 2:
            return False
        # comprobar si hay algun obstaculo entre enemigo y jugador
        for obs in obstacles:
            if line_intersects_rect(self.pos, player_pos, obs):
                return False
        return True

    def move_with_collisions(self, nx, ny):
        """Mueve al enemigo aplicando colisiones simples contra `obstacles`.

        Parametros:
        - nx, ny: desplazamientos deseados en pixeles (pueden venir ya multiplicados
          por velocidad y dt en el codigo llamante).

        La funcion intenta mover en X y Y por separado comprobando colisiones;
        si no puede moverse en ninguno de los ejes (completamente atascado),
        aplica un "rebote" aleatorio para liberarlo.
        """
        self.body_rect.center = (self.pos[0], self.pos[1])
        test_rect = self.body_rect.copy()
        test_rect.centerx = int(self.pos[0] + nx)
        moved = False
        if (not any(test_rect.colliderect(obs) for obs in obstacles)) and 0 < test_rect.centerx < WIDTH:
            self.pos[0] += nx
            moved = True
        test_rect = self.body_rect.copy()
        test_rect.centery = int(self.pos[1] + ny)
        if (not any(test_rect.colliderect(obs) for obs in obstacles)) and 0 < test_rect.centery < HEIGHT:
            self.pos[1] += ny
            moved = True
        # "Rebote" si esta completamente atorado: girar y empujar ligeramente
        if not moved:
            self.angle += math.radians(120 + random.uniform(-30, 30))
            self.pos[0] += math.cos(self.angle) * 20
            self.pos[1] += math.sin(self.angle) * 20
            self.pos[0] = max(self.size/2 + 32, min(WIDTH - self.size/2 - 32, self.pos[0]))
            self.pos[1] = max(self.size/2 + 32, min(HEIGHT - self.size/2 - 32, self.pos[1]))
        self.body_rect.center = (int(self.pos[0]), int(self.pos[1]))
    def choose_new_target(self):
        """Elige un nuevo waypoint aleatorio valido para patrullar.

        Intenta hasta 30 veces escoger una posicion aleatoria que no colisione
        con ningun `obstacle`. Si falla, genera un fallback cerca de la posicion
        actual.
        """
        for _ in range(30):
            tx = random.randint(60, WIDTH - 60)
            ty = random.randint(60, HEIGHT - 60)
            test_rect = pygame.Rect(0, 0, 8, 8)
            test_rect.center = (tx, ty)
            if not any(test_rect.colliderect(o) for o in obstacles):
                self.target = [tx, ty]
                return
        # fallback: si falla, usa posicion actual + vector aleatorio
        self.target = [self.pos[0] + random.randint(-100, 100), self.pos[1] + random.randint(-100, 100)]

    def update(self, player_pos, dt):
        """Actualiza el estado del enemigo por frame.

        Parametros:
        - player_pos: posicion actual del jugador [x, y].
        - dt: delta time en segundos desde el ultimo frame.

        Comportamiento principal:
        1. Si ve al jugador: persigue y lanza `GLOBAL_ALERT` con la posicion.
        2. Si no lo ve: si hay `GLOBAL_ALERT` y ya paso su `response_delay`, va
           a investigar esa posicion.
        3. Si tiene `last_seen_pos` personal, la investiga durante `search_time`.
        4. En ausencia de lo anterior, patrulla hacia `target` (waypoint).
        """
        # dt en segundos
        visible = self.can_see_player(player_pos)
        self.sees_player = visible
        if visible:
            # Cuando detecta al jugador, registrar ultima posicion vista y perseguir
            self.last_seen_pos = list(player_pos)
            self.search_timer = 0.0
            # activar alerta global para que otros enemigos investiguen con retardo
            GLOBAL_ALERT["pos"] = list(player_pos)
            GLOBAL_ALERT["time"] = 0.0
            GLOBAL_ALERT["active"] = True
            dx = player_pos[0] - self.pos[0]; dy = player_pos[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            if dist > 0:
                # perseguir ligeramente mas rapido que el jugador
                CHASE_MULTIPLIER = 1.1
                chase_speed = max(self.base_speed, player_speed * CHASE_MULTIPLIER)
                nx = (dx / dist) * chase_speed; ny = (dy / dist) * chase_speed
                self.move_with_collisions(nx, ny)
            self.angle = math.atan2(dy, dx)
        else:
            # Si existe una alerta global reciente y ya paso nuestro response_delay, investigarla
            if GLOBAL_ALERT["active"] and GLOBAL_ALERT["pos"] is not None and GLOBAL_ALERT["time"] >= self.response_delay:
                tx, ty = GLOBAL_ALERT["pos"]
                dx = tx - self.pos[0]; dy = ty - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    nx = (dx/dist) * self.base_speed; ny = (dy/dist) * self.base_speed
                    self.move_with_collisions(nx, ny)
                    self.angle = math.atan2(dy, dx)
                # si llegamos cerca de la posicion de alerta, consideramos investigado
                if dist <= self.arrive_dist:
                    self.last_seen_pos = None
                    self.search_timer = self.search_time
                else:
                    self.search_timer += dt
            # Si tenemos una ultima posicion vista (personal), ir a investigarla durante search_time
            elif self.last_seen_pos is not None and self.search_timer < self.search_time:
                tx, ty = self.last_seen_pos
                dx = tx - self.pos[0]; dy = ty - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    nx = (dx/dist) * self.base_speed; ny = (dy/dist) * self.base_speed
                    self.move_with_collisions(nx, ny)
                    self.angle = math.atan2(dy, dx)
                # si llegamos cerca de last_seen_pos, abandonamos la busqueda
                if dist <= self.arrive_dist:
                    self.last_seen_pos = None
                    self.search_timer = self.search_time
                else:
                    self.search_timer += dt
            else:
                # patrulla por waypoints
                if self.target is None:
                    self.choose_new_target()
                tx, ty = self.target
                dx = tx - self.pos[0]; dy = ty - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist <= self.arrive_dist:
                    # llegamos: elegimos nuevo objetivo
                    self.choose_new_target()
                else:
                    # mover hacia objetivo
                    nx = (dx/dist) * self.base_speed; ny = (dy/dist) * self.base_speed
                    self.move_with_collisions(nx, ny)
                    self.angle = math.atan2(dy, dx)
                # incrementar timer de busqueda si aplica
            if self.search_timer < self.search_time:
                self.search_timer += dt

        # comprobacion de estancamiento: si no nos movimos suficiente, contar tiempo y regenerar target
        moved_dist = math.hypot(self.pos[0] - self._last_pos[0], self.pos[1] - self._last_pos[1])
        if moved_dist < 1.0:
            self._stuck_time += dt
        else:
            self._stuck_time = 0.0
        if self._stuck_time > 0.5:
            # forzar nuevo objetivo
            self.choose_new_target()
            self._stuck_time = 0.0
        # actualizar last_pos para la proxima comprobacion
        self._last_pos[0], self._last_pos[1] = self.pos[0], self.pos[1]

        # Actualizar animacion: si vemos al jugador, avanzar frames, sino mostrar frame 0
        if self.sees_player:
            self.anim = (self.anim + 1) % NUM_FRAMES
        else:
            self.anim = 0

    def is_stealth_kill(self):
        """Verifica si el enemigo puede ser eliminado sigilosamente.

        Retorna True si el enemigo NO esta viendo al jugador (fuera de su cono de vision).
        """
        return not self.sees_player

    def draw(self, surface):
        """Dibuja al enemigo usando el mismo sprite que el jugador.

        Si `sees_player` es True se anima (ciclo de frames), si no muestra el
        primer frame (indice 0). El sprite se rota para apuntar en la direccion
        del enemigo.
        """
        # Elegir frame del spritesheet de enemigo (usa la lista global `enemy_frames`)
        frame_img = enemy_frames[self.anim % NUM_FRAMES]
        sprite_rot = pygame.transform.rotate(frame_img, -math.degrees(self.angle))
        rect = sprite_rot.get_rect(center=(int(self.pos[0]), int(self.pos[1])))
        surface.blit(sprite_rot, rect)

    def draw_vision(self, surface):
        """Dibuja el cono de vision (semi-transparente) para debug/visualizacion."""
        vision_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        half_fov = math.radians(self.fov / 2)
        left_angle = self.angle - half_fov; right_angle = self.angle + half_fov
        p1 = (self.pos[0], self.pos[1])
        p2 = (self.pos[0] + math.cos(left_angle) * self.radius,
              self.pos[1] + math.sin(left_angle) * self.radius)
        p3 = (self.pos[0] + math.cos(right_angle) * self.radius,
              self.pos[1] + math.sin(right_angle) * self.radius)
        pygame.draw.polygon(vision_surface, (255, 0, 0, 60), [p1, p2, p3])
        surface.blit(vision_surface, (0, 0))

class ShurikenEnemy(Enemy):
    """Enemigo que puede lanzar shurikens hacia el jugador cuando lo detecta.

    Hereda de Enemy pero con comportamiento adicional:
    - Cuando ve al jugador, se queda en posicion y lanza shurikens hacia el.
    - Tiene cooldown entre lanzamientos.
    - El metodo update devuelve una lista de shurikens lanzados en este frame.
    """

    def __init__(self, x, y):
        """Inicializa un ShurikenEnemy en (x, y)."""
        super().__init__(x, y)
        self.shuriken_cooldown = 0.0

    def update(self, player_pos, dt):
        """Actualiza el enemigo y retorna lista de shurikens lanzados en este frame.

        Parametros:
        - player_pos: posicion actual del jugador [x, y].
        - dt: delta time en segundos desde el ultimo frame.

        Retorna:
        - Lista de diccionarios con shurikens lanzados: {"rect": rect, "dir": (dx, dy), "source": "enemy"}
        """
        new_shurikens = []

        # Actualizar cooldown
        if self.shuriken_cooldown > 0:
            self.shuriken_cooldown -= dt

        # Comprobar si ve al jugador
        visible = self.can_see_player(player_pos)
        self.sees_player = visible

        if visible:
            # Cuando detecta al jugador, registrar ultima posicion vista
            self.last_seen_pos = list(player_pos)
            self.search_timer = 0.0
            # activar alerta global para que otros enemigos investiguen con retardo
            GLOBAL_ALERT["pos"] = list(player_pos)
            GLOBAL_ALERT["time"] = 0.0
            GLOBAL_ALERT["active"] = True

            # Calcular vector hacia el jugador
            dx = player_pos[0] - self.pos[0]
            dy = player_pos[1] - self.pos[1]
            dist = math.hypot(dx, dy)

            if dist > 0:
                self.angle = math.atan2(dy, dx)

                # Lanzar shuriken si el cooldown ha terminado
                if self.shuriken_cooldown <= 0:
                    # Direccion normalizada
                    shoot_dx = dx / dist
                    shoot_dy = dy / dist

                    # Crear rect del shuriken
                    if shuriken_img is not None:
                        rect = shuriken_img.get_rect(center=(self.pos[0], self.pos[1]))
                    else:
                        rect = pygame.Rect(self.pos[0], self.pos[1], 8, 8)
                        rect.center = (self.pos[0], self.pos[1])

                    # Agregar shuriken a la lista
                    new_shurikens.append({"rect": rect, "dir": (shoot_dx, shoot_dy), "source": "enemy"})
                    self.shuriken_cooldown = shuriken_cooldown  # Reiniciar cooldown

            # NO PERSEGUIR: simplemente quedarse en posicion mientras lanza
        else:
            # Si existe una alerta global reciente y ya paso nuestro response_delay, investigarla
            if GLOBAL_ALERT["active"] and GLOBAL_ALERT["pos"] is not None and GLOBAL_ALERT["time"] >= self.response_delay:
                tx, ty = GLOBAL_ALERT["pos"]
                dx = tx - self.pos[0]; dy = ty - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    nx = (dx/dist) * self.base_speed; ny = (dy/dist) * self.base_speed
                    self.move_with_collisions(nx, ny)
                    self.angle = math.atan2(dy, dx)
                # si llegamos cerca de la posicion de alerta, consideramos investigado
                if dist <= self.arrive_dist:
                    self.last_seen_pos = None
                    self.search_timer = self.search_time
                else:
                    self.search_timer += dt
            # Si tenemos una ultima posicion vista (personal), ir a investigarla durante search_time
            elif self.last_seen_pos is not None and self.search_timer < self.search_time:
                tx, ty = self.last_seen_pos
                dx = tx - self.pos[0]; dy = ty - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    nx = (dx/dist) * self.base_speed; ny = (dy/dist) * self.base_speed
                    self.move_with_collisions(nx, ny)
                    self.angle = math.atan2(dy, dx)
                # si llegamos cerca de last_seen_pos, abandonamos la busqueda
                if dist <= self.arrive_dist:
                    self.last_seen_pos = None
                    self.search_timer = self.search_time
                else:
                    self.search_timer += dt
            else:
                # patrulla por waypoints
                if self.target is None:
                    self.choose_new_target()
                tx, ty = self.target
                dx = tx - self.pos[0]; dy = ty - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist <= self.arrive_dist:
                    # llegamos: elegimos nuevo objetivo
                    self.choose_new_target()
                else:
                    # mover hacia objetivo
                    nx = (dx/dist) * self.base_speed; ny = (dy/dist) * self.base_speed
                    self.move_with_collisions(nx, ny)
                    self.angle = math.atan2(dy, dx)
                # incrementar timer de busqueda si aplica
            if self.search_timer < self.search_time:
                self.search_timer += dt

        # comprobacion de estancamiento: si no nos movimos suficiente, contar tiempo y regenerar target
        moved_dist = math.hypot(self.pos[0] - self._last_pos[0], self.pos[1] - self._last_pos[1])
        if moved_dist < 1.0:
            self._stuck_time += dt
        else:
            self._stuck_time = 0.0
        if self._stuck_time > 0.5:
            # forzar nuevo objetivo
            self.choose_new_target()
            self._stuck_time = 0.0
        # actualizar last_pos para la proxima comprobacion
        self._last_pos[0], self._last_pos[1] = self.pos[0], self.pos[1]

        # Actualizar animacion: si vemos al jugador, avanzar frames, sino mostrar frame 0
        if self.sees_player:
            self.anim = (self.anim + 1) % NUM_FRAMES
        else:
            self.anim = 0

        return new_shurikens

    def draw(self, surface):
        """Dibuja al ShurikenEnemy usando su spritesheet sin animacion.

        Siempre muestra el frame 1 (segundo frame) - sin animacion, solo rota segun la direccion.
        """
        # Usar siempre el segundo frame (index 1)
        frame_img = shuriken_enemy_frames[1]
        sprite_rot = pygame.transform.rotate(frame_img, -math.degrees(self.angle))
        rect = sprite_rot.get_rect(center=(int(self.pos[0]), int(self.pos[1])))
        surface.blit(sprite_rot, rect)

def reset_game():
    """Crea y devuelve el estado inicial del juego (diccionario `state`).

    Incluye la lista inicial de enemigos, la posicion del jugador y flags de juego.
    """
    enemies = [Enemy(random.randint(60, WIDTH - 60), random.randint(60, HEIGHT - 60)) for _ in range(3)]
    return {
        "player_pos": [400, 300],
        "katana_active": False,
        "katana_angle": 0,
        "katana_direction": 1,
        "shurikens": [],
        "enemies": enemies,
        "wave": 1,
        "game_over": False,
        "player_anim": 0,
        "shuriken_cooldown": 0.0,  # Cooldown del jugador para lanzar shurikens
        "score": 0,  # Puntuacion del jugador
        "player_name": None,
        "score_saved": False
    }

state = reset_game()
clock = pygame.time.Clock()
def draw_player(surface, pos, angle, anim):
    """Dibuja el sprite del jugador rotado segun `angle`.

    Parametros:
    - surface: surface destino donde dibujar.
    - pos: [x, y] posicion del jugador.
    - angle: angulo en radianes hacia donde mira el jugador.
    - anim: indice de animacion (se usa modulo `NUM_FRAMES`).
    """
    frame_img = ninja_frames[anim % NUM_FRAMES]
    sprite_rot = pygame.transform.rotate(frame_img, -math.degrees(angle))
    rect = sprite_rot.get_rect(center=(int(pos[0]), int(pos[1])))
    surface.blit(sprite_rot, rect)

def draw_crosshair(surface, pos, color=WHITE, size=15, thickness=2):
    """Dibuja una cruceta siguiendo al mouse.

    Parametros:
    - surface: destino donde dibujar.
    - pos: [x, y] posicion del mouse.
    - color: color de la cruceta (por defecto rojo).
    - size: brazos de la cruz (pixeles desde el centro).
    - thickness: grosor de las lineas.
    """
    x, y = int(pos[0]), int(pos[1])
    # Linea horizontal
    pygame.draw.line(surface, color, (x - size, y), (x + size, y), thickness)
    # Linea vertical
    pygame.draw.line(surface, color, (x, y - size), (x, y + size), thickness)
    # Circulo central
    pygame.draw.circle(surface, color, (x, y), 3)

menu_state = 'menu_principal'
name_input = ""  # espacio para ingresar nombre del jugador al iniciar partida

# BUCLE PRINCIPAL DEL JUEGO
while True:
    dt = clock.tick(60)  # Tiempo en ms desde el ultimo frame; se convierte a segundos al pasar a enemigos

    # Actualizar temporizador de alerta global (segundos)
    # Si hay una alerta activa y expira, desactivarla
    if GLOBAL_ALERT.get("active"):
        GLOBAL_ALERT["time"] += dt / 1000.0
        if GLOBAL_ALERT["time"] > GLOBAL_ALERT.get("duration", 6.0):
            GLOBAL_ALERT["active"] = False
            GLOBAL_ALERT["pos"] = None

    angle = 0  # Angulo hacia el mouse (se actualiza en modo "jugando")

    # PROCESAR EVENTOS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if menu_state == 'menu_principal':
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_jugar.collidepoint(event.pos):
                    # Pedir nombre ANTES de iniciar la partida
                    menu_state = 'input_name'
                    name_input = ""
                elif btn_conf.collidepoint(event.pos):
                    menu_state = 'configuracion'
                elif btn_salir.collidepoint(event.pos):
                    pygame.quit(); sys.exit()

        # Captura de nombre del jugador ANTES de iniciar
        elif menu_state == 'input_name':
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    name_input = name_input[:-1]
                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    # Iniciar partida solo si hay nombre
                    if name_input.strip() != "":
                        # Guardar nombre y crear estado inicial
                        state = reset_game()
                        state['player_name'] = name_input.strip()
                        state['score'] = 0
                        state['score_saved'] = False
                        iniciar_musica()
                        menu_state = 'jugando'
                else:
                    # Limitar caracteres y longitud
                    if len(name_input) < 16 and event.unicode.isprintable():
                        name_input += event.unicode

        # Menu de configuracion: ajuste de volumen y salida
        elif menu_state == 'configuracion':
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_conf_mas.collidepoint(event.pos):
                    volumen = min(1.0, round(volumen + 0.05, 2))
                    guardar_volumen(volumen)
                    pygame.mixer.music.set_volume(volumen)
                elif btn_conf_menos.collidepoint(event.pos):
                    volumen = max(0.0, round(volumen - 0.05, 2))
                    guardar_volumen(volumen)
                    pygame.mixer.music.set_volume(volumen)
                elif btn_conf_volver.collidepoint(event.pos):
                    menu_state = 'menu_principal'
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                menu_state = 'menu_principal'
                detener_musica()

        # Modo juego: manejo de controles del jugador
        elif menu_state == 'jugando':
            if state["game_over"]:
                # Game Over: permite reiniciar o volver al menu
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    # Reiniciar partida sin pedir nombre nuevamente
                    preserved_name = state.get('player_name')
                    state = reset_game()
                    if preserved_name:
                        state['player_name'] = preserved_name
                    iniciar_musica()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    menu_state = 'menu_principal'
            else:
                # Mientras se juega: manejo de katana, shurikens y pausa
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    state["katana_active"] = True  # Click izquierdo: activar katana
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    state["katana_active"] = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    # Click derecho: lanzar shuriken hacia el mouse (con cooldown)
                    if state["shuriken_cooldown"] <= 0:
                        mx, my = pygame.mouse.get_pos()
                        dx = mx - state["player_pos"][0]
                        dy = my - state["player_pos"][1]
                        length = max(1, math.hypot(dx, dy))
                        dx /= length; dy /= length
                        if shuriken_img is not None:
                            rect = shuriken_img.get_rect(center=(state["player_pos"][0], state["player_pos"][1]))
                        else:
                            rect = pygame.Rect(state["player_pos"][0], state["player_pos"][1], 8, 8)
                            rect.center = (state["player_pos"][0], state["player_pos"][1])
                        state["shurikens"].append({"rect": rect, "dir": (dx, dy), "source": "player"})
                        state["shuriken_cooldown"] = shuriken_cooldown  # Iniciar cooldown
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    menu_state = 'menu_principal'  # ESC: volver al menu
                    detener_musica()

    # RENDERIZAR ESCENA
    if menu_state == 'jugando':
        screen.fill(BROWN_LIGHT)  # Fondo cafe en el juego
    else:
        screen.fill(BLACK)  # Fondo negro en menu/configuracion

    if menu_state == 'jugando':
        # Renderizar obstaculos del mapa
        for obs in obstacles:
            pygame.draw.rect(screen, BROWN_DARK, obs)

        # Actualizar logica del juego (si no es game over)
        if not state["game_over"]:
            # Actualizar cooldown del jugador
            if state["shuriken_cooldown"] > 0:
                state["shuriken_cooldown"] -= dt / 1000.0

            keys = pygame.key.get_pressed()
            dx_move = (keys[pygame.K_d] - keys[pygame.K_a]) * player_speed
            dy_move = (keys[pygame.K_s] - keys[pygame.K_w]) * player_speed
            rdx, rdy = resolve_player_collisions(state["player_pos"][0], state["player_pos"][1], dx_move, dy_move)
            state["player_pos"][0] += rdx; state["player_pos"][1] += rdy
            state["player_pos"][0] = max(player_radius+34, min(WIDTH - player_radius-34, state["player_pos"][0]))
            state["player_pos"][1] = max(player_radius+34, min(HEIGHT - player_radius-34, state["player_pos"][1]))
            mx, my = pygame.mouse.get_pos()
            dxm = mx - state["player_pos"][0]; dym = my - state["player_pos"][1]
            angle = math.atan2(dym, dxm)
            if state["katana_active"]:
                state["player_anim"] = (state["player_anim"] + 1) % NUM_FRAMES
            else:
                state["player_anim"] = 0
            draw_player(screen, state["player_pos"], angle, state["player_anim"])
            if state["katana_active"]:
                katana_angle += katana_speed * katana_direction
                if abs(katana_angle) > 60: katana_direction *= -1
                total_angle = math.degrees(angle) + katana_angle
                rad = math.radians(total_angle)
                katana_x = state["player_pos"][0] + math.cos(rad) * katana_length
                katana_y = state["player_pos"][1] + math.sin(rad) * katana_length
                katana_rect = pygame.Rect(0, 0, 20, 20); katana_rect.center = (katana_x, katana_y)
                for e in state["enemies"][:]:
                    if katana_rect.colliderect(e.body_rect):
                        # Calcular puntos base
                        base_points = 25 if isinstance(e, ShurikenEnemy) else 10
                        # Bonificacion x2 si es eliminacion sigilosa
                        if e.is_stealth_kill():
                            state["score"] += base_points * 2
                        else:
                            state["score"] += base_points
                        state["enemies"].remove(e)
            else:
                katana_angle = 0
            # Mover shurikens y comprobar colisiones contra paredes
            shurikens = []
            for s in state["shurikens"]:
                s["rect"].x += int(s["dir"][0] * shuriken_speed)
                s["rect"].y += int(s["dir"][1] * shuriken_speed)
                # Si colisiona con cualquier obstaculo, eliminar el shuriken
                if any(s["rect"].colliderect(obs) for obs in obstacles):
                    continue
                # Mantener solo si esta dentro de la pantalla
                if s["rect"].right < 0 or s["rect"].left > WIDTH or s["rect"].bottom < 0 or s["rect"].top > HEIGHT:
                    continue
                shurikens.append(s)
            state["shurikens"] = shurikens

            # Comprobar colisiones shuriken-enemigo (solo shurikens del jugador)
            for s in state["shurikens"][:]:
                if s.get("source") == "enemy":
                    continue  # Los shurikens de enemigos no destruyen enemigos
                for e in state["enemies"][:]:
                    if s["rect"].colliderect(e.body_rect):
                        try:
                            # Calcular puntos base
                            base_points = 25 if isinstance(e, ShurikenEnemy) else 10
                            # Bonificacion x2 si es eliminacion sigilosa
                            if e.is_stealth_kill():
                                state["score"] += base_points * 2
                            else:
                                state["score"] += base_points
                            state["enemies"].remove(e)
                        except ValueError:
                            pass
                        try:
                            state["shurikens"].remove(s)
                        except ValueError:
                            pass
                        break

            # Actualizar enemigos y recolectar shurikens lanzados por ShurikenEnemy
            for e in state["enemies"]:
                if isinstance(e, ShurikenEnemy):
                    # El update retorna lista de shurikens lanzados
                    new_shurikens = e.update(state["player_pos"], dt/1000.0)
                    state["shurikens"].extend(new_shurikens)
                else:
                    # Enemigos normales solo actualizan
                    e.update(state["player_pos"], dt/1000.0)

            player_rect = pygame.Rect(0, 0, player_radius*2, player_radius*2)
            player_rect.center = (state["player_pos"][0], state["player_pos"][1])
            for e in state["enemies"]:
                if player_rect.colliderect(e.body_rect):
                    state["game_over"] = True
                    detener_musica()

            # Comprobar colision del jugador con shurikens de enemigos
            for s in state["shurikens"][:]:
                if s.get("source") == "enemy":
                    if player_rect.colliderect(s["rect"]):
                        state["game_over"] = True
                        detener_musica()
                        try:
                            state["shurikens"].remove(s)
                        except ValueError:
                            pass
            # Si ha muerto, guardar puntuacion
            if state.get("game_over") and not state.get("score_saved"):
                save_score(state.get('player_name'), state.get('score', 0))
                state['score_saved'] = True
            if len(state["enemies"])==0:
                state["wave"] += 1
                # Cambiar a musica de nivel 2 en ronda 7
                if state["wave"] == 7:
                    detener_musica()
                    iniciar_musica(nivel=2)
                # Limitar el crecimiento de enemigos para evitar ralentizacion
                # Formula: min(2 + wave, 10) max 10 enemigos normales
                normal_enemy_count = min(2 + state["wave"], 10)
                for _ in range(normal_enemy_count):
                    # spawnea solo en area segura, lejos del jugador
                    while True:
                        x = random.randint(60, WIDTH-60)
                        y = random.randint(60, HEIGHT-60)
                        if math.hypot(x-state["player_pos"][0], y-state["player_pos"][1])>200:
                            break
                    state["enemies"].append(Enemy(x, y))

                # A partir de la oleada 3, agregar ShurikenEnemy (max 5)
                if state["wave"] >= 3:
                    shuriken_enemy_count = min(state["wave"] - 2, 5)
                    for _ in range(shuriken_enemy_count):
                        while True:
                            x = random.randint(60, WIDTH-60)
                            y = random.randint(60, HEIGHT-60)
                            if math.hypot(x-state["player_pos"][0], y-state["player_pos"][1])>250:
                                break
                        state["enemies"].append(ShurikenEnemy(x, y))

        # RENDERIZAR ENEMIGOS Y PROYECTILES
        for e in state["enemies"]:
            # e.draw_vision (conos de vision para debug)
            e.draw(screen)
        for s in state["shurikens"]:
            if shuriken_img is not None:
                screen.blit(shuriken_img, s["rect"])  # Dibujar shuriken como imagen
            else:
                pygame.draw.rect(screen, WHITE, s["rect"])  # Dibujar shuriken como rectangulo blanco si no hay imagen

        # RENDERIZAR UI EN JUEGO
        wave_text = font_big.render(f"Oleada: {state['wave']}", True, WHITE)
        screen.blit(wave_text, (10, 10))
        score_text = font_big.render(f"Puntos: {state['score']}", True, WHITE)
        screen.blit(score_text, (WIDTH - score_text.get_width() - 10, 10))

        # PANTALLA GAME OVER
        if state["game_over"]:
            # Overlay semitransparente
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            # Mostrar tabla de clasificacion sobre el overlay
            leaders = load_leaderboard(5)
            box_w = 320
            bx = WIDTH - box_w - 10
            by = 10
            pygame.draw.rect(screen, (20, 20, 30, 180), (bx, by, box_w, 30 + len(leaders)*28))
            header = font_big.render("Los mejores ninjas", True, WHITE)
            screen.blit(header, (bx + 8, by + 2))
            # List entries
            for i, (n, sc) in enumerate(leaders):
                txt = font_small.render(f"{i+1}. {n} - {sc}", True, WHITE)
                screen.blit(txt, (bx + 8, by + 32 + i*28))
            # Mensaje de reinicio
            text = font_big.render("GAME OVER - Presiona R para reiniciar", True, (255, 255, 255))
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2))

    # MENU PRINCIPAL
    if menu_state == 'menu_principal':
        title = font_big.render("Ninja Fate", True, (220, 220, 80))
        screen.blit(title, (320, 110))
        # Boton Jugar
        pygame.draw.rect(screen, (60, 90, 200), btn_jugar)
        screen.blit(font_small.render("Jugar", True, WHITE), (btn_jugar.x + 34, btn_jugar.y + 11))
        # Boton Configuracion
        pygame.draw.rect(screen, (60, 110, 90), btn_conf)
        screen.blit(font_small.render("Configuracion", True, WHITE), (btn_conf.x + 6, btn_conf.y + 11))
        # Boton Salir
        pygame.draw.rect(screen, (200, 60, 60), btn_salir)
        screen.blit(font_small.render("Salir", True, WHITE), (btn_salir.x + 60, btn_salir.y + 11))
        # Leaderboard
        leaders = load_leaderboard(5)
        box_w = 320
        bx = WIDTH - box_w - 10
        by = 10
        pygame.draw.rect(screen, (30, 30, 40), (bx, by, box_w, 30 + len(leaders)*24))
        header = font_big.render("Los mejores ninjas", True, WHITE)
        screen.blit(header, (bx + 8, by + 2))
        for i, (n, sc) in enumerate(leaders):
            txt = font_small.render(f"{i+1}. {n} - {sc}", True, WHITE)
            screen.blit(txt, (bx + 8, by + 34 + i*22))

    # PANTALLA DE INGRESO DE NOMBRE ANTES DE JUGAR
    if menu_state == 'input_name':
        # Titulo
        label = font_big.render("Nombre del ninja:", True, WHITE)
        screen.blit(label, (WIDTH // 2 - label.get_width() // 2, 200))
        # Cuadro de texto
        box_w = 420
        box_h = 48
        bx = WIDTH // 2 - box_w // 2
        by = 260
        # Fondo blanco para el input y borde
        pygame.draw.rect(screen, WHITE, (bx, by, box_w, box_h))
        pygame.draw.rect(screen, BLACK, (bx, by, box_w, box_h), 2)
        # Muestra el texto ingresado
        display_text = name_input if name_input != "" else "_"
        txt_surf = font_small.render(display_text, True, BLACK)
        screen.blit(txt_surf, (bx + 10, by + (box_h - txt_surf.get_height()) // 2))
        # Instrucciones
        instr = font_small.render("Presiona Enter para comenzar", True, WHITE)
        screen.blit(instr, (WIDTH // 2 - instr.get_width() // 2, by + box_h + 12))

    # MENU CONFIGURACION
    if menu_state == 'configuracion':
        screen.fill((30, 30, 40))
        # Titulo
        txt = font_big.render("Configuracion", True, (220, 220, 220))
        screen.blit(txt, (220, 85))
        # Label de volumen
        txtvol = font_small.render("Volumen", True, (180, 230, 180))
        screen.blit(txtvol, (350, 160))
        # Boton menos (disminuir volumen)
        pygame.draw.rect(screen, (150, 220, 170), btn_conf_menos)
        screen.blit(font_small.render("-", True, BLACK), (btn_conf_menos.x + 11, btn_conf_menos.y + 1))
        # Boton mas (aumentar volumen)
        pygame.draw.rect(screen, (150, 220, 170), btn_conf_mas)
        screen.blit(font_small.render("+", True, BLACK), (btn_conf_mas.x + 11, btn_conf_mas.y + 1))
        # Display de volumen actual
        screen.blit(font_small.render(f"{int(volumen * 100)}%", True, WHITE), (375, 190))
        # Boton volver
        pygame.draw.rect(screen, (80, 80, 200), btn_conf_volver)
        screen.blit(font_small.render("Volver", True, WHITE), (btn_conf_volver.x + 35, btn_conf_volver.y + 7))

    # Dibujar cruceta del mouse (en todos los menus)
    pygame.mouse.set_visible(False)  # Ocultar cursor del mouse
    mouse_pos = pygame.mouse.get_pos()
    draw_crosshair(screen, mouse_pos)

    # Actualizar pantalla
    pygame.display.flip()
