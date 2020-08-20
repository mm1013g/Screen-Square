import sys
import os
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtCore import Qt, QTimer
import win32gui
import math
import random


class BadCube:
    def __init__(self, x):
        self.size = 40
        self.x = x
        self.y = -self.size
        self.dy = 10

    def draw(self, qp):
        qp.setPen(QPen(Qt.red, 5, Qt.SolidLine))
        qp.setBrush(QBrush(Qt.lightGray, Qt.SolidPattern))
        qp.drawRect(self.x - self.size / 2, self.y - self.size / 2, self.size, self.size)

    def update(self):
        self.y += self.dy


class Rectangle:
    def __init__(self, left, right, up, down):
        self.left_border = left
        self.right_border = right
        self.upper_border = up
        self.lower_border = down


class Bullet:
    def __init__(self, x, y, dirX, dirY, speed):
        self.size = 5
        self.x = x
        self.y = y
        self.dirX = dirX
        self.dirY = dirY
        self.speed = speed
        self.angle = math.atan2(dirY - y, dirX - x)
        self.dx = math.cos(self.angle) * self.speed
        self.dy = math.sin(self.angle) * self.speed
        self.bounce_count = 0

    def draw(self, qp):
        qp.setPen(QPen(Qt.red, 5, Qt.SolidLine))
        qp.setBrush(QBrush(Qt.red, Qt.SolidPattern))
        qp.drawEllipse(self.x - self.size / 2, self.y - self.size / 2, self.size, self.size)

    def update(self):
        self.x += self.dx
        self.y += self.dy

    def collision(self, bounds):
        for bound in bounds:
            if bound.left_border + 15 <= self.x <= bound.right_border - 15:  # If x is between wall borders
                if bound.lower_border >= self.y >= bound.upper_border:
                    self.dy *= -1
            if bound.upper_border + 15 <= self.y <= bound.lower_border - 15:
                if bound.left_border <= self.x <= bound.right_border:
                    self.dx *= -1
        return False


class PortalBullet(Bullet):
    def __init__(self, x, y, dirX, dirY, speed, color, color_string):
        super().__init__(x, y, dirX, dirY, speed)
        self.color = color
        self.spawn_type = ""
        self.color_string = color_string
        self.size = 10

    def draw(self, qp):
        qp.setPen(QPen(self.color, 5, Qt.SolidLine))
        qp.setBrush(QBrush(self.color, Qt.SolidPattern))
        qp.drawEllipse(self.x - self.size / 2, self.y - self.size / 2, self.size, self.size)

    def collision(self, bounds):
        for bound in bounds:
            if bound.left_border + self.speed <= self.x <= bound.right_border - self.speed:  # If x is between wall borders
                if bound.lower_border >= self.y >= bound.lower_border - self.speed:
                    self.spawn_portal("down")
                    return True
                elif bound.upper_border <= self.y <= bound.upper_border + self.speed:
                    self.spawn_portal("up")
                    return True
            if bound.upper_border + self.speed <= self.y <= bound.lower_border - self.speed:
                if bound.left_border <= self.x <= bound.left_border + self.speed:
                    self.spawn_portal("left")
                    return True
                elif bound.right_border - self.speed <= self.x <= bound.right_border:
                    self.spawn_portal("right")
                    return True

    def spawn_portal(self, portal_type):
        self.spawn_type = portal_type


class Portal:
    def __init__(self, x, y, direction, color):  # Qt.blue or Qt.orange
        self.x = x
        self.y = y
        self.direction = direction
        self.color = color
        if direction == "up" or direction == "down":
            self.width = 200
            self.height = 50
        else:
            self.width = 50
            self.height = 200

    def draw(self, qp):
        qp.setPen(QPen(self.color, 5, Qt.SolidLine))
        qp.setBrush(QBrush(self.color, Qt.SolidPattern))
        qp.drawRect(self.x - self.width / 2, self.y - self.height / 2, self.width, self.height)


class ScreenRunner(QMainWindow):

    def __init__(self):
        super().__init__()
        self.pressed_keys = set()

        self.rect_x = 500
        self.rect_y = 500
        self.rect_x_vel = 0
        self.rect_y_vel = 0

        self.rect_height = 100
        self.rect_width = 100
        self.rect_can_jump = False
        self.rect_wall_jump_state = ''

        self.bounds = set()
        self.gravity = 0.5

        self.bullets = list()
        self.bad_guys = list()

        self.blue_portal = None
        self.orange_portal = None

        self.space_invaders = True

        self.timer = QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.setInterval(10)
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self.rect_update)
        self.timer.start()

        self.initUI()

    def initUI(self):
        self.setGeometry(320, 180, 1920, 1080)
        self.setStyleSheet("background:transparent")
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.showFullScreen()
        self.show()

    def paintEvent(self, e):
        qp = QPainter(self)
        self.paint_player_rect(qp)
        self.paint_bullets(qp)
        self.paint_bad_guys(qp)
        self.paint_portals(qp)

    def paint_bad_guys(self, qp):
        if self.space_invaders:
            for bad_guy in self.bad_guys:
                bad_guy.draw(qp)

    def paint_player_rect(self, qp):
        qp.setPen(QPen(Qt.darkGreen, 5, Qt.SolidLine))
        qp.setBrush(QBrush(Qt.darkGreen, Qt.SolidPattern))
        qp.drawRect(self.rect_x - self.rect_width / 2, self.rect_y - self.rect_height / 2, self.rect_width,
                    self.rect_height)

    def paint_bullets(self, qp):
        for bullet in self.bullets:
            bullet.draw(qp)

    def paint_portals(self, qp):
        if self.blue_portal is not None:
            self.blue_portal.draw(qp)
        if self.orange_portal is not None:
            self.orange_portal.draw(qp)

    # def controller_update(self):
    #     events = get_gamepad()
    #     for event in events:
    #         if

    def keyPressEvent(self, e):
        key = e.key()
        # Keep track of pressed keys per frame
        self.pressed_keys.add(key)
        # Jump key Pressed Detection
        if key == Qt.Key_Space or key == Qt.Key_Up:
            self.rect_start_jump()

        # Shoot Button
        if key == Qt.Key_0:
            self.shoot_bullet()

        # Build Wall
        if key == Qt.Key_Plus:
            self.open_wall()

        if key == Qt.Key_1:
            self.spawn_badguy()

        if key == Qt.Key_PageUp:
            blue_color = QColor()
            blue_color.setRgb(0, 0, 255, 100)
            self.shoot_portal(blue_color, "blue")

        if key == Qt.Key_PageDown:
            orange_color = QColor()
            orange_color.setRgb(255, 69, 0, 100)
            self.shoot_portal(orange_color, "orange")

    def keyReleaseEvent(self, e):
        key = e.key()
        # Jump Key Released Detection
        if key == Qt.Key_Space or key == Qt.Key_Up:
            self.rect_end_jump()
        # Remove key from pressed set
        self.pressed_keys.remove(key)

    def rect_update(self):
        # Updating Window Positions
        win32gui.EnumWindows(self.update_windows, None)

        # Wall Barriers
        left_wall = self.left_wall_handler()
        right_wall = self.right_wall_handler()

        if left_wall or right_wall:
            self.rect_x_vel = 0

        # Wall Jumping
        if left_wall and self.rect_wall_jump_state != 'left':
            self.rect_can_jump = True
        elif right_wall and self.rect_wall_jump_state != 'right':
            self.rect_can_jump = True

        # Horizontal Movement Key Detection
        if Qt.Key_Left in self.pressed_keys and not left_wall:
            self.rect_x_vel = -10
        elif Qt.Key_Right in self.pressed_keys and not right_wall:
            self.rect_x_vel = 10
        elif Qt.Key_Left not in self.pressed_keys and Qt.Key_Right not in self.pressed_keys:
            self.rect_x_vel = 0
        if Qt.Key_Left in self.pressed_keys and Qt.Key_Right in self.pressed_keys:
            self.rect_x_vel = 0

        self.rect_y_vel += self.gravity
        self.rect_y += self.rect_y_vel
        self.rect_x += self.rect_x_vel

        self.floor_handler()
        self.ceiling_handler()

        for bullet in self.bullets:
            bullet.update()
            win_height = self.frameGeometry().height()
            win_width = self.frameGeometry().width()
            delete = bullet.collision(self.bounds)
            if delete:
                portalX = bullet.x
                portalY = bullet.y

                portal_object = Portal(portalX, portalY, bullet.spawn_type, bullet.color)
                if bullet.color_string == "blue":
                    self.blue_portal = portal_object
                else:
                    self.orange_portal = portal_object

                self.bullets.remove(bullet)

            # if 0 >= bullet.x or bullet.x >= win_width or bullet.y <= 0 or bullet.y >= win_height:
            #     self.bullets.remove(bullet)
            if 0 >= bullet.x or bullet.x >= win_width:
                bullet.dx *= -1
                bullet.bounce_count += 1
            if bullet.y <= 0 or bullet.y >= win_height:
                bullet.dy *= -1
                bullet.bounce_count += 1
            if bullet.bounce_count >= 5:
                self.bullets.remove(bullet)

        for bad_guy in self.bad_guys:
            bad_guy.update()

        # print(len(self.bullets))
        # Clear the bounds
        self.bounds.clear()
        self.update()

    def shoot_bullet(self):
        mouseX = self.cursor().pos().x()
        mouseY = self.cursor().pos().y()
        self.bullets.append(Bullet(self.rect_x, self.rect_y, mouseX, mouseY, 20))

    def rect_start_jump(self):
        if self.rect_can_jump:
            self.rect_y_vel = -24
            self.rect_can_jump = False
            if self.right_wall_handler():
                self.rect_wall_jump_state = 'right'
            elif self.left_wall_handler():
                self.rect_wall_jump_state = 'left'
            else:
                self.rect_wall_jump_state = 'none'

    def rect_end_jump(self):
        if self.rect_y_vel < -12:
            self.rect_y_vel = -12

    def rect_on_ground(self):
        return self.rect_y + self.rect_height / 2 >= self.frameGeometry().height()

    def ceiling_handler(self):
        for bound in self.bounds:
            if self.rect_x + self.rect_width / 2 <= bound.left_border + 15 or self.rect_x - self.rect_width / 2 >= bound.right_border - 15:
                continue
            else:
                if self.rect_y - self.rect_width / 2 <= bound.lower_border and self.rect_y + self.rect_width / 2 >= bound.lower_border + 15:
                    self.rect_y = bound.lower_border + self.rect_height / 2
                    self.rect_y_vel = 0

    def floor_handler(self):
        if self.rect_on_ground():
            self.rect_y = self.frameGeometry().height() - self.rect_height / 2
            self.rect_y_vel = 0
            self.rect_can_jump = True

        for bound in self.bounds:
            if self.rect_x + self.rect_width / 2 <= bound.left_border + 15 or self.rect_x - self.rect_width / 2 >= bound.right_border - 15:
                continue
            else:
                if self.rect_y + self.rect_height / 2 >= bound.upper_border and self.rect_y - self.rect_height / 2 <= bound.upper_border + 15:
                    self.rect_y = bound.upper_border - self.rect_height / 2
                    self.rect_y_vel = 0
                    self.rect_can_jump = True

    def left_wall_handler(self):
        # Monitor Barriers
        if self.rect_x <= self.rect_width / 2:
            return True

        # Other Bounds
        for bound in self.bounds:
            if self.rect_y >= bound.lower_border + self.rect_height / 2 or self.rect_y <= bound.upper_border - self.rect_height / 2:
                continue
            else:
                if self.rect_width / 2 + bound.right_border >= self.rect_x >= self.rect_width / 2 + bound.right_border - 15:
                    self.rect_x = bound.right_border + self.rect_width / 2
                    return True
        # Returns False if nothing detected
        return False

    def right_wall_handler(self):
        # Monitor Barriers
        if self.rect_x >= self.frameGeometry().width() - self.rect_width / 2:
            return True

        # Other Bounds
        for bound in self.bounds:
            if self.rect_y >= bound.lower_border + self.rect_height / 2 or self.rect_y <= bound.upper_border - self.rect_height / 2:
                continue
            else:
                if 15 + bound.left_border >= self.rect_x >= bound.left_border - self.rect_width / 2:
                    self.rect_x = bound.left_border - self.rect_width / 2
                    return True
        return False

    def update_windows(self, hwnd, extra):
        window_name = win32gui.GetWindowText(hwnd)
        if window_name == "wall":
            rect = win32gui.GetWindowRect(hwnd)
            left_border = rect[0]
            upper_border = rect[1]
            right_border = rect[2]
            lower_border = rect[3]
            bound = Rectangle(left_border, right_border, upper_border, lower_border)
            self.bounds.add(bound)
        elif window_name == "blue portal":
            pass
        elif window_name == "orange portal":
            pass

    def open_wall(self):
        os.startfile("wall")

    def spawn_badguy(self):
        self.bad_guys.append(BadCube(random.randint(0, self.frameGeometry().width())))

    def shoot_portal(self, color, color_string):
        mouseX = self.cursor().pos().x()
        mouseY = self.cursor().pos().y()
        self.bullets.append(PortalBullet(self.rect_x, self.rect_y, mouseX, mouseY, 20, color, color_string))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScreenRunner()
    sys.exit(app.exec_())
