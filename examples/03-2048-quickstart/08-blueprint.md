# 구현 청사진
|재구현 모듈|원본 → 공개 인터페이스|의존 방향·첫 검증|
|---|---|---|
|model/grid|grid.js, tile.js → cells[x][y], serialize()|순수 데이터. F01 start|
|engine/turn|game_manager.js → move(direction)|grid·난수 공급자. F02 once, two-pairs|
|storage/session|local_storage_manager.js → get/set/clearGameState, get/setBestScore|저장 어댑터. F03 persist, restart|
|ui/board|html_actuator.js → actuate(grid,metadata), continueGame()|렌더 모델. F04 win-hold, F05 loss|
|ui/input + bootstrap|keyboard_input_manager.js, application.js → move/restart/keepPlaying|사용자 이벤트가 엔진을 호출. B-win-reload로 연결|
