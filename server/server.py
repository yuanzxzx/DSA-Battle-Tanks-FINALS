import socket
import threading as th
import time
import sys
import os
import queue
import logging
import math
import random
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from battle_tanks.components.collision import Collision
from .conexions import DatabaseManager
from battle_tanks.commons.package import Struct

q = queue.SimpleQueue()

#Yu (logging)
if os.path.exists("battle_server.log"):
    try:
        os.remove("battle_server.log")
    except PermissionError:
        pass
#Yu (logging)

logging.basicConfig(filename="battle_server.log",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

logging.info("Running Battle Tanks")
logger = logging.getLogger('BattleTanks')

lock = th.Lock()
TICK_RATE = 1/60

def send_data(conn:socket.socket, data:bytes):
    try:
        conn.sendall(data)
    except (TimeoutError,ConnectionResetError,BrokenPipeError) as e:
        logger.error(f"SEND DATA FAILED: {data}. TO:{th.current_thread().name}. EXCEPT:{e}")


def split_bytes(byte_sequence) -> List[bytes]:
    return [byte_sequence[i:i+Struct.BUFFER_SPLIT_MAP] for i in
            range(0, len(byte_sequence),Struct.BUFFER_SPLIT_MAP)]


class Server:
    """
    Server made in socket TCP
    TODO: socket with udp for players moves.
    """

    def __init__(self,addr, lvl_map_tmx:str):
        self.tick_last_sent = time.time()
        self._data:Dict[int,dict] = defaultdict(dict)
        self._buffer_state_events = []
        self._sockets = []

        self._filter_name:list = []
        self._current_player = 0

        self._socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self._socket.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        self._socket.bind(addr)
        self.positions = {}

        self._max_players = Struct.MAX_PLAYERS
        self.last_landmine_spawn = time.time()
        self.landmine_spawn_count = 0
        self.landmine_positions = []
        self.landmine_spawn_interval = 5.0
        self._executor = ThreadPoolExecutor(max_workers=10,thread_name_prefix="CLIENT_RECV")
        self._socket.listen(self._max_players)

        DatabaseManager.configure({"database_name":"database.json"})
        self.persistence = DatabaseManager.get()

        Collision.load(lvl_map_tmx, Struct.pack_tile)
        
        """
        GAME STATE FOR OBJECTS.
        """

        th_1 = th.Thread(target = self._conexions, daemon = True)
        th_2 = th.Thread(target=self._handle_menu, daemon = True)
        th_3 = th.Thread(target=self._game_loop, daemon = True)
        th_2.start()
        th_1.start()
        th_3.start()

        self._receive()


    def _game_loop(self):
        logger.debug(f"INIT GAME_LOOP {th.current_thread().name}")
        while True:
            time.sleep(TICK_RATE)
            q.put(b"TICK")

    def _find_safe_landmine_location(self, spawn_seed: int):
        rng = random.Random(spawn_seed)
        width, height = Collision.size_screen
        for _ in range(20):
            x = rng.randint(100, max(100, width - 100))
            y = rng.randint(100, max(100, height - 100))
            test_rect = None
            from pygame import Rect
            test_rect = Rect(x, y, 16, 16)
            collision = False
            for brick in Collision.bricks:
                if test_rect.colliderect(brick.rect):
                    collision = True
                    break
            if not collision:
                return (x, y)
        return (rng.randint(100, max(100, width - 100)), rng.randint(100, max(100, height - 100)))

    def _get_position(self,current) -> tuple:
        if Collision.positions:
            return Collision.positions[current % len(Collision.positions)]
        return 323,677


    def _handle_menu(self):
        logger.debug(f"INIT HANDLE_MENU {th.current_thread().name}")
        while True:
            try:
                op = input("\n>")
                if op == "users":
                    for player in Collision.players:
                        print(player.get("name"))
                elif op == "data":
                    for data in self._data.items():
                        print(data)
                elif op == "bricks":
                    print(Collision.bricks)
                elif op == "exit":
                    self._socket.close()
                    os.remove("database.json")
                    sys.exit(1)
                elif op in ("help","h"):
                    print("OPTIONS: users and data")
            except KeyboardInterrupt as e:
                self._socket.close()
                os.remove("database.json")
                sys.exit(1)


    def _handle_client(self,client_socket: socket.socket):
        logger.warning(f"RUNNING NEW THREAD CLIENT: {client_socket.getsockname()} - THREAD -- {th.current_thread().name}")
        while True:
            try:
                data = client_socket.recv(Struct.BUFFER_SIZE_EVENT)
                if not data:
                    position = self._get_player_position(client_socket)
                    if position == -1:
                        break

                    player = self._data[position]
                    # Guardar la posición antes de marcar como eliminado
                    self.persistence.update("player", 
                        {"name": player.get("name")},
                        {
                            "x": player.get("x"),
                            "y": player.get("y"),
                            "angle": player.get("angle"),
                            "angle_cannon": player.get("angle_cannon")
                        }
                    )
                    player["deleted"] = True
                    q.put(player)
                    break

                if data == Struct.CLOSE_CONN:
                    logger.warning(f"CLOSED: {client_socket.getsockname()} "
                                   f"THREAD -- {th.current_thread().name}")

                    for position, player in self._data.items():
                        if client_socket == player.get("conn"):
                            # Guardar la posición antes de marcar como eliminado
                            self.persistence.update("player", 
                                {"name": player.get("name")},
                                {
                                    "x": player.get("x"),
                                    "y": player.get("y"),
                                    "angle": player.get("angle"),
                                    "angle_cannon": player.get("angle_cannon")
                                }
                            )
                            player["deleted"] = True
                            q.put(player)
                    break

                position = self._get_player_position(client_socket)
                if position >= 0:
                    player_data: dict = self._data[position]
                    """
                    FIX THAT
                    """

                    if data in Struct.MOVES:
                        # Validar colisiones después del movimiento
                        if data == Struct.UP_EVENT_PLAYER or data == Struct.DOWN_EVENT_PLAYER:
                            Collision.collide_with_objects(player_data)
                        
                        # Enviar la posición validada al cliente
                        encoded_message = Struct.pack_player(data, player_data)
                        q.put(encoded_message)

                    elif data == Struct.FIRE_EVENT_PLAYER:
                        rad = math.radians(player_data["angle_cannon"])
                        recoil_dist = 10
                        player_data["x"] += math.sin(rad) * recoil_dist
                        player_data["y"] += math.cos(rad) * recoil_dist
                        Collision.collide_with_objects(player_data)

                        encoded_message = Struct.pack_event(player_data)
                        if encoded_message:
                            q.put(encoded_message)
                        
                        # Immediately send the updated player position to all clients to reflect recoil instantly
                        q.put(Struct.pack_player(None, player_data))

                    #-Yu (handle shotgun hitscan for 5 bullets)
                    elif data == Struct.SHOTGUN_EVENT_PLAYER:
                        rad = math.radians(player_data["angle_cannon"])
                        recoil_dist = 15
                        player_data["x"] += math.sin(rad) * recoil_dist
                        player_data["y"] += math.cos(rad) * recoil_dist
                        Collision.collide_with_objects(player_data)
                        
                        original_angle = player_data["angle_cannon"]
                        for offset in [-20, -10, 0, 10, 20]:
                            player_data["angle_cannon"] = original_angle + offset
                            encoded_message = Struct.pack_event(player_data)
                            if encoded_message:
                                q.put(encoded_message)
                        player_data["angle_cannon"] = original_angle
                        
                        # Immediately send the shotgun fire event to all clients to visually spawn bullets
                        q.put(Struct.pack_player(None, player_data, Struct.PLAYER_SHOTGUN))
                    #-Yu (handle shotgun hitscan for 5 bullets)

                    elif data == Struct.LASER_ON_EVENT:
                        player_data["laser_active"] = True
                        event_packet = Struct.pack_tile({
                            "type": Struct.LASER_ON_REMOTE,
                            "x": position,
                            "y": 0,
                            "w": 0,
                            "h": 0
                        })
                        for conn in self._sockets:
                            self._executor.submit(send_data, conn, event_packet)
                    elif data == Struct.LASER_OFF_EVENT:
                        player_data["laser_active"] = False
                        event_packet = Struct.pack_tile({
                            "type": Struct.LASER_OFF_REMOTE,
                            "x": position,
                            "y": 0,
                            "w": 0,
                            "h": 0
                        })
                        for conn in self._sockets:
                            self._executor.submit(send_data, conn, event_packet)
                    elif data == b'\x50':
                        rad_angle = math.radians(-player_data.get("angle_cannon", 0) - 90)
                        start_x, start_y = Collision.calculate_bullet_position(player_data, 0)
                        end_x = start_x + 350 * math.cos(rad_angle)
                        end_y = start_y + 350 * math.sin(rad_angle)

                        closest_brick = None
                        closest_dist = 400 # Max range

                        for brick in list(Collision.bricks):
                            # Deflated the fat box slightly so it doesn't accidentally clip side walls
                            clip = brick.rect.inflate(10, 10).clipline((start_x, start_y), (end_x, end_y))
                            if clip:
                                # Calculate exact distance from the cannon tip to the wall intersection
                                dist = math.hypot(clip[0][0] - start_x, clip[0][1] - start_y)
                                if dist < closest_dist:
                                    closest_dist = dist
                                    closest_brick = brick

                        if closest_brick:
                            # 1. Exact same Server Physics Destruction as Bullets!
                            if hasattr(closest_brick, 'data'):
                                list_game_state = Collision.game_state.split(closest_brick.data)
                                Collision.game_state = b"".join(map(bytes, list_game_state))
                            
                            if closest_brick in Collision.bricks:
                                Collision.bricks.remove(closest_brick)

                            # 2. Broadcast the standard Bullet packet to all clients!
                            try:
                                packet = Struct.pack_tile({
                                    "type": Struct.BROKE_BRICK,
                                    "x": closest_brick.rect.x, "y": closest_brick.rect.y, 
                                    "w": closest_brick.rect.w, "h": closest_brick.rect.h
                                })
                                for conn in self._sockets:
                                    self._executor.submit(send_data, conn, packet)
                            except: pass
                    elif isinstance(data, bytes) and len(data) >= 3:
                        if data[0] == 97:
                            try:
                                # Raw byte extraction - impossible to crash
                                target_id = int(data[1])
                                damage = int(data[2])
                                
                                if target_id in self._data:
                                    current_dmg = self._data[target_id].get("damage_indicator", 0) + damage
                                    
                                    if current_dmg >= 100:
                                        self._data[target_id]["damage_indicator"] = 0
                                        respawn_position = Collision.get_respawn_position(
                                            exclude=(self._data[target_id].get("x", 0), self._data[target_id].get("y", 0))
                                        )
                                        self._data[target_id]["x"], self._data[target_id]["y"] = respawn_position
                                        q.put(Struct.pack_player(None, self._data[target_id], Struct.UPDATE_PLAYER))
                                    else:
                                        self._data[target_id]["damage_indicator"] = current_dmg
                            except Exception:
                                pass
                                
                        elif data[0] == Struct.BROKE_BRICK:
                            for conn in self._sockets:
                                self._executor.submit(send_data, conn, data) #jam

            except (ConnectionResetError, ConnectionRefusedError, socket.error) as e:
                logger.error(f"LOG ERROR: {e}")
                print(f"ERROR IN SOCKET: {e}")

                for position, player in self._data.items():
                    if client_socket == player.get("conn"):
                        player["deleted"] = True
                        q.put(player)

                client_socket.close()
                break

            except Exception as e:
                print(e)
                print(f"THREAD IS: {th.current_thread().is_alive()}")
                print("SOCKET FAILED!")
                print(f"SIZE: {q.qsize()}")
                print(f"EMPTY: {q.empty()}")

                for position, player in self._data.items():
                    if client_socket == player.get("conn"):
                        player["deleted"] = True
                        q.put(player)

                client_socket.close()
                break


    def _conexions(self):
        logger.warning(f"WAITING CONEXIONS --- {th.current_thread().name}")
        while True:
            try:
                if len(self._data) >= self._max_players:
                    time.sleep(10)
                    continue

                conn,addr = self._socket.accept()
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.send(Struct.OK_MESSAGE)
                data = conn.recv(Struct.BUFFER_SIZE_NAME + 1)  # +1 for tank_color

                try:
                    if data != b'': #NAME PLAYER
                        # Separate name and tank_color
                        tank_color = 0
                        if len(data) >= Struct.BUFFER_SIZE_NAME + 1:
                            tank_color = data[-1]  # Last byte is tank_color
                            data = data[:-1]  # Remove tank_color byte
                        
                        # Decode fixed-length padded name (strip null bytes)
                        player_name = data.decode('utf-8').rstrip('\x00')
                        logger.warning(f"ADD NEW_CONEXIONS: {player_name} with tank_color: {tank_color}")
                        if player_name.find("-c") > -1:
                            if player_name[:-2] in self._filter_name:
                                conn.send(Struct.USER_NOT_AVAILABLE)
                            else:
                                conn.send(Struct.OK_MESSAGE)
                            try:
                                conn.close()
                            except Exception:
                                pass
                            continue

                        current = list(set(range(self._max_players)) - set([position for position, _ in self._data.items()]))[0]
                        searching_player = self.persistence.find("player", {"name": player_name})

                        if len(searching_player) > 0:
                            """check user if exists in self._data"""
                            if player_name in self._filter_name:
                                logger.debug(f"NAME IN DATA: {self._filter_name} TO: {Struct.USER_NOT_AVAILABLE}")
                                conn.send(Struct.USER_NOT_AVAILABLE)
                                try:
                                    conn.close()
                                except Exception:
                                    pass
                                continue

                        conn.send(Struct.pack(Collision.lvl_map))

                        logger.debug(f"SEND JOIN: {Struct.JOIN_MESSAGE} TO {conn.getsockname()}")

                        if len(searching_player) == 0:
                            x,y = self._get_position(current)
                            player = self.persistence.save(
                                "player",{
                                    "damage_indicator":0,
                                    "name": player_name,
                                    "position": current,
                                    "x": x,
                                    "y": y,
                                    "cannon_x":338,
                                    "cannon_y":692,
                                    "angle":0,
                                    "angle_cannon":0,
                                    "tank_color": tank_color
                                })
                        else:
                            player = searching_player[0]
                            player["addr"] = addr
                            # Usar la posición guardada del jugador
                            x = player.get("x", self._get_position(current)[0])
                            y = player.get("y", self._get_position(current)[1])
                            player["x"] = x
                            player["y"] = y
                            player["position"] = current
                            player["tank_color"] = tank_color  # Update tank_color

                        player["conn"] = conn
                        """Current Player in Queue."""
                        q.put(player)
                        self._executor.submit(self._handle_client, conn)
                        self._current_player +=1

                    logger.debug(f"SLEEPING THREAD BEFORE {th.current_thread().name}")
                    time.sleep(4)

                except EOFError as e:
                    logger.error(f"ERROR[{e}] CLIENT: {addr}" )
            except (OSError,BlockingIOError) as e:
                logger.error(f"ERROR[{e}] BlockingIOError")


    def _receive(self):
        logger.debug(f"START THREAD: ---[{th.current_thread().name}]")

        while True:
            try:
                data = q.get(timeout=0.016)

                if isinstance(data, dict):
                    """QUEUE FOR NEW PLAYERS."""
                    if len(data.keys()) == 0:
                        continue

                    new_player:dict = data
                    new_player.setdefault("laser_active", False) 
                    new_player.setdefault("angle", 0)
                    new_player.setdefault("angle_cannon", 0) #laser defaults jam
                    current = new_player.get("position")

                    if new_player.get("deleted") is not None:
                        try:
                            self._data.pop(current)
                            self._sockets.remove(new_player.get("conn"))
                            self._filter_name.remove(new_player.get("name"))
                            Collision.players.remove(new_player)
                            logger.debug(f"Removed player at position {current}. THREAD: {th.current_thread().name}")
                            continue
                        except (KeyError, ValueError) as e:
                            data.clear()
                            logger.error(f"DELETING DATA: {e}")
                            continue

                    others_players: Dict[int, dict] = self._data.copy()
                    logger.debug(f"BEFORE SEND TO PLAYER INIT: {new_player}")

                    try:
                        conn_new_player: socket.socket = new_player.get("conn")
                        encoded_message = Struct.pack_player(None, new_player)
                        """ADD NEW CONN"""
                        conn_new_player.sendall(encoded_message)

                        """SENDING MAP OBJECTS"""
                        _game_state = split_bytes(Collision.game_state)
                        conn_new_player.sendall(Struct.pack_single_data(len(_game_state)))

                        for data in _game_state:
                            conn_new_player.sendall(data)

                        # Send any active mine spawns that were created before this player joined
                        for spawn_x, spawn_y in self.landmine_positions:
                            mine_packet = Struct.pack_tile({
                                "type": Struct.MINE_SPAWN,
                                "x": spawn_x,
                                "y": spawn_y,
                                "w": 0,
                                "h": 0
                            })
                            conn_new_player.sendall(mine_packet)

                        self._data[current] = new_player
                        self._filter_name.append(new_player.get("name"))
                        Collision.add_player(new_player)
                        self._sockets.append(conn_new_player)
                        
                    except socket.error as e:
                        del new_player
                        continue

                    if len(others_players) > 0 and new_player is not None:
                        """SENDING NEW_PLAYER TO OTHER OLD PLAYERS"""
                        for position, player in others_players.items():
                            conn: socket.socket = player.get("conn")
                            encoded_message = Struct.pack_player(None, new_player, Struct.NEW_PLAYER)
                            try:
                                conn.send(encoded_message)
                            except socket.error:
                                logger.error(f" IN {th.current_thread().name} FAILED PLAYER: {player}")
                                player["deleted"] = True
                                q.put(player)

                elif isinstance(data,bytes):
                    """QUEUE FOR OLD PLAYERS"""
                    if len(data) == Struct.BUFFER_SIZE_EVENT_RESPONSE or len(data) == Struct.SIZE_PLAYER:
                        # Enviar inmediatamente las actualizaciones de movimiento y disparos
                        for conn in self._sockets:
                            self._executor.submit(send_data, conn, data)
                    else:
                        # Para otros tipos de datos, mantener el tick rate
                        current_time = time.time()
                        if current_time - self.tick_last_sent >= TICK_RATE * 0.9:
                            self.tick_last_sent = current_time

                            if data == b"TICK":
                                if current_time - self.last_landmine_spawn >= self.landmine_spawn_interval:
                                    if self._sockets:
                                        spawn_x, spawn_y = self._find_safe_landmine_location(self.landmine_spawn_count)
                                        self.landmine_spawn_count += 1
                                        self.last_landmine_spawn = current_time
                                        self.landmine_positions.append((spawn_x, spawn_y))
                                        mine_event = Struct.pack_tile({
                                            "type": Struct.MINE_SPAWN,
                                            "x": spawn_x,
                                            "y": spawn_y,
                                            "w": 0,
                                            "h": 0
                                        })
                                        for conn in self._sockets:
                                            self._executor.submit(send_data, conn, mine_event)

                            packets = Collision.update_bullets()
                            for packet in packets:
                                q.put(packet)
                            for p_data in self._data.values():
                                if "energy" not in p_data:
                                    p_data["energy"] = 100.0
                                
                                if p_data.get("laser_active"):
                                    p_data["energy"] -= 35.0 * TICK_RATE
                                    if p_data["energy"] <= 0:
                                        p_data["energy"] = 0
                                        p_data["laser_active"] = False 
                                else:
                                    p_data["energy"] = min(100.0, p_data["energy"] + 15.0 * TICK_RATE)
                            for conn in self._sockets:
                                self._executor.submit(send_data, conn, Struct.pack_players(self._data)) #jam

                            # ==========================================
                            # --- NATIVE SERVER-SIDE LASER DESTRUCTION ---
                            # --- NATIVE SERVER-SIDE LASER DESTRUCTION ---
                            for pos, p_data in self._data.items():
                                if "energy" not in p_data: p_data["energy"] = 100.0
                                
                                if p_data.get("laser_active"):
                                    p_data["energy"] -= 35.0 * TICK_RATE
                                    if p_data["energy"] <= 0:
                                        p_data["energy"] = 0
                                        p_data["laser_active"] = False
                                else:
                                    p_data["energy"] = min(100.0, p_data["energy"] + 15.0 * TICK_RATE)
                            # ==========================================

                            for conn in self._sockets:
                                self._executor.submit(send_data, conn, Struct.pack_players(self._data))

            except (queue.Empty, ConnectionAbortedError) as e:
                continue
            except KeyboardInterrupt:
                self._socket.close()
                logger.warning(f"CLOSING SERVER IN MAIN THREAD...{th.current_thread().name}")
                sys.exit(1)


    def _get_player_position(self, conn) -> int:
        for position, player in self._data.items():
            if player.get("conn") == conn:
                return position
        return -1

