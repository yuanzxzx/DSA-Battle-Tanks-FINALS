""" This is the Player [Tank] """
import math
import os
import pygame as pg
from .cannon import Cannon
from battle_tanks.commons.municion import CannonType

from typing import Callable


class Player(Cannon): # Player class
    """ This class represents to tank (more cannon) """ # Represents the tank (more cannon)
    SPEED = 2 # Speed of the tank
    ANGLE = 5 # Angle of the tank
    ANGLE_RIGHT = 1 # Angle to the right
    ANGLE_LEFT = -1 # Angle to the left
    SIZE_BODY_RECT = (32,32) # Size of the tank body
    DAMAGE =  33.34 #YU - Damage changed into 33.34 from 10 (to kill enemy in 3 shots)
    MAX_DAMAGE = 100 # Maximum damage of the tank
    TELESCOPIC_SIGH = pg.image.load(os.path.join(os.path.abspath("."), "assets/images/telescopic_sight.png")) # Load telescopic sight image
    
    def __init__(self, position: tuple, number: int, cannon_type: dict, tank_color: int = 0): # Initialize Player
        super().__init__(position, cannon_type)
        self.player_number = number # Player number
        self.tank_color = tank_color # Tank color
        self.name = f"Player {number}"  # Default name
        self.damage = 0 # Tank damage
        self.fire = False # Tank fire
        self.angle = 0 # Tank angle
        self.angle_cannon = 0 # Tank cannon angle
        self.type_gun = cannon_type # Tank cannon type

        self.image = pg.Surface((32, 32), pg.SRCALPHA) # Tank image
        self.rect = self.image.get_rect() # Tank rectangle
        self.rect.x = position[0] # Tank x position
        self.rect.y = position[1] # Tank y position

        self.body_rect = pg.Rect(0, 0, 32, 32) # Tank body rectangle
        self.body_rect.center = self.rect.center # Tank body center

        self.vl = 3 # Tank velocity
        self.vlx = 0 # Tank x velocity
        self.vly = 0 # Tank y velocity
        self._life = 10 # Tank life
        self._dead = False # Tank dead
        self.deaths = 0 #death for life system -Yu


    @staticmethod
    def rotate_external(xbool, angle, surface, rect): # Rotate player around 360
        angle += Player.ANGLE * xbool # Add angle
        if math.sqrt(angle ** 2) >= 360: # Check if angle is greater than 360
            angle = 0
        surface = pg.transform.rotate(surface, angle) # Rotate surface
        rect = pg.Rect(rect.topleft, surface.get_size()) # Get rectangle
        rect.center = rect.center # Set center
        return angle, rect


    def update(self): # Update the position of the player and cannon
        self.body_rect.center = self.rect.center # Set the center of the tank body
        self.rect_cannon.center = self.body_rect.center # Set the center of the cannon


    def rotate_rect(self,xbool,surface): # Rotate the rect player around
        self.angle += 10 * xbool # Add angle
        angle = math.sqrt(self.angle**2) # Check if angle is greater than 360
        if angle >= 360: # Check if angle is greater than 360
            self.angle = 0 # Set angle to 0
        surface = pg.transform.rotate(surface,self.angle) # Rotate surface
        rect = pg.Rect(self.rect.topleft,surface.get_size()) # Get rectangle
        rect.center = self.rect.center # Set center
        self.rect = rect # Set rectangle

    @staticmethod
    def draw(surface,angle): # Draw the surface
        return pg.transform.rotate(surface,angle) # Rotate surface

    @property
    def damage(self): # Return damage
        return self._damage # Return damage

    @damage.setter
    def damage(self, value:float): # Set damage
        self._damage = value # Set damage

    @property
    def fire(self): # Return fire
        return self._fire # Return fire

    @fire.setter
    def fire(self, value:bool): # Set fire
        self._fire = value # Set fire
        if self._fire is True: # Check if fire is true
            self.type_gun.count_available -=1 # Deduct ammo

    #-Yu (shotgun fire property deducting ammo)
    @property
    def shotgun_fire(self): # Return shotgun fire
        return getattr(self, '_shotgun_fire', False) # Return shotgun fire

    @shotgun_fire.setter
    def shotgun_fire(self, value:bool): # Set shotgun fire
        self._shotgun_fire = value # Set shotgun fire
        if self._shotgun_fire is True: # Check if shotgun fire is true
            self.type_gun.count_available -= 5
    #-Yu (shotgun fire property deducting ammo)

    def telescopic_sight(self): # Draw the telescopic sight
        return {
                "x": self.rect.x, # X coordinate
                "y": self.rect.y, # Y coordinate
                "angle_cannon": self.angle_cannon, # Angle of the cannon
        }

    def __str__(self): # String representation of the player
        return f"---NUMBER: [{self.player_number}  ---POS: [{self.rect.center}] ---DAMAGE: {self._damage}"
