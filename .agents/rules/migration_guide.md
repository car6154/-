# J-PRO 프로젝트 회사 노트북 이전 가이드 (암호: 프젝해줘)

사용자가 **"프젝해줘"**라고 요청하면 아래의 설치 및 실행 가이드를 친절하고 명확하게 안내합니다.

---

### 💻 회사 노트북 세팅 가이드 (3단계)

#### 1단계. 폴더 복사
- 집 PC의 `제이프로젝트` 폴더 전체를 USB나 클라우드(구글 드라이브 등)를 통해 회사 노트북으로 복사합니다.
- (중요: 숨김 파일인 `.env` 파일도 함께 복사되었는지 확인)

#### 2단계. 필수 라이브러리 설치 (1회만)
회사 노트북의 터미널(명령 프롬프트)에서 `제이프로젝트` 폴더로 이동 후 아래 명령어를 실행합니다:
```bash
pip install streamlit pandas requests beautifulsoup4 plotly numpy python-dotenv openpyxl google-genai
```

#### 3단계. 크롬 확장프로그램 등록 (1회만)
1. 회사 노트북 크롬 주소창에 `chrome://extensions` 입력
2. 우측 상단 **[개발자 모드]** 활성화 (ON)
3. 좌측 상단 **[압축해제된 확장 프로그램을 로드합니다]** 클릭 후 `제이프로젝트/chrome_extension` 폴더 선택

---

### 🚀 실행 명령어
```bash
python -m streamlit run app.py
```
실행 후 브라우저에서 `http://localhost:8501` 접속!
