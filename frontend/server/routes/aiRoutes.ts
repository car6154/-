import { Router } from 'express';

export const aiRouter = Router();

// 6. Gemini AI 스마트 비딩 전략 & 견적 산출 API
aiRouter.post('/api/ai/estimate', async (req, res) => {
  const { prompt, carData } = req.body;
  try {
    const apiKey = process.env.GEMINI_API_KEY || process.env.API_KEY || '';
    if (!apiKey) {
      return res.json({
        success: true,
        model: 'rule_engine',
        estimate: '자사 평균 회전일 및 동급 엔카 시세 기준 표준 입찰을 추천합니다.'
      });
    }

    const { GoogleGenAI } = await import('@google/genai');
    const ai = new GoogleGenAI({ apiKey });
    
    const models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash'];
    let resultText = '';
    let usedModel = '';

    for (const m of models) {
      try {
        const response = await ai.models.generateContent({
          model: m,
          contents: prompt || `차량: ${JSON.stringify(carData || {})}\n동급 시세와 자사 마진 기반 최적의 비딩 전략과 매입 추천가를 간결하게 브리핑해주세요.`
        });
        if (response && response.text) {
          resultText = response.text;
          usedModel = m;
          break;
        }
      } catch (e: any) {
        console.warn(`Model ${m} failed, trying next...`, e.message);
      }
    }

    return res.json({
      success: true,
      model: usedModel || 'gemini-flash',
      estimate: resultText
    });
  } catch (err: any) {
    console.error('Gemini AI 견적 실패:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

// 8. 차얼마 API 로컬 백엔드(FastAPI 8000) 프록시
aiRouter.get('/api/chaolma/:carNo', async (req, res) => {
  const { carNo } = req.params;
  const mileage = req.query.mileage || 50000;
  try {
    const resp = await fetch(`http://127.0.0.1:8000/api/chaolma/${encodeURIComponent(carNo)}?mileage=${mileage}`);
    const data = await resp.json();
    return res.status(resp.status).json(data);
  } catch (e: any) {
    return res.status(500).json({ success: false, message: 'FastAPI 백엔드(8000) 통신 실패: ' + e.message });
  }
});
