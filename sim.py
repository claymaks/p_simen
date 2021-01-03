import math
import time
import random

import pygame
from pygame.locals import (
    K_UP,K_w,
    K_DOWN,K_s,
    K_LEFT,K_a,
    K_RIGHT,K_d,
    QUIT,
    KEYDOWN,
    K_MINUS, K_EQUALS, K_PLUS
)

from defaults import (
  W,H,
  ACCEL, DT
)

def distance(a, b):
    return ((b[0] - a[0])**2 + (b[1] - a[1])**2)**.5

def norm(v, scale=1):
    d = (v[0]**2 + v[1]**2)**.5
    return ((v[0] / d) * scale, (v[1] / d) * scale)


class Point(object):
    def __init__(self, x, y):
        self.clicked = False
        self.near = False
        
        self.x_i = x
        self.y_i = y

        self.x_i_1 = x
        self.y_i_1 = y
        
        self.x_f = H // 2
        self.y_f = W // 2

        self.a = 0
        self.v_x = 0
        self.v_y = 0
        
    def update(self, _map):
        if not self.clicked and self.a == 0:
            return
        
        d = distance((self.x_i, self.y_i), (self.x_f, self.y_f))
        v = (self.v_x**2 + self.v_y**2)**.5
        if d < 2 and v < 7.07:
            self.a = 0
            self.v_x = 0
            self.v_y = 0
            return

        # determine if speeding up or slowing down is required
        self.a = ACCEL
        v = (self.v_x**2 + self.v_y**2)**.5
        if self.a != 0 and v**2 / (2 * self.a) > d:
            self.a = -ACCEL

        # update old points
        (self.x_i_1, self.y_i_1) = (self.x_i, self.y_i)
        
        # calculate acceleration direction
        a_x, a_y = norm((self.x_f - self.x_i, self.y_f - self.y_i), self.a)

        # update position
        self.x_i += (self.v_x * DT) + (0.5 * a_x * DT**2)
        self.y_i += (self.v_y * DT) + (0.5 * a_y * DT**2)

        # update velocity
        self.v_x += a_x * DT
        self.v_y += a_y * DT

        # update 4-plot position
        _map.insert(self)
        

        
            
        

class Map(object):
    def __init__(self, size, subdivide=100):
        # initialize 4-plot position
        self.pxpy_map = [[set() for x in range((size[1]//subdivide) + 2)] for y in range((size[0]//subdivide) + 2)]
        self.pxny_map = self.pxpy_map.copy()
        self.nxpy_map = self.pxpy_map.copy()
        self.nxny_map = self.pxpy_map.copy()

        self.sub = subdivide

    def get_group(self, y, x):
        """Create set of agents in 4-plot area."""
        group = []
        p = (int(y)//self.sub + 1, int(x)//self.sub + 1)
        n = (int(y)//self.sub, int(x)//self.sub)

        group += self.pxpy_map[p[0]][p[1]]
        group += self.pxny_map[p[0]][n[1]]
        group += self.nxpy_map[n[0]][p[1]]
        group += self.nxny_map[n[0]][n[1]]

        return set(group)

    def insert(self, point, check=True):
        """Remove agent from old plots, reinsert into new."""
        
        p0 = (int(point.y_i_1)//self.sub + 1, int(point.x_i_1)//self.sub + 1)
        n0 = (int(point.y_i_1)//self.sub, int(point.x_i_1)//self.sub)

        p1 = (int(point.y_i)//self.sub + 1, int(point.x_i)//self.sub + 1)
        n1 = (int(point.y_i)//self.sub, int(point.x_i)//self.sub)

        if check and p0 == p1 and n0 == n1:
            return

        self.pxpy_map[p0[0]][p0[1]].discard(point)
        self.pxny_map[p0[0]][n0[1]].discard(point)
        self.nxpy_map[n0[0]][p0[1]].discard(point)
        self.nxny_map[n0[0]][n0[1]].discard(point)
        
        self.pxpy_map[p1[0]][p1[1]].add(point)
        self.pxny_map[p1[0]][n1[1]].add(point)
        self.nxpy_map[n1[0]][p1[1]].add(point)
        self.nxny_map[n1[0]][n1[1]].add(point)
        
        

class Environment(object):
    def __init__(self, size=(W,H), agent=Point, caption: str="Environment") -> None:
        self.size = size

        pygame.init()
        pygame.display.set_caption(caption)
        self.display = pygame.display.set_mode(size)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font('freesansbold.ttf', 16)

        self.agent = agent
        self.agents = []

        self.map = Map(size)
        
        self.display.fill((255, 255, 255))
        for _ in range(100):
            x = random.randint(0,size[1])
            y = random.randint(0,size[0])
            self.agents.append(self.agent(x, y))
            self.map.insert(self.agents[-1], check=False)
            
            pygame.draw.circle(self.display, (0, 0, 255), (y, x), 10)
            pygame.display.update()
        

    def update(self):
        list(map(lambda x: x.update(self.map), self.agents))
        

    def draw(self, objs):
        self.display.fill((255, 255, 255))
        
        for cmd,arg in objs:
            cmd(*arg)
            
        for agent in self.agents:
            color = (255,0,0) if agent.clicked else (255, 100, 100) if agent.near else (0,0,255)
            pygame.draw.circle(self.display, color, (int(agent.y_i), int(agent.x_i)), 10)
        pygame.display.update()

    def run(self):
        mouse_lock = False
        
        last_agent = None
        near_agents = set()
        last_near_agents = set()
        objs = []
        
        fps_0 = time.time()
        fps_1 = 60.0 # best estimate
        count = 100
        
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
            keys = pygame.key.get_pressed()

            if keys[K_UP] or keys[K_w]:
                pass
            if keys[K_DOWN] or keys[K_s]:
                pass
            if keys[K_LEFT] or keys[K_a]:
                pass
            if keys[K_RIGHT] or keys[K_d]:
                pass
            if last_agent:
                objs = [((pygame.draw.circle, (self.display, (0,0,0), (int(last_agent.y_i), int(last_agent.x_i)), self.map.sub, 3)))]


            # this code needs to be reformatted, too much is duplicated
            if pygame.mouse.get_pressed()[0] and not mouse_lock:
                mouse_lock = True
                min_dist = math.inf
                min_agent = None
                near_agents = self.map.get_group(*pygame.mouse.get_pos())
                if len(near_agents) > 0:
                    for agent in last_near_agents:
                        agent.near = False
                    last_near_agents = near_agents
                for agent in near_agents:
                    d = distance((agent.y_i, agent.x_i), pygame.mouse.get_pos())
                    if d <= self.map.sub:
                        agent.near = True
                    if d < 10:
                        if d < min_dist:
                            min_dist = d
                            min_agent = agent
                
                if min_agent:
                    if last_agent:
                        last_agent.clicked = False
                    last_agent = min_agent
                    min_agent.clicked = True
                objs = [((pygame.draw.circle, (self.display, (0,0,0), pygame.mouse.get_pos(), self.map.sub, 3)))]

            elif last_agent is not None:
                near_agents = self.map.get_group(last_agent.y_i, last_agent.x_i)
                if len(near_agents) > 0:
                    for agent in last_near_agents:
                        agent.near = False
                    last_near_agents = near_agents
                    for agent in near_agents:
                        d = distance((agent.y_i, agent.x_i), (last_agent.y_i, last_agent.x_i))
                        if d <= self.map.sub:
                            agent.near = True
                
            if not pygame.mouse.get_pressed()[0] and mouse_lock:
                mouse_lock = False

            text = self.font.render(f"{round(100/(fps_1), 1)} FPS", True, (0,0,0), (255,255,255))
            objs.append((self.display.blit, (text, (0,0))))
            if count == 100:
                fps_1 = time.time() - fps_0
                fps_0 = time.time()
                count = 0
                
            self.update()
            self.draw(objs)
            count += 1
            
        pygame.quit()

        
if __name__ == "__main__":
    app = Environment()
    app.run()
