from fastapi import FastAPI
from pydantic import BaseModel
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

firebase_key_json = os.environ.get("FIRE_CREDENTIALS")
if firebase_key_json:
    cred_dict = json.loads(firebase_key_json)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("raid-battle-ec1b5-firebase-adminsdk-fbsvc-f8612b9c98.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()


# バトル作成時に受け取るデータ
class BattleCreateRequest(BaseModel):
    mode: str

class OpinionRequest(BaseModel):
    battle_id: str
    side: str
    text: str

# 作成したバトルを一時的に保存する
battles = {}
options = {}

@app.get("/")
def home():
    return {
        "message": "backend is running"
    }

@app.post("/api/battle/create")
def create_battle(request: BattleCreateRequest):
    battle_id = f"battle{len(battles) + 1:03d}"
    battle = {
        "battle_id": battle_id,
        "mode": request.mode,
        "boss_hp": 10000,
        "ally_hp": 10000,
        "turn": 1,
        "opinion_count": 0
    }
    battles[battle_id] = battle
    return battle

@app.get("/api/battle/{battle_id}")
def get_battle(battle_id: str):

    if battle_id not in battles:
        return {
            "error": "battle not found"
        }
    return battles[battle_id]

@app.post("/api/opinion")
def create_opinion(request: OpinionRequest):
    doc_ref = db.collection("battles").document(request.battle_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="battle not found")
    battle_data = doc.to_dict()
    if battle_data.get("status") == "cleared":
        return {"message": "this battle is already cleared!"}
    if request.side not in ["A", "B"]:
        raise HTTPException(status_code=400, detail="side must be A or B")
    side_upper = request.side.upper()
    # Gemini APIへのプロンプト
    prompt = f"""
    以下の意見に対する「共感度や解決への貢献度」を0から100の整数で採点してください。
    出力は数字のスコアのみ（例: 85）にしてください。
    意見: {request.text}
    """
    damage = 500  # デフォルト値
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        import re
        numbers = re.findall(r'\d+', response.text)
        if numbers:
            score = int(numbers[0])
            # スコア（0〜100）に応じてダメージを算出（例: スコア×20）
            damage = max(100, score * 20)
    except Exception as e:
        print("Gemini API Error:", e)
        damage = 500
    opinion = {
        "side": side_upper,
        "text": request.text,
        "speaker": request.speaker,
        "damage": damage,
        "balance": 75,
        "concrete": 70,
        "feasible": 70,
        "comment": "Gemini APIによるAI判定です。",
        "ai": True
    }
    doc_ref.collection("opinions").add(opinion)
    current_hp = battle_data.get("boss_hp", 100000)
    new_hp = max(0, current_hp - damage)
    current_count = battle_data.get("opinion_count", 0) + 1
    new_status = "cleared" if new_hp <= 0 else "playing"
    doc_ref.update({
        "boss_hp": new_hp,
        "opinion_count": current_count,
        "status": new_status,
        "turn": battle_data.get("turn", 1) + 1
    })
    return {
        "message": "opinion added and boss attacked",
        "opinion": opinion,
        "boss_hp": new_hp,
        "opinion_count": current_count,
        "status": new_status,
        "is_cleared": new_hp <= 0
    }
