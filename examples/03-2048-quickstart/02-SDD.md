# 처리와 저장
F01·F03은 setup에서 저장 문자열을 파싱해 Grid를 복원한다. 저장값이 없으면 두 번 생성한다. 위치는 x열 우선으로 빈 칸을 열거한 뒤 무작위 선택한다. 값은 난수가 0.9 미만이면 2, 그 밖에는 4다.
F02의 키 입력은 방향 번호로 변환된다. 이동하는 쪽 끝부터 순회한다. 한 턴에 이미 합쳐진 타일은 다시 합칠 수 없다. 실제 이동이 발생하면 빈 칸 하나에 타일을 추가하고 더 움직일 수 있는지 검사한다.
F04의 계속하기는 메모리 플래그와 화면만 갱신한다. 다음 유효 이동 시 serialize가 실행된다. F05 패배는 최고 점수를 먼저 갱신하고 진행판만 삭제한다. 화면은 이후 애니메이션 프레임에서 그린다.
브라우저 저장소를 사용할 수 없으면 메모리 저장소로 대체한다. 손상된 JSON은 getGameState의 JSON.parse에서 예외가 전파된다. 이 두 예외는 코드 확인 범위다.

[GameManager](https://github.com/gabrielecirulli/2048/blob/478b6ec346e3787f589e4af751378d06ded4cbbc/js/game_manager.js) · [입력](https://github.com/gabrielecirulli/2048/blob/478b6ec346e3787f589e4af751378d06ded4cbbc/js/keyboard_input_manager.js) · [저장소](https://github.com/gabrielecirulli/2048/blob/478b6ec346e3787f589e4af751378d06ded4cbbc/js/local_storage_manager.js) · [프레임 갱신](https://github.com/gabrielecirulli/2048/blob/478b6ec346e3787f589e4af751378d06ded4cbbc/js/html_actuator.js)
