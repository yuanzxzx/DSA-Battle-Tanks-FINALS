from typing import Tuple
import pygame as pg
from battle_tanks import ROUTE

FONT = ROUTE("dist/client/assets/Pixel Digivolve.otf") # Load font
class TextComponent:

    """Surface for text rendering """
    def __init__(self, position, text, color = None, font_size = 16*2): # Initialize text component
        self._color:Tuple[int,int,int] = color if color is not None else (255,0,0)  # default color
        self.size_font =  font_size
        self._surface = self.render(text,FONT,self._color, self.size_font) # Render text
        self._rect = self._surface.get_rect() # Get rectangle
        self._rect.center = position # Set position
        self._text = text

    @staticmethod
    def render(text:str, font: pg.font, color: Tuple[int,int,int], size): # Render text
        return pg.font.Font(font,size).render(text,1,color)

    def update(self): # Update text
        self._surface = self.render(self._text,FONT,self._color, self.size_font) # Render text

    @property
    def color(self): # Get color
        return self._color

    @color.setter
    def color(self,color:Tuple[int,int,int]): # Set color
        self._color = color
        self._surface = self.render(self._text,FONT,self._color, self.size_font)

    @property
    def text(self): # Get text
        return self._text

    @text.setter
    def text(self,text): # Set text
        """setter """
        self._text = text

    def draw(self,screen): # Draw text
        screen.blit(self._surface,self._rect) # Draw text
