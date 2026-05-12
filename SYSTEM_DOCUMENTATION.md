# DSA Battle Tanks — System Documentation

> **Version:** 1.0 | **Engine:** Pygame | **Architecture:** Client-Server (TCP)

---

## Table of Contents

1. [High-Level System Architecture](#1-high-level-system-architecture)
2. [Low-Level System Architecture](#2-low-level-system-architecture)
3. [Module & File Reference](#3-module--file-reference)
4. [Gameplay Loop Flowchart](#4-gameplay-loop-flowchart)
5. [HUD Interaction Flowchart](#5-hud-interaction-flowchart)
6. [Player Input & Movement Flowchart](#6-player-input--movement-flowchart)
7. [Firing & Bullet Lifecycle Flowchart](#7-firing--bullet-lifecycle-flowchart)
8. [Collision Detection Flowchart](#8-collision-detection-flowchart)
9. [Ammo & Reload System Flowchart](#9-ammo--reload-system-flowchart)
10. [Fog of War (FOV) System Flowchart](#10-fog-of-war-fov-system-flowchart)
11. [Laser Skill Flowchart](#11-laser-skill-flowchart)
12. [Network Communication Flowchart](#12-network-communication-flowchart)
13. [Player Connection & Session Flowchart](#13-player-connection--session-flowchart)
14. [Game State Transition Flowchart](#14-game-state-transition-flowchart)
15. [Data Packet Structure](#15-data-packet-structure)

---

## 1. High-Level System Architecture

This diagram shows the two major runtime processes — the **Server** and each **Client** — and how they communicate over TCP.

```mermaid
graph TD
    subgraph CLIENT["CLIENT PROCESS (client.py)"]
        M["Menu\n(menu.py)"]
        G["Game\n(game.py)"]
        NC["NetworkComponent\n(network.py)"]
        MV["MovementComponent\n(movement.py)"]
        CAM["CameraComponent\n(camera.py)"]
        HUD["HUD Layer\n(client.py main loop)"]

        M -->|"Returns Game instance"| G
        G --> NC
        G --> MV
        G --> CAM
        G --> HUD
        MV -->|"Enqueues key events"| NC
    end

    subgraph SERVER["SERVER PROCESS (server/server.py)"]
        SRV["Server\n(server.py)"]
        COL["Collision\n(collision.py)"]
        DB["DatabaseManager\n(conexions.py)"]
        PKG["Struct Packer\n(package.py)"]

        SRV --> COL
        SRV --> DB
        SRV --> PKG
    end

    NC <-->|"TCP Socket\nport 8010"| SRV

    style CLIENT fill:#0d2b0d,color:#fff,stroke:#2e7d32
    style SERVER fill:#1a1a2e,color:#fff,stroke:#3949ab
```

---

## 2. Low-Level System Architecture

This diagram expands every module, class, key method, and data flow.

```mermaid
graph LR
    subgraph ENTRY["Entry Points"]
        CP["client.py\nmain()"]
        SP["server.py\nServer.__init__()"]
    end

    subgraph MENU_MOD["battle_tanks/menu.py"]
        MNU["Menu\n- multiplayer_mode()\n- draw()\n- update()"]
    end

    subgraph GAME_MOD["battle_tanks/game.py"]
        GM["Game\n- __init__()\n- load()\n- update()\n- draw()\n- close()"]
        GS["GameState\nLOBBY=0\nBATTLE=1"]
    end

    subgraph SPRITES["battle_tanks/sprites/"]
        PL["Player\n- SPEED, ANGLE\n- damage, fire\n- telescopic_sight()\n- check_available_bullets()"]
        CN["Cannon\n- check_available_bullets()\n- rect_cannon"]
        EL["Bullet\n- vx, vy\n- distance_traveled\n- update()"]
        BR["Brick / Block\n- rect, image, data"]
    end

    subgraph COMMONS["battle_tanks/commons/"]
        MUN["CannonType\n- count, count_available\n- reload_time\n- render()"]
        PKG2["Struct\n- pack_player()\n- unpack_player()\n- pack_event()\n- pack_tile()\n- MOVES, FIRE_EVENT"]
        TS["tank_surface\n- tank_cover()\n- draw_bullet()\n- colors[]"]
    end

    subgraph COMPONENTS["battle_tanks/components/"]
        NET["NetworkComponent\n- load_data()\n- recv_move_player()\n- send_move_tcp()\n- send_keys()\n- check_name()\n- SEND_Q / UPDATE_Q"]
        MOV["MovementComponent\n- keys()"]
        COL2["Collision\n- load()\n- collide_with_objects()\n- check_collision_bullet()\n- check_collision_player()\n- calculate_bullet_position()\n- get_laser_intersections()"]
        TM["TileMap\n- make_map()"]
        CAM2["CameraComponent\n- update()\n- apply()\n- apply_rect()"]
        TXT["TextComponent\n- update()\n- draw()"]
    end

    subgraph SRV_MOD["server/"]
        SRVR["Server\n- _conexions()\n- _handle_client()\n- _receive()\n- _handle_menu()"]
        DB2["DatabaseManager\n- save()\n- find()\n- update()"]
    end

    CP --> MNU
    MNU --> GM
    GM --> NET
    GM --> MOV
    GM --> CAM2
    GM --> TM
    GM --> COL2
    GM --> PL
    GM --> BR
    GM --> EL
    PL --> CN
    CN --> MUN
    MOV --> NET
    NET -->|"TCP"| SRVR
    SRVR --> COL2
    SRVR --> DB2
    SRVR --> PKG2
    PKG2 --> COL2
    SP --> SRVR
```

---

## 3. Module & File Reference

| File | Class / Function | Responsibility |
|------|-----------------|----------------|
| `client.py` | `main()` | Entry point; Pygame init, HUD render loop, thread spawning |
| `battle_tanks/menu.py` | `Menu` | Main menu, connection form, tank color picker |
| `battle_tanks/game.py` | `Game`, `GameState` | Game loop orchestration, Fog of War, draw pipeline |
| `battle_tanks/sprites/player.py` | `Player(Cannon)` | Tank entity, damage, fire flag, telescopic sight |
| `battle_tanks/sprites/cannon.py` | `Cannon` | Cannon rect, ammo availability check |
| `battle_tanks/sprites/elements.py` | `Brick`, `Block`, `Bullet` | Map objects and projectile sprite |
| `battle_tanks/commons/municion.py` | `CannonType` | Ammo count, reload timer, bullet render |
| `battle_tanks/commons/package.py` | `Struct` | Binary protocol — pack/unpack player, tile, and event data |
| `battle_tanks/commons/tank_surface.py` | `tank_cover()` | Draws tank body + cannon with color theming |
| `battle_tanks/components/network.py` | `NetworkComponent` | TCP socket, queues for send/receive |
| `battle_tanks/components/movement.py` | `MovementComponent` | Translates key presses → event bytes |
| `battle_tanks/components/collision.py` | `Collision` | Server-side physics, bullet-hit checks, boundary clamping |
| `battle_tanks/components/tile_map.py` | `TileMap` | Loads `.tmx` tile map, renders surface |
| `battle_tanks/components/camera.py` | `CameraComponent` | Scrolling camera offset, applies to sprites |
| `battle_tanks/components/text.py` | `TextComponent` | Pygame font surface helper |
| `server/server.py` | `Server` | TCP accept loop, per-client threads, game-state broadcast |
| `server/conexions.py` | `DatabaseManager` | JSON-based player persistence |

---

## 4. Gameplay Loop Flowchart

The main client loop runs at 60 FPS. This flowchart covers everything from startup to game exit.

```mermaid
flowchart TD
    A([START]) --> B[pygame.init\nCreate 800×660 window]
    B --> C[Load HUD background\nhud_bg.png]
    C --> D[Show Menu\nMenu.update → multiplayer_mode]
    D --> E{Player entered\nvalid server details?}
    E -- No --> D
    E -- Yes --> F[Game.__init__\nConnect TCP, load map,\nspawn Player, init FOW]
    F --> G[Spawn network threads\nth_received · th_send]
    G --> H[/Main Loop 60 FPS/]

    H --> I[Poll pygame events]
    I --> J{QUIT?}
    J -- Yes --> K[game.close → sys.exit]
    J -- No --> L[Handle KEYDOWN / KEYUP]
    L --> M[game.update]
    M --> N[game.draw]
    N --> O[Render HUD strip\nhud_bg + ammo + damage]
    O --> P[pygame.display.flip]
    P --> H

    style A fill:#1b5e20,color:#fff
    style K fill:#b71c1c,color:#fff
    style H fill:#0d47a1,color:#fff
```

---

## 5. HUD Interaction Flowchart

The HUD is a 60-pixel strip rendered below the 800×600 game viewport. It shows ammo icons and damage percentage.

```mermaid
flowchart TD
    A([Every Frame]) --> B[SCREEN.blit hud_bg\nat y = HEIGHT = 600]
    B --> C[bullets Surface\n800 × 36 px, colorkey black]
    C --> D[player.type_gun.render bullets\nDraws ammo icons left-to-right]
    D --> E{count_available > 0?}
    E -- Yes --> F[Draw bullet icons\none per remaining shot]
    E -- No --> G[Increment _count_reload]
    G --> H{_count_reload ≥\n_reload_time 100?}
    H -- No --> I[Show empty strip\nreloading...]
    H -- Yes --> J[Reset count_available\nback to max count]
    J --> F
    F --> K[SCREEN.blit bullets\nat y = HEIGHT + 12]
    K --> L[Update text_damage\n'Damage: X %']
    L --> M[text_damage.draw SCREEN\ncentered at y = HEIGHT+30]

    style A fill:#1565c0,color:#fff
    style J fill:#2e7d32,color:#fff
    style I fill:#e65100,color:#fff
```

---

## 6. Player Input & Movement Flowchart

`MovementComponent.keys()` is called every frame inside `Game.update()`.

```mermaid
flowchart TD
    A([game.update called]) --> B[MovementComponent.keys]
    B --> C[pg.key.get_pressed]

    C --> D{A key?}
    D -- Yes --> E[action = RIGHT_EVENT_PLAYER\nbyte 0x04]
    D -- No --> F{D key?}
    F -- Yes --> G[action = LEFT_EVENT_PLAYER\nbyte 0x03]
    F -- No --> H{W key?}
    H -- Yes --> I[action = UP_EVENT_PLAYER\nbyte 0x05]
    H -- No --> J{S key?}
    J -- Yes --> K[action = DOWN_EVENT_PLAYER\nbyte 0x06]
    J -- No --> L[No move action]

    E & G & I & K --> M

    C --> N{P key?}
    N -- Yes --> O[action = LEFT_ANGLE_EVENT\nbyte 0x07]
    N -- No --> P{I key?}
    P -- Yes --> Q[action = RIGHT_ANGLE_EVENT\nbyte 0x08]
    P -- No --> R[No cannon action]

    O & Q --> M

    M[Append to actions list] --> S{actions list\nnot empty?}
    S -- Yes --> T[NetworkComponent.send_keys\nputs each byte in SEND_Q]
    S -- No --> U([Done])
    T --> U

    subgraph SERVER["Server-side on receipt"]
        V[Struct.pack_player\ncalculates new x,y,angle]
        V --> W[Collision.collide_with_objects\nboundary + brick check]
        W --> X[q.put encoded_message\nbroadcast to all clients]
    end

    T -.->|TCP byte| V

    style A fill:#1565c0,color:#fff
    style SERVER fill:#1a237e,color:#fff
```

---

## 7. Firing & Bullet Lifecycle Flowchart

Firing involves both the client (visual bullet) and server (hit detection).

```mermaid
flowchart TD
    A([Player presses O key]) --> B{check_available_bullets?}
    B -- No ammo --> C([Ignore])
    B -- Yes --> D[player.fire = True\nDecrement count_available]
    D --> E[Send FIRE_EVENT_PLAYER\nbyte 0x11 over TCP]

    subgraph CLIENT_SIDE["Client — Visual Bullet"]
        F[game.update detects\nplayer.fire == True]
        F --> G[Calculate start position\nusing angle_cannon radians]
        G --> H[_bullets.add Bullet sprite\nvx vy from angle]
        H --> I[player.fire = False]
        I --> J[SHOT.play sound]
        J --> K[Every frame:\nbullet.update\nrect.x += vx, rect.y += vy]
        K --> L{distance_traveled\n≥ max_distance 130?}
        L -- Yes --> M[bullet.kill remove from group]
        L -- No --> K
    end

    subgraph SERVER_SIDE["Server — Hit Detection"]
        N[Server receives\nFIRE_EVENT_PLAYER]
        N --> O[Struct.pack_event player_data]
        O --> P[Collision.check_collision_player\nraycast 10 steps × 100 px]
        P --> Q{Hit enemy\nplayer?}
        Q -- Yes --> R[enemy damage_indicator += DAMAGE 10\nif damage ≥ MAX_DAMAGE 100:\n  respawn at random position]
        R --> S[Return status PLAYER_SHOT\nbroadcast pack_player]
        Q -- No --> T[Collision.check_collision_bullet\nbrick raycast]
        T --> U{Hit brick?}
        U -- Yes --> V[Remove brick from game_state\nReturn BROKE_BRICK event]
        U -- No --> W[Return PLAYER_FIRED event\nno collision]
        S & V & W --> X[q.put encoded → broadcast]
    end

    E -.->|TCP| N
    X -.->|TCP| Y[Client receives:\nSOUND_BOOM.play\nor brick removed\nor fire animation on other tank]

    style CLIENT_SIDE fill:#0d2b0d,color:#fff
    style SERVER_SIDE fill:#1a1a2e,color:#fff
    style C fill:#b71c1c,color:#fff
```

---

## 8. Collision Detection Flowchart

`Collision` is a server-side static class. It handles boundaries, bricks, blocks, and bullet hits.

```mermaid
flowchart TD
    A([collide_with_objects called\nafter each move]) --> B{x < 0?}
    B -- Yes --> C[x = 0]
    B -- No --> D{x + BODY_W ≥ map_width?}
    D -- Yes --> E[x = map_width - BODY_W]
    D -- No --> F{y < 0?}
    F -- Yes --> G[y = 0]
    F -- No --> H{y + BODY_H ≥ map_height?}
    H -- Yes --> I[y -= BODY_H]

    C & E & G & I & H --> J[Build body Rect 32×32]

    J --> K[For each brick in cls.bricks]
    K --> L{body.colliderect brick?}
    L -- No --> M[Next brick]
    L -- Yes --> N[Calculate radius_player\nand radius_block]
    N --> O[dx = brick.centerx - body.centerx\ndy = brick.centery - body.centery\ndistance = sqrt dx²+dy²]
    O --> P{distance ≠ 0?}
    P -- Yes --> Q[Normalize dx dy\nSeparate: x -= dx×sep×0.125\n          y -= dy×sep×0.125]
    P -- No --> M
    Q --> M
    M --> R([Done])

    style A fill:#1565c0,color:#fff
    style R fill:#1b5e20,color:#fff
```

---

## 9. Ammo & Reload System Flowchart

`CannonType` tracks shot count and manages automatic reload after all bullets are spent.

```mermaid
flowchart TD
    A([Player fires]) --> B[player.fire setter called\ncount_available -= 1]
    B --> C{count_available > 0?}
    C -- Yes --> D[Normal state\nHUD shows remaining bullets]
    C -- No --> E[Enter reload phase\n_count_reload += 1 per frame]
    E --> F{_count_reload ≥\nreload_time = 100 frames?}
    F -- No --> G[HUD shows empty strip\n~1.67 seconds at 60 FPS]
    G --> E
    F -- Yes --> H[Reset _count_reload = 0\nReset count_available = count max]
    H --> D

    subgraph HUD_RENDER["HUD Render — CannonType.render()"]
        I[Build list of bullet positions\nwidth × index for each available]
        I --> J[For each bullet slot:\ndraw_bullet on surface]
        J --> K[Return rendered surface\nto client.py blit]
    end

    D --> I

    style A fill:#1565c0,color:#fff
    style G fill:#e65100,color:#fff
    style H fill:#2e7d32,color:#fff
```

---

## 10. Fog of War (FOV) System Flowchart

The Fog of War renders a gray overlay with a smooth radial clear-zone centered on the local player. Implemented in `game.py` by contributor **kca**.

```mermaid
flowchart TD
    A([Game.__init__]) --> B[Create fog Surface\nWIDTH × HEIGHT SRCALPHA]
    B --> C[Create fov_mask Surface\nFOV_RADIUS×2 × FOV_RADIUS×2]
    C --> D[Fill fov_mask with FOG_COLOR\n80,80,80,255 fully opaque]
    D --> E[Create sub_mask Surface\nsame size, fully transparent]
    E --> F[For radius = FOV_RADIUS down to 1:\n  normalized = radius / FOV_RADIUS\n  subtract_alpha = 255 × cos radius × π/2\n  draw ring on sub_mask with that alpha]
    F --> G[fov_mask.blit sub_mask\nBLEND_RGBA_SUB → gradient hole]

    G --> H([Every Draw Frame])
    H --> I[fog.fill FOG_COLOR\nreset overlay each frame]
    I --> J[player_screen_rect = camera.apply player]
    J --> K[mask_x = player.centerx - FOV_RADIUS\nmask_y = player.centery - FOV_RADIUS]
    K --> L[fog.blit fov_mask at mask_x,mask_y\nBLEND_RGBA_MIN\ncreates circular clear window]
    L --> M[SCREEN.blit fog at 0,0\ndrawn AFTER all tanks and bricks]

    subgraph VISIBILITY["Enemy Visibility Check"]
        N[For each enemy player in draw loop]
        N --> O[dist = hypot player.center - enemy.center]
        O --> P{dist > FOV_RADIUS?}
        P -- Yes --> Q[Skip draw enemy\nnot visible]
        P -- No --> R[Draw enemy tank\nand health bar]
    end

    M --> N

    style A fill:#1565c0,color:#fff
    style H fill:#1565c0,color:#fff
    style Q fill:#b71c1c,color:#fff
    style R fill:#2e7d32,color:#fff
```

---

## 11. Laser Skill Flowchart

The laser is a toggleable skill bound to **L**. It activates a sight-line check but does not deal damage directly in the current implementation (server receives the event; client draws the beam locally via `get_laser_intersections`).

```mermaid
flowchart TD
    A([Player holds L key]) --> B[KEYDOWN event → key == K_l]
    B --> C{menu.select_option\nis not None?\ni.e., in game?}
    C -- No --> D([Ignore])
    C -- Yes --> E[player.laser_active = True]
    E --> F[network.send_move_tcp\nLASER_ON_EVENT = 'L_ON' bytes]

    F -.->|TCP| G[Server._handle_client\nreceives LASER_ON_EVENT]
    G --> H[player_data laser_active = True\nno broadcast, state stored]

    I([Player releases L key]) --> J[KEYUP event → key == K_l]
    J --> K[player.laser_active = False]
    K --> L[network.send_move_tcp\nLASER_OFF_EVENT = 'L_OFF' bytes]
    L -.->|TCP| M[Server: laser_active = False]

    subgraph CLIENT_VISUAL["Client Visual — get_laser_intersections"]
        N[Collision.get_laser_intersections\nplayer_data, laser_range]
        N --> O[calculate start_pos and end_pos\nfrom angle_cannon]
        O --> P[20 steps along laser ray]
        P --> Q{brick at point?}
        Q -- Yes --> R[Add to hit_objects bricks list]
        Q -- No --> S[Next step]
        R & S --> T[Return hit list to caller]
    end

    E --> N

    style A fill:#1565c0,color:#fff
    style D fill:#b71c1c,color:#fff
    style R fill:#e65100,color:#fff
```

---

## 12. Network Communication Flowchart

Two dedicated background threads decouple send and receive from the game loop.

```mermaid
sequenceDiagram
    participant GL as Game Loop (Main Thread)
    participant SQ as NetworkComponent.SEND_Q
    participant UQ as NetworkComponent.UPDATE_Q
    participant TH_S as th_send Thread
    participant TH_R as th_received Thread
    participant TCP as TCP Socket
    participant SRV as Server

    Note over GL,SRV: Client startup
    GL->>TCP: connect(ip, port)
    TCP->>SRV: accept()
    SRV-->>TCP: OK_MESSAGE (0x01)
    TCP-->>GL: OK received
    GL->>TCP: send name + tank_color (33 bytes)
    SRV-->>TCP: lvl_map filename (pickle)
    TCP-->>GL: player data (13 bytes)
    SRV-->>TCP: game_state chunks (bricks)

    Note over GL,SRV: Runtime loop
    GL->>SQ: send_keys → SEND_Q.put(action_byte)
    TH_S->>SQ: SEND_Q.get()
    TH_S->>TCP: send_move_tcp(action_byte)
    TCP->>SRV: 1-byte event

    SRV->>TCP: broadcast pack_player / pack_tile
    TH_R->>TCP: recv_move_player(120 bytes)
    TH_R->>UQ: UPDATE_Q.put(decoded_list)
    GL->>UQ: recv_to_queue() → process events
```

---

## 13. Player Connection & Session Flowchart

```mermaid
flowchart TD
    A([Client connects]) --> B[Server._conexions thread\naccept new socket]
    B --> C{Max players\nreached = 2?}
    C -- Yes --> D[sleep 10s, retry]
    D --> B
    C -- No --> E[Send OK_MESSAGE 0x01]
    E --> F[Receive name + tank_color\n33 bytes]
    F --> G{Name ends with -c?\ncheck-only request}
    G -- Yes --> H{Name in filter_name\nalready connected?}
    H -- Yes --> I[Send USER_NOT_AVAILABLE\n0x09]
    H -- No --> J[Send OK_MESSAGE]
    G -- No --> K[Send lvl_map pickle]
    K --> L[DatabaseManager.find player by name]
    L --> M{Player exists\nin DB?}
    M -- Yes --> N[Restore saved x,y,angle\nuse existing data]
    M -- No --> O[Create new record\ndefault position 323,677]
    N & O --> P[Assign position slot 0 or 1\nfrom available slots]
    P --> Q[Send pack_player initial data]
    Q --> R[Send game_state chunks\nall brick positions]
    R --> S[Add to _data, _sockets\n_filter_name, Collision.players]
    S --> T[Notify existing players\nNEW_PLAYER broadcast]
    T --> U[Submit _handle_client\nto ThreadPoolExecutor]

    subgraph DISCONNECT["Disconnection"]
        V[data == b'' or CLOSE_CONN]
        V --> W[persistence.update\nsave current x,y,angle]
        W --> X[player deleted = True\nq.put player]
        X --> Y[_receive pops player\nfrom all registries]
    end

    style A fill:#1565c0,color:#fff
    style I fill:#b71c1c,color:#fff
    style U fill:#2e7d32,color:#fff
```

---

## 14. Game State Transition Flowchart

The `GameState` enum controls music and interaction. Lobby → Battle transition happens automatically after 5 minutes or on SPACE.

```mermaid
stateDiagram-v2
    [*] --> Menu : App launch

    Menu --> Lobby : Player connects successfully

    state Lobby {
        [*] --> WaitingForPlayers
        WaitingForPlayers --> WaitingForPlayers : elapsed < 5 minutes\nAND SPACE not pressed
        WaitingForPlayers --> TransitionToBattle : elapsed ≥ 300000ms\nOR SPACE pressed
        TransitionToBattle --> [*]
        note right of WaitingForPlayers
            Music: lobby_track.mp3
            Players can move but
            no damage applied
        end note
    }

    Lobby --> Battle : GameState.BATTLE set

    state Battle {
        [*] --> ActiveCombat
        ActiveCombat --> ActiveCombat : fire / move / collide
        note right of ActiveCombat
            Music: main_track.mp3
            Damage tracked
            Respawn on max damage
        end note
    }

    Battle --> Disconnected : QUIT event or socket error
    Disconnected --> [*] : game.close → sys.exit
```

---

## 15. Data Packet Structure

All data is binary-packed using Python's `struct` module for performance.

### Player Update Packet (13 bytes)

| Byte(s) | Field | Format | Notes |
|---------|-------|--------|-------|
| 0 | Size marker | `B` | Always `13` (SIZE_PLAYER) |
| 1 | Status | `B` | 1=UPDATE, 2=NEW, 3=OLD, 7=SHOT, 8=FIRED |
| 2 | Position slot | `B` | 0 or 1 |
| 3–4 | X coordinate | `h` (int16) | World X |
| 5–6 | Y coordinate | `h` (int16) | World Y |
| 7–8 | Body angle | `h` (int16) | 0–359 degrees |
| 9–10 | Cannon angle | `h` (int16) | 0–359 degrees |
| 11 | Damage | `b` (int8) | 0–100 |
| 12 | Tank color | `B` | 0–23 (color index) |

### Tile / Event Packet (11 bytes)

| Byte(s) | Field | Format | Notes |
|---------|-------|--------|-------|
| 0 | Size marker | `B` | Always `11` (BUFFER_SIZE_EVENT_RESPONSE) |
| 1 | Type | `b` | 4=BROKE_BRICK, 5=BRICK, 6=BLOCK |
| 2–3 | X | `h` | Tile X |
| 4–5 | Y | `h` | Tile Y |
| 6–7 | Width | `h` | Tile width |
| 8–9 | Height | `h` | Tile height |

### Control Event Bytes (1 byte each)

| Byte | Constant | Action |
|------|----------|--------|
| `0x03` | LEFT_EVENT_PLAYER | Turn left |
| `0x04` | RIGHT_EVENT_PLAYER | Turn right |
| `0x05` | UP_EVENT_PLAYER | Move forward |
| `0x06` | DOWN_EVENT_PLAYER | Move backward |
| `0x07` | LEFT_ANGLE_EVENT_PLAYER | Rotate cannon left |
| `0x08` | RIGHT_ANGLE_EVENT_PLAYER | Rotate cannon right |
| `0x11` | FIRE_EVENT_PLAYER | Fire bullet |
| `0x01` | OK_MESSAGE | Handshake ACK |
| `0x09` | USER_NOT_AVAILABLE | Name conflict |
| `0x10` | CLOSE_CONN | Graceful disconnect |
| `L_ON` | LASER_ON_EVENT | Activate laser |
| `L_OFF` | LASER_OFF_EVENT | Deactivate laser |

---

*Documentation generated for DSA-Battle-Tanks-FINALS — May 2026*
