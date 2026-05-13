#!/usr/bin/python3
""" this is the manager game """

import sys
from typing import Tuple, Dict, Union, List
import pygame as pg
import math
import copy

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
    "BASIC": CannonType(20,"BASIC",(5,7)),
    "MEDIUM": CannonType(20,"MEDIUM",(8,10)),
}
pg.mixer.init()
SOUND_BOOM = pg.mixer.Sound(ROUTE("assets/sound/boom.wav"))
SHOT = pg.mixer.Sound(ROUTE("assets/sound/shot.wav"))
SHOTGUN = pg.mixer.Sound(ROUTE("assets/sound/shotgun_fx.mp3"))

SOUND_BOOM.set_volume(0.1)
SHOT.set_volume(0.1)
SHOTGUN.set_volume(0.3)

playend_end_sound = False # To ensure we only play the victory/defeat sound once

def find_sprite(rect: pg.Rect, group: pg.sprite.Group) -> Union[pg.sprite.Sprite, bool]:
    for sprite in group:
        if sprite.rect.colliderect(rect):
            return sprite
    return False

class GameState:
    DEFEAT = 2 #defeat for 3 deaths -Yu
    #-Yu (Victory state)
    VICTORY = 3
    #-Yu (Victory state)

class Game:
    def __init__(self,
                 addr:Union[Tuple[str,int], None],
                 screen:pg.Surface,
                 player_name="John",
                 tank_color:int=0):
        
        global playend_end_sound
        playend_end_sound = False # Reset end game sound flag on new game start

        self.network = NetworkComponent(addr, player_name, tank_color) if addr is not None else None
        self._player_number = self.network.player_number if addr is not None else 0
        self.positions = {}


        pg.display.set_caption(f"Battle Tank - Client: {self._player_number} - User: {player_name}")


        self.WIDTH,self.HEIGHT = screen.get_size()
        self.SCREEN = screen

        #-Yu (load heart images for life system)
        try:
            self.heart_full_img = pg.image.load(ROUTE("assets/images/heart_full.png")).convert_alpha()
            self.heart_full_img = pg.transform.scale(self.heart_full_img, (12, 12))
            self.heart_empty_img = pg.image.load(ROUTE("assets/images/heart_empty.png")).convert_alpha()
            self.heart_empty_img = pg.transform.scale(self.heart_empty_img, (12, 12))
        except Exception as e:
            print("Warning: Could not load heart images, falling back to circles.", e)
            self.heart_full_img = None
            self.heart_empty_img = None
        #-Yu (load heart images for life system)

        self.tile = TileMap(self.network.lvl_map)
        self.tile_image = self.tile.make_map()
        self.tile_rect = self.tile_image.get_rect()

        self.players: Dict[int,Player] = {}
        self._bricks = pg.sprite.Group()
        self._bullets = pg.sprite.Group()
        self._damage = 0

        self.laser_timers = {}
        self.laser_burn_cooldown = 0 #jam

        if self.network and self.network.player_data != Struct.USER_NOT_AVAILABLE:
            position = (self.network.player_data["x"],self.network.player_data["y"])
        else:
            position = (0,0)

        self.player = Player(position, self._player_number, cannon_type=copy.deepcopy(type_guns.get("MEDIUM")), tank_color=tank_color)
        self.players[self._player_number] = self.player
        self.camera = CameraComponent(self.tile.WIDTH, self.tile.HEIGHT, (self.WIDTH, self.HEIGHT))
        self.move = MovementComponent(self.network, self.player)
# kca
        # Fog of War configuration
        self.FOV_RADIUS = 300
        self.fog = pg.Surface((self.WIDTH, self.HEIGHT), pg.SRCALPHA)
        self.fov_mask = pg.Surface((self.FOV_RADIUS * 2, self.FOV_RADIUS * 2), pg.SRCALPHA)
        
        #-Yu (track max players to know when to trigger victory)
        self.max_players_seen = 0
        #-Yu (track max players to know when to trigger victory)
        
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

# lars        
        pg.mixer.music.stop() 
        pg.mixer.music.load(ROUTE("assets/sound/main_track.mp3"))
        pg.mixer.music.set_volume(0.3)
        pg.mixer.music.play(-1)
        
        self.state = 1
        

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
#yu (defeat state)
# Handle Defeat Menu
        if self.state == 2:
            
            if pg.mouse.get_pressed()[0]:
                btn_rect = pg.Rect(self.WIDTH//2 - 100, self.HEIGHT//2 + 50, 200, 50)
                if btn_rect.collidepoint(pg.mouse.get_pos()):
                    self.return_to_menu()
            return # Don't update game logic if defeated

        #-Yu (Victory handling menu)
        if self.state == 3:

            if pg.mouse.get_pressed()[0]:
                btn_rect = pg.Rect(self.WIDTH//2 - 100, self.HEIGHT//2 + 50, 200, 50)
                if btn_rect.collidepoint(pg.mouse.get_pos()):
                    self.return_to_menu()
            return # Don't update game logic if victorious
        #-Yu (Victory handling menu)

        #-Yu (disconnect server collision when player dies 3 times)
        if getattr(self.player, 'deaths', 0) >= 3:
            self.state = 2
            # Immediately disconnect to remove the tank from the server's collision tracking
            if self.network:
                try:
                    self.network.socket_tcp.send(Struct.CLOSE_CONN)
                    self.network.socket_tcp.close()
                except Exception:
                    pass
                self.network = None
        #-Yu (disconnect server collision when player dies 3 times)

        #-Yu (check victory condition)
        self.max_players_seen = max(self.max_players_seen, len(self.players))
        if self.state == 1 and self.max_players_seen > 1:
            alive_players = 0
            for p_id, p in self.players.items():
                if getattr(p, 'deaths', 0) < 3:
                    alive_players += 1
            # If we are the only one left alive!
            if alive_players == 1 and getattr(self.player, 'deaths', 0) < 3:
                self.state = 3
                # Disconnect since game is over
                if self.network:
                    try:
                        self.network.socket_tcp.send(Struct.CLOSE_CONN)
                        self.network.socket_tcp.close()
                    except Exception:
                        pass
                    self.network = None
        #-Yu (check victory condition)

        for key, player in self.players.items():
            if player.fire:
                SHOT.play()
                rad = math.radians(player.angle_cannon)
                start_x = player.rect.centerx + math.sin(rad) * -30
                start_y = player.rect.centery + math.cos(rad) * -30
                self._bullets.add(Bullet(start_x, start_y, player.angle_cannon, owner=player))
                
                if player.player_number == self._player_number:
                    recoil_dist = 10
                    player.rect.x += int(math.sin(rad) * recoil_dist)
                    player.rect.y += int(math.cos(rad) * recoil_dist)
                    player.body_rect.center = player.rect.center

                player.fire = False

            #-Yu (spawn 5 bullets for shotgun blast)
            if getattr(player, 'shotgun_fire', False):
                SHOTGUN.play()
                for offset in [-20, -10, 0, 10, 20]:
                    rad = math.radians(player.angle_cannon + offset)
                    start_x = player.rect.centerx + math.sin(rad) * -30
                    start_y = player.rect.centery + math.cos(rad) * -30
                    self._bullets.add(Bullet(start_x, start_y, player.angle_cannon + offset))
                
                if player.player_number == self._player_number:
                    recoil_dist = 15
                    rad = math.radians(player.angle_cannon)
                    player.rect.x += int(math.sin(rad) * recoil_dist)
                    player.rect.y += int(math.cos(rad) * recoil_dist)
                    player.body_rect.center = player.rect.center
                
                player.shotgun_fire = False
            #-Yu (spawn 5 bullets for shotgun blast)

        self._bullets.update()
        for bullet in list(self._bullets):
            if find_sprite(bullet.rect, self._bricks):
                bullet.kill()
                continue
            for p_id, p in self.players.items():
                if getattr(bullet, 'owner', None) != p and p.rect.colliderect(bullet.rect):
                    bullet.kill()
                    break
        
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
                    player = Player((recv["x"],recv["y"]), position, cannon_type = copy.deepcopy(type_guns.get("BASIC")), tank_color=tank_color)
                    player.name = recv.get("name", f"Player {position}")  # Establecer el nombre del jugador
                    self.players[position] = player
                #zmon
                elif recv.get("status") in (Struct.UPDATE_PLAYER, Struct.PLAYER_SHOT, Struct.PLAYER_FIRED, Struct.PLAYER_SHOTGUN):
                    position = recv["position"]
                 #zmon   
                    if recv.get("status") == Struct.PLAYER_SHOT:
                #        self.camera.shake()
                        SOUND_BOOM.play()
                    elif recv.get("status") == Struct.PLAYER_FIRED:
                        if position != self._player_number and self.players.get(position):
                            self.players[position].fire = True
                    elif recv.get("status") == Struct.PLAYER_SHOTGUN:
                        if position != self._player_number and self.players.get(position):
                            self.players[position].shotgun_fire = True
                #zmon
                    if self.players.get(position):
                        player = self.players[position]

                        player.rect.x = recv["x"]
                        player.rect.y = recv["y"]

                        player.body_rect.x = player.rect.x
                        player.body_rect.y = player.rect.y

                        player.angle = recv["angle"]
                        player.angle_cannon = recv["angle_cannon"]
#yu (defeat state)
                        #-Yu (death detection with 1s cooldown to prevent UDP packet order bugs)
                        # We use a 1000ms cooldown to prevent UDP out-of-order packets from counting a single death multiple times (e.g. from a shotgun blast)
                        if recv["damage_indicator"] < player.damage:
                            current_time = pg.time.get_ticks()
                            if current_time - getattr(player, 'last_death_time', 0) > 1000:
                                player.deaths = getattr(player, 'deaths', 0) + 1
                                player.last_death_time = current_time
                        player.damage = recv["damage_indicator"]
                        #-Yu (death detection with 1s cooldown to prevent UDP packet order bugs)

                        player.laser_active = recv.get("laser_active", getattr(player, "laser_active", False)) #jam

                    else:
                        tank_color = recv.get("tank_color", 0)
                        player = Player((recv["x"], recv["y"]), position, cannon_type=type_guns.get("BASIC"), tank_color=tank_color)
                        player.name = recv.get("name", f"Player {position}")  # Establecer el nombre del jugador
#yu (defeat state)
                        player.deaths = 0
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
     
        if getattr(self.player, "laser_active", False):
            rad_angle = math.radians(-self.player.angle_cannon - 90)
            world_start = (self.player.rect.centerx, self.player.rect.centery)
            world_max_end = (world_start[0] + 300 * math.cos(rad_angle), world_start[1] + 300 * math.sin(rad_angle))
            
            closest_brick = None
            closest_dist = 300
            
            # Find the first brick in the path
            for brick in self._bricks:
                clip = brick.rect.clipline(world_start, world_max_end)
                if clip:
                    dist = math.hypot(clip[0][0] - world_start[0], clip[0][1] - world_start[1])
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_brick = brick
                        
            if closest_brick:
                dt = 1/60 
                brick_id = f"brick_{closest_brick.rect.x}_{closest_brick.rect.y}"
                self.laser_timers[brick_id] = self.laser_timers.get(brick_id, 0) + dt
                
                if self.laser_timers[brick_id] >= 1.0:
                    if self.network:
                        melt_packet = Struct.pack_tile({
                            "type": Struct.BROKE_BRICK, "x": closest_brick.rect.x, "y": closest_brick.rect.y, "w": closest_brick.rect.w, "h": closest_brick.rect.h
                        })
                        self.network.send_move_tcp(melt_packet)
                    
                    if closest_brick in self._bricks: self._bricks.remove(closest_brick)
                    if closest_brick in Collision.bricks: Collision.bricks.remove(closest_brick)
                    try: self._spawn_particles(closest_brick.rect.centerx, closest_brick.rect.centery) 
                    except: pass
                    closest_brick.kill()
                    del self.laser_timers[brick_id] #jam
        
        for p_id, enemy in self.players.items():
            if enemy.player_number != self._player_number and getattr(enemy, "laser_active", False):
                rad_angle = math.radians(-enemy.angle_cannon - 90)
                start_pos = (enemy.rect.centerx, enemy.rect.centery)
                end_pos = (start_pos[0] + 300 * math.cos(rad_angle), start_pos[1] + 300 * math.sin(rad_angle))
                if self.player.rect.clipline(start_pos, end_pos):
                    if getattr(self, "laser_burn_cooldown", 0) <= 0:
                        if self.network:
                            dmg_packet = Struct.pack_tile({
                                "type": 97, "x": self._player_number, "y": 10, "w": 0, "h": 0
                            })
                            self.network.send_move_tcp(dmg_packet)
                        self.laser_burn_cooldown = 15 # Take damage every 1/4 second
                        self._spawn_particles(self.player.rect.centerx, self.player.rect.centery, count=5)
        
        if getattr(self, "laser_burn_cooldown", 0) > 0:
            self.laser_burn_cooldown -= 1

        self.camera.update(self.player) #jam


    def draw(self, main_screen: pg.Surface):
        """ Draw the player and scene. """
        self.SCREEN.blit(self.tile_image,self.camera.apply_rect(self.tile_rect))
#kca
        for _,player in self.players.items():
            #-Yu (hide completely defeated players)
            if getattr(player, 'deaths', 0) >= 3:
                continue # Do not draw defeated players
            #-Yu (hide completely defeated players)
            
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

            if getattr(player, "laser_active", False):
                rad_angle = math.radians(-player.angle_cannon - 90)
                barrel_offset = 20 
                
                world_start = (player.rect.centerx, player.rect.centery)
                world_max_end = (world_start[0] + 300 * math.cos(rad_angle), world_start[1] + 300 * math.sin(rad_angle))
                
                closest_dist = 300
                for brick in self._bricks:
                    clip = brick.rect.clipline(world_start, world_max_end)
                    if clip:
                        dist = math.hypot(clip[0][0] - world_start[0], clip[0][1] - world_start[1])
                        if dist < closest_dist:
                            closest_dist = dist
                            
                draw_len = max(0, closest_dist - barrel_offset)
                start_x = tank_rect.centerx + barrel_offset * math.cos(rad_angle)
                start_y = tank_rect.centery + barrel_offset * math.sin(rad_angle)
                draw_end = (start_x + draw_len * math.cos(rad_angle), start_y + draw_len * math.sin(rad_angle))
                
                pg.draw.line(self.SCREEN, (255, 50, 50), (start_x, start_y), draw_end, 5)
                pg.draw.line(self.SCREEN, (255, 255, 255), (start_x, start_y), draw_end, 2) #jam
           
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
            #-Yu (heart UI life indicator)
            # Indicador de vidas (3 corazones arriba del nombre)
            deaths = getattr(player, 'deaths', 0)
            lives_left = max(0, 3 - deaths)
            lives_width = 12 * 3 + 4 * 2
            lives_x = tank_rect.centerx - lives_width // 2
            lives_y = text_rect.top - 14

            for i in range(3):
                if self.heart_full_img and self.heart_empty_img:
                    img = self.heart_full_img if i < lives_left else self.heart_empty_img
                    self.SCREEN.blit(img, (lives_x + i * 16, lives_y))
                else:
                    color = (0, 255, 0) if i < lives_left else (100, 100, 100)
                    pg.draw.circle(self.SCREEN, color, (lives_x + i * 16 + 6, lives_y + 6), 5)
            #-Yu (heart UI life indicator)

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
        telescopic_pos = Collision.calculate_bullet_position(self.player.telescopic_sight(), 130)
        telescopic_rect = self.camera.apply_rect(pg.rect.Rect(telescopic_pos[0],telescopic_pos[1],20,20))

        self.SCREEN.blit(Player.TELESCOPIC_SIGH, telescopic_rect)
        main_screen.blit(self.SCREEN, (0,0))
#Yu (defeat state)
        if self.state == GameState.DEFEAT:
            # Defeat screen overlay
            s = pg.Surface((self.WIDTH, self.HEIGHT), pg.SRCALPHA)
            s.fill((128, 128, 128, 200)) # Gray with alpha
            main_screen.blit(s, (0, 0))
            
            # Defeat red text
            font_large = pg.font.Font(None, 84)
            text_surface = font_large.render("DEFEAT", True, (255, 0, 0))
            text_rect = text_surface.get_rect(center=(self.WIDTH//2, self.HEIGHT//2 - 50))
            main_screen.blit(text_surface, text_rect)
            
            # Go back to lobby button
            btn_rect = pg.Rect(self.WIDTH//2 - 100, self.HEIGHT//2 + 50, 200, 50)
            pg.draw.rect(main_screen, (200, 200, 200), btn_rect, border_radius=8)
            pg.draw.rect(main_screen, (0, 0, 0), btn_rect, 3, border_radius=8)
            
            font_small = pg.font.Font(None, 36)
            btn_text = font_small.render("Go to Menu", True, (0, 0, 0))
            btn_text_rect = btn_text.get_rect(center=btn_rect.center)
            main_screen.blit(btn_text, btn_text_rect)

        #-Yu (draw victory screen)
        if self.state == GameState.VICTORY:
            # Victory screen overlay
            s = pg.Surface((self.WIDTH, self.HEIGHT), pg.SRCALPHA)
            s.fill((0, 0, 0, 150)) # Dark transparent
            main_screen.blit(s, (0, 0))
            
            # Victory yellow text
            font_large = pg.font.Font(None, 84)
            text_surface = font_large.render("VICTORY", True, (255, 255, 0))
            text_rect = text_surface.get_rect(center=(self.WIDTH//2, self.HEIGHT//2 - 50))
            main_screen.blit(text_surface, text_rect)
            
            # Go back to menu button
            btn_rect = pg.Rect(self.WIDTH//2 - 100, self.HEIGHT//2 + 50, 200, 50)
            pg.draw.rect(main_screen, (200, 200, 200), btn_rect, border_radius=8)
            pg.draw.rect(main_screen, (0, 0, 0), btn_rect, 3, border_radius=8)
            
            font_small = pg.font.Font(None, 36)
            btn_text = font_small.render("Go to Menu", True, (0, 0, 0))
            btn_text_rect = btn_text.get_rect(center=btn_rect.center)
            main_screen.blit(btn_text, btn_text_rect)
        #-Yu (draw victory screen)
    
    def return_to_menu(self):
        """ Cleanly restarts the client to return to the main menu """
        if self.network:
            try:
                self.network.socket_tcp.send(Struct.CLOSE_CONN)
                self.network.socket_tcp.close()
            except Exception:
                pass
        
        import os
        import sys
        
        # Completely restart the process to cleanly wipe all game state, UI state, and network threads
        os.execv(sys.executable, [sys.executable] + sys.argv)
#Yu (defeat state)

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
