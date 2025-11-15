# Ninja Fate

## Descripcion General

**Ninja Fate** es un videojuego de accion arcade con vista desde arriba (top-down) donde controlas a un ninja que debe sobrevivir oleadas de enemigos en modo horda. El juego combina mecanicas clasicas de combate rapido con un sistema de IA para enemigos.

### Caracteristicas principales
-  Modo horda infinito con oleadas progresivas
-  Sistema de IA con patrullaje, persecucion y alerta global
-  Combate dinamico: katana (corta distancia) y shurikens (largo alcance)
-  Sistema de audio con control de volumen
-  Configuracion guardada en SQLite
-  Mecanica instakill (todo muere de un golpe)

---

## Objetivo del Juego

Sobrevive el mayor tiempo posible eliminando oleadas de enemigos. Cada oleada aumenta en dificultad:
- **Oleada 1**: 3 enemigos
- **Oleada 2**: 4 enemigos
- **Oleada 3**: 5 enemigos
- Y asi sucesivamente...

El juego termina cuando recibes un golpe de cualquier enemigo. Presiona **R** para reintentar.

---

## Controles


| **Movimiento** | `W` / `A` / `S` / `D` |
| **Atacar (Katana)** | Click izquierdo del mouse (mantener) |
| **Lanzar Shuriken** | Click derecho del mouse |
| **Menu/Pausa** | `ESC` |
| **Reiniciar** | `R` (en pantalla game over) |

### Detalles de Combate

**Katana (Corta Distancia)**
- Activacion: Click izquierdo y mantener
- Rango: 50 pixeles desde el jugador
- Efecto: Rota continuamente mientras se ataca
- Fuerza: Instakill a enemigos

**Shurikens (Largo Alcance)**
- Activacion: Click derecho hacia el mouse
- Velocidad: 10 pixeles/frame
- Alcance: Ilimitado hasta borde de pantalla
- Fuerza: Instakill a enemigos

---

## Enemigos

### Comportamiento de IA

Los enemigos implementan un sistema de IA:

1. **Patrullaje por Waypoints**
   - Movimiento aleatorio cuando no detectan al jugador
   - Velocidad base: 1.8-2.4 pixeles/frame
   - Objetivo: Parecer natural e impredecible

2. **Deteccion del Jugador**
   - Campo de vision (FOV): 90 grados
   - Radio de vision: 200 pixeles
   - Linea de vision: Los obstaculos bloquean la vision
   - Algoritmo: CCW (Counter-Clockwise) para intersecciones precisas

3. **Persecucion**
   - Se activa cuando el jugador es visible
   - Velocidad: 1.1x la velocidad del ninja (5.5 pixeles/frame)
   - Efecto: Lanza alerta global para otros enemigos

4. **Sistema de Alerta Global**
   - Cuando un enemigo ve al jugador, notifica a todos
   - Otros enemigos responden con retardo individual (0.0-1.5 segundos)
   - Crea efecto de "llamada de refuerzo" realista
   - Duracion: 6 segundos

5. **Investigacion de Ultimas Posiciones Vistas**
   - Si pierden al jugador, investigan su ultima posicion conocida
   - Duracion de busqueda: 2 segundos
   - Si no encuentran nada, regresan a patrullaje

6. **Deteccion de Estancamiento**
   - Si se quedan atrapados 0.5+ segundos, hacen un "rebote"
   - Giran ~120 grados y se empujan 20 pixeles
   - Previene comportamiento erratico

### Caracteristicas Tecnicas

- **Dimensiones**: 25 pixeles de radio
- **Velocidad de patrulla**: 1.8-2.4 pixeles/frame
- **Velocidad de persecucion**: ~5.5 pixeles/frame
- **Distancia de llegada**: 12 pixeles (consideran que llegaron al objetivo)
- **Retardo individual de alerta**: 0.0-1.5 segundos (aleatorio)

---

## Jugador (Ninja)

### Estadisticas
- **Velocidad**: 5 pixeles/frame (400 pixeles/segundo logico)
- **Radio**: 12 pixeles
- **Durabilidad**: 1 golpe (instakill)
- **Armas**: Katana + Shurikens ilimitados

### Mecanicas de Movimiento
- Movimiento en 8 direcciones (WASD)
- Colisiones contra obstaculos: Movimiento separado en X/Y
- Deslizamiento por paredes cuando chocas diagonalmente
- Limites de pantalla: No puedes salir del mapa

### Sistema de Animacion
- **Frames**: 9 sprites de ataque
- **Velocidad**: 1 frame por update de juego
- **Rotacion**: Sigue la direccion del mouse
- **Ciclo**: Se reinicia cada ataque

---

## Mapa

### Dimensiones
- **Resolucion**: 800x600 pixeles
- **Area jugable**: 766x568 pixeles (menos bordes)

### Obstaculos
```
Paredes perimetrales: 32 pixeles de grosor
- Pared arriba
- Pared abajo
- Pared izquierda
- Pared derecha

Pilares interiores:
- Pilar izquierda superior: 34x100 pixeles
- Pilar derecha inferior: 34x100 pixeles

Barras centrales:
- Barra central superior: 140x34 pixeles
- Barra central inferior: 140x34 pixeles
```

**Nota**: Los obstaculos bloquean:
- Movimiento del jugador
- Movimiento de enemigos
- Vision de enemigos (linea de vision)

---

## Configuracion

### Menu de Configuracion
Accede desde el menu principal presionando **Configuracion**.

**Opciones disponibles:**
- **Volumen**: 0-100% (guardado en base de datos)
- **Resolucion**: (Futuro)

**Controles en Configuracion:**
- `+` button: Aumentar volumen (+5%)
- `-` button: Disminuir volumen (-5%)
- `Volver`: Regresa al menu principal
- `ESC`: Regresa al menu principal

### Persistencia de Datos
- Los ajustes se guardan automaticamente en `config.db`
- Base de datos SQLite local
- El volumen persiste entre sesiones

---

## Audio

- **Musica de fondo**: `musica/lvl1.mp3`
- **Ciclo**: Loop infinito durante el juego
- **Control**: Menu de configuracion
- **Volumen por defecto**: 20%

**Comportamiento:**
- Inicia al presionar "Jugar"
- Se detiene al volver al menu principal
- Persiste el volumen configurado

---

## Estructura de Proyecto

```
game2025-sarabia/
├── Main.py                    # Archivo principal
├── README.md                  # Este archivo
├── config.db                  # Base de datos (generada al ejecutar)
├── imagenes/
│   ├── Ninja_attack_R.png     # Spritesheet ninja (9 frames)
│   ├── lvl1.png               # Fondo del mapa (800x600)
│   ├── icon.png               # Icono de ventana
│   └── Frames/                # Frames individuales (backup)
└── musica/
    └── lvl1.mp3               # Musica de fondo
```

---

## Requisitos del Sistema

### Dependencias
- **Python**: 3.8 o superior
- **Pygame**: 2.0+
- **SQLite3**: Incluido en Python

### Hardware Minimo
- **CPU**: Procesador dual-core
- **RAM**: 512 MB
- **Resolucion**: 800x600 pixeles
- **GPU**: Cualquiera con soporte para 2D

---

## Instalacion (entorno virtual recomendado)

Se recomienda usar un entorno virtual (`venv`) para mantener las dependencias aisladas. A continuacion tienes instrucciones para crear y usar un `venv` en `./.venv` (Python 3.10 recomendado).

1) Crear el entorno virtual (usa Python 3.10 si lo tienes):

```powershell
# Windows (PowerShell)
py -3.10 -m venv .venv
# Si no tienes el lanzador `py`, usa:
python -m venv .venv
```

2) Activar el entorno virtual:

```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1

# CMD (Windows)
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

3) Actualizar pip e instalar dependencias:

```powershell
python -m pip install --upgrade pip
python -m pip install pygame
```

4) Guardar las dependencias instaladas (una vez instaladas) en `requirements.txt`:

```powershell
python -m pip freeze > requirements.txt
```

5) Ejecutar el juego:

```powershell
python Main.py
```

6) Salir / desactivar el entorno:

```powershell
deactivate
```

---

Nota: Añadi un `.gitignore` para excluir el directorio `.venv` y la base de datos local `config.db`.

---

## Instalacion (alternativa rapida)

Si prefieres no usar un entorno virtual, puedes instalar la dependencia globalmente (no recomendado para desarrollos colaborativos):

```bash
pip install pygame
python Main.py
```

Recomendamos seguir la sección "Instalacion (entorno virtual recomendado)" arriba para un entorno reproducible.

---

## Como Jugar

### Secuencia de Inicio
1. Ejecuta `python Main.py`
2. Se abrira la ventana del juego (800x600)
3. Veras el menu principal

### En el Menu Principal
- **Jugar**: Comienza una nueva partida
- **Configuracion**: Ajusta el volumen
- **Salir**: Cierra el juego

### Durante el Juego
1. Muevete con `WASD`
2. Ataca enemigos cercanos con click izquierdo (katana)
3. Lanza shurikens con click derecho (a larga distancia)
4. Esquiva enemigos (contacto = muerte)
5. Sobrevive oleadas cada vez mas dificiles
6. Presiona `ESC` para volver al menu
7. Cuando mueras, presiona `R` para reintentar

### Estrategia
- Los enemigos persiguen cuando te ven
- Usa los obstaculos como escudo
- La katana es mas efectiva pero requiere estar cerca
- Los shurikens son buenos para atacar desde distancia
- Observa los conos de vision de los enemigos (semi-transparentes en debug)

---

## Mecanica de Colisiones

### Tipos de Colisiones

**1. Colisiones de Jugador**
- Usa rectangulos del tamanno del jugador
- Se prueba movimiento en X y Y por separado
- Permite deslizar por paredes

**2. Colisiones de Enemigos**
- Mismo sistema que el jugador
- Incluye "rebote" cuando se quedan atrapados
- Radio de cuerpo: 25 pixeles

**3. Colisiones de Proyectiles**
- Los shurikens usan AABB (rectangulos)
- Se eliminan al salir de pantalla
- Instakill a enemigos

**4. Deteccion de Vision**
- Algoritmo CCW (Counter-Clockwise)
- Detecta intersecciones de lineas precisamente
- Los obstaculos bloquean linea de vision

### Algoritmos Utilizados

**CCW (Counter-Clockwise)**
- Determina orientacion de tres puntos
- Calcula el lado donde esta un punto respecto a una linea
- Usada para intersecciones de lineas

**Lines Intersect**
- Verifica si dos lineas se cruzan
- Usado para linea de vision de enemigos
- Usado para deteccion de golpes de katana

---

## Desarrollo de IA

### Sistema de Estados del Enemigo

```
ESTADO: Patrullaje
↓
CONDICION: Ves al jugador
↓
ESTADO: Persecucion + Alerta Global
↓
CONDICION: Pierdes de vista al jugador
↓
ESTADO: Investigacion (2 segundos)
↓
CONDICION: No encuentras nada
↓
ESTADO: Patrullaje (ciclo)
```

### Patrones de Patrullaje
- Objetivo aleatorio dentro del mapa
- Reintenta hasta 30 veces para evitar obstaculos
- Si falla, usa fallback cercano
- Renueva objetivo al llegar (distancia < 12 px)

---

## Optimizaciones

### Performance
- Limpieza de shurikens fuera de pantalla
- Deteccion de estancamiento de enemigos (evita bucles infinitos)
- Colisiones separadas en X/Y (mas eficiente)
- Delta time preciso (60 FPS)

### Memoria
- Enemigos reutilizados en oleadas
- Sprites cacheados en memoria
- Base de datos SQLite (minima huella)

---

## Problemas Conocidos

- Nada reportado aun. Si encuentras un bug, abre un issue.

---

## Notas Tecnicas

### Fisicas
- Todo usa coordenadas enteras (pixeles)
- Colisiones AABB (rectangulos alineados al eje)
- Sin gravedad ni fisicas reales

### Rendering
- Ciclo a 60 FPS fijo
- Clear + Draw + Flip cada frame
- Sprites rotados en tiempo real

### Sincronizacion
- Delta time en milisegundos (convertido a segundos para IA)
- Alerta global usa temporizador independiente
- Retardo de respuesta individual por enemigo

---

## Autor

Luis Sarabia - Proyecto desarrollado como practica de programacion en Python con pygame.

---

## Enlaces

- **Repositorio**: https://github.com/SKSarabia/game2025-sarabia
- **Issues**: https://github.com/SKSarabia/game2025-sarabia/issues
- **Releases**: https://github.com/SKSarabia/game2025-sarabia/releases

---

## Roadmap Futuro

- [ ] Modo historia con niveles progresivos
- [ ] Jefe final (Samurai) con fases
- [ ] Sistema de poder-ups
- [ ] Sonidos de efectos (SFX)
- [ ] Particulas visuales
- [ ] Multijugador local
- [ ] Editor de mapas
- [ ] Tabla de puntuaciones persistente

---

## Feedback y Soporte

Si tienes preguntas, sugerencias o encuentras problemas:
1. Abre un issue en GitHub
2. Describe el problema con detalle
3. Incluye pasos para reproducir si es posible

¡Gracias por jugar Ninja Fate!
