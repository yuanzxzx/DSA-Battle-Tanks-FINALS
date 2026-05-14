
import pygame as pg
import pytmx 

from battle_tanks import ROUTE


class TileMap: # Load tilemap with tmx
    """ Load tilemap with tmx"""
    def __init__(self,filename): # Initialize tilemap
        tm = pytmx.load_pygame(ROUTE(f"assets/maps/{filename}"),pixelaplha = True) # Load tilemap
        self.WIDTH = tm.width * tm.tilewidth # Get width of tilemap
        self.HEIGHT = tm.height * tm.tileheight # Get height of tilemap
        self.tmxdata = tm


    def render(self,surface): # Render tilemap with surface using tmx
        ti = self.tmxdata.get_tile_image_by_gid # Get tile image by gid
        for layer in self.tmxdata.visible_layers: # Loop through visible layers
            if isinstance(layer,pytmx.TiledTileLayer): # Check if the layer is a tile layer
                for x,y,gid in layer: # Loop through tiles
                    tile = ti(gid) # Get tile image
                    if tile: # Check if tile is not None
                        surface.blit(tile,(x* self.tmxdata.tilewidth,y* self.tmxdata.tileheight))

    def make_map(self): # Make a surface object
        temp_surface = pg.Surface((self.WIDTH,self.HEIGHT)) # Create a surface
        self.render(temp_surface) # Render tilemap with surface
        return temp_surface # Return surface



    