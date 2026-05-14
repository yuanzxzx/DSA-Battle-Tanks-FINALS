# Management of the munition system and UI rendering
from typing import List, Tuple, Optional

import pygame as pg

from battle_tanks.commons.tank_surface import draw_bullet

# Hardcoded dimensional fallback to avoid distorted rendering of bullet icons
DEFAULT_BULLET_DIMENSIONS: Tuple[int, int] = (4, 10)

# Neutral baseline rotation so bullets face forward in the HUD
DEFAULT_BULLET_ANGLE: int = 0

# Encapsulate ammo properties and firing state to maintain strict combat logic boundaries
class CannonType:
    
    # Pre-allocate default values to prevent null reference errors during weapon swaps
    def __init__(self, count: int, gun_type: dict, size: Tuple[int, int]) -> None:
        self.count: int = count 
        self._count_available: int = count
        self.type: dict = gun_type
        self.limit: bool = False
        self.vl: Optional[float] = None
        self.size: Tuple[int, int] = size
        self.damage: Optional[int] = None
        self._reload_time: int = 100
        self._count_reload: int = 0

    # Expose ammo counter read-only initially to safeguard UI synchronization
    @property
    def count_available(self) -> int:
        return self._count_available

    # Allow controlled overrides of ammo reserves to support powerups or penalties
    @count_available.setter
    def count_available(self, count_available: int) -> None:
        self._count_available = count_available

    # Isolate reload frame timing to prevent monolithic clutter in the render loop
    def _process_reload_mechanic(self) -> None:
        try:
            # Poll for depleted magazine to begin cooldown ticks
            if self._count_available <= 0:
                
                # Advance the reload progression frame by frame to sync with game loop
                self._count_reload += 1

                # Trigger instantaneous refill when the cooldown threshold is met
                if self._count_reload >= self._reload_time:
                    
                    # Reset the counter to allow future reloading cycles
                    self._count_reload = 0
                    
                    # Replenish full capacity so the player can resume firing
                    self._count_available = self.count
        except Exception as e:
            # Fail gracefully to ensure game continues running even if reload math breaks
            print(f"Reload logic interrupted by state error: {e}")

    # Decouple spatial calculation to make UI scaling easier to maintain
    def _get_bullet_render_positions(self) -> List[Tuple[int, int]]:
        width: int = self.size[0]
        try:
            # Distribute bullets horizontally by multiplying index by width to prevent overlapping textures
            return [(width * i, 0) for i in range(0, self._count_available)]
        except Exception as e:
            # Provide an empty array to prevent rendering crashes on invalid data
            print(f"Failed to calculate bullet layout offsets: {e}")
            return []

    # Update frame logic and dispatch draw calls for the ammo GUI layer
    def render(self, bullet_surface: pg.Surface) -> pg.Surface:
        self._process_reload_mechanic()
        
        bullet_positions: List[Tuple[int, int]] = self._get_bullet_render_positions()

        try:
            # Iterate through the generated coordinate map to stamp each bullet texture
            for position in bullet_positions:
                draw_bullet(bullet_surface, position, DEFAULT_BULLET_ANGLE, DEFAULT_BULLET_DIMENSIONS)
        except pg.error as e:
            # Trap rendering exceptions so isolated UI bugs do not crash the entire client
            print(f"Pygame drawing failure during ammo rendering: {e}")
            
        return bullet_surface
