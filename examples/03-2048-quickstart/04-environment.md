# 기준과 재현
2026-11-25, macOS 27.0.1 / arm64, Node v22.23.3. 브라우저 캡처는 OpenBot 내장 브라우저 800×900, DPR 1. 번들은 478b6ec346e3787f589e4af751378d06ded4cbbc의 원본 JS 네 파일과 MIT 고지를 포함한다. JS에는 플랫폼 전용 빌드가 없다. 파일별 SHA-256은 03-files.json에 있다.
  
공식 서비스 play2048.co의 응답 HTML SHA-256은 3d533fede091f6338845a155b08c3a1bb866a70495b5fcaeb536dd167596e804, 체크아웃의 index.html은 7a76f74c23aeb8ee6af73ff796343834b82f75271a610b7174a8ea6707cc8c77이다. 화면과 동작은 고정 소스를 로컬 HTTP로 실행해 확인했다. 서비스 배포의 게임 로직 버전은 미확인이다.
  
원본 엔진 대조는 이 폴더에서 아래 한 줄을 실행한다. 별도 패키지 설치나 네트워크가 필요 없다.

```sh
node 07-compare.cjs upstream
```
  
화면 재현은 새 임시 폴더의 game/에 [기준 소스](https://github.com/gabrielecirulli/2048/tree/478b6ec346e3787f589e4af751378d06ded4cbbc)를 풀고 같은 임시 폴더에 04-fixture.html을 복사한다. 그 폴더에서 python3 -m http.server 8000 --bind 127.0.0.1 을 실행한다. 새 브라우저 프로필에서 /game/은 정상 시작, /04-fixture.html은 1024 두 개를 넣고 게임으로 이동한다. 이 상태에서 왼쪽 화살표를 누른다. 브라우저의 신규 타일 위치는 무작위다. 엔진 시험에서는 난수를 0으로 고정한다.
