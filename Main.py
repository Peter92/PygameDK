from __future__ import division
import time
import pygame
import math
import random
from operator import itemgetter

from DKWorld import *
from DKMisc import *
from FrameLimit import GameTime, GameTimeLoop

        
class ObjectMovement(object):
    """Class that can store infinite movement, possibly other stuff later on."""
    
    def __init__(self, x=0, y=0, speed=100):
        """Input starting location and the max speed."""
        self.x_int, self.x_float = split_num(x)
        self.y_int, self.y_float = split_num(y)
        self.speed = speed
    
    def _formatstr(self, n_int, n_float):
        """Convert int and float to a string, needed for large numbers
        when adding wouldn't work. 
        (will be moved out of this class later)
        """
        if n_int < 0:
            n_str = '-'[n_int != -1:] + str(n_int + 1) + '.' + str(1 - n_float)[2:]
        else:
            n_str = str(n_int) + '.' + str(n_float)[2:]
        return n_str
    
    def __str__(self):
        return str((self._formatstr(self.x_int, self.x_float), 
                    self._formatstr(self.y_int, self.y_float))).replace("'", "")
        
    def move(self, x=0, y=0, multiplier=None):
        """Add to the total movement."""
        if multiplier is None:
            multiplier = self.speed
            
        if x:
            x_int, x_float = split_num(x * multiplier)
            self.x_int += x_int
            self.x_float += x_float
                
        if y:
            y_int, y_float = split_num(y * multiplier)
            self.y_int += y_int
            self.y_float += y_float
        
        self.overflow()
    
    def overflow(self):
        """Overflow the decimal value if above 1."""
        i = 1 if self.x_float >= 1 else -1
        while not 0 <= self.x_float < 1:
            self.x_float -= i
            self.x_int += i
        i = 1 if self.y_float >= 1 else -1
        while not 0 <= self.y_float < 1:
            self.y_float -= i
            self.y_int += i
    
class GameData(object):
    """Stuff to do with block selection currently."""
    BLOCK_TAG = set()
    BLOCK_TMP = set()
    BLOCK_TMP_OLD = set()
    BLOCK_TMP_START = None
    BLOCK_TMP_END = None
    BLOCK_TMP_TYPE = 0
    BLOCK_DATA = {}
    
    
class MainGame(object):

    WIDTH = 1280
    HEIGHT = 720
    DEFAULT_TILE = WATER
    TILE_MAX_SIZE = 128
    TILE_MIN_SIZE = 16
    FPS = None
    TICKS = 120

    def recalculate(self):
        """Update all tiles with new screen dimensions."""
        overflow = 2 #How many extra blocks to draw around screen
        try:
            self.frame_data['Redraw'] = True
        except AttributeError:
            pass
        
        #Calculate edges of screen
        x_min = self.cam.x_int + 1 - overflow
        y_min = self.cam.y_int + 1 - overflow
        x_max = self.cam.x_int + int(self.WIDTH / self.tilesize) + overflow
        y_max = self.cam.y_int + int(self.HEIGHT / self.tilesize) + overflow
        
        #Build list of all tiles
        self.screen_coordinates = [(x, y) 
                                   for x in range(x_min, x_max) 
                                   for y in range(y_min, y_max)]
        
        
        #Delete the tiles that have gone off screen
        del_keys = []
        for key in self.screen_block_data:
            if not x_min < key[0] < x_max or not y_min < key[1] < y_max:
                del_keys.append(key)
        for key in del_keys:
            del self.screen_block_data[key]
        
        
        #Rebuild the new list of blocks
        for coordinate in self.screen_coordinates:
        
            tile_origin = ((coordinate[0] - self.cam.x_int) - self.cam.x_float, 
                           (coordinate[1] - self.cam.y_int) - self.cam.y_float)
            tile_location = tuple(i * self.tilesize for i in tile_origin)
            
            if coordinate in self.screen_block_data:
                #Update existing point with new location
                self.screen_block_data[coordinate][2] = tile_location
            
            else:
                #Generate new point info
                block_type = get_tile(coordinate)
                block_hash = quick_hash(*coordinate, offset=self.noise_level)
                
                #Get alternate colour based on if the block is tagged
                #Colours are different for debugging purposes
                colour_mix = None
                if self.game_data.BLOCK_TMP_TYPE and coordinate in self.game_data.BLOCK_TMP:
                    colour_mix = YELLOW
                elif coordinate in self.game_data.BLOCK_TAG and coordinate not in self.game_data.BLOCK_TMP:
                    colour_mix = CYAN
                
                main_colour = TILECOLOURS[block_type]
                block_colour = [min(255, max(0, c + block_hash)) for c in main_colour]
                
                #Mix alternate colour if required
                try:
                    block_colour = [(c + colour_mix[i] * 15) / 16 for i, c in enumerate(block_colour)]
                except TypeError:
                    pass
                
                self.screen_block_data[coordinate] = [block_type, 
                                                      block_colour, 
                                                      tile_location]
        
    
    def setscreen(self):
        """Recalculate screen specific things."""
        try:
            self.frame_data['Redraw'] = True
        except AttributeError:
            pass
        try:
            self.screen_block_data
        except AttributeError:
            self.screen_block_data = {}
        self.mid_point = [self.WIDTH // 2, self.HEIGHT // 2]
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.RESIZABLE | pygame.DOUBLEBUF | pygame.HWSURFACE)
    
    def play(self):
    
        #Initialise screen
        pygame.init()
        self.setscreen()
        
        #Initialise game
        GT = GameTime(self.FPS, self.TICKS)
        self.game_data = GameData()
        self.state = 'Main'
        self.tilesize = 20
        self.noise_level = 15
        self.screen.fill((255, 255, 255))
        
        #Camera
        self.cam = ObjectMovement(0, 0, 0.125)
        
        #Run inital code
        self.recalculate()
        self._world_draw()
        pygame.display.flip()
        while True:
            with GameTimeLoop(GT) as game_time:
            
                #Store frame specific things so you don't need to call it multiple times
                self.frame_data = {'Redraw': False,
                                   'Events': pygame.event.get(),
                                   'Keys': pygame.key.get_pressed(),
                                   'MousePos': pygame.mouse.get_pos(),
                                   'MouseClick': pygame.mouse.get_pressed()}
                if self.frame_data['Keys'][pygame.K_ESCAPE]:
                    pygame.quit()
                    
                #Handle quitting and resizing window
                for event in self.frame_data['Events']:
                    if event.type == pygame.QUIT:
                        return
                    elif event.type == pygame.VIDEORESIZE:
                        self.WIDTH, self.HEIGHT = event.dict['size']
                        self.setscreen()
                        self.recalculate()
                        
                #---MAIN LOOP START---#
                
                if self.state == 'Main':
                    self.dk_core(game_time.ticks)
                
                
                
                #---MAIN LOOP END---#
                if game_time.fps:
                    pygame.display.set_caption('{} {}'.format(game_time.fps, self.cam))
                    
                if self.frame_data['Redraw']:
                    self.screen.fill((0, 0, 0))
                    self._world_draw()
                    pygame.display.flip()
    
    def _world_draw(self):
        """Draws the world background."""
        for coordinate in self.screen_coordinates:
            type, colour, location = self.screen_block_data[coordinate]
            pygame.draw.rect(self.screen, colour, (location[0], location[1], self.tilesize, self.tilesize))
    
    def get_tile_coords(self, coordinates):
        """Calculate which tile is at the coordinates."""
        click_segment = [split_num(i / self.tilesize) for i in coordinates]
        cam_data = ((self.cam.x_int, self.cam.x_float),
                    (self.cam.y_int, self.cam.y_float))
        tile = []
        for i, num in enumerate(cam_data):
            new_n_int = num[0] + click_segment[i][0]
            new_n_float = num[1] + click_segment[i][1]
            while new_n_float > 1:
                new_n_int += 1
                new_n_float -= 1
            tile.append(new_n_int)
        return tuple(tile)
        
    
    def dk_core(self, num_ticks):
        """Main game function
        Remember to multiply values by num_ticks to keep a constant speed.
        """
        
        recalculate = False
        #Camera control
        if num_ticks:
            cam_up = -int(self.frame_data['Keys'][pygame.K_w])
            cam_down = int(self.frame_data['Keys'][pygame.K_s])
            cam_left = -int(self.frame_data['Keys'][pygame.K_a])
            cam_right = int(self.frame_data['Keys'][pygame.K_d])
            
            if cam_up or cam_down or cam_left or cam_right:
                self.cam.move(cam_left + cam_right, cam_up + cam_down, num_ticks)
                recalculate = True
        
        
        
        for event in self.frame_data['Events']:
            if event.type == pygame.MOUSEBUTTONDOWN:
            
                #Click on blocks
                if event.button == 1:
                    tile_coordinates = self.get_tile_coords(self.frame_data['MousePos'])
                    self.game_data.BLOCK_TMP_START = self.game_data.BLOCK_TMP_END = tile_coordinates
                    self.game_data.BLOCK_TMP_TYPE = tile_coordinates not in self.game_data.BLOCK_TAG
                
                #Increase zoom
                if event.button == 4:
                    zoom = 1
                
                #Decrease zoom
                if event.button == 5:
                    zoom = -1
        
        #Highlighting/tagging blocks
        if self.game_data.BLOCK_TMP_START:
        
            #Commit selection to tag dictionary
            if not self.frame_data['MouseClick'][0]:
                for i in self.game_data.BLOCK_TMP:
                    try:
                        del self.screen_block_data[i]
                    except KeyError:
                        pass
                recalculate = True
                        
                self.game_data.BLOCK_TMP_START = None
                if self.game_data.BLOCK_TMP_TYPE:
                    self.game_data.BLOCK_TAG |= self.game_data.BLOCK_TMP
                else:
                    self.game_data.BLOCK_TAG -= self.game_data.BLOCK_TMP
                self.game_data.BLOCK_TMP = set()
                self.game_data.BLOCK_TMP_OLD = set()
            
            #Show the selection while dragging
            else:
                tile_coordinates = self.get_tile_coords(self.frame_data['MousePos'])
                
                #Adjust the range depending on which direction the dragging is
                if tile_coordinates[0] <= self.game_data.BLOCK_TMP_START[0]:
                    x_range = range(tile_coordinates[0], self.game_data.BLOCK_TMP_START[0] + 1)
                else:
                    x_range = range(self.game_data.BLOCK_TMP_START[0], tile_coordinates[0] + 1)
                if tile_coordinates[1] <= self.game_data.BLOCK_TMP_START[1]:
                    y_range = range(tile_coordinates[1], self.game_data.BLOCK_TMP_START[1] + 1)
                else:
                    y_range = range(self.game_data.BLOCK_TMP_START[1], tile_coordinates[1] + 1)
                
                #Rebuild list of blocks
                self.game_data.BLOCK_TMP = set((x, y) for x in x_range for y in y_range)
                self.game_data.BLOCK_TMP.add(self.game_data.BLOCK_TMP_START)
                
                #Delete the cached block data for any block updates
                difference1 = self.game_data.BLOCK_TMP_OLD - self.game_data.BLOCK_TMP
                difference2 = self.game_data.BLOCK_TMP - self.game_data.BLOCK_TMP_OLD
                for i in difference1 | difference2:
                    try:
                        del self.screen_block_data[i]
                    except KeyError:
                        pass
                recalculate = True
                self.game_data.BLOCK_TMP_OLD = self.game_data.BLOCK_TMP
        
        #Handle zooming and related camera movement
        try:
            zoom
        except UnboundLocalError:
            pass
        else:
            extend_edges_amount = 0.1
            
            #Calculate required info
            zoom_speed = self.tilesize // 10 + 1
            old_width = self.WIDTH / self.tilesize
            old_height = self.HEIGHT / self.tilesize
            
            #Update the tile size
            self.tilesize += zoom_speed * zoom
            self.tilesize = round(max(self.TILE_MIN_SIZE, min(self.tilesize, self.TILE_MAX_SIZE)))
            
            #Calculate updated info
            new_width = self.WIDTH / self.tilesize
            new_height = self.HEIGHT / self.tilesize
            move_amount = [old_width - new_width, old_height - new_height, 1]
            
            if self.frame_data['MousePos']:
            
                #Move camera at min or max zoom level
                if old_width == new_width:
                    if self.tilesize == self.TILE_MIN_SIZE:
                        #Camera speed when fully zoomed out
                        multiplier = 4
                    elif self.tilesize == self.TILE_MAX_SIZE:
                        #Camera speed when fully zoomed in
                        multiplier = -0.5
                    move_amount[0] -= ((self.frame_data['MousePos'][0] / self.WIDTH) - 0.5) * multiplier
                    move_amount[1] -= ((self.frame_data['MousePos'][1] / self.HEIGHT) - 0.5) * multiplier
                
                #Move camera when zooming
                else:
                
                    x_mouse = self.frame_data['MousePos'][0]
                    y_mouse = self.frame_data['MousePos'][1]
                    
                    #Multiply the mouse so that zooming at the edge will move outwards
                    if extend_edges_amount:
                    
                        x_mult = (x_mouse / self.WIDTH)
                        if x_mult < 0.5:
                            x_mult2 = 1 - x_mult * 2
                            x_mouse -= extend_edges_amount * x_mult2 * self.WIDTH
                        elif x_mult > 0.5:
                            x_mult2 = (x_mult - 0.5) * 2
                            x_mouse += extend_edges_amount * x_mult2 * self.WIDTH
                            
                        y_mult = (y_mouse / self.HEIGHT)
                        if y_mult < 0.5:
                            y_mult2 = 1 - y_mult * 2
                            y_mouse -= extend_edges_amount * y_mult2 * self.HEIGHT
                        elif y_mult > 0.5:
                            y_mult2 = (y_mult - 0.5) * 2
                            y_mouse += extend_edges_amount * y_mult2 * self.HEIGHT
                            
                    
                    move_amount[0] *= x_mouse / self.WIDTH
                    move_amount[1] *= y_mouse / self.HEIGHT
                
                
            self.cam.move(*move_amount)
            recalculate = True
            
        if recalculate:
            self.recalculate()
        
        
        if self.frame_data['Keys'][pygame.K_c]:
            print str(self.cam)
    
MainGame().play()
