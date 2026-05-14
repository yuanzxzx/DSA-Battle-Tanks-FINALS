import pytmx
import pygame as pg
import math
import pathlib
import random

from typing import Tuple, List
from collections.abc import Callable
from battle_tanks.sprites import Brick, Player, Block


class Collision:
    bricks = pg.sprite.Group()
    players:List[dict] = []
    size_screen:tuple = (0,0)
    lvl_map:str = ""
    game_state:bytes = b""
    positions = []
    #zmon
    active_bullets: List[dict] = []

    @classmethod
    def add_bullet(cls, player_data: dict, collision_radius: int = 30):
        start_pos = cls.calculate_bullet_position(player_data, 0)
        radian_angle = math.radians(player_data["angle_cannon"])
        bullet = {
            "x": float(start_pos[0]),
            "y": float(start_pos[1]),
            "vx": -math.sin(radian_angle) * 7,
            "vy": -math.cos(radian_angle) * 7,
            "distance_traveled": 0,
            "max_distance": 130,
            "owner": player_data,
            "radius": collision_radius
        }
        cls.active_bullets.append(bullet)

    @classmethod
    def update_bullets(cls) -> List[bytes]:
        """
        Updates active bullets over time. Returns a list of event packets (e.g. brick broken or player hit)
        to be broadcasted to clients.
        """
        packets = []
        for bullet in list(cls.active_bullets):
            bullet["x"] += bullet["vx"]
            bullet["y"] += bullet["vy"]
            bullet["distance_traveled"] += math.sqrt(bullet["vx"]**2 + bullet["vy"]**2)

            bullet_pos = (bullet["x"], bullet["y"])
            collision_radius = bullet["radius"]
            owner_name = bullet["owner"].get("name")

            # Check collision with bricks
            hit_brick = False
            for brick in cls.bricks:
                target_pos = brick.rect.center
                distance = math.sqrt((bullet_pos[0] - target_pos[0]) ** 2 +
                                     (bullet_pos[1] - target_pos[1]) ** 2)
                if distance <= collision_radius:
                    from battle_tanks.commons.package import Struct
                    list_game_state: List[bytes] = cls.game_state.split(brick.data)
                    cls.game_state = b"".join(map(bytes, list_game_state))
                    brick.remove(cls.bricks)
                    
                    packet = Struct.pack_tile({
                        "type": Struct.BROKE_BRICK,
                        "x": brick.rect.x,
                        "y": brick.rect.y,
                        "w": brick.rect.w,
                        "h": brick.rect.h,
                    })
                    packets.append(packet)
                    hit_brick = True
                    break

            if hit_brick:
                cls.active_bullets.remove(bullet)
                continue

            # Check collision with players
            hit_player = False
            for other_player in cls.players:
                if other_player.get("name") == owner_name:
                    continue

                target_pos = (other_player["x"] + 16, other_player["y"] + 16)
                distance = math.sqrt((bullet_pos[0] - target_pos[0]) ** 2 +
                                     (bullet_pos[1] - target_pos[1]) ** 2)
                if distance <= collision_radius:
                    from battle_tanks.commons.package import Struct
                    other_player["damage_indicator"] += Player.DAMAGE

                    if other_player["damage_indicator"] >= Player.MAX_DAMAGE:
                        other_player["damage_indicator"] = 0
                        respawn_position = cls.get_respawn_position(exclude=(other_player["x"], other_player["y"]))
                        other_player["x"], other_player["y"] = respawn_position

                    packet = Struct.pack_player(None, other_player, Struct.PLAYER_SHOT)
                    packets.append(packet)
                    hit_player = True
                    break

            if hit_player:
                cls.active_bullets.remove(bullet)
                continue

            if bullet["distance_traveled"] >= bullet["max_distance"]:
                cls.active_bullets.remove(bullet)

        return packets
#zmon


    @staticmethod
    def calculate_bullet_position(player_data:dict, distance:int) -> Tuple[int,int]:
        """
        :param player_data: getting x,y and angle_cannon
        :param distance: range of bullet

        """
        radian_angle = math.radians(player_data["angle_cannon"])
        vlx = distance * - math.sin(radian_angle)
        vly = distance * - math.cos(radian_angle)

        x = player_data["x"] + 16 + math.sin(radian_angle) * -30
        y = player_data["y"] + 16 + math.cos(radian_angle) * -30

        x += vlx
        y += vly

        return x, y


    @classmethod
    def check_collision_bullet(cls, player_data: dict, collision_radius: int) -> dict:
        """
        :param player_data: getting x,y and angle_cannon
        :param collision_radius: radius of collision
        """
        bullet_start_pos = Collision.calculate_bullet_position(player_data, 0)  # Starting position
        bullet_end_pos = Collision.calculate_bullet_position(player_data, 130)  # End position

        steps = 13
        for step in range(steps + 1):
            t = step / steps
            bullet_pos = (
                bullet_start_pos[0] + t * (bullet_end_pos[0] - bullet_start_pos[0]),
                bullet_start_pos[1] + t * (bullet_end_pos[1] - bullet_start_pos[1])
            )

            for brick in cls.bricks:
                brick: Brick
                target_pos = brick.rect.center
                distance = math.sqrt((bullet_pos[0] - target_pos[0]) ** 2 +
                                     (bullet_pos[1] - target_pos[1]) ** 2)
                collided = distance <= collision_radius
                if collided:
                    if isinstance(brick, Brick):
                        list_game_state: List[bytes] = cls.game_state.split(brick.data)
                        cls.game_state = b"".join(map(bytes, list_game_state))
                        brick.remove(cls.bricks)
                        return {
                            "type":5,
                            "x": brick.rect.x,
                            "y": brick.rect.y,
                            "w": brick.rect.w,
                            "h": brick.rect.h,
                        }

        return {}

    @classmethod
    def _is_safe_spawn_position(cls, position: tuple) -> bool:
        if not position or len(position) != 2:
            return False

        x, y = int(position[0]), int(position[1])
        body = pg.Rect(x, y, Player.SIZE_BODY_RECT[0], Player.SIZE_BODY_RECT[1])

        if x < 0 or y < 0:
            return False
        if cls.size_screen[0] and cls.size_screen[1]:
            if x + body.w > cls.size_screen[0] or y + body.h > cls.size_screen[1]:
                return False

        for brick in cls.bricks:
            if body.colliderect(brick.rect):
                return False

        return True

    @classmethod
    def _find_random_safe_spawn(cls, attempts: int = 50) -> tuple:
        if cls.size_screen[0] and cls.size_screen[1]:
            for _ in range(attempts):
                x = random.randint(0, cls.size_screen[0] - Player.SIZE_BODY_RECT[0])
                y = random.randint(0, cls.size_screen[1] - Player.SIZE_BODY_RECT[1])
                if cls._is_safe_spawn_position((x, y)):
                    return x, y

        return 323, 677

    @classmethod
    def get_respawn_position(cls, exclude: tuple = None) -> tuple:
        """Return a spawn point that is not the same as the excluded location."""
        if not cls.positions:
            return cls._find_random_safe_spawn()

        exclude = (int(exclude[0]), int(exclude[1])) if exclude is not None else None

        safe_positions = [pos for pos in cls.positions if cls._is_safe_spawn_position(pos)]
        if exclude is not None:
            safe_positions = [pos for pos in safe_positions if pos != exclude]

        if safe_positions:
            return random.choice(safe_positions)

        # If all map spawn points are invalid, try the non-excluded safe ones first.
        fallback_positions = [pos for pos in cls.positions if cls._is_safe_spawn_position(pos)]
        if fallback_positions:
            return random.choice(fallback_positions)

        return cls._find_random_safe_spawn()


    @classmethod
    def check_collision_player(cls, player_data: dict, collision_radius: int) -> dict:
        """
        :param player_data: getting x,y and angle_cannon
        :param collision_radius: radius of collision
        """
        bullet_start_pos = Collision.calculate_bullet_position(player_data, 0)  # Starting position
        bullet_end_pos = Collision.calculate_bullet_position(player_data, 130)  # End position

        steps = 13
        for step in range(steps + 1):
            t = step / steps
            bullet_pos = (
                bullet_start_pos[0] + t * (bullet_end_pos[0] - bullet_start_pos[0]),
                bullet_start_pos[1] + t * (bullet_end_pos[1] - bullet_start_pos[1])
            )



            for other_player in cls.players:
                if other_player.get("name") == player_data.get("name"):
                    continue

                target_pos = (other_player["x"] + 16, other_player["y"] + 16)
                distance = math.sqrt((bullet_pos[0] - target_pos[0]) ** 2 +
                                     (bullet_pos[1] - target_pos[1]) ** 2)
                collided = distance <= collision_radius
                if collided:
                    other_player["damage_indicator"] += Player.DAMAGE

                    if other_player["damage_indicator"] >= Player.MAX_DAMAGE:
                        other_player["damage_indicator"] = 0
                        respawn_position = cls.get_respawn_position(exclude=(other_player["x"], other_player["y"]))
                        other_player["x"], other_player["y"] = respawn_position

                    return {
                            "type":7,
                            "player": other_player,
                    }

        return {}

    @classmethod
    def load(cls,lvl_map_tmx:str, func_tile_pack: Callable):
        _tile_map = pytmx.TiledMap(lvl_map_tmx)
        cls.lvl_map = pathlib.Path(lvl_map_tmx).name
        cls.size_screen = (_tile_map.width * _tile_map.tilewidth,
                           _tile_map.height * _tile_map.tileheight)

        for tile_object in _tile_map.objects:
            if tile_object.name == "player":
                cls.positions.append((int(tile_object.x),int(tile_object.y)))
            elif tile_object.name == "brick":
                brick = Brick(tile_object.x,tile_object.y,tile_object.width,tile_object.height)
                data_tile = func_tile_pack({
                    "x": brick.rect.x,
                    "y": brick.rect.y,
                    "h": brick.rect.h,
                    "w": brick.rect.w,
                    "type": 5
                })
                brick.data = data_tile

                """
                ONLY ADDED BRICK IN GAMESTATE.
                """
                cls.game_state += data_tile
                cls.bricks.add(brick)


            elif tile_object.name == "block":
                block = Block(tile_object.x,tile_object.y,tile_object.width,tile_object.height)
                cls.bricks.add(block)


    @classmethod
    def add_player(cls, player:dict):
        cls.players.append(player)

    @classmethod
    def collide_with_objects(cls,player: dict):
        """
        COLLIDE WITH X AND Y SIZE
        """
        if player["x"] <= 0:
            player["x"] = 0
        elif player["x"] + Player.SIZE_BODY_RECT[0] >= cls.size_screen[0]:
            player["x"] = cls.size_screen[0] - Player.SIZE_BODY_RECT[0]

        if player["y"] <= 0:
            player["y"] = 0
        elif player["y"] + Player.SIZE_BODY_RECT[1] >= cls.size_screen[1]:
            player["y"] = player["y"] - Player.SIZE_BODY_RECT[1]


        body = pg.Rect(player["x"], player["y"], Player.SIZE_BODY_RECT[0], Player.SIZE_BODY_RECT[1])


        for brock in cls.bricks:
            if not body.colliderect(brock.rect):
                continue

            width_rect = body.w * body.w
            height_rect = body.h * body.h

            radius_player = math.sqrt( width_rect  + height_rect ) / 2.0

            width_block = brock.rect.w * brock.rect.w
            height_block = brock.rect.h * brock.rect.h

            radius_block = math.sqrt(width_block + height_block) / 2.0
            radius_sum = radius_block + radius_player

            dx =  brock.rect.right / 2 -( body.right / 2)
            dy =  brock.rect.bottom / 2 - (body.bottom / 2)

            distance = math.sqrt(dx* dx  + dy*dy )
            separation = radius_sum - distance

            if body.colliderect(brock.rect):
                if distance >= radius_sum:
                    pass

                if distance != 0:
                    dx /= distance
                    dy /= distance
                    player["x"] -= dx * separation * 0.125
                    player["y"] -= dy  * separation * 0.125

    @classmethod
    def check_bullet_at_point(cls, x: float, y: float):
        for brick in list(cls.bricks):
            if brick.rect.collidepoint(x, y):
                if hasattr(brick, 'data'):
                    list_game_state: List[bytes] = cls.game_state.split(brick.data)
                    cls.game_state = b"".join(map(bytes, list_game_state))
                brick.remove(cls.bricks) #jam

                from battle_tanks.commons.package import Struct 
                return Struct.pack_tile({
                    "type": Struct.BROKE_BRICK,
                    "x": brick.rect.x,
                    "y": brick.rect.y,
                    "w": brick.rect.w,
                    "h": brick.rect.h
                })
        return None

    @classmethod
    def get_laser_intersections(cls, player_data: dict, laser_range: int):
        ##CLIENT SIDE: Returns a list of bricks currently hit by the laser.
        start_pos = cls.calculate_bullet_position(player_data, 0)
        end_pos = cls.calculate_bullet_position(player_data, laser_range)
        
        hit_objects = {"bricks": []}
        steps = 20  # Increase steps for better precision with a long laser
        
        for step in range(steps + 1):
            t = step / steps
            point = (
                start_pos[0] + t * (end_pos[0] - start_pos[0]),
                start_pos[1] + t * (end_pos[1] - start_pos[1])
            )

            for brick in cls.bricks:
                if brick.rect.collidepoint(point):
                    if brick not in hit_objects["bricks"]:
                        hit_objects["bricks"].append(brick)
        
        return hit_objects
