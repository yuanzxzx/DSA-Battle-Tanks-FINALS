import pygame as pg 

class CameraComponent: # Create a camera object 
    """ The camera object that will be used to render the scene and interact """
    def __init__(self,width,height,screen_size): # Initialize the camera object
        self.camera = pg.Rect((0,0),(width,height)) # Create the camera rectangle
        self.width = width # Set the width of the camera
        self.height = height # Set the height of the camera
        self.screen_size = screen_size # Set the screen size
    def apply(self,entity): # Apply the camera transformation to the entity
        """ Apply the camera transformation to the entity """
        return entity.rect.move(self.camera.topleft)
    def apply_rect(self,rect): # Apply the camera transformation to the rectangle
        return rect.move(self.camera.topleft)
    def update(self,target): # Update the camera position
        x_pos = -target.rect.centerx + self.screen_size[0] // 2 # Calculate the x position of the camera
        y_pos = -target.rect.centery + self.screen_size[1] // 2 # Calculate the y position of the camera
        #limit scrolling to map size
        x_pos = min(0,x_pos) #left
        y_pos = min(0,y_pos) #top
        x_pos = max(-(self.width - self.screen_size[0]),x_pos) #right
        y_pos = max(-(self.height - self.screen_size[1]),y_pos) #bottom
        self.camera = pg.Rect(x_pos,y_pos,self.width,self.height) # Update the camera rectangle

