import pygame
import sys
import math
import random
import sqlite3


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
        cur.execute('INSERT INTO config (id, volumen) VALUES (1, 0.2)')
        conn.commit()
        fila = (0.2,)

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

# Configuracion de pantalla
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ninja Fate")
icon = pygame.image.load('imagenes/icon.png').convert_alpha()
pygame.display.set_icon(icon)


# Colores
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GRAY = (100, 100, 100)
BLACK = (0, 0, 0)

# Alerta global para enemigos:
# todos recibiran la posicion "last seen" pero con un retardo individual
GLOBAL_ALERT = {"pos": None, "time": 0.0, "active": False, "duration": 6.0}

player_speed = 5
player_radius = 12
katana_length = 50
katana_speed = 30
katana_angle = 0
katana_direction = 1
shuriken_speed = 10

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
MUSIC_PATH = 'musica/lvl1.mp3'
def iniciar_musica():
    if MUSIC_PATH:
        pygame.mixer.music.load(MUSIC_PATH)
        pygame.mixer.music.set_volume(volumen)
        pygame.mixer.music.play(-1)
def detener_musica():
    if MUSIC_PATH:
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
        self.size = 25
        self.angle = random.uniform(0, math.pi * 2)
        # velocidad base de patrulla (pixels/frame)
        self.base_speed = random.uniform(1.8, 2.4)
        self.speed = self.base_speed
        # campo de vision (grados) y radio de vision (pixeles)
        self.fov = 90
        self.radius = 200
        self.stuck_timer = 0
        self.body_rect = pygame.Rect(0, 0, self.size, self.size)
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
        orig_pos = self.pos[:]
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
        if self.can_see_player(player_pos):
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

    def draw(self, surface):
        """Dibuja una representacion simple del enemigo (triangulo direccional)."""
        length = self.size; width = self.size / 1.5
        points = [(length, 0), (-length/2, -width/2), (-length/2, width/2)]
        rotated = []
        for x, y in points:
            rx = x * math.cos(self.angle) - y * math.sin(self.angle)
            ry = x * math.sin(self.angle) + y * math.cos(self.angle)
            rotated.append((self.pos[0] + rx, self.pos[1] + ry))
        pygame.draw.polygon(surface, RED, rotated)

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
        "player_anim": 0
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

menu_state = 'menu_principal'

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
                    menu_state = 'jugando'
                    state = reset_game()
                    iniciar_musica()
                elif btn_conf.collidepoint(event.pos):
                    menu_state = 'configuracion'
                elif btn_salir.collidepoint(event.pos):
                    pygame.quit(); sys.exit()
        
        # Menu de configuracion: ajuste de volumen y salida
        elif menu_state == 'configuracion':
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_conf_mas.collidepoint(event.pos):
                    volumen = min(1.0, volumen + 0.05)
                    guardar_volumen(volumen)
                    pygame.mixer.music.set_volume(volumen)
                elif btn_conf_menos.collidepoint(event.pos):
                    volumen = max(0.0, volumen - 0.05)
                    guardar_volumen(volumen)
                    pygame.mixer.music.set_volume(volumen)
                elif btn_conf_volver.collidepoint(event.pos):
                    menu_state = 'menu_principal'
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                menu_state = 'menu_principal'
        
        # Modo juego: manejo de controles del jugador
        elif menu_state == 'jugando':
            if state["game_over"]:
                # Game Over: solo permite reiniciar
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    state = reset_game()
            else:
                # Mientras se juega: manejo de katana, shurikens y pausa
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    state["katana_active"] = True  # Click izquierdo: activar katana
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    state["katana_active"] = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    # Click derecho: lanzar shuriken hacia el mouse
                    mx, my = pygame.mouse.get_pos()
                    dx = mx - state["player_pos"][0]
                    dy = my - state["player_pos"][1]
                    length = max(1, math.hypot(dx, dy))
                    dx /= length; dy /= length
                    state["shurikens"].append({
                        "rect": pygame.Rect(state["player_pos"][0], state["player_pos"][1], 8, 8),
                        "dir": (dx, dy)
                    })
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    menu_state = 'menu_principal'  # ESC: volver al menu
    
    # RENDERIZAR ESCENA
    screen.fill(BLACK)  # Limpiar pantalla
    
    if menu_state == 'jugando':
        # Renderizar obstaculos del mapa
        for obs in obstacles:
            pygame.draw.rect(screen, GRAY, obs)
        
        # Actualizar logica del juego (si no es game over)
        if not state["game_over"]:
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
                katana_angle, katana_direction
                katana_angle += katana_speed * katana_direction
                if abs(katana_angle) > 60: katana_direction *= -1
                total_angle = math.degrees(angle) + katana_angle
                rad = math.radians(total_angle)
                katana_x = state["player_pos"][0] + math.cos(rad) * katana_length
                katana_y = state["player_pos"][1] + math.sin(rad) * katana_length
                katana_rect = pygame.Rect(0, 0, 20, 20); katana_rect.center = (katana_x, katana_y)
                for e in state["enemies"][:]:
                    if katana_rect.colliderect(e.body_rect):
                        state["enemies"].remove(e)
            else:
                katana_angle = 0
            for s in state["shurikens"]:
                s["rect"].x += int(s["dir"][0] * shuriken_speed)
                s["rect"].y += int(s["dir"][1] * shuriken_speed)
            state["shurikens"] = [s for s in state["shurikens"] if 0 <= s["rect"].x <= WIDTH and 0 <= s["rect"].y <= HEIGHT]
            for s in state["shurikens"][:]:
                for e in state["enemies"][:]:
                    if s["rect"].colliderect(e.body_rect):
                        state["enemies"].remove(e)
                        state["shurikens"].remove(s)
                        break
            for e in state["enemies"]:
                e.update(state["player_pos"], dt/1000.0)
            player_rect = pygame.Rect(0, 0, player_radius*2, player_radius*2)
            player_rect.center = (state["player_pos"][0], state["player_pos"][1])
            for e in state["enemies"]:
                if player_rect.colliderect(e.body_rect):
                    state["game_over"] = True
            if len(state["enemies"])==0:
                state["wave"] += 1
                for _ in range(2 + state["wave"]):
                    # spawnea solo en area segura, lejos del jugador
                    while True:
                        x = random.randint(60, WIDTH-60)
                        y = random.randint(60, HEIGHT-60)
                        if math.hypot(x-state["player_pos"][0], y-state["player_pos"][1])>160:
                            break
                    state["enemies"].append(Enemy(x, y))
        for e in state["enemies"]:
            e.draw_vision(screen)
            e.draw(screen)
        # RENDERIZAR ENEMIGOS Y PROYECTILES
        for e in state["enemies"]:
            e.draw_vision(screen)  # Dibujar cono de vision (debug)
            e.draw(screen)  # Dibujar enemigo
        for s in state["shurikens"]:
            pygame.draw.rect(screen, WHITE, s["rect"])  # Dibujar shuriken
        
        # RENDERIZAR UI EN JUEGO
        wave_text = font_big.render(f"Oleada: {state['wave']}", True, WHITE)
        screen.blit(wave_text, (10, 10))
        
        # PANTALLA GAME OVER
        if state["game_over"]:
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
    
    # MENU CONFIGURACION
    if menu_state == 'configuracion':
        screen.fill((30, 30, 40))
        # Titulo
        txt = font_big.render("Configuracion", True, (220, 220, 220))
        screen.blit(txt, (220, 85))
        # Label de volumen
        txtvol = font_small.render("Volumen", True, (180, 230, 180))
        screen.blit(txtvol, (340, 182))
        # Boton menos (disminuir volumen)
        pygame.draw.rect(screen, (150, 220, 170), btn_conf_menos)
        screen.blit(font_small.render("-", True, BLACK), (btn_conf_menos.x + 11, btn_conf_menos.y + 1))
        # Boton mas (aumentar volumen)
        pygame.draw.rect(screen, (150, 220, 170), btn_conf_mas)
        screen.blit(font_small.render("+", True, BLACK), (btn_conf_mas.x + 11, btn_conf_mas.y + 1))
        # Display de volumen actual
        screen.blit(font_small.render(f"{int(volumen * 100)}%", True, WHITE), (330, 190))
        # Boton volver
        pygame.draw.rect(screen, (80, 80, 200), btn_conf_volver)
        screen.blit(font_small.render("Volver", True, WHITE), (btn_conf_volver.x + 35, btn_conf_volver.y + 7))
    
    # Actualizar pantalla
    pygame.display.flip()
