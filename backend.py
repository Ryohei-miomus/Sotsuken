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

    if request.battle_id not in battles:
        return {
            "error": "battle not found"
        }

    if request.side not in ["A", "B"]:
        return {
            "error": "side must be A or B"
        }

    opinion = {
        "side": request.side,
        "text": request.text
    }

    if request.battle_id not in opinions:
        opinions[request.battle_id] = []

    opinions[request.battle_id].append(opinion)

    battles[request.battle_id]["opinion_count"] += 1

    return {
        "message": "opinion added",
        "opinion": opinion,
        "opinion_count": battles[request.battle_id]["opinion_count"]
    }
