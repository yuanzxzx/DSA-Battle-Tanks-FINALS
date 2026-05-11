#!/usr/bin/python3
""" this is the manager game """

import sys
from typing import Tuple, Dict, Union, List
import pygame as pg
import math

from battle_tanks.commons.package import Struct, Collision
from battle_tanks.components.movement import MovementComponent
from battle_tanks.components.tile_map import TileMap
from battle_tanks.components.camera import CameraComponent
from battle_tanks.sprites import Player, Brick
from battle_tanks.sprites.elements import Bullet #zmon
from battle_tanks.commons.municion import CannonType
from battle_tanks.commons.tank_surface import tank_cover
from battle_tanks.components.network import NetworkComponent
from battle_tanks import ROUTE


type_guns = {
    "MEDIUM": CannonType(20,"MEDIUM",(8,10)),
}
pg.mixer.init()
SOUND_BOOM = pg.mixer.Sound(ROUTE("assets/sound/boom.wav"))
SHOT = pg.mixer.Sound(ROUTE("assets/sound/shot.wav"))

SOUND_BOOM.set_volume(0.1)
SHOT.set_volume(0.1)



def find_sprite(rect: pg.Rect, group: pg.sprite.Group) -> Union[pg.sprite.Sprite, bool]:
    for sprite in group:
        if sprite.rect.colliderect(rect):
            return sprite
    return False


class Game:
    def __init__(self,
                 addr:Union[Tuple[str,int], None],
                 screen:pg.Surface,
                 player_name="John",
                 tank_color:int=0):

        self.network = NetworkComponent(addr, player_name, tank_color) if addr is not None else None
        self._player_number = self.network.player_number if addr is not None else 0
        self.positions = {}


        pg.display.set_caption(f"Battle Tank - Client: {self._player_number} - User: {player_name}")


        self.WIDTH,self.HEIGHT = screen.get_size()
        self.SCREEN = screen

        self.tile = TileMap(self.network.lvl_map)
        self.tile_image = self.tile.make_map()
        self.tile_rect = self.tile_image.get_rect()

        self.players: Dict[int,Player] = {}
        self._bricks = pg.sprite.Group()
        self._bullets = pg.sprite.Group()
        self._damage = 0

        if self.network and self.network.player_data != Struct.USER_NOT_AVAILABLE:
            position = (self.network.player_data["x"],self.network.player_data["y"])
        else:
            position = (0,0)

        self.player = Player(position, self._player_number, cannon_type=type_guns.get("MEDIUM"), tank_color=tank_color)
        self.players[self._player_number] = self.player
        self.camera = CameraComponent(self.tile.WIDTH, self.tile.HEIGHT, (self.WIDTH, self.HEIGHT))
        self.move = MovementComponent(self.network, self.player)
# kca
        # Fog of War configuration
        self.FOV_RADIUS = 350
        self.fog = pg.Surface((self.WIDTH, self.HEIGHT), pg.SRCALPHA)
        self.fov_mask = pg.Surface((self.FOV_RADIUS * 2, self.FOV_RADIUS * 2), pg.SRCALPHA)
        
        self.FOG_COLOR = (80, 80, 80, 255) # Gray fog
        self.fov_mask.fill(self.FOG_COLOR) # Start fully opaque
        
        # Create a gradient mask to subtract alpha
        sub_mask = pg.Surface((self.FOV_RADIUS * 2, self.FOV_RADIUS * 2), pg.SRCALPHA)
        sub_mask.fill((0, 0, 0, 0)) # Transparent by default (subtract nothing outside FOV)
        
        # Draw concentric rings to form a smooth gradient of alpha subtraction
        for radius in range(self.FOV_RADIUS, 0, -1):
            normalized = radius / self.FOV_RADIUS
            # Cosine interpolation for ultra smooth falloff
            subtract_alpha = int(255 * math.cos(normalized * math.pi / 2))
            pg.draw.circle(sub_mask, (0, 0, 0, subtract_alpha), (self.FOV_RADIUS, self.FOV_RADIUS), radius, 2)
            
        # Subtract the gradient mask from the opaque fov_mask
        self.fov_mask.blit(sub_mask, (0, 0), special_flags=pg.BLEND_RGBA_SUB)
# kca
        self.load()


    @property
    def damage(self):
        """ return damage from player """
        return self.player.damage


    def load(self):
        for data_sprite in self.network.get_events_to_game_state():
            if data_sprite[0] == Struct.BRICK:
                brick = Brick(data_sprite[1],data_sprite[2],data_sprite[3],data_sprite[4])
                self._bricks.add(brick)


    def update(self):
        """ Update Game"""

        for key,player in self.players.items():
            if player.fire:
                SHOT.play()
                
                
                radian_angle = math.radians(player.angle_cannon)
                start_x = player.rect.centerx + math.sin(radian_angle) * -30
                start_y = player.rect.centery + math.cos(radian_angle) * -30
                self._bullets.add(Bullet(start_x, start_y, player.angle_cannon))
                
                player.fire = False

        self._bullets.update()

        """ SEND MOVES BYTES """
        self.move.keys()
        """ MOVES RESPONSE """

        if self.network:
            recv_all:List[dict] = self.network.recv_to_queue()

            for recv in recv_all:
                if (recv.get("status") == Struct.NEW_PLAYER or
                        recv.get("status") == Struct.OLD_PLAYER):
                    position = recv["position"]
                    tank_color = recv.get("tank_color", 0)
                    player = Player((recv["x"],recv["y"]), position, cannon_type = type_guns.get("BASIC"), tank_color=tank_color)
                    player.name = recv.get("name", f"Player {position}")  # Establecer el nombre del jugador
                    self.players[position] = player
                #zmon
                elif recv.get("status") in (Struct.UPDATE_PLAYER, Struct.PLAYER_SHOT):
                    position = recv["position"]
                #zmon   
                    if recv.get("status") == Struct.PLAYER_SHOT:
                        self.camera.shake()
                        SOUND_BOOM.play()
                #zmon
                    if self.players.get(position):
                        player = self.players[position]

                        player.rect.x = recv["x"]
                        player.rect.y = recv["y"]

                        player.body_rect.x = player.rect.x
                        player.body_rect.y = player.rect.y

                        player.angle = recv["angle"]
                        player.angle_cannon = recv["angle_cannon"]
                        player.damage = recv["damage_indicator"]

                    else:
                        tank_color = recv.get("tank_color", 0)
                        player = Player((recv["x"], recv["y"]), position, cannon_type=type_guns.get("BASIC"), tank_color=tank_color)
                        player.name = recv.get("name", f"Player {position}")  # Establecer el nombre del jugador
                        self.players[position] = player

                elif recv.get("status") == Struct.BROKE_BRICK:
                    brick_rect = pg.Rect(recv["x"], recv["y"], recv["w"], recv["h"])
                    sprite_brick = find_sprite(brick_rect, self._bricks)
                    if sprite_brick:
                        self._bricks.remove(sprite_brick)
                        SOUND_BOOM.play()
              #          self.camera.shake() #zmon
                        sprite_brick.kill()

                elif recv.get("status") == Struct.BLOCK:
                    Brick.boom() #Change for Block sound
                  #  self.camera.shake() #zmon


        self.camera.update(self.player)


    def draw(self, main_screen: pg.Surface):
        """ Draw the player and scene. """
        self.SCREEN.blit(self.tile_image,self.camera.apply_rect(self.tile_rect))
#kca
        for _,player in self.players.items():
            # Fog of War visibility check
            if player != self.player:
                dist = math.hypot(self.player.rect.centerx - player.rect.centerx, 
                                  self.player.rect.centery - player.rect.centery)
                if dist > self.FOV_RADIUS:
                    continue
#kca
            # Dibujar el tanque
            tank_rect = self.camera.apply(player)
            tank_cover(player.tank_color, tank_rect, self.SCREEN, angle=player.angle,
                       angle_cannon=player.angle_cannon)
            
            # Dibujar el nombre del jugador
            font = pg.font.Font(None, 24)  # Crear una fuente
            text_surface = font.render(player.name, True, (255, 255, 255))  # Texto blanco
            text_rect = text_surface.get_rect()
            
            # Posicionar el texto encima del tanque
            text_rect.centerx = tank_rect.centerx
            text_rect.bottom = tank_rect.top - 5  # 5 píxeles arriba del tanque
            
            # Dibujar el texto
            self.SCREEN.blit(text_surface, text_rect)

            # Dibujar la barra de vida
            health_width = 50  # Ancho de la barra de vida
            health_height = 5  # Alto de la barra de vida
            health_x = tank_rect.centerx - health_width // 2
            health_y = text_rect.bottom + 2  # 2 píxeles debajo del nombre

            # Barra de vida base (gris)
            pg.draw.rect(self.SCREEN, (100, 100, 100), 
                        (health_x, health_y, health_width, health_height))
            
            # Calcular el ancho de la barra de vida actual
            health_percentage = 1 - (player.damage / Player.MAX_DAMAGE)
            current_health_width = int(health_width * health_percentage)
            
            # Barra de vida actual (roja)
            pg.draw.rect(self.SCREEN, (255, 0, 0), 
                        (health_x, health_y, current_health_width, health_height))

        for brick in self._bricks:
            self.SCREEN.blit(brick.image,self.camera.apply(brick))
            #zmon
        for bullet in self._bullets:
            self.SCREEN.blit(bullet.image, self.camera.apply(bullet))
            #zmon
#kca
        # Render Fog of War over map and players
        self.fog.fill(self.FOG_COLOR)
        player_screen_rect = self.camera.apply(self.player)
        mask_x = player_screen_rect.centerx - self.FOV_RADIUS
        mask_y = player_screen_rect.centery - self.FOV_RADIUS
        self.fog.blit(self.fov_mask, (mask_x, mask_y), special_flags=pg.BLEND_RGBA_MIN)
        self.SCREEN.blit(self.fog, (0, 0))
#kca   
        telescopic_pos = Collision.calculate_bullet_position(self.player.telescopic_sight(), 100)
        telescopic_rect = self.camera.apply_rect(pg.rect.Rect(telescopic_pos[0],telescopic_pos[1],20,20))

        self.SCREEN.blit(Player.TELESCOPIC_SIGH, telescopic_rect)
        main_screen.blit(self.SCREEN, (0,0))
    

    def close(self):
        if self.network:
            self.network.socket_tcp.send(Struct.CLOSE_CONN)
            self.network.socket_tcp.close()
        pg.quit()
        sys.exit()


    def __str__(self):
        return (f"\n\nPlayer Number: {self._player_number} "
                f"\nPlayer Name: {self.network.name} "
                f"\nStatus: {'Multiplayer' if self.network.addr else 'Single'}\n\n") #zmon
