import cv2
import mediapipe as mp
import numpy as np
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.animation import Animation
from kivy.storage.jsonstore import JsonStore  # Модуль для сохранения прогресса на телефоне

class PushUpRPGGame(App):
    def build(self):
        # Настройка базы данных на телефоне для сохранения рекордов
        self.store = JsonStore('user_progress.json')
        
        # Загружаем вчерашний/лучший рекорд
        if self.store.exists('record'):
            self.best_wave = self.store.get('record')['wave']
            self.best_lvl = self.store.get('record')['lvl']
        else:
            self.best_wave = 1
            self.best_lvl = 1

        # Главный экран
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 1. Шапка с рекордами и текущим уровнем игрока
        self.stats_top = Label(
            text=f"⭐ ВЧЕРАШНИЙ РЕКОРД: Волна {self.best_wave}, Лвл {self.best_lvl}\n"
                 f"✨ ТВОЙ СТАТУС: Лвл 1 (0 XP) | ВОЛНА: 1",
            font_size='16sp',
            size_hint_y=0.1,
            color=(0.9, 0.9, 0, 1), # Желтый цвет
            halign='center'
        )
        layout.add_widget(self.stats_top)
        
        # 2. Окно камеры (занимает 45% экрана)
        self.camera_img = Image(size_hint_y=0.45)
        layout.add_widget(self.camera_img)
        
        # Контейнер игровой зоны
        game_zone = BoxLayout(orientation='horizontal', size_hint_y=0.45)
        
        # 3. Картинка моба
        self.mob_img = Image(source='slime.png', size_hint_x=0.4) 
        game_zone.add_widget(self.mob_img)
        
        # 4. Текст со статистикой боя и HP моба
        self.counter_label = Label(
            text="Загрузка...", 
            font_size='18sp', 
            size_hint_x=0.6,
            halign='left',
            valign='middle'
        )
        self.counter_label.bind(size=self.counter_label.setter('text_size'))
        game_zone.add_widget(self.counter_label)
        
        layout.add_widget(game_zone)

        # Прокачка игрока
        self.player_lvl = 1
        self.player_xp = 0
        self.xp_to_next_lvl = 20  # Сколько нужно опыта для 2 уровня
        self.current_wave = 1

        # База шаблонов мобов
        self.mob_templates = [
            {"name": "Слизень-Лежебока", "base_hp": 5, "image": "slime.png", "xp": 10},
            {"name": "Гоблин-Торопыга", "base_hp": 10, "image": "goblin.png", "xp": 20},
            {"name": "Каменный Голем", "base_hp": 15, "image": "golem.png", "xp": 35},
            {"name": "Орк-Надзиратель", "base_hp": 25, "image": "orc.png", "xp": 60}
        ]
        
        self.current_mob_index = 0
        self.stage = None  
        
        # Генерируем первого моба для 1-й волны
        self.spawn_mob()

        # Настройка камеры и ИИ
        self.capture = cv2.VideoCapture(0)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_drawing = mp.solutions.drawing_utils

        Clock.schedule_interval(self.update, 1.0 / 30.0)
        return layout

    def spawn_mob(self):
        """Создание моба с учетом текущей волны (каждая волна увеличивает HP)"""
        template = self.mob_templates[self.current_mob_index]
        
        # С каждой новой волной HP моба растет на 20%
        hp_multiplier = 1.0 + (self.current_wave - 1) * 0.2
        calculated_hp = int(template["base_hp"] * hp_multiplier)
        
        self.current_mob = {
            "name": template["name"],
            "max_hp": calculated_hp,
            "current_hp": calculated_hp,
            "image": template["image"],
            "xp": template["xp"]
        }
        
        # Меняем картинку на экране
        self.mob_img.source = self.current_mob["image"]
        self.update_ui_text("Новый враг! В бой!")

    def animate_damage(self):
        anim = Animation(size_hint_x=0.2, size_hint_y=0.2, opacity=0.5, duration=0.1)
        anim += Animation(size_hint_x=0.4, size_hint_y=1.0, opacity=1.0, duration=0.15)
        anim.start(self.mob_img)

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c-b, c-b) - np.arctan2(a-b, a-b)
        angle = np.abs(radians*180.0/np.pi)
        return 360 - angle if angle > 180.0 else angle

    def update_ui_text(self, status_msg):
        # Обновляем верхнюю панель статуса
        self.stats_top.text = (
            f"⭐ ВЧЕРАШНИЙ РЕКОРД: Волна {self.best_wave}, Лвл {self.best_lvl}\n"
            f"✨ ТВОЙ СТАТУС: Лвл {self.player_lvl} ({self.player_xp}/{self.xp_to_next_lvl} XP) | ВОЛНА: {self.current_wave}"
        )
        
        # Обновляем панель боя
        self.counter_label.text = (
            f"ВРАГ: {self.current_mob['name']}\n"
            f"HP ВРАГА: {self.current_mob['current_hp']} / {self.current_mob['max_hp']}\n"
            f"Награда: +{self.current_mob['xp']} XP\n\n"
            f"Статус: {status_msg}"
        )

    def add_xp(self, amount):
        """Логика добавления опыта и повышения уровня"""
        self.player_xp += amount
        while self.player_xp >= self.xp_to_next_lvl:
            self.player_xp -= self.xp_to_next_lvl
            self.player_lvl += 1
            self.xp_to_next_lvl = int(self.xp_to_next_lvl * 1.5) # Следующий лвл требует больше XP
            
        # Проверяем и сохраняем новый рекорд, если он побит
        if self.current_wave > self.best_wave or (self.current_wave == self.best_wave and self.player_lvl > self.best_lvl):
            self.store.put('record', wave=self.current_wave, lvl=self.player_lvl)

    def update(self, dt):
        success, frame = self.capture.read()
        if not success:
            return

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)

        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            try:
                landmarks = results.pose_landmarks.landmark
                shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x, landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].y]
                elbow = [landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW].x, landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW].y]
                wrist = [landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST].x, landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST].y]
                
                angle = self.calculate_angle(shoulder, elbow, wrist)
                
                if angle < 90 and self.stage != "down":
                    self.stage = "down"
                    self.update_ui_text("Внизу! Толкай вверх!")

                if angle > 160 and self.stage == 'down':
                    self.stage = "up"
                    
                    self.current_mob["current_hp"] -= 1
                    self.animate_damage()
                    
                    if self.current_mob["current_hp"] <= 0:
                        # Даем награду за убийство
                        self.add_xp(self.current_mob["xp"])
                        
                        # Переходим к следующему мобу
                        self.current_mob_index += 1
                        
                        # БЕСКОНЕЧНЫЙ ЦИКЛ: Если прошли всех 4 мобов, начинаем новый круг
                        if self.current_mob_index >= len(self.mob_templates):
                            self.current_mob_index = 0
                            self.current_wave += 1  # Повышаем волну (мобы станут сильнее)
                            
                        self.spawn_mob()
                    else:
                        self.update_ui_text("Урон нанесен! Опускайся снова.")
                        
            except Exception:
                pass

        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape, frame.shape), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.camera_img.texture = texture

    def on_stop(self):
        self.capture.release()

if __name__ == '__main__':
    PushUpRPGGame().run()
