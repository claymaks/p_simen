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

RAD = 10

def compare_uv(uv1, uv2, error=.1):
    err_sum = abs(uv1[0] - uv2[0]) + abs(uv1[1] - uv2[1])
    return err_sum < error, err_sum

def collide(p1, p2):
    # https://en.wikipedia.org/wiki/Elastic_collision
    d2 = distance((p1.x_i, p1.y_i), (p2.x_i, p2.y_i))**2
    p1vx = (((p1.v_x - p2.v_x) * (p1.x_i - p2.x_i)) / d2) * (p1.x_i - p2.x_i)
    p1vy = (((p1.v_y - p2.v_y) * (p1.y_i - p2.y_i)) / d2) * (p1.y_i - p2.y_i)

    p2vx = (((p2.v_x - p1.v_x) * (p2.x_i - p1.x_i)) / d2) * (p2.x_i - p1.x_i)
    p2vy = (((p2.v_y - p1.v_y) * (p2.y_i - p1.y_i)) / d2) * (p2.y_i - p1.y_i)

    return ((p1vx, p1vy), (p2vx, p2vy))
    
def distance(a, b):
    return ((b[0] - a[0])**2 + (b[1] - a[1])**2)**.5

def norm(v, scale=1):
    d = (v[0]**2 + v[1]**2)**.5
    if d == 0: return (0, 0)
    return ((v[0] / d) * scale, (v[1] / d) * scale)


class Point(object):
    def __init__(self, x, y):
        self.clicked = False
        self.near = False
        
        self.x_i = x
        self.y_i = y

        self.x_i_1 = x
        self.y_i_1 = y

        self.target = False
        self.x_f = random.randint(0, H)  # H // 2
        self.y_f = random.randint(0, W)  # W // 2

        self.a = 0
        self.v_x = 0
        self.v_y = 0
        
    def update(self, _map):
        if not self.clicked and self.a == 0:
            return

        if self.target:
            self.a = ACCEL
        
        d = distance((self.x_i, self.y_i), (self.x_f, self.y_f))
        v = (self.v_x**2 + self.v_y**2)**.5
        if (self.target and d < 5 and v < 7.07) or \
           (not self.target and v < 1):
            self.target = False
            self.a = 0
            self.v_x = 0
            self.v_y = 0
            return

        # determine if speeding up or slowing down is required
        v = (self.v_x**2 + self.v_y**2)**.5
        if self.target and self.a != 0 and v**2 / (2 * self.a) > d and \
           compare_uv(norm((self.v_x, self.v_y)), norm((self.x_f - self.x_i, self.y_f - self.y_i)))[0]:
            self.a = -ACCEL
        elif self.target and self.a !=0:
            self.a = ACCEL
        
        # calculate acceleration direction
        if self.target:
            a_x, a_y = norm((self.x_f - self.x_i, self.y_f - self.y_i), self.a)
        else:
            a_x, a_y = norm((self.x_i - self.x_i_1, self.y_i - self.y_i_1), self.a)

        # update old points
        (self.x_i_1, self.y_i_1) = (self.x_i, self.y_i)

        # update position
        self.x_i += (self.v_x * DT) + (0.5 * a_x * DT**2)
        self.y_i += (self.v_y * DT) + (0.5 * a_y * DT**2)

        # update velocity
        self.v_x += a_x * DT
        self.v_y += a_y * DT

        # bounce off edge
        if self.x_i < 0:
            self.x_i = 0
            self.v_x = -self.v_x
        elif self.x_i > H:
            self.x_i = H
            self.v_x = -self.v_x

        if self.y_i < 0:
            self.y_i = 0
            self.v_y = -self.v_y
        elif self.y_i > W:
            self.y_i = W
            self.v_y = -self.v_y

        # expand this to handle multiple collisions later
        collision = None
        potential = _map.get_group(self.y_i, self.x_i)
        potential.discard(self)
        for obj in potential:
            if distance((self.x_i, self.y_i), (obj.x_i, obj.y_i)) <= 2 * RAD:
                collision = obj
                break
        if not collision:
            _map.insert(self)
            return

        v2, v1 = collide(self, collision)
        (self.v_x, self.v_y) = (v1[0], v1[1])
        (collision.v_x, collision.v_y) = (v2[0], v2[1])
        
        if collision.a == 0:
            collision.a = -ACCEL

        offset = distance((self.x_i, self.y_i), (obj.x_i, obj.y_i)) - (RAD * 2)
        offsets = norm((collision.x_i - self.x_i, collision.y_i - self.y_i), 0.1 + offset)
        collision.x_i -= offsets[0]
        collision.y_i -= offsets[1]
        
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
        try:
            group = []
            p = (int(y)//self.sub + 1, int(x)//self.sub + 1)
            n = (int(y)//self.sub, int(x)//self.sub)

            group += self.pxpy_map[p[0]][p[1]]
            group += self.pxny_map[p[0]][n[1]]
            group += self.nxpy_map[n[0]][p[1]]
            group += self.nxny_map[n[0]][n[1]]
        except IndexError as e:
            print(f"get: {e}")
            print(f"\t{x},{y}")
            print(f"\tp: {p}")
            print(f"\tn: {n}")

        return set(group)

    def insert(self, point, check=True):
        """Remove agent from old plots, reinsert into new."""
        try:
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
        except IndexError as e:
            print(f"insert: {e}")
            print(f"\t{x},{y}")
            print(f"\tp0: {p0}")
            print(f"\tn0: {n0}")
            print(f"\tp1: {p1}")
            print(f"\tn1: {n1}")

class Environment(object):
    def __init__(self, agent, size=(W,H), caption: str="Environment") -> None:
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
            
            pygame.draw.circle(self.display, (0, 0, 255), (y, x), RAD)
            pygame.display.update()
        

    def update(self):
        list(map(lambda x: x.update(self.map), self.agents))
        

    def draw(self, objs):
        self.display.fill((255, 255, 255))
        
        for cmd,arg in objs:
            cmd(*arg)
            
        for agent in self.agents:
            color = (255,0,0) if agent.clicked else (255, 100, 100) if agent.near else (0,0,255)
            pygame.draw.circle(self.display, color, (int(agent.y_i), int(agent.x_i)), RAD)
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
                    min_agent.target = True
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
    app = Environment(Point)
    app.run()
