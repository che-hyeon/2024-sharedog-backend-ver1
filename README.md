# 2024-sharedog-backend

나눠주개 백엔드 레포

## 💻 프로젝트 설정& 가상환경 실행 방법

```
# 가상환경 만들기(처음에만)
python -m venv venv
# mac
#python3 -m venv venv
```
```
#가상환경 실행(파일 열 때마다)
source venv/Scripts/activate
# mac
# source venv/bin/activate
```
```
#가상환경 킨 후
pip install django

# 서비스에 설치되 패키지 다운 받는 법
pip install -r requirements.txt
```
```
# 가상환경 종료시키기
deactivate
```

## 🎯 Commit Convention

"태그:제목"의 형태이며, : 뒤에만 space가 있음에 유의합니다. ex) Feat: 메인페이지 추가

- `Feat`: 새로운 기능을 추가할 경우
- `Fix`: 버그를 고친 경우
- `Design`: CSS 등 사용자 UI 디자인 변경
- `Docs`: 문서 수정
- `!BREAKING CHANGE`: 커다란 API 변경의 경우 (ex API의 arguments, return 값의 변경, DB 테이블 변경, 급하게 치명적인 버그를 고쳐야 하는 경우)
- `!HOTFIX`: 급하게 치명적인 버그를 고쳐야하는 경우
- `Style`: 코드 포맷 변경, 세미 콜론 누락, 코드 수정이 없는 경우
- `Refactor`: 프로덕션 코드 리팩토링, 새로운 기능이나 버그 수정없이 현재 구현을 개선한 경우
- `Comment`: 필요한 주석 추가 및 변경
- `Test`: 테스트 추가, 테스트 리팩토링(프로덕션 코드 변경 X)
- `Chore`: 빌드 태스트 업데이트, 패키지 매니저를 설정하는 경우(프로덕션 코드 변경 X)
- `Rename`: 파일 혹은 폴더명을 수정하거나 옮기는 작업만인 경우
- `Remove`: 파일을 삭제하는 작업만 수행한 경우

## 💡 PR Convetion
pr이 왜 안뜨냐 ,,
깃모지 쉽게쓰는법
npm install -g gitmoji-cli 설치
gitmoji -c 으로 깃모지,커밋메세지 입력가능

```
$ gitmoji -c
? Choose a gitmoji: 🎨 - Improve structure / format of the code.
? Enter the commit title [02/48]: [Design] #3 - 가로스크롤 개선
? Enter the commit message:
```

ex) 🎨 [Design] #3 - 가로스크롤 개선

✨ [Feature] #3 - 모달팝업 개발

| 아이콘 | 코드                 | 설명                                         | 관련 태그         |
| ------ | -------------------- | -------------------------------------------- | ----------------- |
| ✨     | `:sparkles:`         | 새로운 기능 추가                             | `Feat`            |
| 🐛     | `:bug:`              | 버그 수정                                    | `Fix`             |
| 🎨     | `:art:`              | UI 개선, 코드 스타일링 변경 (코드 품질 개선) | `Design`, `Style` |
| 💄     | `:lipstick:`         | UI, CSS 스타일링 추가 또는 변경              | `Design`          |
| 📝     | `:memo:`             | 문서 수정                                    | `Docs`            |
| 🚑     | `:ambulance:`        | 치명적인 버그 긴급 수정                      | `!HOTFIX`         |
| ♻️     | `:recycle:`          | 코드 리팩토링                                | `Refactor`        |
| ✅     | `:white_check_mark:` | 테스트 추가 또는 수정                        | `Test`            |
| 🔧     | `:wrench:`           | 설정 파일 변경                               | `Chore`           |
| 🔥     | `:fire:`             | 불필요한 파일 또는 코드 삭제                 | `Remove`          |
