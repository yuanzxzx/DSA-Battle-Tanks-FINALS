import sys
from typing import Dict, Union
import pygame as pg

from battle_tanks.components.text import TextComponent
from battle_tanks.game import Game
from battle_tanks.commons.package import Struct
from battle_tanks.commons.tank_surface import tank_cover, colors
from battle_tanks.components.network import NetworkComponent
from battle_tanks import ROUTE

GREEN_STATUS = (0, 128, 0)
RED_STATUS = (255,0,0)
NEU = (191, 191, 191)
BACKGROUND = (0,30,0)

class Menu:


    def __init__(self, main_surface: pg.Surface):
        self.main_surface = main_surface
        self.clock = pg.time.Clock()
        self.angle = 0
        self.angle_cannon = 0
        self.selected_tank_color = 0  # Default to blue

        # Load background image
        self.background_image = pg.image.load(ROUTE('assets/images/camo_bg.png')).convert()
        # Scale to fit the screen
        self.background_image = pg.transform.scale(self.background_image, (self.main_surface.get_width(), self.main_surface.get_height()))
    
        self.options: Dict[int, dict] = {
            2: {
                "text_draw": TextComponent((300, 250), "MULTIPLAYER MODE", font_size=45, color=NEU),
                "action": "MULTIPLAYER_MODE"
            },
        }


    def multiplayer_mode(self, game_screen) -> Union[Game, None]:
        """Menu connection form."""
        ip_text = "localhost"
        name: str = "JOHN PORK"
        user_text = "8010"
        option_select = 0
        status = NEU

        center_x = self.main_surface.get_width() // 2
        input_width = 360
        input_height = 44
        input_x = center_x - input_width // 2

        name_rect = pg.Rect(input_x, 270, input_width, input_height)
        ip_rect = pg.Rect(input_x, 330, input_width, input_height)
        port_rect = pg.Rect(input_x, 390, input_width, input_height)
        
        # Create enter button rect
        enter_text_temp = TextComponent((center_x, 490), "ENTER", status, font_size=36)
        enter_text_temp.update()
        enter_rect = enter_text_temp._rect.inflate(30, 18)
        
        # Cursor blink indicator
        cursor_blink_time = 0
        cursor_blink_interval = 500  # milliseconds
        
        # Help button setup for this screen
        help_button_rect = pg.Rect(20, self.main_surface.get_height() - 70, 50, 50)
        help_popup_visible = False
        
        # Color picker button setup
        color_picker_expanded = False
        tank_preview_scale = 150
        tank_preview_x = self.main_surface.get_width() - tank_preview_scale - 20
        tank_preview_y = self.main_surface.get_height() - tank_preview_scale - 120
        
        # Color button
        color_button_width = 100
        color_button_height = 40
        color_button_x = tank_preview_x + (tank_preview_scale - color_button_width) // 2
        color_button_y = tank_preview_y + tank_preview_scale + 15
        color_button_rect = pg.Rect(color_button_x, color_button_y, color_button_width, color_button_height)
        
        # Expanded color picker grid
        color_picker_cols = 6
        color_picker_rows = 4
        color_circle_size = 25
        color_rects = {}

        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()

                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = event.pos
                    # Check help button click first (always allow toggle)
                    if help_button_rect.collidepoint(mouse_pos):
                        help_popup_visible = not help_popup_visible
                    # Check if clicking outside popup to close it
                    elif help_popup_visible:
                        popup_rect = pg.Rect((self.main_surface.get_width() - 420) // 2, (self.main_surface.get_height() - 360) // 2, 420, 360)
                        if not popup_rect.collidepoint(mouse_pos):
                            help_popup_visible = False
                    # Check color button click
                    elif color_button_rect.collidepoint(mouse_pos):
                        color_picker_expanded = not color_picker_expanded
                    # Check color picker clicks when expanded
                    elif color_picker_expanded:
                        color_clicked = False
                        for color_id, color_rect in color_rects.items():
                            if color_rect.collidepoint(mouse_pos):
                                self.selected_tank_color = color_id
                                color_picker_expanded = False
                                color_clicked = True
                                break
                        if color_clicked:
                            continue  # Skip form field checks if color was selected
                    
                    # Check form field clicks (works regardless of color_picker_expanded state)
                    if port_rect.collidepoint(mouse_pos):
                        option_select = 0
                    elif ip_rect.collidepoint(mouse_pos):
                        option_select = 1
                    elif name_rect.collidepoint(mouse_pos):
                        option_select = 2
                    elif enter_rect.collidepoint(mouse_pos):
                        try:
                            if len(user_text) > 0 and len(name) > 0:
                                check_name = NetworkComponent.check_name((ip_text, int(user_text)), name)
                                if check_name:
                                    game = Game((ip_text, int(user_text)), game_screen, name, self.selected_tank_color)
                                    if game.network.player_data != Struct.USER_NOT_AVAILABLE:
                                        return game
                                else:
                                    status = RED_STATUS
                        except ConnectionRefusedError as e:
                            print(e)
                            status = RED_STATUS

                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_TAB:
                        option_select = (option_select + 1) % 3
                    elif event.key == pg.K_BACKSPACE:
                        if option_select == 2:
                            name = name[:-1]
                        elif option_select == 1:
                            ip_text = ip_text[:-1]
                        else:
                            user_text = user_text[:-1]

                    elif event.key == pg.K_RETURN:
                        try:
                            if len(user_text) > 0 and len(name) > 0:
                                check_name = NetworkComponent.check_name((ip_text, int(user_text)), name)
                                if check_name:
                                    game = Game((ip_text, int(user_text)), game_screen, name, self.selected_tank_color)
                                    if game.network.player_data != Struct.USER_NOT_AVAILABLE:
                                        return game
                                else:
                                    status = RED_STATUS
                        except ConnectionRefusedError as e:
                            print(e)
                            status = RED_STATUS

                    else:
                        char = event.dict.get("unicode")
                        if not char:
                            continue

                        if option_select == 2:
                            name += char.upper()
                        elif option_select == 1:
                            ip_text += char
                        elif option_select == 0:
                            if char.isdigit() and len(user_text) < 5:
                                user_text += char

                if event.type == pg.KEYDOWN and event.key not in (pg.K_DOWN, pg.K_UP):
                    if len(name) > 0 and option_select == 2:
                        try:
                            port = int(user_text)
                            if 0 < port < 65535:
                                check_name = NetworkComponent.check_name((ip_text, int(user_text)), name)
                                if check_name is True:
                                    status = GREEN_STATUS
                                elif check_name is False:
                                    status = RED_STATUS
                                else:
                                    status = NEU
                        except ValueError:
                            status = RED_STATUS

            # Update cursor blink state
            cursor_blink_time += self.clock.get_time()
            show_cursor = (cursor_blink_time // cursor_blink_interval) % 2 == 0

            self.main_surface.blit(self.background_image, (0, 0))

            # Title with 3D shadow effect - split into "BATTLE" and "TANKS"
            shadow_color = (30, 30, 30)
            title_color = (255, 255, 255)
            font_size = 115
            title_x = self.main_surface.get_width() // 2
            title_y_battle = 80
            title_y_tanks = 168
            shadow_offset_x = 6
            shadow_offset_y = 6
            
            # Draw BATTLE with shadow
            battle_shadow = TextComponent((title_x + shadow_offset_x, title_y_battle + shadow_offset_y), "BATTLE", font_size=font_size, color=shadow_color)
            battle_shadow.update()
            battle_shadow.draw(self.main_surface)
            
            battle_text = TextComponent((title_x, title_y_battle), "BATTLE", font_size=font_size, color=title_color)
            battle_text.update()
            battle_text.draw(self.main_surface)
            
            # Draw TANKS with shadow
            tanks_shadow = TextComponent((title_x + shadow_offset_x, title_y_tanks + shadow_offset_y), "TANKS", font_size=font_size, color=shadow_color)
            tanks_shadow.update()
            tanks_shadow.draw(self.main_surface)
            
            tanks_text = TextComponent((title_x, title_y_tanks), "TANKS", font_size=font_size, color=title_color)
            tanks_text.update()
            tanks_text.draw(self.main_surface)

            input_padding = 16
            surface_input_port = pg.Surface((input_width, input_height), pg.SRCALPHA)
            surface_input_ip = pg.Surface((input_width, input_height), pg.SRCALPHA)
            surface_input_name = pg.Surface((input_width, input_height), pg.SRCALPHA)

            port_bg = (40, 70, 40) if option_select == 0 else (20, 40, 20)
            ip_bg = (40, 70, 40) if option_select == 1 else (20, 40, 20)
            name_bg = (40, 70, 40) if option_select == 2 else (20, 40, 20)

            # Draw rounded background rectangles
            pg.draw.rect(surface_input_port, port_bg, (0, 0, input_width, input_height), border_radius=10)
            pg.draw.rect(surface_input_ip, ip_bg, (0, 0, input_width, input_height), border_radius=10)
            pg.draw.rect(surface_input_name, name_bg, (0, 0, input_width, input_height), border_radius=10)

            port_border = (255, 255, 255) if option_select == 0 else NEU
            ip_border = (255, 255, 255) if option_select == 1 else NEU
            name_border = (255, 255, 255) if option_select == 2 else NEU

            pg.draw.rect(self.main_surface, port_border, port_rect, 3 if option_select == 0 else 2, border_radius=10)
            pg.draw.rect(self.main_surface, ip_border, ip_rect, 3 if option_select == 1 else 2, border_radius=10)
            pg.draw.rect(self.main_surface, name_border, name_rect, 3 if option_select == 2 else 2, border_radius=10)

            text_input = TextComponent((input_padding + 5, input_height // 2), user_text, (255, 255, 255), font_size=30)
            text_input._rect = text_input._surface.get_rect(midleft=(input_padding, input_height // 2))
            text_input.draw(surface_input_port)
            # Draw cursor for port field if active
            if option_select == 0 and show_cursor:
                cursor_x = text_input._rect.right + 5
                pg.draw.line(surface_input_port, (255, 255, 255), (cursor_x, 8), (cursor_x, input_height - 8), 2)

            text_input_ip = TextComponent((input_padding + 5, input_height // 2), ip_text, (255, 255, 255), font_size=30)
            text_input_ip._rect = text_input_ip._surface.get_rect(midleft=(input_padding, input_height // 2))
            text_input_ip.draw(surface_input_ip)
            # Draw cursor for IP field if active
            if option_select == 1 and show_cursor:
                cursor_x = text_input_ip._rect.right + 5
                pg.draw.line(surface_input_ip, (255, 255, 255), (cursor_x, 8), (cursor_x, input_height - 8), 2)

            text_input_name = TextComponent((input_padding + 5, input_height // 2), name, (255, 255, 255), font_size=30)
            text_input_name._rect = text_input_name._surface.get_rect(midleft=(input_padding, input_height // 2))
            text_input_name.draw(surface_input_name)
            # Draw cursor for name field if active
            if option_select == 2 and show_cursor:
                cursor_x = text_input_name._rect.right + 5
                pg.draw.line(surface_input_name, (255, 255, 255), (cursor_x, 8), (cursor_x, input_height - 8), 2)

            self.main_surface.blit(surface_input_name, name_rect.topleft)
            self.main_surface.blit(surface_input_ip, ip_rect.topleft)
            self.main_surface.blit(surface_input_port, port_rect.topleft)
            
            # Draw white outline around all text boxes
            pg.draw.rect(self.main_surface, (255, 255, 255), port_rect, 1, border_radius=10)
            pg.draw.rect(self.main_surface, (255, 255, 255), ip_rect, 1, border_radius=10)
            pg.draw.rect(self.main_surface, (255, 255, 255), name_rect, 1, border_radius=10)

            label_color_name = (255, 255, 255) if option_select == 2 else NEU
            label_color_ip = (255, 255, 255) if option_select == 1 else NEU
            label_color_port = (255, 255, 255) if option_select == 0 else NEU

            text_name = TextComponent((input_x - 80, name_rect.centery), "NAME:", color=label_color_name, font_size=30)
            text_ip = TextComponent((input_x - 80, ip_rect.centery), "SERVER:", color=label_color_ip, font_size=30)
            text_port = TextComponent((input_x - 80, port_rect.centery), "PORT:", color=label_color_port, font_size=30)
            text_enter = TextComponent((center_x, enter_rect.centery), "ENTER", status, font_size=36)
            text_name.update()
            text_ip.update()
            text_port.update()
            text_enter.update()

            pg.draw.rect(self.main_surface, (50, 90, 50), enter_rect, border_radius=8)
            pg.draw.rect(self.main_surface, status if status != NEU else (255, 255, 255), enter_rect, 2, border_radius=8)

            text_name.draw(self.main_surface)
            text_ip.draw(self.main_surface)
            text_port.draw(self.main_surface)
            text_enter.draw(self.main_surface)

            if port_rect.collidepoint(pg.mouse.get_pos()) or ip_rect.collidepoint(pg.mouse.get_pos()) or name_rect.collidepoint(pg.mouse.get_pos()) or enter_rect.collidepoint(pg.mouse.get_pos()) or help_button_rect.collidepoint(pg.mouse.get_pos()):
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_HAND)
            else:
                pg.mouse.set_cursor(pg.SYSTEM_CURSOR_ARROW)

            self.angle += 0.5
            self.angle_cannon -= 0.5
            self.angle %= 360
            self.angle_cannon %= 360

            # Draw rotating tank showing selected color
            tank_cover(self.selected_tank_color, (tank_preview_x, tank_preview_y), self.main_surface, scale=(tank_preview_scale, tank_preview_scale), angle=self.angle, angle_cannon=self.angle_cannon)
            
            # Draw color picker button
            button_color = (60, 100, 60) if color_picker_expanded else (40, 70, 40)
            button_border = (255, 255, 255) if color_picker_expanded else NEU
            pg.draw.rect(self.main_surface, button_color, color_button_rect, border_radius=8)
            pg.draw.rect(self.main_surface, button_border, color_button_rect, 2, border_radius=8)
            
            # Draw button text
            button_text = "SELECT" if color_picker_expanded else "TANK COLOR"
            button_label = TextComponent((color_button_rect.centerx, color_button_rect.centery), button_text, color=(255, 255, 255), font_size=14)
            button_label.update()
            button_label.draw(self.main_surface)
            
            # Draw expanded color picker
            if color_picker_expanded:
                # Update color rects based on button position
                color_picker_start_x = tank_preview_x - 30
                color_picker_start_y = color_button_y - (color_picker_rows * (color_circle_size + 8) + 20)
                
                for i in range(24):
                    row = i // color_picker_cols
                    col = i % color_picker_cols
                    x = color_picker_start_x + col * (color_circle_size + 8)
                    y = color_picker_start_y + row * (color_circle_size + 8)
                    color_rects[i] = pg.Rect(x, y, color_circle_size, color_circle_size)
                
                # Draw semi-transparent background for expanded picker
                picker_bg_rect = pg.Rect(color_picker_start_x - 10, color_picker_start_y - 10, 
                                          color_picker_cols * (color_circle_size + 8) + 20, 
                                          color_picker_rows * (color_circle_size + 8) + 20)
                bg_surface = pg.Surface((picker_bg_rect.width, picker_bg_rect.height))
                bg_surface.set_alpha(220)
                bg_surface.fill((20, 30, 20))
                self.main_surface.blit(bg_surface, picker_bg_rect.topleft)
                pg.draw.rect(self.main_surface, NEU, picker_bg_rect, 2, border_radius=8)
                
                # Draw color circles
                for color_id, color_rect in color_rects.items():
                    is_selected = (color_id == self.selected_tank_color)
                    border_width = 3 if is_selected else 1
                    border_color = (255, 255, 255) if is_selected else NEU
                    
                    pg.draw.circle(self.main_surface, colors[color_id], color_rect.center, color_circle_size // 2)
                    pg.draw.circle(self.main_surface, border_color, color_rect.center, color_circle_size // 2, border_width)

            # Draw help button
            help_button_color = (60, 100, 60) if help_popup_visible else (40, 70, 40)
            help_button_border = (255, 255, 255) if help_popup_visible else NEU
            pg.draw.rect(self.main_surface, help_button_color, help_button_rect, border_radius=8)
            pg.draw.rect(self.main_surface, help_button_border, help_button_rect, 2, border_radius=8)
            
            # Draw question mark
            question_mark = TextComponent((help_button_rect.centerx, help_button_rect.centery), "?", color=(255, 255, 255), font_size=30)
            question_mark.update()
            question_mark.draw(self.main_surface)
            
            # Draw help popup
            if help_popup_visible:
                popup_width = 420
                popup_height = 360
                popup_x = (self.main_surface.get_width() - popup_width) // 2
                popup_y = (self.main_surface.get_height() - popup_height) // 2
                
                # Semi-transparent background
                popup_bg = pg.Surface((popup_width, popup_height))
                popup_bg.set_alpha(240)
                popup_bg.fill((20, 30, 20))
                self.main_surface.blit(popup_bg, (popup_x, popup_y))
                pg.draw.rect(self.main_surface, (255, 255, 255), (popup_x, popup_y, popup_width, popup_height), 2, border_radius=10)
                
                # Title
                title = TextComponent((popup_x + popup_width // 2, popup_y + 20), "GAME CONTROLS", color=(255, 255, 255), font_size=28)
                title.update()
                title.draw(self.main_surface)
                
                # Keybinds
                controls = [
                    "MOVEMENT:",
                    "W - Move Forward",
                    "S - Move Backward", 
                    "A - Move Left",
                    "D - Move Right",
                    "",
                    "CANNON:",
                    "I - Rotate Left",
                    "P - Rotate Right",
                    "",
                    "ACTIONS:",
                    "O - Fire Bullet",
                    "K - Burst Fire (15s Cooldown)",
                    "M - Place Landmine"
                ]
                
                y_offset = 55
                for control in controls:
                    if control == "":
                        y_offset += 8
                        continue
                    color = (255, 255, 0) if ":" in control else (200, 200, 200)
                    font_size = 20 if ":" in control else 18
                    text = TextComponent((popup_x + popup_width // 2, popup_y + y_offset), control, color=color, font_size=font_size)
                    text.update()
                    text.draw(self.main_surface)
                    y_offset += 24

            pg.display.flip()
            self.clock.tick(60)


    def single_local_mode(self) -> Game:
        """ Single local game """
        return Game(None, self.main_surface, "John", self.selected_tank_color)


    def update(self, main_game) -> Game:
        """Go directly to multiplayer mode."""
        return self.multiplayer_mode(main_game)


    def draw(self):
        """ Draw options"""
        self.main_surface.blit(self.background_image, (0, 0))
        
        mouse_pos = pg.mouse.get_pos()

        for op, values in self.options.items():
            op_draw = values.get("text_draw")
            
            # Highlight option if mouse is hovering over it or keyboard selected
            if op_draw._rect.collidepoint(mouse_pos) or self.position == op:
                op_draw.color = (255, 255, 255)
                if op_draw._rect.collidepoint(mouse_pos):
                    self.position = op
            else:
                op_draw.color = NEU

            op_draw.update()
            op_draw.draw(self.main_surface)
                text_ip.color = NEU
                text_name.color = NEU

            """
            LABELS: IP, PORT AND NAME
            """
            text_ip.draw(self.main_surface)
            text_port.draw(self.main_surface)
            text_name.draw(self.main_surface)
            text_enter.draw(self.main_surface)

            """
            INPUT
            """
            self.main_surface.blit(surface_input_port, (120,160))
            self.main_surface.blit(surface_input_ip, (120,100))
            self.main_surface.blit(surface_input_name,(120,40))

            """
            TANK
            """
            self.angle += 0.5
            self.angle_cannon -= 0.5

            self.angle = self.angle % 360
            self.angle_cannon = self.angle_cannon % 360

            tank_cover(0, (150, 300), self.main_surface, scale=(200, 200), angle=self.angle, angle_cannon=self.angle_cannon)
            tank_cover(1, (450, 300), self.main_surface, scale=(200, 200), angle=self.angle, angle_cannon=self.angle_cannon)

            pg.display.flip()
            self.clock.tick(60)


        return None


    def single_local_mode(self) -> Game:
        """ Single local game """
        return Game(None, self.main_surface, "John")


    def update(self, main_game) -> Game:
        """ getting game state"""
        if len(self.options) == 1:
            self.select_option = [op for op in self.options.keys()][0]
            self.select_option = self.options.get(self.select_option).get("action")

        while self.select_option is None:
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    key = event.dict.get('key')

                    if key == pg.K_DOWN or key == pg.K_s:
                        if self.position < len(self.options):
                            self.position +=1

                    if key == pg.K_UP or  key == pg.K_w:
                        if len(self.options) <= self.position:
                            self.position -=1

                    elif key == pg.K_RETURN:
                        select_option: dict = self.options.get(self.position)
                        self.select_option = select_option.get("action")

                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()


            self.draw()
            pg.display.flip()

        return self.multiplayer_mode(main_game) if self.select_option == "MULTIPLAYER_MODE" \
            else self.single_local_mode()


    def draw(self):
        """ Draw options"""
        self.main_surface.fill(BACKGROUND)

        if self.position != 0:
            select_option: dict = self.options.get(self.position)
            text_draw: TextComponent = select_option.get("text_draw")
            text_draw.color=(255,255,255)

            self.options.update({self.position: {
                "text_draw": text_draw,
                "action" : select_option.get("action")
                        }})

        for op,values in self.options.items():
            op_draw = values.get("text_draw")
            if op != self.position:
                op_draw.color=NEU

            op_draw.update()
            op_draw.draw(self.main_surface)

        tank_cover(0,(150,300),self.main_surface,scale=(200,200),angle=0,angle_cannon=0)
        tank_cover(1,(450,300),self.main_surface,scale=(200,200),angle=360,angle_cannon=180)

