""" Client and Single Game"""

import pygame as pg
import queue 
import threading as th
import math

from battle_tanks.components.text import TextComponent
from battle_tanks import  ROUTE, game
from battle_tanks.commons.package import Struct
from battle_tanks.components import NetworkComponent
from battle_tanks.menu import Menu

def network_client_consumer(client: NetworkComponent): 
    """
    Waits for responses from the server and sends the results to the update queue.
    """
    while True:
        # Receive data from the server
        data = client.recv_move_player() 
        
        # Put the received data into the update queue
        NetworkComponent.UPDATE_Q.put(data)


def network_client_handler(client: NetworkComponent):
    """
    Handles network communication for a client.
    """
    while True:
        # Get an item from the SEND_Q queue
        data = NetworkComponent.SEND_Q.get()
        
        # If the item is not queue.Empty, send the move to the server
        if data is not queue.Empty:
            client.send_move_tcp(data)
        
def main():
    """ Client game of server"""

    pg.display.set_caption(f"Battle Tank") # Set the title of the window
    pg.display.set_icon(pg.image.load(ROUTE("assets/images/lemon.ico"))) # Set the icon of the window
    pg.font.init() # Initialize the font
    pg.event.set_allowed([ # Set the events allowed
        pg.QUIT, 
        pg.KEYDOWN,
        pg.KEYUP,
    ])

    clock = pg.time.Clock() # Initialize the clock
    WIDTH,HEIGHT = 800, 600 # Set the width and height of the window
    SCREEN = pg.display.set_mode((WIDTH,HEIGHT + 60))
    hud_bg = pg.image.load(ROUTE("assets/images/hud_bg.png")).convert_alpha()
    hud_bg = pg.transform.scale(hud_bg, (WIDTH, 60)) # Resize the hud background

    main_game = pg.Surface((WIDTH,HEIGHT))
    menu = Menu(SCREEN)
    # game = menu.update(main_game) - Pacinio -- update does not exist in menu
    game = menu.multiplayer_mode(main_game) 
    text_damage = TextComponent((WIDTH//2,HEIGHT +30 ),f"Damage: {game.damage} %", color=(168, 0, 0), font_size=40)
    bullets = pg.Surface((WIDTH,36))

    #-Yu (load shotgun icon)
    game.last_shotgun_time = -10000
    try:
        shotgun_icon = pg.image.load(ROUTE("assets/images/shotgun_icon.png")).convert_alpha()#Load shotgun icon
        shotgun_icon = pg.transform.scale(shotgun_icon, (40, 40)) # Resize shotgun icon
    except Exception: # Handle exception
        shotgun_icon = pg.Surface((40, 40), pg.SRCALPHA) # Create a surface for shotgun icon
        pg.draw.circle(shotgun_icon, (100, 100, 100), (20, 20), 20) # Draw a circle for shotgun icon
    #-Yu (load shotgun icon)

    """
    CLIENT NETWORK
    """
    th_recevied = th.Thread(target = network_client_consumer, daemon = True, args= (game.network,)) # Thread for receiving data from the server
    th_send = th.Thread(target = network_client_handler, daemon = True, args=(game.network,)) # Thread for sending data to the server

    th_recevied.start() # Start the thread for receiving data
    th_send.start() # Start the thread for sending data

    while True: # Loop for the game
        for event in pg.event.get(): # Get events
            if event.type == pg.QUIT: # Quit event
                game.close()
            
            elif event.type == pg.KEYDOWN: # Keydown event
                key = event.key # Get the key that was pressed
                if key == pg.K_l and game.state != 2: # Lock laser event
                    if getattr(game.player, "energy", 0) >= 100.0: # Check if player has enough energy
                        game.player.laser_active = True # Activate laser
                        game.network.send_move_tcp(Struct.LASER_ON_EVENT) # Send laser on event to the server
                #-Yu (listen for K key to fire shotgun)
                elif key == pg.K_k and game.state != 2: # Listen for K key to fire shotgun
                    current_time = pg.time.get_ticks() # Get the current time
                    if current_time - game.last_shotgun_time >= 10000: # Check if enough time has passed since the last shotgun fire
                        if game.player.type_gun.limit is True or game.player.type_gun.count_available >= 5: # Check if player has enough shotgun shells
                            game.last_shotgun_time = current_time # Set the last shotgun time to the current time
                            game.player.shotgun_fire = True # Set shotgun fire to true
                            if game.network:
                                game.network.send_move_tcp(Struct.SHOTGUN_EVENT_PLAYER)
                #-Yu (listen for K key to fire shotgun)
            
            elif event.type == pg.KEYUP: # Keyup event
                key = event.key # Get the key that was released
                if key == pg.K_l: # Laser off event
                    game.player.laser_active = False # Deactivate laser
                    if game.network:
                        game.network.send_move_tcp(Struct.LASER_OFF_EVENT) # Send laser off event to the server
                elif key == pg.K_o and game.state != 2: # Listen for O key to fire
                    current_time = pg.time.get_ticks() # Get the current time
                    cooldown_duration = 835 # Cooldown duration
                    if current_time - game.last_shot_time >= cooldown_duration: # Check if enough time has passed since the last shot
                        if game.player.check_available_bullets(): # Check if player has enough bullets
                            game.last_shot_time = current_time # Set the last shot time to the current time
                            game.player.fire = True # Set fire to true
                            if game.network:
                                game.network.send_move_tcp(Struct.FIRE_EVENT_PLAYER) # Send fire event to the server

        
        SCREEN.fill((0,0,0)) # Fill the screen with black
        game.update() # Update the game
        game.draw(main_game) # Draw the game
        SCREEN.blit(main_game,(0,0)) # Blit the main game to the screen
        SCREEN.blit(hud_bg,(0,HEIGHT)) # Blit the hud background to the screen

        bullets.set_colorkey((0, 0, 0))
        bullets.fill((0,0,0)) # Fill the bullets surface with black
        game.player.type_gun.render(bullets) # Render bullets
        SCREEN.blit(bullets, (0, HEIGHT + 12)) # Blit bullets to the screen

        #-Yu (draw shotgun UI cooldown)
        shotgun_x = WIDTH - 60 # Set x position of shotgun
        shotgun_y = HEIGHT + 10 # Set y position of shotgun
        SCREEN.blit(shotgun_icon, (shotgun_x, shotgun_y)) # Blit shotgun to the screen
        
        current_time = pg.time.get_ticks() # Get the current time
        time_since_shotgun = current_time - game.last_shotgun_time # Get the time since the last shotgun fire
        if time_since_shotgun < 10000: # Check if enough time has passed since the last shotgun fire
            angle_ratio = 1 - (time_since_shotgun / 10000.0) # Calculate the angle ratio
            end_angle = angle_ratio * 2 * math.pi # Calculate the end angle
            rect = pg.Rect(shotgun_x, shotgun_y, 40, 40) # Create a rectangle for the shotgun
            pg.draw.arc(SCREEN, (255, 0, 0), rect, math.pi/2, math.pi/2 + end_angle, 4) # Draw the arc for the shotgun cooldown
        #-Yu (draw shotgun UI cooldown)

        text_damage.text = f"Damage: {game.damage} %" # Set the text for the damage
        text_damage.update() # Update the damage text
        text_damage.draw(SCREEN) # Draw the damage text
        clock.tick(60) # Set the clock tick to 60
        pg.display.flip() # Flip the display

if __name__ == "__main__":
    main()
