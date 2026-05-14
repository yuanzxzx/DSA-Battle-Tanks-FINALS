# Management of the munition system and UI rendering
from typing import List, Tuple, Optional

import pygame as pg

from battle_tanks.commons.tank_surface import draw_bullet

# Hardcoded dimensional fallback to avoid distorted rendering of bullet icons
DEFAULT_BULLET_DIMENSIONS= (4, 10) 

# Neutral baseline rotation so bullets face forward in the HUD
DEFAULT_BULLET_ANGLE = 0 

# Encapsulate ammo properties and firing state to maintain strict combat logic boundaries
class CannonType:
    
    # Pre-allocate default values to prevent null reference errors during weapon swaps
    def __init__(self, count, gun_type, size) -> None: 
        self.count = count #Total ammo count
        self._count_available = count #Current ammo count
        self.type = gun_type #Type of gun
        self.limit = False #Limit ammo
        self.vl = None #Bullet velocity
        self.size = size #Bullet size
        self.damage = None #Damage
        self._reload_time = 100 #Reload time
        self._count_reload = 0 #Reload counter

    # Expose ammo counter read-only initially to safeguard UI synchronization
    @property
    def count_available(self) -> int: #Getter for ammo counter
        return self._count_available

    # Allow controlled overrides of ammo reserves to support powerups or penalties
    @count_available.setter
    def count_available(self, count_available) -> None: #Setter for ammo counter
        self._count_available = count_available

    # Isolate reload frame timing to prevent monolithic clutter in the render loop
    def _process_reload_mechanic(self) -> None: #Reload mechanic
        try:
            # Poll for depleted magazine to begin cooldown ticks
            if self._count_available <= 0: #Check if ammo is empty
                self._count_reload += 1 #Increment reload counter
                # Trigger instantaneous refill when the cooldown threshold is met
                if self._count_reload >= self._reload_time: #Check if reload time is met
                    # Reset the counter to allow future reloading cycles
                    self._count_reload = 0 #Reset reload counter
                    # Replenish full capacity so the player can resume firing
                    self._count_available = self.count #Replenish ammo
        except Exception as e:
            # Fail gracefully to ensure game continues running even if reload math breaks
            print(f"Reload logic interrupted by state error: {e}")

    # Decouple spatial calculation to make UI scaling easier to maintain
    def _get_bullet_render_positions(self) -> List[Tuple[int, int]]: #Get bullet render positions
        width: int = self.size[0] #Get bullet width
        try:
            # Distribute bullets horizontally by multiplying index by width to prevent overlapping textures
            return [(width * i, 0) for i in range(0, self._count_available)] #Return bullet positions
        except Exception as e:
            # Provide an empty array to prevent rendering crashes on invalid data
            print(f"Failed to calculate bullet layout offsets: {e}") #Print error message
            return [] #Return empty array

    # Update frame logic and dispatch draw calls for the ammo GUI layer
    def render(self, bullet_surface: pg.Surface) -> pg.Surface: #Render ammo GUI layer
        self._process_reload_mechanic() #Process reload mechanic
        
        bullet_positions: List[Tuple[int, int]] = self._get_bullet_render_positions() #Get bullet positions

        try: #Try to render bullets
            # Iterate through the generated coordinate map to stamp each bullet texture
            for position in bullet_positions: #Iterate through bullet positions
                draw_bullet(bullet_surface, position, DEFAULT_BULLET_ANGLE, DEFAULT_BULLET_DIMENSIONS) #Draw bullet texture
        except pg.error as e:
            # Trap rendering exceptions so isolated UI bugs do not crash the entire client
            print(f"Pygame drawing failure during ammo rendering: {e}")
            
        return bullet_surface
