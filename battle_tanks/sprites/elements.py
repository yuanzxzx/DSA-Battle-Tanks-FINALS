import pygame as pg
import math #zmon
from battle_tanks import ROUTE

class SpriteBasic(pg.sprite.Sprite): #SpriteBasic class
    def __init__(self, x_pos,y_pos,width,height): # Initialize SpriteBasic
        super().__init__() # Initialize SpriteBasic
        self._data = None # Set data to None
        self.rect = pg.Rect((x_pos, y_pos), (width, height)) # Set rectangle of sprite

    @property
    def data(self): # Get data
        return self._data

    @data.setter
    def data(self, data: bytes): # Set data
       self._data = data
class Brick(SpriteBasic): #Brick class
    """Class representing a Brick object"""
    def __init__(self,x_pos,y_pos,width,height): # Initialize Brick
        super().__init__(x_pos,y_pos,width,height) # Initialize Brick
        self.box_img = pg.image.load(ROUTE("assets/images/tiles.png")) # Load brick image
        self.image = self.box_img.subsurface((0,0),(32,32)) # Set brick image

class Block(SpriteBasic): #Block class
    """ Class representing a Block object """
    def __init__(self,x_pos,y_pos,width,height): # Initialize Block
        super().__init__(x_pos,y_pos,width,height) # Initialize Block

class Bullet(pg.sprite.Sprite): #Bullet class
    def __init__(self, x, y, angle_cannon, owner=None, max_distance=130): # Initialize Bullet
        super().__init__() # Initialize Bullet
        self.image = pg.Surface((6, 6), pg.SRCALPHA) # Set bullet image
        pg.draw.circle(self.image, (255, 255, 0), (3, 3), 3) # Yellow bullet
        self.rect = self.image.get_rect(center=(x, y)) # Set bullet rectangle
        self.x = float(x) # Set bullet x position
        self.y = float(y) # Set bullet y position
        self.distance_traveled = 0 # Set bullet distance traveled
        self.max_distance = max_distance # Set bullet max distance
        self.owner = owner # Set bullet owner
        
        radian_angle = math.radians(angle_cannon) # Convert bullet angle to radians
        self.vx = -math.sin(radian_angle) * 7 # Set bullet x velocity
        self.vy = -math.cos(radian_angle) * 7 # Set bullet y velocity

    def update(self): # Update bullet position
        self.x += self.vx # Update bullet x position
        self.y += self.vy # Update bullet y position
        self.rect.centerx = int(round(self.x)) # Update bullet x position
        self.rect.centery = int(round(self.y)) # Update bullet y position
        self.distance_traveled += math.sqrt(self.vx**2 + self.vy**2) # Update bullet distance traveled
        if self.distance_traveled >= self.max_distance: # Check if bullet distance traveled
            self.kill() # Kill bullet

class Landmine(pg.sprite.Sprite): #Landmine class
    def __init__(self, x, y, explosion_radius=60): # Initialize Landmine
        super().__init__() # Initialize Landmine
        self.x = float(x) # Set landmine x position
        self.y = float(y) # Set landmine y position
        self.explosion_radius = explosion_radius # Set landmine explosion radius
        self.is_active = False # Set landmine active state
        self.activation_time = 0 # Set landmine activation time
        self.activation_delay = 0.5  # 0.5 seconds before it's active
        
        self.image = pg.Surface((16, 16), pg.SRCALPHA) # Set landmine image
        pg.draw.circle(self.image, (139, 0, 0), (8, 8), 8)  # Draw landmine circle
        pg.draw.polygon(self.image, (255, 0, 0), [(8, 0), (10, 6), (6, 6)])  # Draw landmine triangle
        
        self.rect = self.image.get_rect(center=(x, y)) # Set landmine rectangle

    def activate(self): # Activate the landmine after delay
        self.activation_time += 1/60 # Update landmine activation time
        if self.activation_time >= self.activation_delay: # Check if landmine activation time
            self.is_active = True # Set landmine active state

    def update(self): # Update landmine activation state
        if not self.is_active: # Check if landmine is active
            self.activate() # Activate landmine

    def detonate(self): # Trigger the landmine explosion
        return self.explosion_radius  # Return radius for damage calculation
