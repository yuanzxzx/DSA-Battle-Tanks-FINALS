import pygame as pg
import math #zmon
from battle_tanks import ROUTE


class SpriteBasic(pg.sprite.Sprite):
    def __init__(self, x_pos,y_pos,width,height):
        super().__init__()
        self._data = None
        self.rect = pg.Rect((x_pos, y_pos), (width, height))


    @classmethod
    def boom(cls):
        pass
        # cls.SOUND_BOOM.play()


    @property
    def data(self):
        return self._data


    @data.setter
    def data(self, data: bytes):
       self._data = data


class Brick(SpriteBasic):
    """Class representing a Brick object"""
    def __init__(self,x_pos,y_pos,width,height):
        super().__init__(x_pos,y_pos,width,height)
        self.box_img = pg.image.load(ROUTE("assets/images/tiles.png"))
        self.image = self.box_img.subsurface((0,0),(32,32))


class Block(SpriteBasic):
    """ Class representing a Block object """
    def __init__(self,x_pos,y_pos,width,height):
        super().__init__(x_pos,y_pos,width,height)
#zmon
class Bullet(pg.sprite.Sprite):
    def __init__(self, x, y, angle_cannon, owner=None, max_distance=130):
        super().__init__()
        self.image = pg.Surface((6, 6), pg.SRCALPHA)
        pg.draw.circle(self.image, (255, 255, 0), (3, 3), 3) # Yellow bullet
        self.rect = self.image.get_rect(center=(x, y))
        self.x = float(x)
        self.y = float(y)
        self.distance_traveled = 0
        self.max_distance = max_distance
        self.owner = owner
        
        radian_angle = math.radians(angle_cannon)
        self.vx = -math.sin(radian_angle) * 7
        self.vy = -math.cos(radian_angle) * 7

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.centerx = int(round(self.x))
        self.rect.centery = int(round(self.y))
        self.distance_traveled += math.sqrt(self.vx**2 + self.vy**2)
        if self.distance_traveled >= self.max_distance:
            self.kill()
#zmon
