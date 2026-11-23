# 작업 스케줄러가 부르는 실행 래퍼 — ifo 업황지수를 받아 저장소에 올린다.
#
# ifo 는 GitHub 런너에서 들쭉날쭉하다. 사무소 IP 로는 늘 내려오므로
# 여기서 받아 data/ifo.json 으로 올리고, 런너는 막히는 판에서 그것을
# 읽는다. 까닭은 tools/ifo_snapshot.py 머리말에 있다.
#
# 손으로 돌려도 된다:  powershell -ExecutionPolicy Bypass -File run_ifo.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# 이 저장소에는 가상환경이 없다 — 빌드는 본디 런너에서 돌기 때문이다.
# 시스템 Python 을 쓴다(requests·openpyxl 이 이미 들어 있다).
$python = "C:\Users\BOKFFM\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) { throw "Python 이 없습니다: $python" }

$env:PYTHONIOENCODING = "utf-8"

# 혼자 도는 일이라 자취를 남긴다. 저장소 밖에 둔다 — 안에 두면 git 에 걸린다.
$log = "D:\Claude\Projects\_운영\ifo-snapshot.log"
& $python "$root\tools\ifo_snapshot.py" @args 2>&1 |
    Tee-Object -FilePath $log -Append
exit $LASTEXITCODE
