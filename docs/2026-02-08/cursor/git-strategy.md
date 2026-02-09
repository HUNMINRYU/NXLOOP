# 🐙 Git 저장소 초기화 및 브랜치 전략 설정

> **작성일시**: 2026-02-07 01:01  
> **대상 시스템**: NEXLOOP  
> **목적**: GitHub 원격 저장소 연결 및 브랜치 전략 수립

---

## 1. 완료된 작업 요약

### 1.1 GitHub 원격 저장소 연결

- **저장소 URL**: `https://github.com/HUNMINRYU/NXLOOP.git`
- **인증 설정**: `git config credential.helper store` (보안을 위해 URL에서 토큰 제거 후 설정 완료)
- **메인 브랜치**: `main` 브랜치 최초 Push 완료

### 1.2 브랜치 구조 생성

- **개발 브랜치**: `develop` 브랜치 생성 및 원격 Push 완료 (`-u origin develop`)
- **현재 활성 브랜치**: `develop`

---

## 2. 브랜치 전략 (Git Flow 기반)

현재 저장소는 **안정성**과 **지속적 개발**을 위해 이중 브랜치 구조를 유지합니다.

| 브랜치    | 역할                                          | 상응 원격 브랜치 |
| --------- | --------------------------------------------- | ---------------- |
| `main`    | **프로덕션** (배포용, 가장 안정적인 상태)     | `origin/main`    |
| `develop` | **개발** (새로운 기능이 통합되는 통합 브랜치) | `origin/develop` |

---

## 3. 권장 개발 워크플로우

### ① 기능 개발 (Feature Branch)

```bash
# develop 브랜치에서 시작
git checkout develop
git pull origin develop

# 새 기능 브랜치 생성
git checkout -b feature/기능명
```

### ② 작업 완료 후 통합

```bash
# 기능 브랜치에서 커밋
git add .
git commit -m "feat: 기능 설명"

# develop 브랜치로 병합
git checkout develop
git merge feature/기능명
git push origin develop

# 기능 브랜치 삭제
git branch -d feature/기능명
```

### ③ 프로덕션 배포

```bash
# develop의 검증된 코드를 main으로 통합
git checkout main
git merge develop
git push origin main
```

---

## 4. 기술 인사이트 (Technical Insights)

- **보안 설정**: 초기 Push 시 보안 토큰을 URL에 포함했으나, 설정 직후 `git remote set-url`을 통해 표준 HTTPS URL로 원복하였습니다. 이제 인증은 `~.git-credentials`에 저장된 정보로 수행됩니다.
- **Upstream 추적**: `-u` 플래그를 사용하여 로컬 브랜치와 원격 브랜치를 연결했습니다. 이후에는 `git push` 또는 `git pull` 명령어만으로 자동으로 대상 브랜치가 지정됩니다.
- **배포 자동화 준비**: `main`과 `develop`이 분리되어 있어, 향후 Cloud Build 트리거를 브랜치별로 다르게 설정(예: main은 Production, develop은 Staging 배포)할 수 있는 기반이 마련되었습니다.

---

## 5. 상태

**진행 상태**: ✅ 초기화 완료 (2026-02-07 01:01)

---

## 6. 2026-02-09 추가 메모 (운영 관점)

- 실제 작업은 `develop`에서 바로 진행하기보다, **feature 브랜치에서 커밋을 만든 뒤 `develop`로 통합**하는 흐름이 유지되면 안전합니다.
- 최종 반영은 아래 3단계로 정리하면 실수가 줄어듭니다.

```bash
# 1) feature 브랜치에서 커밋
git add .
git commit -m "feat: ..."

# 2) develop로 통합
git checkout develop
git merge feature/기능명

# 3) 원격 develop 업데이트
git push origin develop
```
