import pytmx
import pygame as pg
import math
import pathlib
import random

from typing import Tuple, List
from collections.abc import Callable
from battle_tanks.sprites import Brick, Player, Block


class Collision: # Create a collision detection system
    bricks = pg.sprite.Group() # Create a group of bricks
    players:List[dict] = [] # Create a list of players
    size_screen:tuple = (0,0) # Set the screen size
    lvl_map:str = "" # Set the level map
    game_state:bytes = b"" # Set the game state
    positions = [] # Set the positions
    #zmon
    active_bullets: List[dict] = []

    @classmethod # Add a bullet to the collision detection
    def add_bullet(cls, player_data: dict, collision_radius: int = 30):
        start_pos = cls.calculate_bullet_position(player_data, 0) # Calculate the starting position of the bullet
        radian_angle = math.radians(player_data["angle_cannon"]) # Calculate the angle of the bullet
        bullet = { # Create a bullet
            "x": float(start_pos[0]), # Set the x position of the bullet
            "y": float(start_pos[1]), # Set the y position of the bullet
            "vx": -math.sin(radian_angle) * 7, # Set the x velocity of the bullet
            "vy": -math.cos(radian_angle) * 7, # Set the y velocity of the bullet
            "distance_traveled": 0, # Set the distance traveled by the bullet
            "max_distance": 130, # Set the maximum distance the bullet can travel
            "owner": player_data, # Set the owner of the bullet
            "radius": collision_radius # Set the radius of the bullet
        }
        cls.active_bullets.append(bullet) # Add the bullet to the active bullets list

    @classmethod # Update the bullet positions
    def update_bullets(cls) -> List[bytes]: # Update the bullet positions
        """
        Updates active bullets over time. Returns a list of event packets (e.g. brick broken or player hit)
        to be broadcasted to clients.
        """
        packets = []
        for bullet in list(cls.active_bullets): # Iterate through the active bullets
            bullet["x"] += bullet["vx"] # Update the x position of the bullet
            bullet["y"] += bullet["vy"] # Update the y position of the bullet
            bullet["distance_traveled"] += math.sqrt(bullet["vx"]**2 + bullet["vy"]**2) # Update the distance traveled by the bullet

            bullet_pos = (bullet["x"], bullet["y"]) # Set the position of the bullet
            collision_radius = bullet["radius"]
            owner_name = bullet["owner"].get("name")

            # Check collision with bricks
            hit_brick = False # Set the hit brick flag to false
            for brick in cls.bricks: # Iterate through the bricks
                target_pos = brick.rect.center # Set the position of the brick
                distance = math.sqrt((bullet_pos[0] - target_pos[0]) ** 2 +
                                     (bullet_pos[1] - target_pos[1]) ** 2) # Calculate the distance between the bullet and the brick
                if distance <= collision_radius: # Check if the bullet collides with the brick
                    from battle_tanks.commons.package import Struct # Import the struct class
                    list_game_state: List[bytes] = cls.game_state.split(brick.data) # Split the game state by the brick data
                    cls.game_state = b"".join(map(bytes, list_game_state)) # Join the game state by the brick data
                    brick.remove(cls.bricks) # Remove the brick from the bricks list
                    
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

            if hit_brick: # If the bullet hits a brick
                cls.active_bullets.remove(bullet) # Remove the bullet from the active bullets list
                continue

            # Check collision with players
            hit_player = False # Set the hit player flag to false
            for other_player in cls.players: # Iterate through the players
                if other_player.get("name") == owner_name: # Check if the bullet owner is the same as the player
                    continue # Skip the bullet owner

                target_pos = (other_player["x"] + 16, other_player["y"] + 16) # Set the position of the player
                distance = math.sqrt((bullet_pos[0] - target_pos[0]) ** 2 + (bullet_pos[1] - target_pos[1]) ** 2) # Calculate the distance between the bullet and the player
                if distance <= collision_radius: # Check if the bullet collides with the player
                    from battle_tanks.commons.package import Struct # Import the struct class
                    other_player["damage_indicator"] += Player.DAMAGE # Add damage to the player

                    if other_player["damage_indicator"] >= Player.MAX_DAMAGE: # Check if the player is dead
                        random_index = random.randint(0, len(cls.positions) - 1) if cls.positions else 0 # Pick random index from positions list
                        other_player["damage_indicator"] = 0 # Reset the damage indicator
                        if cls.positions: # If there are positions
                            other_player["x"] = cls.positions[random_index][0] # Set the x position of the player
                            other_player["y"] = cls.positions[random_index][1] # Set the y position of the player

                    packet = Struct.pack_player(None, other_player, Struct.PLAYER_SHOT) # Pack the player data
                    packets.append(packet) # Add the packet to the packets list
                    hit_player = True # Set the hit player flag to true
                    break

            if hit_player: # If the bullet hits a player
                cls.active_bullets.remove(bullet) # Remove the bullet from the active bullets list
                continue

            if bullet["distance_traveled"] >= bullet["max_distance"]: # Check if the bullet has traveled its maximum distance
                cls.active_bullets.remove(bullet) # Remove the bullet from the active bullets list

        return packets
#zmon


    @staticmethod
    def calculate_bullet_position(player_data:dict, distance:int) -> Tuple[int,int]: # Calculate the position of the bullet
        """
        :param player_data: getting x,y and angle_cannon
        :param distance: range of bullet

        """
        radian_angle = math.radians(player_data["angle_cannon"]) # Convert the angle to radians
        vlx = distance * - math.sin(radian_angle) # Calculate the x velocity of the bullet
        vly = distance * - math.cos(radian_angle) # Calculate the y velocity of the bullet

        x = player_data["x"] + 16 + math.sin(radian_angle) * -30 # Calculate the x position of the bullet
        y = player_data["y"] + 16 + math.cos(radian_angle) * -30 # Calculate the y position of the bullet

        x += vlx # Add the x velocity to the x position
        y += vly # Add the y velocity to the y position

        return x, y


    @classmethod
    def check_collision_bullet(cls, player_data: dict, collision_radius: int) -> dict: # Check for bullet collision
        """
        :param player_data: getting x,y and angle_cannon
        :param collision_radius: radius of collision
        """
        bullet_start_pos = Collision.calculate_bullet_position(player_data, 0)  # Starting position
        bullet_end_pos = Collision.calculate_bullet_position(player_data, 130)  # End position

        steps = 13 # Number of steps to check for collision
        for step in range(steps + 1): # Iterate through the steps
            t = step / steps # Calculate the step
            bullet_pos = ( # Calculate the bullet position
                bullet_start_pos[0] + t * (bullet_end_pos[0] - bullet_start_pos[0]), # Calculate the bullet x position
                bullet_start_pos[1] + t * (bullet_end_pos[1] - bullet_start_pos[1])  # Calculate the bullet y position
            )

            for brick in cls.bricks: # Iterate through the bricks
                brick: Brick
                target_pos = brick.rect.center # Set the position of the brick
                distance = math.sqrt((bullet_pos[0] - target_pos[0]) ** 2 + (bullet_pos[1] - target_pos[1]) ** 2) # Calculate the distance between the bullet and the brick
                collided = distance <= collision_radius # Check if the bullet collides with the brick
                if collided: # If the bullet collides with the brick
                    if isinstance(brick, Brick): # Check if the brick is a brick
                        list_game_state: List[bytes] = cls.game_state.split(brick.data) # split the game state by the brick data
                        cls.game_state = b"".join(map(bytes, list_game_state)) # join the list of bytes to form the new game state
                        brick.remove(cls.bricks) # Remove the brick from the bricks list
                        return {
                            "type":5,
                            "x": brick.rect.x,
                            "y": brick.rect.y,
                            "w": brick.rect.w,
                            "h": brick.rect.h,
                        }

        return {}


    @classmethod
    def check_collision_player(cls, player_data: dict, collision_radius: int) -> dict: # Check for player collision
        bullet_start_pos = Collision.calculate_bullet_position(player_data, 0)  # Starting position
        bullet_end_pos = Collision.calculate_bullet_position(player_data, 130)  # End position

        steps = 13 # Number of steps to check for collision
        for step in range(steps + 1): # Iterate through the steps
            t = step / steps # Calculate the step
            bullet_pos = ( # Calculate the bullet position
                bullet_start_pos[0] + t * (bullet_end_pos[0] - bullet_start_pos[0]),
                bullet_start_pos[1] + t * (bullet_end_pos[1] - bullet_start_pos[1])
            )

            for other_player in cls.players: # Iterate through the players
                if other_player.get("name") == player_data.get("name"): # Check if the bullet owner is the same as the player
                    continue # Skip the bullet owner

                target_pos = (other_player["x"] + 16, other_player["y"] + 16) # Set the position of the player
                distance = math.sqrt((bullet_pos[0] - target_pos[0]) ** 2 + (bullet_pos[1] - target_pos[1]) ** 2) # Calculate the distance between the bullet and the player
                collided = distance <= collision_radius # Check if the bullet collides with the player
                if collided: # If the bullet collides with the player
                    other_player["damage_indicator"] += Player.DAMAGE # Add damage to the player

                    if other_player["damage_indicator"] >= Player.MAX_DAMAGE: # Check if the player is dead
                        random_index = random.randint(0, len(cls.positions) - 1) if cls.positions else 0 # Pick random index from positions list
                        other_player["damage_indicator"] = 0 # Reset the damage indicator

                        other_player["x"] = cls.positions[random_index][0] # Set the x position of the player
                        other_player["y"] = cls.positions[random_index][1] # Set the y position of the player

                    return {
                            "type":7,
                            "player": other_player,
                    }

        return {}

    @classmethod
    def load(cls,lvl_map_tmx:str, func_tile_pack: Callable): # Load the level map
        _tile_map = pytmx.TiledMap(lvl_map_tmx) # Load the tile map
        cls.lvl_map = pathlib.Path(lvl_map_tmx).name # Set the level map name
        cls.size_screen = (_tile_map.width * _tile_map.tilewidth, # Set the screen size
                           _tile_map.height * _tile_map.tileheight)

        for tile_object in _tile_map.objects: # Iterate through the tile objects
            if tile_object.name == "player": # Check if the tile object is a player
                cls.positions.append((int(tile_object.x),int(tile_object.y))) # Add the player position to the positions list
            elif tile_object.name == "brick": # Check if the tile object is a brick
                brick = Brick(tile_object.x,tile_object.y,tile_object.width,tile_object.height) # Create a brick object
                data_tile = func_tile_pack({ # Create a tile data
                    "x": brick.rect.x,
                    "y": brick.rect.y,
                    "h": brick.rect.h,
                    "w": brick.rect.w,
                    "type": 5
                })
                brick.data = data_tile # Set the brick data
                cls.game_state += data_tile # Add the brick data to the game state
                cls.bricks.add(brick) # Add the brick to the bricks list
            elif tile_object.name == "block": # Check if the tile object is a block
                block = Block(tile_object.x,tile_object.y,tile_object.width,tile_object.height) # Create a block object
                cls.bricks.add(block) # Add the block to the bricks list

    @classmethod
    def add_player(cls, player:dict): # Add a player to the game state
        cls.players.append(player) # Add the player to the players list

    @classmethod
    def collide_with_objects(cls,player: dict): # Check for player collision
        if player["x"] <= 0: # Check if the player is at the left boundary
            player["x"] = 0 # Set the x position of the player
        elif player["x"] + Player.SIZE_BODY_RECT[0] >= cls.size_screen[0]: # Check if the player is at the right boundary
            player["x"] = cls.size_screen[0] - Player.SIZE_BODY_RECT[0] # Set the x position of the player

        if player["y"] <= 0: # Check if the player is at the top boundary
            player["y"] = 0 # Set the y position of the player
        elif player["y"] + Player.SIZE_BODY_RECT[1] >= cls.size_screen[1]: # Check if the player is at the bottom boundary
            player["y"] = player["y"] - Player.SIZE_BODY_RECT[1] # Set the y position of the player

        body = pg.Rect(player["x"], player["y"], Player.SIZE_BODY_RECT[0], Player.SIZE_BODY_RECT[1]) # Create a body rectangle for the player

        for brock in cls.bricks: # Iterate through the bricks
            if not body.colliderect(brock.rect): # Check if the body collides with the brick
                continue

            width_rect = body.w * body.w # Calculate the width of the body
            height_rect = body.h * body.h # Calculate the height of the body

            radius_player = math.sqrt( width_rect  + height_rect ) / 2.0 # Calculate the radius of the body

            width_block = brock.rect.w * brock.rect.w # Calculate the width of the brick
            height_block = brock.rect.h * brock.rect.h # Calculate the height of the brick

            radius_block = math.sqrt(width_block + height_block) / 2.0 # Calculate the radius of the brick
            radius_sum = radius_block + radius_player # Calculate the sum of the radii

            dx =  brock.rect.right / 2 -( body.right / 2) # Calculate the difference between the x positions
            dy =  brock.rect.bottom / 2 - (body.bottom / 2) # Calculate the difference between the y positions

            distance = math.sqrt(dx* dx  + dy*dy ) # Calculate the distance between the body and the brick
            separation = radius_sum - distance # Calculate the separation between the body and the brick

            if body.colliderect(brock.rect): # Check if the body collides with the brick
                if distance >= radius_sum: # Check if the distance is greater than or equal to the sum of the radii
                    pass

                if distance != 0: # Check if the distance is not zero
                    dx /= distance # Divide the difference between the x positions by the distance
                    dy /= distance # Divide the difference between the y positions by the distance
                    player["x"] -= dx * separation * 0.125 # Subtract the separation multiplied by the factor from the x position
                    player["y"] -= dy  * separation * 0.125 # Subtract the separation multiplied by the factor from the y position

    @classmethod
    def check_bullet_at_point(cls, x: float, y: float): # Check if the bullet collides with a brick
        for brick in list(cls.bricks): # Iterate through the bricks
            if brick.rect.collidepoint(x, y): # Check if the bullet collides with the brick
                if hasattr(brick, 'data'): # Check if the brick has data
                    list_game_state: List[bytes] = cls.game_state.split(brick.data) # Split the game state by the brick data
                    cls.game_state = b"".join(map(bytes, list_game_state)) # Join the game state back together
                brick.remove(cls.bricks) 

                from battle_tanks.commons.package import Struct # Import the Struct class
                return Struct.pack_tile({ # Pack the tile data
                    "type": Struct.BROKE_BRICK,
                    "x": brick.rect.x,
                    "y": brick.rect.y,
                    "w": brick.rect.w,
                    "h": brick.rect.h
                })
        return None

    @classmethod
    def get_laser_intersections(cls, player_data: dict, laser_range: int): # Get the laser intersections
        ##CLIENT SIDE: Returns a list of bricks currently hit by the laser.
        start_pos = cls.calculate_bullet_position(player_data, 0) # Calculate the starting position of the laser
        end_pos = cls.calculate_bullet_position(player_data, laser_range) # Calculate the ending position of the laser
        
        hit_objects = {"bricks": []}
        steps = 20  # Increase steps for better precision with a long laser
        
        for step in range(steps + 1): # Iterate through the steps
            t = step / steps # Calculate the step
            point = ( # Calculate the point
                start_pos[0] + t * (end_pos[0] - start_pos[0]),
                start_pos[1] + t * (end_pos[1] - start_pos[1])
            )

            for brick in cls.bricks: # Iterate through the bricks
                if brick.rect.collidepoint(point):
                    if brick not in hit_objects["bricks"]:
                        hit_objects["bricks"].append(brick)
        
        return hit_objects
