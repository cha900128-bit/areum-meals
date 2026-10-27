아름고등학교 급식 위젯 (GitHub Pages용)

1) 이 ZIP 파일의 압축을 풉니다.
2) GitHub의 cha900128-bit/areum-meals 저장소에서 [Add file] → [Upload files]를 클릭합니다.
3) 압축을 푼 폴더 자체가 아닌 그 안의 .github, scripts, public, README.txt를 모두 선택하여 업로드합니다.
4) Commit changes를 눌러 main 브랜치에 저장합니다.
5) [Settings] → [Pages]에서 Source를 "GitHub Actions"로 변경합니다.
6) [Actions]에서 "아름고 급식 자동 갱신 및 웹사이트 게시"가 성공하는지 확인합니다.
7) 사이트 주소: https://cha900128-bit.github.io/areum-meals/

자동 갱신: GitHub 서버가 하루 네 차례 NEIS 급식 정보를 가져와 정적 JSON을 게시합니다.
  클라이언트는 외부 급식 API에 직접 접속하지 않으므로 학교 네트워크 방화벽 영향이 적습니다.
  00:00~13:59 점심, 14:00~23:59 저녁. 자정에는 다음 날 점심으로 자동 전환.
  좌우 화살표 순서: ... 전날 저녁 < 오늘 점심 < 오늘 저녁 < 내일 점심 ...

중요:
- 데이터 원본(NEIS/기타 급식 정보 제공처)에 문제가 있으면 식단이 조회되지 않을 수 있습니다.
- GitHub Actions 예약 작업은 지연될 수 있습니다.
- 공개 저장소의 예약 작업은 60일 이상 저장소 활동이 없으면 자동 중지될 수 있습니다.
- 네트워크 정책에 따라 학교에서 GitHub Pages 이외에 githubusercontent 접근을 제한할 수 있으나,
  이 버전의 급식 표시는 GitHub Pages 내 자체 JSON만 사용합니다.
- GitHub Actions 비밀변수 NEIS_API_KEY를 등록하면 공식 API 요청에 인증키를 사용할 수 있습니다(선택).
- NEIS 급식 메뉴의 알레르기 표시는 보기 편하도록 제거합니다. 알레르기 확인은 학교 공식 식단표를 이용하세요.
