# 재현 범위표

|기능|원본 심볼|06 근거 ID = 07 테스트 ID|실제 화면|
|---|---|---|---|
|F01|GameManager.setup|start|05-start.png|
|F02|GameManager.move|pair, once, two-pairs, blocked|05-win.png (승리 병합)|
|F03|LocalStorageManager.getGameState / GameManager.restart|persist, restart|승리 상태 복원 실측|
|F04|GameManager.keepPlaying / HTMLActuator.message|win-hold, continue-reload, continue-move|05-win.png|
|F05|GameManager.movesAvailable / actuate|loss|엔진 실측|
  
01·02·08~12는 위 ID와 동작을 참조한다. 04의 환경은 전 기능 공통이다. 06-engine.jsonl의 trace는 07에서 엄격한 순서와 값으로 비교한다. 06-browser.json은 별도의 브라우저 관찰이다.
  
**남은 확인** 모바일 스와이프·키 동의어·저장소 차단은 기기/브라우저별 입력을 재생해야 한다. 서비스 사이트의 배포 커밋은 공개 HTML만으로 식별하지 못했다. 같은 빌드의 매니페스트가 필요하다. 시각 픽셀 차이는 자동 비교하지 않았다.
