const express = require('express');
const { spawn } = require('child_process');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(express.json());
app.use(cors());
app.use(express.static(path.join(__dirname, '../../../frontend')));

const GEMINI_API_KEY = "AQ.Ab8RN6Jh53dRBiZqxZ-WjSKrcX4vBZBHIpq-G68F1KDSPbWkjA";

// メモリ上のバトルセッション保持用
const sessions = {};

// 1. バトルセッション作成
app.post('/api/battle/create', (req, res) => {
    const { mode, theme, boss_hp } = req.body;
    
    // modeが 'check' の場合は単なる疎通確認用として扱う
    if (mode === 'check') {
        return res.json({ status: 'ok' });
    }

    const battleId = 'battle_' + Date.now();
    
    sessions[battleId] = {
        theme: theme || '社会の壁',
        bossHp: boss_hp || 100000,
        bossMaxHp: boss_hp || 100000
    };

    console.log(`[作成] セッションID: ${battleId}, テーマ: ${theme}`);
    res.json({ battle_id: battleId });
});

// 2. レイドバトルの意見判定エンドポイント
app.post('/api/opinion', (req, res) => {
    const { battle_id, side, text, speaker } = req.body;
    
    let session = sessions[battle_id] || { theme: '社会の壁', bossHp: 100000, bossMaxHp: 100000 };
    
    // Pythonに渡すデータをJSON文字列にして引数として渡す
    const payload = JSON.stringify({
        theme: session.theme,
        side: side,
        text: text,
        speaker: speaker
    });

    const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';
    const env = { ...process.env, GEMINI_API_KEY: GEMINI_API_KEY };

    // ai_script.py にデータを渡して実行
    const pythonProcess = spawn(pythonCommand, ['ai_script.py', payload], { env });

    let pythonData = '';
    let pythonError = '';

    pythonProcess.stdout.on('data', (data) => {
        pythonData += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        pythonError += data.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`=== Python実行エラー (終了コード: ${code}) ===`);
            console.error(pythonError);
            
            // エラー詳細をレスポンスに含めてフロントエンドで確認できるようにする
            return res.status(500).json({ 
                error: 'Pythonスクリプトの実行に失敗しました', 
                details: pythonError 
            });
        }

        try {
            // 余分な前後の空白や改行を取り除く
            const cleanData = pythonData.trim();
            const aiResult = JSON.parse(cleanData);
            
            // ダメージ計算
            const damage = aiResult.relevant !== false ? Math.round((300 + (aiResult.balance * 0.4 + aiResult.concrete * 0.3 + aiResult.feasible * 0.3) * 13) / 10) * 10 : 0;

            session.bossHp = Math.max(0, session.bossHp - damage);

            res.json({
                opinion: {
                    damage: damage,
                    relevant: aiResult.relevant ?? true,
                    balance: aiResult.balance ?? 70,
                    concrete: aiResult.concrete ?? 70,
                    feasible: aiResult.feasible ?? 70,
                    comment: aiResult.comment || "有効な意見です。"
                },
                boss_hp: session.bossHp,
                is_cleared: session.bossHp <= 0
            });

        } catch (e) {
            console.error('JSONパースエラー:', pythonData);
            res.status(500).json({ error: 'AIからの応答パースに失敗しました', raw: pythonData });
        }
    });
});

app.listen(3000, () => {
    console.log('サーバーが起動しました: http://localhost:3000');
});