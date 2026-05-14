""" GUNS """
import os
import pygame as pg
from ..commons.municion import CannonType


class Cannon: # Cannon class, the cannon is object  that can be used to by the player (tank)
    def __init__(self,position,type_gun: CannonType): # Initialize cannon
        self.rect_cannon = pg.Rect(0,0,20*2,28*2) # Set rectangle of cannon
        self.rect_cannon.center = position # Set center of cannon
        # self.image_bullet: pg.Surface = pg.image.load(os.path.join(os.path.abspath("."), "assets/images/bullet"))
        self.angle_cannon = 0 # Set angle of cannon
        self.type_gun = type_gun # Set type of cannon

    def __str__(self): # String representation
        return "BULLETS AVAILABLE: " + str(self.type_gun.count_available) # Return number of bullets

    def check_available_bullets(self): # Check available bullets
        if self.type_gun.count_available > 0 or self.type_gun.limit is True: # Check if bullets are available
            return True # Return True
        return False # Return False
