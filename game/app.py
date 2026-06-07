import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Push-Up RPG Live", layout="centered")
st.title("🏋️‍♂️ RPG Отжимания: РЕАЛЬНОЕ ВРЕМЯ")

# Инициализация игровых переменных (для хранения на сервере)
if 'player_lvl' not in st.session_state:
    st.session_state.player_lvl = 1
    st.session_state.current_wave = 1

st.subheader(f"✨ ТВОЙ СТАТУС: Уровень {st.session_state.player_lvl} | ВОЛНА: {st.session_state.current_wave}")

# Встраиваем JavaScript + HTML5, который будет крутить MediaPipe прямо в браузере смартфона
html_code = """
<!DOCTYPE html>
<html>
<head>
    <!-- Подключаем MediaPipe и OpenCV.js напрямую в телефон -->
    <script src="https://jsdelivr.net" crossorigin="anonymous"></script>
    <script src="https://jsdelivr.net" crossorigin="anonymous"></script>
    <script src="https://jsdelivr.net" crossorigin="anonymous"></script>
    
    <style>
        body { font-family: sans-serif; text-align: center; background: #f0f2f6; margin: 0; padding: 10px; }
        #container { display: flex; flex-direction: column; align-items: center; }
        #game-ui { display: flex; justify-content: space-around; width: 100%; max-width: 500px; background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .stat-box { text-align: center; }
        .mob-title { font-size: 20px; font-weight: bold; color: #ff4b4b; }
        .hp-text { font-size: 18px; font-weight: bold; color: #333; }
        .status-text { font-size: 16px; font-weight: bold; color: #007bff; margin: 5px 0; }
        #video-container { position: relative; width: 100%; max-width: 480px; aspect-ratio: 4/3; }
        video, canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 10px; transform: scaleX(-1); }
    </style>
</head>
<body>

<div id="container">
    <div id="game-ui">
        <div class="stat-box">
            <div id="mob-name" class="mob-title">Слизень-Лежебока</div>
            <div id="mob-hp" class="hp-text">HP: 5 / 5</div>
        </div>
        <div class="stat-box">
            <div style="font-size: 14px; color: #666;">СЧЕТЧИК</div>
            <div id="pushup-count" style="font-size: 28px; font-weight: bold; color: #28a745;">0</div>
        </div>
    </div>
    
    <div id="status" class="status-text">Загрузка ИИ камеры... Подождите</div>

    <div id="video-container">
        <video id="webcam" autoplay playsinline></video>
        <canvas id="output_canvas"></canvas>
    </div>
</div>

<script>
    const videoElement = document.getElementById('webcam');
    const canvasElement = document.getElementById('output_canvas');
    const canvasCtx = canvasElement.getContext('2d');
    
    // Игровые переменные внутри браузера
    let counter = 0;
    let stage = "up";
    let currentMobIdx = 0;
    let wave = 1;
    
    const mobs = [
        { name: "Слизень-Лежебока", baseHp: 5 },
        { name: "Гоблин-Торопыга", baseHp: 10 },
        { name: "Каменный Голем", baseHp: 15 },
        { name: "Орк-Надзиратель", baseHp: 25 }
    ];
    
    let currentMobHp = mobs[0].baseHp;
    let maxMobHp = mobs[0].baseHp;

    function calculateAngle(p1, p2, p3) {
        let radians = Math.atan2(p3.y - p2.y, p3.x - p2.x) - Math.atan2(p1.y - p2.y, p1.x - p2.x);
        let angle = Math.abs((radians * 180.0) / Math.PI);
        if (angle > 180.0) angle = 360 - angle;
        return angle;
    }

    function onResults(results) {
        if (!results.poseLandmarks) {
            document.getElementById('status').innerText = "Встаньте боком, чтобы тело было видно";
            return;
        }

        document.getElementById('status').innerText = "ИИ активен! Отжимайтесь!";
        
        // Настройка размеров холста под видео телефона
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;

        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        
        // Рисуем скелет на экране смартфона
        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {color: '#FF0000', lineWidth: 2});
        drawLandmarks(canvasCtx, results.poseLandmarks, {color: '#00FF00', lineWidth: 1, radius: 3});

        try {
            // Точки левой стороны тела (Плечо = 11, Локоть = 13, Запястье = 15)
            const shoulder = results.poseLandmarks[11];
            const elbow = results.poseLandmarks[13];
            const wrist = results.poseLandmarks[15];

            if (shoulder && elbow && wrist) {
                const angle = calculateAngle(shoulder, elbow, wrist);

                // Логика отжиманий в реальном времени
                if (angle < 90 && stage !== "down") {
                    stage = "down";
                    document.getElementById('status').innerText = "Внизу! Вставай!";
                    document.getElementById('status').style.color = "blue";
                }
                
                if (angle > 160 && stage === "down") {
                    stage = "up";
                    counter++;
                    currentMobHp--;
                    
                    document.getElementById('pushup-count').innerText = counter;
                    document.getElementById('status').innerText = "Удар нанесен!";
                    document.getElementById('status').style.color = "green";

                    // Проверка смерти моба
                    if (currentMobHp <= 0) {
                        currentMobIdx++;
                        if (currentMobIdx >= mobs.length) {
                            currentMobIdx = 0;
                            wave++;
                        }
                        
                        let nextMob = mobs[currentMobIdx];
                        maxMobHp = Math.floor(nextMob.baseHp * (1 + (wave - 1) * 0.2));
                        currentMobHp = maxMobHp;
                        
                        document.getElementById('mob-name').innerText = nextMob.name + ` (Волна ${wave})`;
                    }
                    
                    document.getElementById('mob-hp').innerText = `HP: ${currentMobHp} / ${maxMobHp}`;
                }
            }
        } catch (err) {
            console.log(err);
        }
        canvasCtx.restore();
    }

    // Инициализация MediaPipe Pose на самом смартфоне
    const pose = new Pose({locateFile: (file) => {
        return `https://jsdelivr.net{file}`;
    }});
    
    pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });
    pose.onResults(onResults);

    // Запуск фронтальной камеры телефона внутри браузера
    const camera = new Camera(videoElement, {
        onFrame: async () => {
            await pose.send({image: videoElement});
        },
        width: 480,
        height: 360
    });
    camera.start().then(() => {
        document.getElementById('status').innerText = "Камера запущена. Встаньте в профиль!";
    });
</script>

</body>
</html>
"""

# Рендерим HTML5+JS код на весь экран
components.html(html_code, height=650, scrolling=True)
