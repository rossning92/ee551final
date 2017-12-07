import os
import sys
import pygame as pg
from pygame.math import Vector2
import random
import math
from threading import Thread
import controller_facerec as controller
from pygame import surfarray


SCREEN_SIZE = (1000, 600)
CLEAR_COLOR = (20, 20, 50)
CAPTION = "Rotation Animation"


def createSpriteFrames(sheet, size, columns, rows, missing=0):
    """
    Creates a list of frames from a sprite image. The missing
    argument specifies how many empty cells (if any) there are on the
    bottom row.
    """
    total = rows * columns - missing
    frames = []
    for frame in range(total):
        y, x = divmod(frame, columns)
        frames.append(sheet.subsurface((x * size[0], y * size[1]), size))
    return frames


class Animation(pg.sprite.Sprite):
    """A class for an animated sprite."""

    cached_frames = {}

    def __init__(self, pos, size, fps, imageFile, gridSize, missing=0, loop=False):
        pg.sprite.Sprite.__init__(self)

        # Try to load sprite frames from cache
        if imageFile in Animation.cached_frames:
            frames = Animation.cached_frames[imageFile]
        else:
            img = pg.image.load(imageFile).convert_alpha()
            frameWidth = img.get_width() // gridSize[0]
            frameHeight = img.get_height() // gridSize[1]
            frames = createSpriteFrames(img, (frameWidth, frameHeight), gridSize[0], gridSize[1], missing)
            frames = [pg.transform.smoothscale(x, size) for x in frames]
            Animation.cached_frames[imageFile] = frames

        self.frames = frames
        self.frame = 0
        self.image = self.frames[self.frame]
        self.rect = self.image.get_rect(center=pos)
        self.animate_fps = fps
        self.loop = loop

    def update(self, dt):
        iNewFrame = self.frame + self.animate_fps * dt

        if not self.loop and iNewFrame > len(self.frames):
            self.kill()
            return

        self.frame = (iNewFrame) % len(self.frames)
        self.image = self.frames[int(self.frame)]


class CameraFrame(pg.sprite.Sprite):

    FRAME_SIZE = (160, 120)

    def __init__(self):
        pg.sprite.Sprite.__init__(self)
        self.image = pg.image.load('camera_loading.jpg')
        self.image = pg.transform.smoothscale(self.image, CameraFrame.FRAME_SIZE)

        self.rect = self.image.get_rect()

        self.lastFrame = None

    def update(self, dt):
        if controller.cameraFrameArray is not None:
            if self.lastFrame is not controller.cameraFrameArray:
                self.lastFrame = controller.cameraFrameArray

                # Draw camera frame
                arr = controller.cameraFrameArray
                arr = arr[..., ::-1].transpose(1, 0, 2)
                surf = surfarray.make_surface(arr)
                surf = pg.transform.smoothscale(surf, CameraFrame.FRAME_SIZE)

                self.image = surf


class Shuttle(pg.sprite.Sprite):
    def __init__(self):
        pg.sprite.Sprite.__init__(self)

        self.acceleration = 5.0
        self.pos = (100, 100)
        self.degree = 0

        # Load shuttle image
        img = pg.image.load("spacecraft.png").convert_alpha()
        img = pg.transform.rotozoom(img, 0, 0.5)
        self.shuttleImg = img
        self.image = img

        fireWidth = int(self.shuttleImg.get_width())
        fireHeight = fireWidth
        img = pg.image.load('fire_sprite.png').convert_alpha()
        sprites = createSpriteFrames(img, (64, 64), 4, 4)
        sprites = [pg.transform.smoothscale(x, (fireWidth, fireHeight)) for x in sprites]
        self.fireSprites = sprites

        self.rect = self.image.get_rect(center=(100, 100))

    def update(self, dt):

        pos = self.pos

        # Move shuttle to current mouse pos
        destPos = Vector2(pg.mouse.get_pos())

        # Update shuttle pos according to face detection result
        destPos = Vector2(controller.facePos)
        center = Vector2(0.5, 0.5)
        destPos = (destPos - center) * 2.0 + center  # Expand coordinate a little
        destPos[0] *= SCREEN_SIZE[0]
        destPos[1] *= SCREEN_SIZE[1]

        v = destPos - pos

        # Draw fire
        imageCopy = self.shuttleImg.convert_alpha()
        i = min(15, int(v.length() / 200 * 15))
        i = 15 - i
        imageCopy.blit(self.fireSprites[i], (0, self.shuttleImg.get_height() * 0.6))

        # Update rotation
        if v.length() > 20:
            self.degree = math.degrees(math.atan2(-v.y, v.x)) - 90

        imageCopy = pg.transform.rotate(imageCopy, self.degree)

        # Update position
        if v.length() > 20:
            t = dt * self.acceleration
            if t < 1.0:
                pos += v * t
            else:
                pos = destPos

        self.pos = pos
        self.rect = self.image.get_rect(center=pos)
        self.image = imageCopy

        # Check collision with asteroids
        collisions = pg.sprite.spritecollide(self, asteroids, False)
        collided = pg.sprite.spritecollideany(self, collisions, pg.sprite.collide_mask)
        if collided:
            # Create explosion animation
            rootGroup.add(Animation(pos=self.pos,
                                    size=(400, 400),
                                    fps=24,
                                    imageFile='explosions_sprite.png',
                                    gridSize=(5, 5)))
            self.kill()


class Asteroid(pg.sprite.Sprite):
    """A class for an animated spinning asteroid."""
    rotation_cache = {}

    def __init__(self, location, frame_speed=50, angular_speed=0):
        """
        The argument location is the center point of the asteroid;
        frame_speed is the speed in frames per second; angular_speed is the
        rotation speed in degrees per second.
        """
        pg.sprite.Sprite.__init__(self)
        self.frame = 0
        self.frames = createSpriteFrames(ASTEROID, (96, 80), 21, 7, missing=4)
        self.last_frame_info = None
        self.image = self.frames[self.frame]
        self.rect = self.image.get_rect(center=location)
        self.animate_fps = frame_speed
        self.angle = 0.0
        self.angular_speed = angular_speed  # Degrees per second.

        self.speed = Vector2(
            random.randint(-500, 500),
            random.randint(-500, 500))
        self.boundRect = pg.Rect((0, 0), SCREEN_SIZE)

    def get_image(self, cache=True):
        """
        Get a new image if either the frame or angle has changed. If cache
        is True the image will be placed in the rotation_cache. This can
        greatly improve speed but is only feasible if caching all the images
        would not cause memory issues.
        """
        frame_info = angle, frame = (int(self.angle), int(self.frame))
        if frame_info != self.last_frame_info:
            if frame_info in Asteroid.rotation_cache:
                image = Asteroid.rotation_cache[frame_info]
            else:
                raw = self.frames[frame]
                image = pg.transform.rotozoom(raw, angle, 1.0)
                if cache:
                    Asteroid.rotation_cache[frame_info] = image
            self.last_frame_info = frame_info
        else:
            image = self.image
        return image

    def update(self, dt):
        """Change the angle and fps based on a time delta."""
        self.angle = (self.angle + self.angular_speed * dt) % 360
        self.frame = (self.frame + self.animate_fps * dt) % len(self.frames)
        self.image = self.get_image(False)

        pos = Vector2(self.rect.center)
        pos += self.speed * dt

        if pos.x < self.boundRect.x:
            self.speed.x *= -1
            pos.x = self.boundRect.x
        if pos.y < self.boundRect.y:
            self.speed.y *= -1
            pos.y = self.boundRect.y
        if pos.x > self.boundRect.right:
            self.speed.x *= -1
            pos.x = self.boundRect.right
        if pos.y > self.boundRect.bottom:
            self.speed.y *= -1
            pos.y = self.boundRect.bottom

        self.rect = self.image.get_rect(center=pos)


class Control(object):
    """Game loop and event loop found here."""

    def __init__(self):
        global asteroids
        global rootGroup

        """Prepare the essentials and setup an asteroid group."""
        self.screen = pg.display.get_surface()
        self.screen_rect = self.screen.get_rect()
        self.done = False
        self.keys = pg.key.get_pressed()
        self.clock = pg.time.Clock()
        self.fps = 60.0

        asteroids = self.make_asteroids()

        rootGroup = asteroids.copy()
        rootGroup.add(Shuttle())
        rootGroup.add(CameraFrame())

        self.bgTile = pg.image.load('space_tile.jpg')

    def make_asteroids(self):
        """
        Arbitrary method that creates a group with four asteroids.
        A static; a rotating; an animating; and a rotating-animating one.
        """
        location_one = [loc // 4 for loc in self.screen_rect.size]
        location_two = [loc * 3 for loc in location_one]
        location_three = [location_two[0], location_one[1]]
        location_four = [location_one[0], location_two[1]]
        asteroids = [Asteroid(location_one, 20, 150),
                     Asteroid(location_two, 50, 200),
                     Asteroid(location_three, 20, 200),
                     Asteroid(location_four, 50, 150)]
        return pg.sprite.Group(asteroids)

    def event_loop(self):
        """Bare bones event loop."""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.done = True
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_r:
                    rootGroup.add(Shuttle())
                elif event.key == pg.K_q:
                    self.done = pg.QUIT

    def display_fps(self):
        """Show the program's FPS in the window handle."""
        caption = "{} - FPS: {:.2f}".format(CAPTION, self.clock.get_fps())
        pg.display.set_caption(caption)

    def main_loop(self):
        """Clean main game loop."""
        delta = 0
        while not self.done:
            self.event_loop()

            rootGroup.update(delta)

            # Rendering logic
            self.screen.fill(CLEAR_COLOR)

            # Draw background
            for x in range(0, SCREEN_SIZE[0], self.bgTile.get_width()):
                for y in range(0, SCREEN_SIZE[1], self.bgTile.get_height()):
                    self.screen.blit(self.bgTile, (x, y))

            rootGroup.draw(self.screen)

            pg.display.update()
            delta = self.clock.tick(self.fps) / 1000.0
            self.display_fps()


def main():
    """Initialize; load image; and start program."""
    global ASTEROID

    pg.init()
    os.environ["SDL_VIDEO_CENTERED"] = "TRUE"
    pg.display.set_caption(CAPTION)

    info = pg.display.Info()
    global SCREEN_SIZE
    SCREEN_SIZE = (info.current_w, info.current_h)
    pg.display.set_mode(SCREEN_SIZE)

    ASTEROID = pg.image.load("asteroid_simple.png").convert_alpha()
    Control().main_loop()
    pg.quit()
    sys.exit()


if __name__ == "__main__":
    t = Thread(target=controller.run)
    t.start()

    main()
