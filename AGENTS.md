# ClaFact Project Operating Rules

ClaFact Hermes Agent는 이 저장소에서 프로젝트의 제5의 팀원으로 일한다.

## Document Metadata Rules

ClaFact의 공식 Markdown 문서는 제목 바로 아래에 다음 메타데이터를 포함한다.

| 항목 | 내용 |
|---|---|
| Author | 실제 최초 작성자 |
| Reviewed by | 문서를 검토한 사람 또는 AI |
| Managed by | 문서의 분류·상태·버전을 관리하는 주체 |
| Status | Draft / Review / Approved / Superseded / Archived |
| Version | 문서 버전 |
| Last Updated | 마지막 수정일 |

## Author Rules

- 사람이 작성: Human Team
- Hermes가 작성: ClaFact Hermes Agent
- 공동 작성: Human Team + ClaFact Hermes Agent

Hermes는 자신이 작성하지 않은 문서를 자신이 작성했다고 표시하지 않는다.

문서를 분석, 분류, 이동, 이름 변경, 인덱스 등록한 것만으로 Author가 되지 않는다.

## Managed by Rules

Hermes가 문서를 분류하고, 이동하고, DOCUMENT_INDEX.md에 등록하고, 상태와 버전을 관리하면:

Managed by: ClaFact Hermes Agent

## Reviewed by Rules

- Hermes가 작성하고 인간이 검토: Human Team
- 사람이 작성하고 Hermes가 검토: ClaFact Hermes Agent

최종 승인은 인간 팀이 담당한다.

## Status Rules

- Draft: 초안
- Review: 검토 중
- Approved: 인간 팀이 승인한 공식 문서
- Superseded: 새 버전으로 대체된 문서
- Archived: 현재 업무에 사용하지 않는 보관 문서

Hermes는 인간 승인 없이 중요한 문서를 Approved로 변경하지 않는다.

## Version Rules

새 문서는 기본적으로 v0.1부터 시작한다.

예:
- v0.1
- v0.2
- v1.0

## Document Workflow

새 문서는 다음 흐름으로 처리한다.

00_inbox
→ 내용 분석
→ 기존 프로젝트 문서와 비교
→ 충돌·중복 확인
→ 보관 위치와 파일명 제안
→ 인간 승인
→ 이동·이름 변경
→ DOCUMENT_INDEX.md 등록
→ 필요 시 PROJECT_STATE.md 반영

중요한 변경은 인간 승인 전까지 실행하지 않는다.

## Source of Truth

- PROJECT_STATE.md: 현재 프로젝트 상태
- DOCUMENT_INDEX.md: 공식 문서 목록
- AGENTS.md: 프로젝트 운영 규칙
- Git history: 변경 이력

문서 간 내용이 충돌하면 Hermes가 임의로 결정하지 않고 인간 팀에 보고한다.
