import sys
import json
import os
from google import genai
from google.genai import types

def main():
    # 1. Node.jsから渡された引数（JSON文字列）を受け取る
    if len(sys.argv) < 2:
        print(json.dumps({"error": "引数が不足しています"}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
    except Exception as e:
        print(json.dumps({"error": f"JSONのパースに失敗しました: {str(e)}"}))
        sys.exit(1)

    theme = payload.get("theme", "社会の壁")
    side = payload.get("side", "a")
    text = payload.get("text", "")
    speaker = payload.get("speaker", "匿名")

    # 2. 環境変数からGemini APIキーを取得
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(json.dumps({"error": "APIキーが設定されていません"}))
        sys.exit(1)

    # 3. Geminiクライアントの初期化（新SDKの例）
    client = genai.Client(api_key=api_key)

    # 4. AIへのプロンプト作成
    prompt = f"""
あなたは協力型ディベートゲーム「レイドバトル」の審判AIです。
テーマ: "{theme}"
発言派閥: {side.upper()}派 ({speaker})
プレイヤーの意見: "{text}"

この意見を以下の3つの軸で0〜100点で採点し、コメントをつけてください。
- balance: 両派への配慮やバランス
- concrete: 具体性
- feasible: 実現可能性
- relevant: 解決案として成立しているか（true/false）
- comment: 日本語50字以内の評価コメント

必ず以下のJSONフォーマットのみで出力してください（マークダウンの ```json などは含めないでください）。
{{
  "relevant": true,
  "balance": 75,
  "concrete": 70,
  "feasible": 70,
  "comment": "論理的なアプローチで非常に効果的です。"
}}
"""

    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        
        # 出力テキストを取得してそのままNode.jsに返す（標準出力）
        result_text = response.text.strip()
        # 万が一マークダウンが含まれていた場合のクレンジング
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        print(result_text.strip())

    except Exception as e:
        print(json.dumps({
            "relevant": True,
            "balance": 70,
            "concrete": 70,
            "feasible": 70,
            "comment": f"API呼び出しエラー: {str(e)}"
        }))

if __name__ == "__main__":
    main()